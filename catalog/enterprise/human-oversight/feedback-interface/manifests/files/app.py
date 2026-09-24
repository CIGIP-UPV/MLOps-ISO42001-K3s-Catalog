"""
Feedback interface (CMP-12 Feedback Interface, enterprise tier).

Operators review the recent predictions of the model, consolidated from the
edge into the platform data stock, and record a verdict on each one:
correct, incorrect or uncertain, with an optional corrected label and
comment. Supervisors can also suspend the model version in service, which
edge-mlflow-sync propagates to the edge model server (human oversight,
ISO/IEC 42001 B.6.1.3.3; the verdicts feed the model lifecycle, B.6.2.6.4).

Data
    reads   predictions        platform data stock (TimescaleDB), role feedback
    writes  operator_feedback  append-only; the latest verdict is in force
    tags    suspended, ...     MLflow model version (registry REST API)

Sign-in against Keycloak (realm ai-system, client feedback-interface) from
the server side; the session is a signed cookie. Roles: VERDICT_ROLES may
record verdicts, SUSPEND_ROLES may also suspend and resume a version.

Endpoints
    GET  /healthz /readyz /metrics
    GET  /login, POST /login, POST /logout
    GET  /                         predictions and model version (HTML)
    GET  /api/session              user, roles and CSRF token (JSON)
    GET  /api/predictions          recent predictions with their verdict (JSON)
    POST /feedback                 record a verdict (form or JSON)
    POST /models/suspend           suspend the served version (form or JSON)
    POST /models/resume            resume it (form or JSON)
Every change is logged as a JSON line on stdout (Fluent Bit -> Loki).
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import jwt
import psycopg2
import psycopg2.extras
import requests
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

ENV = os.environ
VERDICTS = ("correct", "incorrect", "uncertain")
LABELS = ("normal", "anomaly")
COOKIE = "fb_session"
MAX_COMMENT = 1000


def csv_env(name: str, default: str) -> set[str]:
    return {x.strip() for x in ENV.get(name, default).split(",") if x.strip()}


VERDICT_ROLES = csv_env("VERDICT_ROLES", "operator,production-manager,compliance-officer")
SUSPEND_ROLES = csv_env("SUSPEND_ROLES", "production-manager,compliance-officer")
SESSION_TTL = int(ENV.get("SESSION_TTL", "1800"))
COOKIE_SECURE = ENV.get("COOKIE_SECURE", "false").lower() == "true"
LOOKBACK = ENV.get("LOOKBACK", "24 hours")
PAGE_SIZE = int(ENV.get("PAGE_SIZE", "50"))
MODEL_NAME = ENV.get("MODEL_NAME", "zdm-anomaly-detector")
MODEL_ALIAS = ENV.get("MODEL_ALIAS", "champion")
MLFLOW_URL = ENV.get("MLFLOW_TRACKING_URI", "http://platform-mlflow.mlops.svc.cluster.local:5000").rstrip("/")
KC_URL = ENV.get("KEYCLOAK_URL", "http://enterprise-keycloak.security.svc.cluster.local").rstrip("/")
KC_REALM = ENV.get("KEYCLOAK_REALM", "ai-system")
KC_CLIENT = ENV.get("KEYCLOAK_CLIENT_ID", "feedback-interface")

logging.basicConfig(level=ENV.get("LOG_LEVEL", "INFO"), format="%(message)s")
log = logging.getLogger("enterprise-feedback-interface")

VERDICTS_TOTAL = Counter("feedback_verdicts_total", "Operator verdicts recorded", ["verdict", "model_version"])
LOGINS_TOTAL = Counter("feedback_logins_total", "Sign-in attempts", ["result"])
SUSPENSIONS_TOTAL = Counter("model_suspensions_total", "Suspend and resume actions", ["action"])

app = FastAPI(title="enterprise-feedback-interface", version="1.0.0", docs_url=None, redoc_url=None)
templates = Environment(loader=FileSystemLoader(ENV.get("TEMPLATE_DIR", str(Path(__file__).parent / "templates"))),
                        autoescape=select_autoescape(["html"]))
serializer = URLSafeTimedSerializer(ENV.get("SESSION_SECRET", ""), salt="feedback-session")


def emit(event: str, **fields: Any) -> None:
    log.info(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "component": "enterprise-feedback-interface", "event": event, **fields}, default=str))


# ---------------------------------------------------------------------------
# External systems (replaced in the unit tests)
# ---------------------------------------------------------------------------
def db_connect():
    return psycopg2.connect(host=ENV["DB_HOST"], port=ENV.get("DB_PORT", "5432"), dbname=ENV["DB_NAME"],
                            user=ENV["DB_USER"], password=ENV["DB_PASSWORD"], connect_timeout=5)


def db_query(sql: str, params: dict | None = None) -> list[dict]:
    with db_connect() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params or {})
        return [dict(r) for r in cur.fetchall()]


def kc_password_token(username: str, password: str) -> str | None:
    """Access token for the user, or None when Keycloak refuses the credentials."""
    r = requests.post(f"{KC_URL}/realms/{KC_REALM}/protocol/openid-connect/token", timeout=10,
                      data={"grant_type": "password", "client_id": KC_CLIENT,
                            "username": username, "password": password, "scope": "openid"})
    if r.status_code in (400, 401):
        return None
    r.raise_for_status()
    return r.json()["access_token"]


_jwks: jwt.PyJWKClient | None = None


def kc_claims(token: str) -> dict:
    """Verifies the signature (realm keys), expiry and authorised party of the token."""
    global _jwks
    if _jwks is None:
        _jwks = jwt.PyJWKClient(f"{KC_URL}/realms/{KC_REALM}/protocol/openid-connect/certs")
    key = _jwks.get_signing_key_from_jwt(token).key
    claims = jwt.decode(token, key, algorithms=["RS256"], options={"verify_aud": False})
    if claims.get("azp") != KC_CLIENT:
        raise jwt.InvalidTokenError("token issued for another client")
    return claims


def mlflow_call(method: str, path: str, **payload: Any) -> dict:
    url = f"{MLFLOW_URL}/api/2.0/mlflow/{path}"
    r = (requests.get(url, params=payload, timeout=10) if method == "GET"
         else requests.request(method, url, json=payload, timeout=10))
    r.raise_for_status()
    return r.json() if r.content else {}


# ---------------------------------------------------------------------------
# Session and permissions
# ---------------------------------------------------------------------------
def session_of(request: Request) -> dict | None:
    raw = request.cookies.get(COOKIE)
    if not raw:
        return None
    try:
        return serializer.loads(raw, max_age=SESSION_TTL)
    except BadSignature:
        return None


def require(request: Request, roles: set[str]) -> dict:
    sess = session_of(request)
    if sess is None:
        raise HTTPException(status_code=401, detail="sign-in required")
    if not roles & set(sess["roles"]):
        raise HTTPException(status_code=403, detail="role not allowed")
    return sess


def check_csrf(sess: dict, supplied: str | None) -> None:
    if not supplied or not hmac.compare_digest(str(supplied), sess["csrf"]):
        raise HTTPException(status_code=403, detail="invalid CSRF token")


async def body_of(request: Request) -> tuple[dict, bool]:
    """Form or JSON body; the flag tells whether the client expects JSON."""
    raw = await request.body()
    if request.headers.get("content-type", "").startswith("application/json"):
        return (json.loads(raw or b"{}"), True)
    return ({k: v[0] for k, v in parse_qs(raw.decode(), keep_blank_values=True).items()}, False)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; form-action 'self'"
    return response


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------
PREDICTIONS_SQL = """
    SELECT p.time, p.site_id, p.source_id, p.machine_id, p.model_name, p.model_version,
           p.score, p.label, f.verdict, f.corrected_label, f.operator, f.created_at AS verdict_at
      FROM predictions p
      LEFT JOIN LATERAL (
        SELECT verdict, corrected_label, operator, created_at FROM operator_feedback o
         WHERE o.site_id = p.site_id AND o.prediction_source_id = p.source_id AND o.prediction_time = p.time
         ORDER BY created_at DESC LIMIT 1) f ON TRUE
     WHERE p.time > now() - %(lookback)s::interval
     ORDER BY p.time DESC LIMIT %(limit)s
"""


def recent_predictions(limit: int = PAGE_SIZE) -> list[dict]:
    return db_query(PREDICTIONS_SQL, {"lookback": LOOKBACK, "limit": limit})


def validate_verdict(data: dict, predicted_label: str) -> tuple[str, str | None, str | None]:
    verdict = str(data.get("verdict", "")).strip()
    corrected = str(data.get("corrected_label") or "").strip() or None
    comment = str(data.get("comment") or "").strip() or None
    if verdict not in VERDICTS:
        raise HTTPException(status_code=422, detail=f"verdict must be one of {', '.join(VERDICTS)}")
    if corrected is not None and corrected not in LABELS:
        raise HTTPException(status_code=422, detail=f"corrected label must be one of {', '.join(LABELS)}")
    if corrected is not None and verdict != "incorrect":
        raise HTTPException(status_code=422, detail="a corrected label only goes with an incorrect verdict")
    if corrected is not None and corrected == predicted_label:
        raise HTTPException(status_code=422, detail="the corrected label equals the predicted one")
    if comment is not None and len(comment) > MAX_COMMENT:
        raise HTTPException(status_code=422, detail=f"comment longer than {MAX_COMMENT} characters")
    return verdict, corrected, comment


def record_feedback(data: dict, operator: str) -> dict:
    try:
        source_id = int(data.get("source_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="source_id must be an integer") from None
    site_id, pred_time = str(data.get("site_id", "")), str(data.get("time", ""))
    rows = db_query("SELECT time, site_id, source_id, machine_id, model_name, model_version, label"
                    "  FROM predictions WHERE site_id = %(site)s AND source_id = %(src)s AND time = %(t)s",
                    {"site": site_id, "src": source_id, "t": pred_time})
    if not rows:
        raise HTTPException(status_code=404, detail="prediction not found in the platform data stock")
    p = rows[0]
    verdict, corrected, comment = validate_verdict(data, p["label"])
    saved = db_query(
        "INSERT INTO operator_feedback (site_id, prediction_source_id, prediction_time, machine_id, model_name,"
        " model_version, predicted_label, verdict, corrected_label, comment, operator)"
        " VALUES (%(site)s, %(src)s, %(t)s, %(machine)s, %(model)s, %(version)s, %(pred)s, %(verdict)s,"
        " %(corrected)s, %(comment)s, %(operator)s) RETURNING id, created_at",
        {"site": p["site_id"], "src": p["source_id"], "t": p["time"], "machine": p["machine_id"],
         "model": p["model_name"], "version": p["model_version"], "pred": p["label"], "verdict": verdict,
         "corrected": corrected, "comment": comment, "operator": operator})[0]
    VERDICTS_TOTAL.labels(verdict, p["model_version"]).inc()
    emit("feedback_recorded", feedback_id=saved["id"], site_id=p["site_id"], prediction_source_id=p["source_id"],
         prediction_time=p["time"], machine_id=p["machine_id"], model_version=p["model_version"],
         predicted_label=p["label"], verdict=verdict, corrected_label=corrected, operator=operator)
    return {"id": saved["id"], "created_at": saved["created_at"], "model_version": p["model_version"],
            "verdict": verdict, "corrected_label": corrected}


def served_version() -> dict:
    """Version the serving alias points to, with its suspension tags."""
    mv = mlflow_call("GET", "registered-models/alias", name=MODEL_NAME, alias=MODEL_ALIAS)["model_version"]
    tags = {t["key"]: t["value"] for t in mv.get("tags", [])}
    return {"name": MODEL_NAME, "alias": MODEL_ALIAS, "version": mv["version"],
            "suspended": tags.get("suspended") == "true", "suspended_by": tags.get("suspended_by"),
            "suspended_at": tags.get("suspended_at"), "suspended_reason": tags.get("suspended_reason")}


def set_suspension(suspend: bool, user: str, reason: str | None) -> dict:
    mv = served_version()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if suspend:
        tags = {"suspended": "true", "suspended_by": user, "suspended_at": now,
                "suspended_reason": (reason or "")[:MAX_COMMENT]}
        for k, v in tags.items():
            mlflow_call("POST", "model-versions/set-tag", name=MODEL_NAME, version=mv["version"], key=k, value=v)
    else:
        for k in ("suspended", "suspended_by", "suspended_at", "suspended_reason"):
            try:
                mlflow_call("DELETE", "model-versions/delete-tag", name=MODEL_NAME, version=mv["version"], key=k)
            except requests.HTTPError:
                pass  # tag already absent
        mlflow_call("POST", "model-versions/set-tag", name=MODEL_NAME, version=mv["version"],
                    key="last_resumed", value=f"{now} by {user}")
    action = "suspend" if suspend else "resume"
    SUSPENSIONS_TOTAL.labels(action).inc()
    emit("model_suspended" if suspend else "model_resumed", model_name=MODEL_NAME, model_version=mv["version"],
         alias=MODEL_ALIAS, user=user, reason=reason if suspend else None)
    return {"model_name": MODEL_NAME, "model_version": mv["version"], "suspended": suspend}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/readyz")
def readyz(response: Response) -> dict:
    try:
        db_query("SELECT 1 AS ok")
    except Exception as exc:  # noqa: BLE001
        response.status_code = 503
        return {"ready": False, "error": type(exc).__name__}
    return {"ready": True}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/login", response_class=HTMLResponse)
def login_form(error: str | None = None) -> HTMLResponse:
    return HTMLResponse(templates.get_template("login.html").render(error=error))


@app.post("/login")
async def login(request: Request) -> Response:
    data, as_json = await body_of(request)
    username, password = str(data.get("username", "")).strip(), str(data.get("password", ""))
    status, reason = 401, "invalid credentials"
    try:
        token = kc_password_token(username, password) if username and password else None
        if token is not None:
            claims = kc_claims(token)
            roles = sorted(set(claims.get("realm_access", {}).get("roles", [])) & (VERDICT_ROLES | SUSPEND_ROLES))
            if roles:
                user = claims.get("preferred_username", username)
                LOGINS_TOTAL.labels("ok").inc()
                emit("login_succeeded", user=user, roles=roles)
                cookie = serializer.dumps({"user": user, "roles": roles, "csrf": secrets.token_urlsafe(24)})
                resp = (JSONResponse({"user": user, "roles": roles}) if as_json
                        else RedirectResponse("/", status_code=303))
                resp.set_cookie(COOKIE, cookie, max_age=SESSION_TTL, httponly=True, samesite="strict",
                                secure=COOKIE_SECURE)
                return resp
            status, reason = 403, "no role of the feedback interface"
    except Exception as exc:  # noqa: BLE001 - Keycloak unreachable or token rejected
        status, reason = 503, f"sign-in unavailable ({type(exc).__name__})"
    LOGINS_TOTAL.labels("denied" if status in (401, 403) else "error").inc()
    emit("login_failed", user=username or None, status=status, reason=reason)
    if as_json:
        return JSONResponse({"detail": reason}, status_code=status)
    return HTMLResponse(templates.get_template("login.html").render(error=reason), status_code=status)


@app.post("/logout")
async def logout(request: Request) -> Response:
    sess = session_of(request)
    data, _ = await body_of(request)
    if sess is not None:
        check_csrf(sess, data.get("csrf"))
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/api/session")
def api_session(request: Request) -> dict:
    sess = require(request, VERDICT_ROLES | SUSPEND_ROLES)
    return {"user": sess["user"], "roles": sess["roles"], "csrf": sess["csrf"],
            "can_suspend": bool(SUSPEND_ROLES & set(sess["roles"]))}


@app.get("/api/predictions")
def api_predictions(request: Request, limit: int = PAGE_SIZE) -> dict:
    require(request, VERDICT_ROLES | SUSPEND_ROLES)
    rows = recent_predictions(max(1, min(limit, 500)))
    return {"predictions": json.loads(json.dumps(rows, default=str))}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, msg: str | None = None) -> Response:
    sess = session_of(request)
    if sess is None:
        return RedirectResponse("/login", status_code=303)
    try:
        model = served_version()
    except Exception as exc:  # noqa: BLE001
        model = {"error": type(exc).__name__}
    return HTMLResponse(templates.get_template("index.html").render(
        session=sess, predictions=recent_predictions(), model=model, msg=msg, verdicts=VERDICTS, labels=LABELS,
        can_verdict=bool(VERDICT_ROLES & set(sess["roles"])), can_suspend=bool(SUSPEND_ROLES & set(sess["roles"]))))


@app.post("/feedback")
async def feedback(request: Request) -> Response:
    sess = require(request, VERDICT_ROLES)
    data, as_json = await body_of(request)
    check_csrf(sess, request.headers.get("x-csrf-token") or data.get("csrf"))
    saved = record_feedback(data, sess["user"])
    if as_json:
        return JSONResponse(json.loads(json.dumps(saved, default=str)), status_code=201)
    return RedirectResponse(f"/?msg=verdict+recorded+for+version+{saved['model_version']}", status_code=303)


async def suspension(request: Request, suspend: bool) -> Response:
    sess = require(request, SUSPEND_ROLES)
    data, as_json = await body_of(request)
    check_csrf(sess, request.headers.get("x-csrf-token") or data.get("csrf"))
    result = set_suspension(suspend, sess["user"], str(data.get("reason") or "").strip() or None)
    if as_json:
        return JSONResponse(result)
    word = "suspended" if suspend else "resumed"
    return RedirectResponse(f"/?msg=version+{result['model_version']}+{word}", status_code=303)


@app.post("/models/suspend")
async def suspend(request: Request) -> Response:
    return await suspension(request, True)


@app.post("/models/resume")
async def resume(request: Request) -> Response:
    return await suspension(request, False)
