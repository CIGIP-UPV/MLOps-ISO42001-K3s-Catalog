"""
Drift check, step 1 (runs on the MLflow image): prepares the two datasets.

reference.csv  training frame of the model version currently behind the
               serving alias (artefact reference/reference.csv of its run)
current.csv    recent consolidated data of the platform data stock, turned
               into feature vectors exactly as the training pipeline does
meta.json      model, version, windows and row counts
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import mlflow
import pandas as pd
import psycopg2
from mlflow.tracking import MlflowClient

ENV = os.environ
WORK = Path(ENV.get("WORK_DIR", "/work"))


def emit(event: str, **fields) -> None:
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "component": "platform-evidently", "step": "extract", "event": event, **fields}), flush=True)


def current_frame(window: str, bucket: str) -> pd.DataFrame:
    sql = """
        SELECT time_bucket(%(bucket)s::interval, time) AS t, machine_id, signal_name, avg(value) AS value
          FROM sensor_readings WHERE time > now() - %(window)s::interval GROUP BY 1, 2, 3
    """
    with psycopg2.connect(host=ENV["DB_HOST"], port=ENV.get("DB_PORT", "5432"), dbname=ENV["DB_NAME"],
                          user=ENV["DB_USER"], password=ENV["DB_PASSWORD"], connect_timeout=10) as conn:
        long = pd.read_sql(sql, conn, params={"bucket": bucket, "window": window})
    if long.empty:
        return pd.DataFrame()
    wide = long.pivot_table(index=["t", "machine_id"], columns="signal_name", values="value").sort_index()
    wide = wide.groupby(level="machine_id").ffill().dropna(axis=0, how="any")
    wide.columns = [str(c) for c in wide.columns]
    return wide.reset_index(drop=True)


def main() -> int:
    name, alias = ENV.get("MODEL_NAME", "zdm-anomaly-detector"), ENV.get("MODEL_ALIAS", "champion")
    window, bucket = ENV.get("CURRENT_WINDOW", "1 hour"), ENV.get("BUCKET", "10 seconds")
    min_rows = int(ENV.get("MIN_CURRENT_ROWS", "30"))
    WORK.mkdir(parents=True, exist_ok=True)
    meta = {"model_name": name, "alias": alias, "current_window": window, "bucket": bucket, "skip": False}

    try:
        mv = MlflowClient().get_model_version_by_alias(name, alias)
    except Exception as exc:  # noqa: BLE001
        meta.update(skip=True, reason=f"no version behind alias {alias}: {str(exc)[:200]}")
        (WORK / "meta.json").write_text(json.dumps(meta))
        emit("skipped", reason=meta["reason"])
        return 0

    ref_path = mlflow.artifacts.download_artifacts(run_id=mv.run_id, artifact_path="reference/reference.csv",
                                                   dst_path=str(WORK / "artefacts"))
    reference = pd.read_csv(ref_path)
    features = list(reference.columns)
    current = current_frame(window, bucket)
    missing = [f for f in features if f not in current.columns]
    meta.update(model_version=str(mv.version), run_id=mv.run_id, features=features,
                reference_rows=len(reference), current_rows=len(current),
                reference_window=mv.tags.get("data_window", ""))
    if len(current) < min_rows or missing:
        meta.update(skip=True, reason=f"current data: {len(current)} rows, missing features {missing}")
    else:
        reference.to_csv(WORK / "reference.csv", index=False)
        current[features].to_csv(WORK / "current.csv", index=False)
    (WORK / "meta.json").write_text(json.dumps(meta))
    emit("datasets_ready" if not meta["skip"] else "skipped", **{k: v for k, v in meta.items() if k != "features"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
