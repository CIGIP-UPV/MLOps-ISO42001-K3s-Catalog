"""
Drift check, step 3 (runs on the MLflow image): Retraining Recommendation.

* recommends retraining when the share of drifted features reaches
  THRESHOLD (and no retraining was triggered within COOLDOWN);
* records the result in retraining_recommendations (platform data stock);
* logs the drift report to MLflow (experiment DRIFT_EXPERIMENT), so the
  report is kept next to the model versions it refers to;
* when AUTO_RETRAIN is true, starts a retraining Job from the CronJob of
  platform-training-jobs with TRIGGER=drift (activation flow).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import mlflow
import psycopg2

ENV = os.environ
WORK = Path(ENV.get("WORK_DIR", "/work"))


def emit(event: str, **fields) -> None:
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "component": "platform-evidently", "step": "recommend", "event": event, **fields}), flush=True)


def connect():
    return psycopg2.connect(host=ENV["DB_HOST"], port=ENV.get("DB_PORT", "5432"), dbname=ENV["DB_NAME"],
                            user=ENV["DB_USER"], password=ENV["DB_PASSWORD"], connect_timeout=10)


def recently_triggered(model: str, cooldown: str) -> bool:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM retraining_recommendations WHERE model_name = %s"
                    " AND action LIKE 'retraining job%%' AND created_at > now() - %s::interval", (model, cooldown))
        return cur.fetchone()[0] > 0


def start_retraining(cronjob: str, namespace: str) -> str:
    from kubernetes import client, config
    config.load_incluster_config()
    batch = client.BatchV1Api()
    cj = batch.read_namespaced_cron_job(cronjob, namespace)
    spec = cj.spec.job_template.spec
    for c in spec.template.spec.containers:
        c.env = [e for e in (c.env or []) if e.name != "TRIGGER"] + [client.V1EnvVar(name="TRIGGER", value="drift")]
    job = client.V1Job(
        metadata=client.V1ObjectMeta(generate_name=f"{cronjob}-drift-",
                                     labels=(cj.spec.job_template.metadata.labels or {}),
                                     annotations={"cronjob.kubernetes.io/instantiate": "manual",
                                                  "mlops-iso42001.cigip-upv.es/trigger": "drift"}),
        spec=spec)
    return batch.create_namespaced_job(namespace, job).metadata.name


def main() -> int:
    meta = json.loads((WORK / "meta.json").read_text())
    summary = json.loads((WORK / "summary.json").read_text())
    model = meta["model_name"]
    if summary.get("skipped"):
        emit("skipped", model_name=model, reason=summary.get("reason"))
        return 0

    threshold = float(ENV.get("THRESHOLD", "0.5"))
    share = float(summary["share_of_drifted_columns"])
    recommended = share >= threshold
    action = "no action"
    if recommended:
        if recently_triggered(model, ENV.get("COOLDOWN", "6 hours")):
            action = "recommended; retraining already triggered within the cooldown"
        elif ENV.get("AUTO_RETRAIN", "true").lower() == "true":
            try:
                job = start_retraining(ENV["TRAINING_CRONJOB"], ENV.get("POD_NAMESPACE", "mlops"))
                action = f"retraining job {job} created"
            except Exception as exc:  # noqa: BLE001
                action = f"recommended; retraining job creation failed: {str(exc)[:200]}"
        else:
            action = "recommended; waiting for manual retraining"

    report_uri = None
    try:
        mlflow.set_experiment(ENV.get("DRIFT_EXPERIMENT", "zdm-drift-monitoring"))
        with mlflow.start_run(run_name=f"drift-v{meta['model_version']}-{time.strftime('%Y%m%dT%H%M%S')}") as run:
            mlflow.set_tags({"model_name": model, "model_version": meta["model_version"],
                             "model_run_id": meta["run_id"], "recommended": str(recommended), "action": action})
            mlflow.log_params({"threshold": threshold, "current_window": meta["current_window"],
                               "bucket": meta["bucket"]})
            mlflow.log_metrics({"share_of_drifted_columns": share,
                                "number_of_drifted_columns": summary["number_of_drifted_columns"],
                                "reference_rows": meta["reference_rows"], "current_rows": meta["current_rows"]})
            mlflow.log_artifact(str(WORK / "report.html"), artifact_path="drift")
            mlflow.log_dict(summary, "drift/summary.json")
            report_uri = f"runs:/{run.info.run_id}/drift/report.html"
    except Exception as exc:  # noqa: BLE001
        emit("mlflow_log_failed", error=str(exc)[:300])

    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO retraining_recommendations (model_name, model_version, reference_window, current_window,"
            " drift_share, drifted_columns, threshold, recommended, action, report_uri)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (model, meta["model_version"], meta.get("reference_window"), meta["current_window"], share,
             summary["drifted_columns"], threshold, recommended, action, report_uri))
        rec_id = cur.fetchone()[0]

    emit("recommendation", id=rec_id, model_name=model, model_version=meta["model_version"],
         share_of_drifted_columns=share, drifted_columns=summary["drifted_columns"], threshold=threshold,
         recommended=recommended, action=action, report_uri=report_uri)
    return 0


if __name__ == "__main__":
    sys.exit(main())
