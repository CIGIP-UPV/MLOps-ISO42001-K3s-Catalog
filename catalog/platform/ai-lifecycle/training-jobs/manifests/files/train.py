"""
Model training pipeline (platform).

1. Reads the consolidated sensor readings from the platform data stock
   (TimescaleDB, table sensor_readings) for the training window and turns
   them into one feature vector per machine and time bucket.
2. Trains an IsolationForest anomaly detector (zero-defect manufacturing:
   flag abnormal process states before they produce defects).
3. Checks the release criteria (minimum samples, anomaly rate bounds) and,
   when enough operator feedback exists, the agreement of the candidate with
   the operators: the latest verdict of each prediction (feedback interface,
   CMP-12), with the input features recorded for it, is used as a label.
4. Logs parameters, metrics, the training frame (reference data for drift
   monitoring) and the model to MLflow, registers a new model version with
   data provenance tags and, when the criteria pass, moves the serving alias
   to it. The alias change is what edge-mlflow-sync propagates to the edge.

Environment: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
MLFLOW_TRACKING_URI, MODEL_NAME, MODEL_ALIAS, EXPERIMENT, WINDOW, BUCKET,
MIN_SAMPLES, CONTAMINATION, MAX_ANOMALY_RATE, PROMOTE, TRIGGER,
FEEDBACK_MIN_LABELS, FEEDBACK_MIN_AGREEMENT.
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


def true_label(verdict: str, predicted: str, corrected: str | None) -> str | None:
    """Label given by an operator verdict: the prediction itself when it was
    judged correct, the corrected label (or the other class) when incorrect,
    and none when the operator was not sure."""
    if verdict == "correct":
        return predicted
    if verdict == "incorrect":
        return corrected or ("normal" if predicted == "anomaly" else "anomaly")
    return None


def load_feedback_labels() -> pd.DataFrame:
    """Latest verdict of each consolidated prediction, joined with its input features."""
    sql = """
        WITH latest AS (
          SELECT DISTINCT ON (site_id, prediction_source_id, prediction_time)
                 site_id, prediction_source_id, prediction_time, verdict, predicted_label, corrected_label
            FROM operator_feedback
           ORDER BY site_id, prediction_source_id, prediction_time, created_at DESC)
        SELECT l.verdict, l.predicted_label, l.corrected_label, p.features::text AS features
          FROM latest l
          JOIN predictions p ON p.site_id = l.site_id AND p.source_id = l.prediction_source_id
                            AND p.time = l.prediction_time
         WHERE p.features IS NOT NULL
    """
    try:
        with psycopg2.connect(host=ENV["DB_HOST"], port=ENV.get("DB_PORT", "5432"), dbname=ENV["DB_NAME"],
                              user=ENV["DB_USER"], password=ENV["DB_PASSWORD"], connect_timeout=10) as conn:
            rows = pd.read_sql(sql, conn)
    except Exception as exc:  # noqa: BLE001 - no feedback table yet: train without labels
        emit("feedback_labels_unavailable", error=str(exc)[:300])
        return pd.DataFrame()
    rows["label"] = [true_label(v, p, c) for v, p, c in
                     zip(rows["verdict"], rows["predicted_label"], rows["corrected_label"])]
    return rows


def evaluate_on_feedback(est, features: list[str], labels: pd.DataFrame) -> dict:
    """Agreement of the candidate with the operator labels (anomaly = positive class)."""
    usable = labels.dropna(subset=["label"])
    x_rows, y = [], []
    for feats, label in zip(usable["features"], usable["label"]):
        values = json.loads(feats)
        if all(f in values for f in features):
            x_rows.append([values[f] for f in features])
            y.append(label == "anomaly")
    result = {"feedback_verdicts": len(labels), "feedback_labels": len(y),
              "feedback_uncertain": int(labels["label"].isna().sum()) if len(labels) else 0}
    if not y:
        return result
    pred = est.predict(pd.DataFrame(x_rows, columns=features)) == -1
    y_true = np.array(y)
    tp = int(np.sum(pred & y_true))
    result["feedback_agreement"] = float(np.mean(pred == y_true))
    if pred.sum():
        result["feedback_precision_anomaly"] = tp / int(pred.sum())
    if y_true.sum():
        result["feedback_recall_anomaly"] = tp / int(y_true.sum())
    return result


def main() -> int:
    name, alias = ENV.get("MODEL_NAME", "zdm-anomaly-detector"), ENV.get("MODEL_ALIAS", "champion")
    window, bucket = ENV.get("WINDOW", "24 hours"), ENV.get("BUCKET", "10 seconds")
    min_samples = int(ENV.get("MIN_SAMPLES", "200"))
    contamination = float(ENV.get("CONTAMINATION", "0.02"))
    max_rate = float(ENV.get("MAX_ANOMALY_RATE", "0.10"))
    promote = ENV.get("PROMOTE", "true").lower() == "true"
    trigger = ENV.get("TRIGGER", "schedule")
    fb_min_labels = int(ENV.get("FEEDBACK_MIN_LABELS", "20"))
    fb_min_agreement = float(ENV.get("FEEDBACK_MIN_AGREEMENT", "0"))

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

        # Operator feedback as labels (CMP-12, B.6.2.6.4).
        labels = load_feedback_labels()
        fb = evaluate_on_feedback(est, features, labels) if len(labels) else \
            {"feedback_verdicts": 0, "feedback_labels": 0, "feedback_uncertain": 0}
        emit("feedback_labels_loaded", **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in fb.items()},
             min_labels=fb_min_labels, min_agreement=fb_min_agreement)
        mlflow.log_metrics({k: float(v) for k, v in fb.items()})
        fb_gate = fb["feedback_labels"] < fb_min_labels or fb.get("feedback_agreement", 1.0) >= fb_min_agreement

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
                     "data_window": window, **{f"data.{k}": v for k, v in provenance.items()},
                     **{f"feedback.{k.removeprefix('feedback_')}": (f"{v:.4f}" if isinstance(v, float) else v)
                        for k, v in fb.items()}}.items():
            client.set_model_version_tag(name, mv.version, k, str(v))

        passed = rate <= max_rate and fb_gate
        if rate > max_rate:
            reason = f"failed: anomaly rate {rate:.3f} > {max_rate}"
        elif not fb_gate:
            reason = f"failed: agreement with operator feedback {fb['feedback_agreement']:.3f} < {fb_min_agreement}"
        else:
            reason = "passed"
        mlflow.set_tag("release_criteria", reason)
        client.set_model_version_tag(name, mv.version, "release_criteria", "passed" if passed else "failed")
        if passed and promote:
            client.set_registered_model_alias(name, alias, mv.version)
        emit("model_registered", model_name=name, model_version=mv.version, run_id=run.info.run_id,
             samples=len(frame), train_anomaly_rate=round(rate, 4), release_criteria=passed,
             feedback_labels=fb["feedback_labels"], feedback_agreement=fb.get("feedback_agreement"),
             promoted_alias=alias if (passed and promote) else None)
        return 0 if passed else 3


if __name__ == "__main__":
    sys.exit(main())
