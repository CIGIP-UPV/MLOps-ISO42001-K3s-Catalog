"""Unit tests of the feedback interface (files/app.py).

The database, Keycloak and MLflow are replaced by fakes, so the tests run
without a cluster:

    pip install pytest httpx
    pytest catalog/enterprise/human-oversight/feedback-interface/tests
"""

import datetime as dt
import importlib
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FILES = Path(__file__).resolve().parents[1] / "manifests" / "files"
os.environ.setdefault("SESSION_SECRET", "test-secret")
os.environ.setdefault("TEMPLATE_DIR", str(FILES / "templates"))
sys.path.insert(0, str(FILES))
app_module = importlib.import_module("app")

PREDICTION = {"time": dt.datetime(2026, 9, 24, 9, 1, 25, tzinfo=dt.timezone.utc), "site_id": "lab-edge-01",
              "source_id": 7, "machine_id": "cnc-01", "model_name": "zdm-anomaly-detector",
              "model_version": "2", "label": "anomaly"}
USERS = {"ana": ("pw-ana", ["operator"]), "sam": ("pw-sam", ["production-manager"]),
         "eve": ("pw-eve", ["data-scientist"])}


class FakeDB:
    def __init__(self):
        self.feedback: list[dict] = []

    def query(self, sql, params=None):
        params = params or {}
        if sql.strip().startswith("SELECT 1"):
            return [{"ok": 1}]
        if "INSERT INTO operator_feedback" in sql:
            row = {**params, "id": len(self.feedback) + 1, "created_at": dt.datetime.now(dt.timezone.utc)}
            self.feedback.append(row)
            return [{"id": row["id"], "created_at": row["created_at"]}]
        if "FROM predictions WHERE site_id" in sql:
            ok = (params["site"] == PREDICTION["site_id"] and params["src"] == PREDICTION["source_id"])
            return [dict(PREDICTION)] if ok else []
        if "LEFT JOIN LATERAL" in sql:
            return [{**PREDICTION, "score": 0.71, "verdict": None, "corrected_label": None,
                     "operator": None, "verdict_at": None}]
        raise AssertionError(f"unexpected SQL: {sql}")


class FakeRegistry:
    def __init__(self):
        self.tags: dict[str, str] = {}

    def call(self, method, path, **payload):
        if path == "registered-models/alias":
            return {"model_version": {"version": "2", "tags": [{"key": k, "value": v} for k, v in self.tags.items()]}}
        if path == "model-versions/set-tag":
            self.tags[payload["key"]] = payload["value"]
            return {}
        if path == "model-versions/delete-tag":
            self.tags.pop(payload["key"], None)
            return {}
        raise AssertionError(path)


@pytest.fixture()
def env(monkeypatch):
    db, reg = FakeDB(), FakeRegistry()
    monkeypatch.setattr(app_module, "db_query", db.query)
    monkeypatch.setattr(app_module, "mlflow_call", reg.call)
    monkeypatch.setattr(app_module, "kc_password_token",
                        lambda u, p: f"token:{u}" if u in USERS and USERS[u][0] == p else None)
    monkeypatch.setattr(app_module, "kc_claims",
                        lambda t: {"preferred_username": t.split(":")[1],
                                   "realm_access": {"roles": USERS[t.split(":")[1]][1]}})
    return TestClient(app_module.app), db, reg


def login(client, user):
    r = client.post("/login", json={"username": user, "password": USERS[user][0]})
    assert r.status_code == 200, r.text
    return client.get("/api/session").json()["csrf"]


def verdict_body(**over):
    body = {"site_id": "lab-edge-01", "source_id": 7, "time": "2026-09-24T09:01:25+00:00", "verdict": "correct"}
    body.update(over)
    return body


def test_health_needs_no_session(env):
    client, _, _ = env
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"ready": True}


def test_without_session_access_is_denied(env):
    client, _, _ = env
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.get("/api/predictions").status_code == 401
    assert client.post("/feedback", json=verdict_body()).status_code == 401
    assert client.post("/models/suspend", json={"reason": "x"}).status_code == 401


def test_wrong_password_and_missing_role(env):
    client, _, _ = env
    assert client.post("/login", json={"username": "ana", "password": "nope"}).status_code == 401
    assert client.post("/login", json={"username": "eve", "password": "pw-eve"}).status_code == 403


def test_tampered_cookie_is_rejected(env):
    client, _, _ = env
    login(client, "ana")
    client.cookies.set("fb_session", client.cookies.get("fb_session") + "x")
    assert client.get("/api/session").status_code == 401


def test_verdict_requires_csrf(env):
    client, db, _ = env
    login(client, "ana")
    assert client.post("/feedback", json=verdict_body()).status_code == 403
    assert db.feedback == []


def test_verdict_is_recorded_with_the_session_user(env):
    client, db, _ = env
    csrf = login(client, "ana")
    r = client.post("/feedback", json=verdict_body(verdict="incorrect", corrected_label="normal",
                                                   comment="tool change", operator="mallory"),
                    headers={"X-CSRF-Token": csrf})
    assert r.status_code == 201, r.text
    row = db.feedback[0]
    assert row["operator"] == "ana"                       # never taken from the request
    assert row["version"] == "2" and row["pred"] == "anomaly"   # taken from the stored prediction
    assert (row["verdict"], row["corrected"], row["comment"]) == ("incorrect", "normal", "tool change")


def test_form_submission_redirects(env):
    client, db, _ = env
    csrf = login(client, "ana")
    r = client.post("/feedback", data={**verdict_body(), "csrf": csrf}, follow_redirects=False)
    assert r.status_code == 303 and len(db.feedback) == 1


@pytest.mark.parametrize("over,status", [
    ({"verdict": "maybe"}, 422),
    ({"verdict": "correct", "corrected_label": "normal"}, 422),
    ({"verdict": "incorrect", "corrected_label": "anomaly"}, 422),   # equals the prediction
    ({"verdict": "incorrect", "corrected_label": "broken"}, 422),
    ({"comment": "x" * 1001}, 422),
    ({"source_id": "abc"}, 422),
    ({"source_id": 999}, 404),
])
def test_invalid_verdicts(env, over, status):
    client, db, _ = env
    csrf = login(client, "ana")
    assert client.post("/feedback", json=verdict_body(**over), headers={"X-CSRF-Token": csrf}).status_code == status
    assert db.feedback == []


def test_operator_cannot_suspend(env):
    client, _, reg = env
    csrf = login(client, "ana")
    assert client.post("/models/suspend", json={"reason": "x"}, headers={"X-CSRF-Token": csrf}).status_code == 403
    assert reg.tags == {}


def test_supervisor_suspends_and_resumes(env):
    client, _, reg = env
    csrf = login(client, "sam")
    r = client.post("/models/suspend", json={"reason": "operators disagree"}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200 and r.json()["suspended"] is True
    assert reg.tags["suspended"] == "true" and reg.tags["suspended_by"] == "sam"
    r = client.post("/models/resume", json={}, headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200 and "suspended" not in reg.tags and "last_resumed" in reg.tags


def test_index_and_listing(env):
    client, _, _ = env
    login(client, "sam")
    page = client.get("/")
    assert page.status_code == 200 and "cnc-01" in page.text and "Suspend version 2" in page.text
    data = client.get("/api/predictions").json()["predictions"]
    assert data[0]["model_version"] == "2"


def test_security_headers(env):
    client, _, _ = env
    r = client.get("/login")
    assert r.headers["x-frame-options"] == "DENY" and "default-src 'self'" in r.headers["content-security-policy"]
