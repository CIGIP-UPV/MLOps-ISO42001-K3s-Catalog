"""
Edge model server (FastAPI).

Serves the model version that edge-mlflow-sync has placed in MODEL_DIR:

    MODEL_DIR/current.json            {"name", "version", "path", "features", ...}
    MODEL_DIR/versions/<name>-v<N>/   MLflow pyfunc model

Endpoints
    GET  /health    liveness (process up)
    GET  /ready     200 when a model is loaded, 503 otherwise
    GET  /version   name, version and features of the loaded model
    POST /reload    reload the version pointed to by current.json
    POST /predict   score one or more samples
    GET  /metrics   Prometheus metrics (ISO/IEC 42001 B.6.2.6.2)

Every prediction is logged to the edge data stock (table predictions) and as
a JSON line on stdout (Fluent Bit -> Loki, B.6.2.8.1).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

import mlflow.pyfunc
import pandas as pd
import psycopg2
from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/models"))
CURRENT = MODEL_DIR / "current.json"
LOG_PREDICTIONS = os.environ.get("LOG_PREDICTIONS", "true").lower() == "true"

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(message)s")
log = logging.getLogger("edge-fastapi-model")

PREDICTIONS = Counter("model_predictions_total", "Predictions served",
                      ["model_name", "model_version", "outcome"])
LATENCY = Histogram("model_prediction_latency_seconds", "Prediction latency",
                    ["model_name", "model_version"],
                    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5))
SCORE = Histogram("model_anomaly_score", "Anomaly score of served predictions",
                  ["model_name", "model_version"],
                  buckets=(-0.2, -0.1, 0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8))
INFO = Gauge("model_info", "Model version currently served (value 1)", ["model_name", "model_version"])
LOADED = Gauge("model_loaded", "1 when a model is loaded")
RELOADS = Counter("model_reloads_total", "Model reload attempts", ["result"])
LOG_ERRORS = Counter("model_prediction_log_errors_total", "Predictions not written to the edge data stock")

state: dict[str, Any] = {"model": None, "meta": None, "loaded_at": None}
lock = threading.Lock()
app = FastAPI(title="edge-fastapi-model", version="1.0.0")


def emit(event: str, **fields: Any) -> None:
    log.info(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "component": "edge-fastapi-model", "event": event, **fields}))


def load_current() -> dict:
    meta = json.loads(CURRENT.read_text())
    model = mlflow.pyfunc.load_model(str(MODEL_DIR / meta["path"]))
    with lock:
        old = state["meta"]
        state.update(model=model, meta=meta, loaded_at=time.time())
    if old:
        INFO.remove(old["name"], str(old["version"]))
    INFO.labels(meta["name"], str(meta["version"])).set(1)
    LOADED.set(1)
    return meta


@app.on_event("startup")
def startup() -> None:
    LOADED.set(0)
    if CURRENT.exists():
        try:
            meta = load_current()
            RELOADS.labels("ok").inc()
            emit("model_loaded", model_name=meta["name"], model_version=str(meta["version"]))
        except Exception as exc:  # noqa: BLE001
            RELOADS.labels("error").inc()
            emit("model_load_failed", error=str(exc))
    else:
        emit("no_model_yet", model_dir=str(MODEL_DIR))


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready(response: Response) -> dict:
    if state["model"] is None:
        response.status_code = 503
        return {"ready": False}
    return {"ready": True}


@app.get("/version")
def version() -> dict:
    meta = state["meta"]
    if meta is None:
        raise HTTPException(status_code=503, detail="no model loaded")
    return {"model_name": meta["name"], "model_version": str(meta["version"]),
            "alias": meta.get("alias"), "run_id": meta.get("run_id"),
            "features": meta.get("features"), "sha256": meta.get("sha256"),
            "loaded_at": state["loaded_at"]}


@app.post("/reload")
def reload() -> dict:
    try:
        meta = load_current()
    except Exception as exc:  # noqa: BLE001
        RELOADS.labels("error").inc()
        emit("model_reload_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"reload failed: {exc}") from exc
    RELOADS.labels("ok").inc()
    emit("model_reloaded", model_name=meta["name"], model_version=str(meta["version"]))
    return {"model_name": meta["name"], "model_version": str(meta["version"])}


class Sample(BaseModel):
    machine_id: str = Field(..., examples=["cnc-01"])
    features: dict[str, float]


class PredictRequest(BaseModel):
    samples: list[Sample]


def log_predictions(rows: list[tuple]) -> None:
    try:
        with psycopg2.connect(host=os.environ["DB_HOST"], port=os.environ.get("DB_PORT", "5432"),
                              dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
                              password=os.environ["DB_PASSWORD"], connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO predictions (machine_id, model_name, model_version, input_hash, score, label)"
                    " VALUES (%s, %s, %s, %s, %s, %s)", rows)
    except Exception as exc:  # noqa: BLE001
        LOG_ERRORS.inc()
        emit("prediction_log_failed", error=str(exc))


@app.post("/predict")
def predict(req: PredictRequest) -> dict:
    with lock:
        model, meta = state["model"], state["meta"]
    if model is None:
        raise HTTPException(status_code=503, detail="no model loaded")
    name, ver = meta["name"], str(meta["version"])
    features = meta["features"]
    missing = sorted({f for s in req.samples for f in features if f not in s.features})
    if missing:
        PREDICTIONS.labels(name, ver, "rejected").inc(len(req.samples))
        raise HTTPException(status_code=422, detail=f"missing features: {missing}")

    frame = pd.DataFrame([[s.features[f] for f in features] for s in req.samples], columns=features)
    start = time.perf_counter()
    out = model.predict(frame)
    LATENCY.labels(name, ver).observe(time.perf_counter() - start)

    results, rows = [], []
    for s, (_, r) in zip(req.samples, out.iterrows()):
        score, anomaly = float(r["score"]), bool(r["is_anomaly"])
        label = "anomaly" if anomaly else "normal"
        PREDICTIONS.labels(name, ver, label).inc()
        SCORE.labels(name, ver).observe(score)
        digest = hashlib.sha256(json.dumps(s.features, sort_keys=True).encode()).hexdigest()[:16]
        results.append({"machine_id": s.machine_id, "score": score, "label": label})
        rows.append((s.machine_id, name, ver, digest, score, label))
        emit("prediction", machine_id=s.machine_id, model_name=name, model_version=ver,
             input_hash=digest, score=round(score, 6), label=label)
    if LOG_PREDICTIONS:
        log_predictions(rows)
    return {"model_name": name, "model_version": ver, "predictions": results}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
