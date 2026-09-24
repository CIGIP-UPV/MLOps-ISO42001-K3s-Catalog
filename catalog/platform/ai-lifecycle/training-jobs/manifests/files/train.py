"""
Model training pipeline (platform).

1. Reads the consolidated sensor readings from the platform data stock
   (TimescaleDB, table sensor_readings) for the training window and turns
   them into one feature vector per machine and time bucket.
2. Trains an IsolationForest anomaly detector (zero-defect manufacturing:
   flag abnormal process states before they produce defects).
3. Checks the release criteria (minimum samples, anomaly rate bounds).
4. Logs parameters, metrics, the training frame (reference data for drift
   monitoring) and the model to MLflow, registers a new model version with
   data provenance tags and, when the criteria pass, moves the serving alias
   to it. The alias change is what edge-mlflow-sync propagates to the edge.

Environment: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
MLFLOW_TRACKING_URI, MODEL_NAME, MODEL_ALIAS, EXPERIMENT, WINDOW, BUCKET,
MIN_SAMPLES, CONTAMINATION, MAX_ANOMALY_RATE, PROMOTE, TRIGGER.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import mlflow
import mlflow.pyfunc
import numpy as np
import pandas as pd
import psycopg2
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.ensemble import IsolationForest

ENV = os.environ


def emit(event: str, **fields) -> None:
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "component": "platform-training-jobs", "event": event, **fields}), flush=True)


class AnomalyModel(mlflow.pyfunc.PythonModel):
    """Returns, for each sample, an anomaly score (higher = more abnormal) and a flag."""

    def __init__(self, estimator, features):
        self.estimator = estimator
        self.features = list(features)

    def predict(self, context, model_input, params=None):
        x = model_input[self.features]
        return pd.DataFrame({"score": -self.estimator.score_samples(x),
                             "is_anomaly": self.estimator.predict(x) == -1})


def load_frame(window: str, bucket: str) -> tuple[pd.DataFrame, dict]:
    sql = """
        SELECT time_bucket(%(bucket)s::interval, time) AS t, machine_id, signal_name, avg(value) AS value
          FROM sensor_readings
         WHERE time > now() - %(window)s::interval
         GROUP BY 1, 2, 3
    """
    prov_sql = """
        SELECT count(*), min(time), max(time), max(batch_id), array_agg(DISTINCT site_id)
          FROM sensor_readings WHERE time > now() - %(window)s::interval
    """
    with psycopg2.connect(host=ENV["DB_HOST"], port=ENV.get("DB_PORT", "5432"), dbname=ENV["DB_NAME"],
                          user=ENV["DB_USER"], password=ENV["DB_PASSWORD"], connect_timeout=10) as conn:
        long = pd.read_sql(sql, conn, params={"bucket": bucket, "window": window})
        with conn.cursor() as cur:
            cur.execute(prov_sql, {"window": window})
            rows, t_min, t_max, max_batch, sites = cur.fetchone()
    provenance = {"source": f"timescaledb:{ENV['DB_NAME']}.sensor_readings", "window": window,
                  "bucket": bucket, "raw_rows": int(rows), "time_min": str(t_min), "time_max": str(t_max),
                  "max_consolidation_batch": str(max_batch), "sites": ",".join(sites or [])}
    if long.empty:
        return pd.DataFrame(), provenance
    wide = long.pivot_table(index=["t", "machine_id"], columns="signal_name", values="value").sort_index()
    wide = wide.groupby(level="machine_id").ffill().dropna(axis=0, how="any")
    wide.columns = [str(c) for c in wide.columns]
    return wide.reset_index(drop=True), provenance


def main() -> int:
    name, alias = ENV.get("MODEL_NAME", "zdm-anomaly-detector"), ENV.get("MODEL_ALIAS", "champion")
    window, bucket = ENV.get("WINDOW", "24 hours"), ENV.get("BUCKET", "10 seconds")
    min_samples = int(ENV.get("MIN_SAMPLES", "200"))
    contamination = float(ENV.get("CONTAMINATION", "0.02"))
    max_rate = float(ENV.get("MAX_ANOMALY_RATE", "0.10"))
    promote = ENV.get("PROMOTE", "true").lower() == "true"
    trigger = ENV.get("TRIGGER", "schedule")

    frame, provenance = load_frame(window, bucket)
    features = sorted(frame.columns)
    emit("training_data_loaded", samples=len(frame), features=features, **provenance)

    mlflow.set_experiment(ENV.get("EXPERIMENT", "zdm-anomaly-detection"))
    with mlflow.start_run(run_name=f"{trigger}-{time.strftime('%Y%m%dT%H%M%S')}") as run:
        mlflow.set_tags({"trigger": trigger, **{f"data.{k}": v for k, v in provenance.items()}})
        mlflow.log_params({"algorithm": "IsolationForest", "n_estimators": 200, "contamination": contamination,
                           "window": window, "bucket": bucket, "n_features": len(features),
                           "features": ",".join(features)})

        # Release criteria (B.6.1.3.4): enough data and a plausible anomaly rate.
        if len(frame) < min_samples or not features:
            mlflow.set_tag("release_criteria", "failed: not enough samples")
            mlflow.log_metric("n_samples", len(frame))
            emit("release_criteria_failed", reason="not enough samples", samples=len(frame), required=min_samples)
            return 2

        est = IsolationForest(n_estimators=200, contamination=contamination, random_state=42)
        est.fit(frame[features])
        scores = -est.score_samples(frame[features])
        rate = float(np.mean(est.predict(frame[features]) == -1))
        mlflow.log_metrics({"n_samples": len(frame), "train_anomaly_rate": rate,
                            "score_mean": float(scores.mean()), "score_std": float(scores.std())})

        with tempfile.TemporaryDirectory() as tmp:
            ref = Path(tmp) / "reference.csv"
            frame[features].to_csv(ref, index=False)
            mlflow.log_artifact(str(ref), artifact_path="reference")

        model = AnomalyModel(est, features)
        example = frame[features].head(5)
        info = mlflow.pyfunc.log_model(
            artifact_path="model", python_model=model, input_example=example,
            signature=infer_signature(example, model.predict(None, example)),
            registered_model_name=name)

        client = MlflowClient()
        mv = client.get_model_version(name, info.registered_model_version)
        for k, v in {"trigger": trigger, "train_anomaly_rate": f"{rate:.4f}",
                     "data_window": window, **{f"data.{k}": v for k, v in provenance.items()}}.items():
            client.set_model_version_tag(name, mv.version, k, str(v))

        passed = rate <= max_rate
        mlflow.set_tag("release_criteria", "passed" if passed else f"failed: anomaly rate {rate:.3f} > {max_rate}")
        client.set_model_version_tag(name, mv.version, "release_criteria", "passed" if passed else "failed")
        if passed and promote:
            client.set_registered_model_alias(name, alias, mv.version)
        emit("model_registered", model_name=name, model_version=mv.version, run_id=run.info.run_id,
             samples=len(frame), train_anomaly_rate=round(rate, 4), release_criteria=passed,
             promoted_alias=alias if (passed and promote) else None)
        return 0 if passed else 3


if __name__ == "__main__":
    sys.exit(main())
