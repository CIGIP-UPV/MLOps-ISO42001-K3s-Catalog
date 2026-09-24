"""
Drift check, step 2 (runs on the Evidently image, API 0.4.x): computes the
data drift report between reference.csv and current.csv with the
DataDriftPreset, stores it in the Evidently UI (project PROJECT) and writes
summary.json and report.html for step 3.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

ENV = os.environ
WORK = Path(ENV.get("WORK_DIR", "/work"))


def emit(event: str, **fields) -> None:
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "component": "platform-evidently", "step": "drift", "event": event, **fields}), flush=True)


def metric(result: dict, name: str) -> dict:
    return next(m["result"] for m in result["metrics"] if m["metric"] == name)


def main() -> int:
    meta = json.loads((WORK / "meta.json").read_text())
    if meta.get("skip"):
        (WORK / "summary.json").write_text(json.dumps({"skipped": True, "reason": meta.get("reason")}))
        emit("skipped", reason=meta.get("reason"))
        return 0

    features = meta["features"]
    reference = pd.read_csv(WORK / "reference.csv")[features]
    current = pd.read_csv(WORK / "current.csv")[features]
    report = Report(metrics=[DataDriftPreset()])
    report.run(reference_data=reference, current_data=current)
    result = report.as_dict()
    dataset = metric(result, "DatasetDriftMetric")
    table = metric(result, "DataDriftTable")
    per_column = {c: {"stattest": v.get("stattest_name"), "score": v.get("drift_score"),
                      "drift": bool(v.get("drift_detected"))}
                  for c, v in table["drift_by_columns"].items()}
    summary = {"skipped": False,
               "share_of_drifted_columns": dataset["share_of_drifted_columns"],
               "number_of_drifted_columns": dataset["number_of_drifted_columns"],
               "dataset_drift": bool(dataset["dataset_drift"]),
               "drifted_columns": [c for c, v in per_column.items() if v["drift"]],
               "per_column": per_column}
    report.save_html(str(WORK / "report.html"))

    ui = ENV.get("EVIDENTLY_UI_URL")
    if ui:
        try:
            from evidently.ui.remote import RemoteWorkspace
            ws = RemoteWorkspace(ui)
            name = ENV.get("PROJECT", meta["model_name"])
            found = ws.search_project(name)
            project = found[0] if found else ws.create_project(name)
            ws.add_report(project.id, report)
            summary["ui_project_id"] = str(project.id)
        except Exception as exc:  # noqa: BLE001
            summary["ui_error"] = repr(exc)[:300]

    (WORK / "summary.json").write_text(json.dumps(summary))
    emit("drift_computed", model_name=meta["model_name"], model_version=meta["model_version"],
         **{k: v for k, v in summary.items() if k != "per_column"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
