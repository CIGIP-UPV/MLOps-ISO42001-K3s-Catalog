"""
Edge version control: propagates the model version promoted in the platform
MLflow registry to the edge.

Each run:
  1. resolves models:/<MODEL_NAME>@<MODEL_ALIAS> in the platform registry;
  2. does nothing if that version is already the one in MODEL_DIR/current.json;
  3. otherwise downloads it (through the MLflow server, no object storage
     credentials), checks that it loads, and records its SHA-256;
  4. switches MODEL_DIR/current.json atomically, asks the edge model server
     to reload and verifies that /version reports the new version;
  5. records every step in the edge data stock (table model_versions) and as
     JSON lines on stdout, and keeps the last KEEP_VERSIONS versions on disk
     so that a previous version can be restored (rollback);
  6. propagates the suspension of a version: when a supervisor sets the tag
     suspended=true on it in the registry (feedback interface, human
     oversight), current.json is marked as suspended and the edge model server
     stops serving it; removing the tag resumes it.

Environment: MLFLOW_TRACKING_URI, MODEL_NAME, MODEL_ALIAS, MODEL_DIR,
SERVER_URL, KEEP_VERSIONS, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import mlflow
import mlflow.pyfunc
import psycopg2
import requests
from mlflow.tracking import MlflowClient

ENV = os.environ
MODEL_DIR = Path(ENV.get("MODEL_DIR", "/models"))
CURRENT = MODEL_DIR / "current.json"


def emit(event: str, **fields) -> None:
    print(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                      "component": "edge-mlflow-sync", "event": event, **fields}), flush=True)


def record(name: str, version: str, status: str, alias=None, run_id=None, source=None, sha=None) -> None:
    """Version history of the edge (B.6.1.3.2). Best effort: never blocks a rollout."""
    try:
        with psycopg2.connect(host=ENV["DB_HOST"], port=ENV.get("DB_PORT", "5432"), dbname=ENV["DB_NAME"],
                              user=ENV["DB_USER"], password=ENV["DB_PASSWORD"], connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO model_versions (model_name, model_version, alias, run_id, source_uri,"
                    " artefact_sha256, status) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    " ON CONFLICT (model_name, model_version, status) DO UPDATE SET received_at = now()",
                    (name, version, alias, run_id, source, sha, status))
    except Exception as exc:  # noqa: BLE001
        emit("version_record_failed", error=str(exc), status=status)


def tree_sha256(path: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in path.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(path)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def prune(name: str, keep: int, active: str) -> None:
    versions = sorted((MODEL_DIR / "versions").glob(f"{name}-v*"),
                      key=lambda p: int(p.name.rsplit("-v", 1)[1]) if p.name.rsplit("-v", 1)[1].isdigit() else -1)
    for old in versions[:-keep]:
        if old.name != active:
            shutil.rmtree(old, ignore_errors=True)
            emit("version_pruned", path=str(old))


def suspension(mv) -> dict | None:
    """Suspension recorded on the model version in the registry, or None."""
    tags = dict(mv.tags or {})
    if tags.get("suspended") != "true":
        return None
    return {"by": tags.get("suspended_by"), "at": tags.get("suspended_at"), "reason": tags.get("suspended_reason")}


def switch(meta: dict, server: str) -> tuple[bool, dict]:
    """Write current.json atomically, reload the server and read back /version."""
    staged = MODEL_DIR / ".current.json.tmp"
    staged.write_text(json.dumps(meta, indent=1))
    os.replace(staged, CURRENT)  # atomic switch
    try:
        requests.post(f"{server}/reload", timeout=60).raise_for_status()
        served = requests.get(f"{server}/version", timeout=10).json()
    except Exception as exc:  # noqa: BLE001
        return False, {"error": str(exc)[:300]}
    ok = (str(served.get("model_version")) == str(meta["version"])
          and bool(served.get("suspended")) == bool(meta.get("suspended")))
    return ok, served


def main() -> int:
    name, alias = ENV.get("MODEL_NAME", "zdm-anomaly-detector"), ENV.get("MODEL_ALIAS", "champion")
    server = ENV.get("SERVER_URL", "http://edge-fastapi-model:8000").rstrip("/")
    keep = int(ENV.get("KEEP_VERSIONS", "3"))

    client = MlflowClient()
    try:
        mv = client.get_model_version_by_alias(name, alias)
    except Exception as exc:  # noqa: BLE001
        emit("no_promoted_version", model_name=name, alias=alias, error=str(exc)[:300])
        return 0

    susp = suspension(mv)
    current = json.loads(CURRENT.read_text()) if CURRENT.exists() else {}
    if str(current.get("version")) == str(mv.version) and current.get("name") == name:
        if bool(current.get("suspended")) == bool(susp):
            emit("up_to_date", model_name=name, model_version=mv.version, alias=alias, suspended=bool(susp))
            return 0
        # Same version, suspension changed: switch the flag without touching the model files.
        ok, served = switch({**current, "suspended": bool(susp), "suspension": susp}, server)
        status, event = ("suspended", "version_suspended") if susp else ("resumed", "version_resumed")
        if not ok:
            emit("suspension_switch_failed", model_name=name, model_version=mv.version, served=served)
            return 1
        record(name, str(mv.version), status, alias, mv.run_id, mv.source, current.get("sha256"))
        emit(event, model_name=name, model_version=mv.version, alias=alias, **({"suspension": susp} if susp else {}))
        return 0

    emit("new_version_detected", model_name=name, model_version=mv.version, alias=alias,
         previous_version=current.get("version"), run_id=mv.run_id)
    target = f"versions/{name}-v{mv.version}"
    dest = MODEL_DIR / target
    tmp = MODEL_DIR / "versions" / f".{name}-v{mv.version}.tmp"
    try:
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        local = mlflow.artifacts.download_artifacts(artifact_uri=f"models:/{name}/{mv.version}", dst_path=str(tmp))
        model_path = Path(local)
        loaded = mlflow.pyfunc.load_model(str(model_path))  # smoke test before switching
        schema = loaded.metadata.get_input_schema()
        features = schema.input_names() if schema else None
        sha = tree_sha256(model_path)
        shutil.rmtree(dest, ignore_errors=True)
        model_path.rename(dest)
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(tmp, ignore_errors=True)
        record(name, str(mv.version), "download_failed", alias, mv.run_id, mv.source)
        emit("download_failed", model_name=name, model_version=mv.version, error=str(exc)[:500])
        return 1
    record(name, str(mv.version), "downloaded", alias, mv.run_id, mv.source, sha)

    meta = {"name": name, "version": str(mv.version), "alias": alias, "run_id": mv.run_id,
            "source": mv.source, "path": target, "features": features, "sha256": sha,
            "suspended": bool(susp), "suspension": susp,
            "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    staged = MODEL_DIR / ".current.json.tmp"
    ok, served = switch(meta, server)
    if not ok:
        # Keep the previous version active so the edge keeps serving it.
        if current:
            staged.write_text(json.dumps(current, indent=1))
            os.replace(staged, CURRENT)
            try:
                requests.post(f"{server}/reload", timeout=60)
            except Exception:  # noqa: BLE001
                pass
        record(name, str(mv.version), "activation_failed", alias, mv.run_id, mv.source, sha)
        emit("activation_failed", model_name=name, model_version=mv.version, served=served,
             rolled_back_to=current.get("version"))
        return 1

    record(name, str(mv.version), "active", alias, mv.run_id, mv.source, sha)
    emit("version_activated", model_name=name, model_version=mv.version, alias=alias,
         previous_version=current.get("version"), sha256=sha)
    prune(name, keep, Path(target).name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
