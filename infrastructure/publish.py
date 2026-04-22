#\!/usr/bin/env python3
"""
publish.py — Build the Helm repository under docs/ from the catalog/ sources.

What it does, end-to-end:

    1. Enriches every Chart.yaml with icon URL, keywords, kubeVersion,
       maintainers (e-mail + URL) and ArtifactHub-compatible annotations
       (category, license, tier, ISO/IEC 42001 Annex B clauses, reference
       architecture, display name).

    2. Creates a README.md for every chart that does not already have one,
       following the same structure as the charts that ship one.

    3. Generates a coherent set of SVG icons under docs/icons/ — one per
       chart, colour-coded by tier, self-hosted so the Rancher / ArtifactHub
       UI renders them reliably from the GitHub Pages endpoint.

    4. Packages each chart as a .tgz under docs/charts/.

    5. Regenerates docs/index.yaml (Helm repository index) with SHA-256
       digests and creation timestamps.

    6. Refreshes docs/index.html so each chart card displays its icon,
       current version and a direct .tgz download link.

All changes are local. No git commits, no pushes.

Run:
    python3 infrastructure/publish.py
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import tarfile
from typing import Any

import yaml


# ───────────────────────────────────────────────────────────── Paths / URLs ──

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
DOCS = ROOT / "docs"
CHARTS_DIR = DOCS / "charts"
ICONS_DIR = DOCS / "icons"

REPO_URL = "https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog"
SOURCE_REPO = "https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog"
MAINTAINER = {
    "name": "CIGIP-UPV",
    "email": "cigip@upv.es",
    "url": "https://cigip.webs.upv.es/",
}


# ───────────────────────────────────────────────────────── Chart metadata ──

NEW_CHART_VERSION = "0.2.0"

CHART_META: dict[str, dict[str, Any]] = {
    # ── Edge ─────────────────────────────────────────────────────────────
    "edge-fastapi-model": {
        "path": "catalog/edge/ai-inference/fastapi-model",
        "tier": "edge", "category": "AI Inference",
        "display": "FastAPI Model Server",
        "iso_clauses": ["B.6.2.6.2", "B.6.2.6.4"],
        "ah_category": "ai-machine-learning",
        "tagline": "REST / gRPC inference server with Prometheus metrics, health probes and rolling-update strategy for on-edge model serving.",
        "keywords": ["iso42001", "edge", "ai-inference", "fastapi", "model-server", "mlops", "inference"],
    },
    "edge-kafka": {
        "path": "catalog/edge/data-ingestion/kafka",
        "tier": "edge", "category": "Data Ingestion",
        "display": "Apache Kafka (Edge)",
        "iso_clauses": ["B.6.2.6.4", "B.6.2.8.1"],
        "ah_category": "streaming-messaging",
        "tagline": "Distributed event streaming on K3s with KRaft mode; pre-configured topics for sensor data, predictions and alerts.",
        "keywords": ["iso42001", "edge", "data-ingestion", "kafka", "streaming", "event-bus", "kraft"],
    },
    "edge-mosquitto": {
        "path": "catalog/edge/data-ingestion/mosquitto",
        "tier": "edge", "category": "Data Ingestion",
        "display": "Eclipse Mosquitto",
        "iso_clauses": ["B.6.1.3.1", "B.6.2.6.4"],
        "ah_category": "streaming-messaging",
        "tagline": "Lightweight MQTT broker for plant-floor sensor telemetry with authentication and WebSocket support.",
        "keywords": ["iso42001", "edge", "mqtt", "data-ingestion", "broker", "sensors", "iot"],
    },
    "edge-node-red": {
        "path": "catalog/edge/data-ingestion/node-red",
        "tier": "edge", "category": "Data Ingestion",
        "display": "Node-RED",
        "iso_clauses": ["B.6.2.6.4"],
        "ah_category": "integration-delivery",
        "tagline": "Low-code flow editor for sensor data acquisition, MQTT routing and OPC-UA / REST integration.",
        "keywords": ["iso42001", "edge", "data-ingestion", "node-red", "low-code", "opc-ua", "mqtt"],
    },
    "edge-opc-ua-gateway": {
        "path": "catalog/edge/data-ingestion/opc-ua-gateway",
        "tier": "edge", "category": "Data Ingestion",
        "display": "OPC-UA Gateway",
        "iso_clauses": ["B.6.1.3.1", "B.6.2.6.4"],
        "ah_category": "integration-delivery",
        "tagline": "OPC-UA to MQTT/Kafka bridge (EMQX Neuron) that pulls tags from PLC/SCADA endpoints and forwards them into the edge event bus.",
        "keywords": ["iso42001", "edge", "data-ingestion", "opc-ua", "gateway", "neuron", "plc", "scada"],
    },
    "edge-fluent-bit": {
        "path": "catalog/edge/monitoring/fluent-bit",
        "tier": "edge", "category": "Monitoring",
        "display": "Fluent Bit",
        "iso_clauses": ["B.6.2.8.1"],
        "ah_category": "monitoring-logging",
        "tagline": "DaemonSet log forwarder shipping container logs to Loki with Kubernetes metadata for audit-trail compliance.",
        "keywords": ["iso42001", "edge", "monitoring", "logging", "fluent-bit", "audit-trail"],
    },
    "edge-prometheus-agent": {
        "path": "catalog/edge/monitoring/prometheus-agent",
        "tier": "edge", "category": "Monitoring",
        "display": "Prometheus Agent",
        "iso_clauses": ["B.6.1.2.2", "B.6.2.6.1"],
        "ah_category": "monitoring-logging",
        "tagline": "Prometheus running in agent mode — scrapes local targets and forwards metrics to the platform via remote-write.",
        "keywords": ["iso42001", "edge", "monitoring", "metrics", "prometheus", "remote-write"],
    },
    "edge-falco": {
        "path": "catalog/edge/security/falco",
        "tier": "edge", "category": "Security",
        "display": "Falco",
        "iso_clauses": ["B.6.2.6.7", "B.6.2.8.1"],
        "ah_category": "security",
        "tagline": "Runtime threat detection with eBPF / kernel-module drivers and custom rules for AI model file access and container anomalies.",
        "keywords": ["iso42001", "edge", "security", "runtime-security", "falco", "ebpf"],
    },
    "edge-mongodb": {
        "path": "catalog/edge/storage/mongodb",
        "tier": "edge", "category": "Storage",
        "display": "MongoDB (Edge Buffer)",
        "iso_clauses": ["B.6.2.6.1"],
        "ah_category": "database",
        "tagline": "Document buffer with TTL indexes for automatic cleanup of raw sensor events at the edge.",
        "keywords": ["iso42001", "edge", "storage", "mongodb", "document-store", "buffer"],
    },
    "edge-postgresql": {
        "path": "catalog/edge/storage/postgresql",
        "tier": "edge", "category": "Storage",
        "display": "PostgreSQL (Edge Cache)",
        "iso_clauses": ["B.6.2.6.1", "B.6.2.6.3", "B.6.2.8.1"],
        "ah_category": "database",
        "tagline": "Feature cache and prediction store initialised with predictions, feedback and audit tables for edge inference.",
        "keywords": ["iso42001", "edge", "storage", "postgresql", "feature-store", "prediction-cache"],
    },

    # ── Platform ─────────────────────────────────────────────────────────
    "platform-mlflow": {
        "path": "catalog/platform/ai-lifecycle/mlflow",
        "tier": "platform", "category": "AI Lifecycle",
        "display": "MLflow",
        "iso_clauses": ["B.6.1.3.2", "B.6.1.3.4", "B.6.2.6.4"],
        "ah_category": "ai-machine-learning",
        "tagline": "Experiment tracking, model registry and artefact storage backed by PostgreSQL and MinIO.",
        "keywords": ["iso42001", "platform", "ai-lifecycle", "mlflow", "model-registry", "experiment-tracking"],
    },
    "platform-training-jobs": {
        "path": "catalog/platform/ai-lifecycle/training-jobs",
        "tier": "platform", "category": "AI Lifecycle",
        "display": "Training Jobs",
        "iso_clauses": ["B.6.2.6.4"],
        "ah_category": "ai-machine-learning",
        "tagline": "CronJob for scheduled retraining and a drift-triggered Job template integrated with MLflow.",
        "keywords": ["iso42001", "platform", "ai-lifecycle", "training", "retraining", "cronjob", "mlops"],
    },
    "platform-evidently": {
        "path": "catalog/platform/ai-lifecycle/evidently",
        "tier": "platform", "category": "AI Lifecycle",
        "display": "Evidently AI",
        "iso_clauses": ["B.6.2.6.2", "B.6.2.8.1", "B.8.0.5.1"],
        "ah_category": "ai-machine-learning",
        "tagline": "Data and model drift detection service that closes the MLOps loop by triggering retraining jobs when drift exceeds a configurable threshold.",
        "keywords": ["iso42001", "platform", "ai-lifecycle", "drift-detection", "monitoring", "mlops", "evidently"],
    },
    "platform-minio": {
        "path": "catalog/platform/data-management/minio",
        "tier": "platform", "category": "Data Management",
        "display": "MinIO",
        "iso_clauses": ["B.6.2.3.1", "B.6.2.5.1"],
        "ah_category": "storage",
        "tagline": "S3-compatible object storage with six auto-provisioned buckets, policies and lifecycle rules.",
        "keywords": ["iso42001", "platform", "data-management", "minio", "s3", "object-storage"],
    },
    "platform-postgresql": {
        "path": "catalog/platform/data-management/postgresql",
        "tier": "platform", "category": "Data Management",
        "display": "PostgreSQL (Platform)",
        "iso_clauses": ["B.6.1.3.4"],
        "ah_category": "database",
        "tagline": "Shared metadata store initialised with databases for MLflow, Keycloak, Zammad and Grafana.",
        "keywords": ["iso42001", "platform", "data-management", "postgresql", "metadata-store"],
    },
    "platform-timescaledb": {
        "path": "catalog/platform/data-management/timescaledb",
        "tier": "platform", "category": "Data Management",
        "display": "TimescaleDB",
        "iso_clauses": ["B.6.2.6.1", "B.6.2.6.3"],
        "ah_category": "database",
        "tagline": "Time-series warehouse with hypertables for sensor readings, predictions and OEE KPIs.",
        "keywords": ["iso42001", "platform", "data-management", "timescaledb", "time-series", "oee", "kpi"],
    },
    "platform-grafana": {
        "path": "catalog/platform/monitoring/grafana",
        "tier": "platform", "category": "Monitoring",
        "display": "Grafana",
        "iso_clauses": ["B.6.1.3.1", "B.6.1.3.3", "B.6.2.6.2"],
        "ah_category": "monitoring-logging",
        "tagline": "Dashboards for OEE, model health, infrastructure and operator feedback; Keycloak OIDC ready.",
        "keywords": ["iso42001", "platform", "monitoring", "dashboards", "grafana", "oidc"],
    },
    "platform-loki": {
        "path": "catalog/platform/monitoring/loki",
        "tier": "platform", "category": "Monitoring",
        "display": "Loki",
        "iso_clauses": ["B.6.2.8.1"],
        "ah_category": "monitoring-logging",
        "tagline": "Centralised log aggregation with long retention for ISO/IEC 42001 audit-trail compliance.",
        "keywords": ["iso42001", "platform", "monitoring", "logging", "loki", "audit-trail"],
    },
    "platform-prometheus": {
        "path": "catalog/platform/monitoring/prometheus",
        "tier": "platform", "category": "Monitoring",
        "display": "Prometheus + Alertmanager",
        "iso_clauses": ["B.6.1.2.2", "B.6.2.6.2", "B.8.0.5.1"],
        "ah_category": "monitoring-logging",
        "tagline": "kube-prometheus-stack with custom AI alert rules for latency, error rate and model drift.",
        "keywords": ["iso42001", "platform", "monitoring", "prometheus", "alertmanager", "kube-prometheus-stack"],
    },
    "platform-rancher": {
        "path": "catalog/platform/orchestration/rancher",
        "tier": "platform", "category": "Orchestration",
        "display": "Rancher",
        "iso_clauses": ["B.6.2.5.1"],
        "ah_category": "integration-delivery",
        "tagline": "Multi-cluster Kubernetes management UI with audit logging and cert-manager TLS.",
        "keywords": ["iso42001", "platform", "orchestration", "rancher", "multi-cluster", "k3s"],
    },
    "platform-argocd": {
        "path": "catalog/platform/orchestration/argocd",
        "tier": "platform", "category": "Orchestration",
        "display": "Argo CD",
        "iso_clauses": ["B.6.2.5.1", "B.6.2.6.4", "B.6.2.8.1"],
        "ah_category": "integration-delivery",
        "tagline": "GitOps controller that reconciles the declared state of the catalog against the cluster, providing an immutable change-management audit trail.",
        "keywords": ["iso42001", "platform", "orchestration", "gitops", "argocd", "continuous-delivery"],
    },
    "platform-vault": {
        "path": "catalog/platform/security/vault",
        "tier": "platform", "category": "Security",
        "display": "HashiCorp Vault",
        "iso_clauses": ["B.6.1.3.3", "B.6.1.4.1", "B.8.0.2.1"],
        "ah_category": "security",
        "tagline": "Centralised secrets manager with KV, PKI and database engines; provides dynamic credentials and encryption keys to every tier via External Secrets.",
        "keywords": ["iso42001", "platform", "security", "vault", "secrets", "pki", "kms"],
    },
    "platform-cert-manager": {
        "path": "catalog/platform/security/cert-manager",
        "tier": "platform", "category": "Security",
        "display": "cert-manager",
        "iso_clauses": ["B.6.1.4.1", "B.6.2.3.1"],
        "ah_category": "security",
        "tagline": "Automated X.509 certificate provisioning and renewal (ACME, self-signed, Vault PKI) for every ingress endpoint in the reference architecture.",
        "keywords": ["iso42001", "platform", "security", "cert-manager", "tls", "acme", "letsencrypt", "pki"],
    },

    # ── Enterprise ───────────────────────────────────────────────────────
    "enterprise-keycloak": {
        "path": "catalog/enterprise/access-management/keycloak",
        "tier": "enterprise", "category": "Access Management",
        "display": "Keycloak",
        "iso_clauses": ["B.6.1.3.1", "B.8.0.2.1"],
        "ah_category": "security",
        "tagline": "Identity provider with AI system realm, RBAC roles and pre-configured OIDC clients.",
        "keywords": ["iso42001", "enterprise", "access-management", "keycloak", "identity", "oidc", "rbac"],
    },
    "enterprise-grafana-dashboards": {
        "path": "catalog/enterprise/dashboards/grafana",
        "tier": "enterprise", "category": "Dashboards",
        "display": "Grafana Dashboards (Overlay)",
        "iso_clauses": ["B.6.1.3.3", "B.6.2.6.2"],
        "ah_category": "monitoring-logging",
        "tagline": "Pre-built dashboards for OEE, model health, security events and operator feedback.",
        "keywords": ["iso42001", "enterprise", "dashboards", "grafana", "oee", "feedback"],
    },
    "enterprise-minio-overlay": {
        "path": "catalog/enterprise/document-store/minio",
        "tier": "enterprise", "category": "Document Store",
        "display": "MinIO Docs Overlay",
        "iso_clauses": ["B.6.2.3.1", "B.6.2.6.5"],
        "ah_category": "storage",
        "tagline": "Overlay buckets for ISO/IEC 42001 compliance documentation, model cards and audit evidence with object locking.",
        "keywords": ["iso42001", "enterprise", "document-store", "minio", "compliance", "audit-evidence"],
    },
    "enterprise-zammad": {
        "path": "catalog/enterprise/helpdesk/zammad",
        "tier": "enterprise", "category": "Helpdesk",
        "display": "Zammad",
        "iso_clauses": ["B.6.2.6.6", "B.8.0.4.1", "B.8.0.5.1"],
        "ah_category": "integration-delivery",
        "tagline": "Incident management with webhook integration for Prometheus alerts and SMTP notifications.",
        "keywords": ["iso42001", "enterprise", "helpdesk", "zammad", "ticketing", "incident-response"],
    },
}


# ─────────────────────────────────────────────────────────── SVG Icon set ──

TIER_COLORS = {
    "edge":       {"bg1": "#065f46", "bg2": "#10b981", "fg": "#ffffff"},
    "platform":   {"bg1": "#1e40af", "bg2": "#3b82f6", "fg": "#ffffff"},
    "enterprise": {"bg1": "#92400e", "bg2": "#f59e0b", "fg": "#ffffff"},
}

ICON_GLYPHS = {
    "edge-fastapi-model":       ("\u26a1", "API"),
    "edge-kafka":               ("\u224b", "KFK"),
    "edge-mosquitto":           ("\u25c9", "MQTT"),
    "edge-node-red":            ("\u25cf", "NR"),
    "edge-opc-ua-gateway":      ("\u29c9", "OPC"),
    "edge-fluent-bit":          ("\u2261", "LOG"),
    "edge-prometheus-agent":    ("\u25c7", "MET"),
    "edge-falco":               ("\u2b22", "SEC"),
    "edge-mongodb":             ("\u2b2d", "NoSQL"),
    "edge-postgresql":          ("\u25a3", "PG"),

    "platform-mlflow":          ("\u2699", "ML"),
    "platform-training-jobs":   ("\u21bb", "JOB"),
    "platform-evidently":       ("\u223f", "DRIFT"),
    "platform-minio":           ("\u25a6", "S3"),
    "platform-postgresql":      ("\u25a3", "PG"),
    "platform-timescaledb":     ("\u231b", "TS"),
    "platform-grafana":         ("\u25c8", "DASH"),
    "platform-loki":            ("\u2261", "LOG"),
    "platform-prometheus":      ("\u25c7", "MET"),
    "platform-rancher":         ("\u2388", "RNC"),
    "platform-argocd":          ("\u21bb", "GIT"),
    "platform-vault":           ("\u26c1", "VAULT"),
    "platform-cert-manager":    ("\u2713", "TLS"),

    "enterprise-keycloak":      ("\u2b18", "IAM"),
    "enterprise-grafana-dashboards": ("\u25c8", "OEE"),
    "enterprise-minio-overlay": ("\u25a6", "DOC"),
    "enterprise-zammad":        ("\u2709", "HELP"),
}


def make_icon_svg(chart_name: str) -> str:
    meta = CHART_META[chart_name]
    colors = TIER_COLORS[meta["tier"]]
    glyph, caption = ICON_GLYPHS[chart_name]
    cap_font = 15 if len(caption) <= 3 else 12 if len(caption) == 4 else 10

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96">\n'
        '  <defs>\n'
        f'    <linearGradient id="g-{chart_name}" x1="0" y1="0" x2="1" y2="1">\n'
        f'      <stop offset="0%"  stop-color="{colors["bg1"]}"/>\n'
        f'      <stop offset="100%" stop-color="{colors["bg2"]}"/>\n'
        '    </linearGradient>\n'
        f'    <filter id="s-{chart_name}" x="-10%" y="-10%" width="120%" height="120%">\n'
        '      <feGaussianBlur in="SourceAlpha" stdDeviation="1.2"/>\n'
        '      <feOffset dx="0" dy="1" result="offsetblur"/>\n'
        '      <feComponentTransfer><feFuncA type="linear" slope="0.35"/></feComponentTransfer>\n'
        '      <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>\n'
        '    </filter>\n'
        '  </defs>\n'
        f'  <rect x="4" y="4" width="88" height="88" rx="14" ry="14" fill="url(#g-{chart_name})"/>\n'
        f'  <text x="48" y="56" text-anchor="middle" dominant-baseline="middle" '
        f'font-family="system-ui, -apple-system, sans-serif" font-size="40" font-weight="700" '
        f'fill="{colors["fg"]}" filter="url(#s-{chart_name})">{glyph}</text>\n'
        f'  <text x="48" y="80" text-anchor="middle" '
        f'font-family="system-ui, -apple-system, sans-serif" font-size="{cap_font}" '
        f'font-weight="700" letter-spacing="1" fill="{colors["fg"]}" fill-opacity="0.95">{caption}</text>\n'
        '</svg>\n'
    )


# ──────────────────────────────────────────────────── README.md template ──

README_TEMPLATE = """# {display} — `{name}`

> {tagline}

[\![Tier](https://img.shields.io/badge/tier-{tier}-{badge_color})](#) [\![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [\![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [MLOps ISO/IEC 42001 K3s Catalog]({source}) — a companion resource
to the reference architecture described in *Mateo-Casali et al. (2025), Reference
Architecture for the Design and Implementation of AI Systems in Manufacturing
in Conformity to ISO/IEC 42001*.

---

## Overview

- **Tier**: `{tier}`
- **Category**: `{category}`
- **ISO/IEC 42001 Annex B clauses covered**: {iso_str}

{description_block}

---

## Quick start

```bash
# Add the Helm repository
helm repo add cigip-upv {repo_url}
helm repo update

# Install this chart
helm install {short_name} cigip-upv/{name} \\
  --namespace {namespace} \\
  --create-namespace
```

Alternatively, clone the repository and install from the manifests folder:

```bash
git clone {source}
cd MLOps-ISO42001-K3s-Catalog/{rel_path}/manifests
helm dependency update .
helm install {short_name} . -n {namespace} --create-namespace
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml).
For a Rancher-driven deployment, the friendly questionnaire lives in
[`questions.yaml`](./manifests/questions.yaml); Rancher will render one form
field per declared question when the chart is installed from the catalog.

Override any value at install time:

```bash
helm install {short_name} cigip-upv/{name} \\
  --namespace {namespace} --create-namespace \\
  --set someKey=someValue
```

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
{iso_rows}

The mapping is maintained at the catalog level in the root [`README.md`]({source}#iso-42001-annex-b-coverage).

---

## Maintainer

- **{maintainer_name}** — *{maintainer_url}* — `{maintainer_email}`

Released under the Apache 2.0 License.
"""


ISO_REQS = {
    "B.6.1.2.2":  "Resources — Monitoring Performance",
    "B.6.1.3.1":  "Resources — Access Control",
    "B.6.1.3.2":  "Resources — Version Control",
    "B.6.1.3.3":  "Resources — Human Oversight / Feedback",
    "B.6.1.3.4":  "Resources — Inventory / Registry",
    "B.6.2.3.1":  "Planning — System Documentation",
    "B.6.2.5.1":  "Planning — Deployment Plan",
    "B.6.2.6.1":  "Operation — Infrastructure Monitoring",
    "B.6.2.6.2":  "Operation — Model Performance",
    "B.6.2.6.3":  "Operation — KPI Assessment (OEE)",
    "B.6.2.6.4":  "Operation — Retraining / Lifecycle",
    "B.6.2.6.5":  "Operation — Update & Repair Plan",
    "B.6.2.6.6":  "Operation — Incident Communication",
    "B.6.2.6.7":  "Operation — Security Monitoring",
    "B.6.2.8.1":  "Operation — Logging / Audit Trail",
    "B.8.0.2.1":  "Continual Improvement — Roles",
    "B.8.0.4.1":  "Continual Improvement — Helpdesk",
    "B.8.0.5.1":  "Continual Improvement — Alerts",
}


# ───────────────────────────────────────────────────────────────── Helpers ──

def yaml_dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, default_flow_style=False,
                          allow_unicode=True, width=120)


def enrich_chart_yaml(chart_name: str) -> tuple[pathlib.Path, dict]:
    meta = CHART_META[chart_name]
    chart_dir = ROOT / meta["path"]
    chart_yaml = chart_dir / "manifests" / "Chart.yaml"

    data = yaml.safe_load(chart_yaml.read_text(encoding="utf-8")) or {}

    data["apiVersion"] = "v2"
    data["name"] = chart_name
    data["type"] = data.get("type", "application")
    data["version"] = NEW_CHART_VERSION
    data["appVersion"] = str(data.get("appVersion", "1.0.0"))
    data["kubeVersion"] = ">=1.24.0-0"
    data["description"] = meta["tagline"]
    data["icon"] = f"{REPO_URL}/icons/{chart_name}.svg"
    data["home"] = REPO_URL
    data["sources"] = [SOURCE_REPO]
    data["keywords"] = meta["keywords"]
    data["maintainers"] = [MAINTAINER.copy()]
    data["annotations"] = {
        "category": meta["category"],
        "artifacthub.io/category": meta["ah_category"],
        "artifacthub.io/license": "Apache-2.0",
        "artifacthub.io/links": json.dumps([
            {"name": "source",  "url": SOURCE_REPO},
            {"name": "catalog", "url": REPO_URL},
        ]),
        "mlops-iso42001.cigip-upv.es/tier": meta["tier"],
        "mlops-iso42001.cigip-upv.es/display-name": meta["display"],
        "mlops-iso42001.cigip-upv.es/iso42001-clauses": ", ".join(meta["iso_clauses"]),
        "mlops-iso42001.cigip-upv.es/reference-architecture":
            "Mateo-Casali et al. (2025) — RA for AI Systems in Manufacturing in Conformity to ISO/IEC 42001",
    }

    field_order = [
        "apiVersion", "name", "type", "version", "appVersion", "kubeVersion",
        "description", "icon", "home", "sources", "keywords",
        "maintainers", "annotations", "dependencies",
    ]
    ordered = {k: data[k] for k in field_order if k in data}
    for k, v in data.items():
        ordered.setdefault(k, v)

    chart_yaml.write_text(
        "# Auto-generated / enriched by infrastructure/publish.py\n"
        "# Source of truth for the Chart metadata displayed in Rancher and ArtifactHub.\n"
        + yaml_dump(ordered),
        encoding="utf-8",
    )
    return chart_yaml, ordered


def ensure_readme(chart_name: str, data: dict) -> None:
    meta = CHART_META[chart_name]
    chart_dir = ROOT / meta["path"]
    readme_path = chart_dir / "README.md"
    if readme_path.exists():
        return

    iso_rows = "\n".join(
        f"| `{c}` | {ISO_REQS.get(c, 'ISO/IEC 42001 Annex B requirement')} |"
        for c in meta["iso_clauses"]
    )
    iso_str = ", ".join(f"`{c}`" for c in meta["iso_clauses"])

    badge_color = {"edge": "065f46", "platform": "1e40af", "enterprise": "92400e"}[meta["tier"]]
    short_name = chart_name.split("-", 1)[1] if "-" in chart_name else chart_name
    namespace = meta["tier"]
    rel_path = meta["path"]

    description_block = (
        f"This chart packages **{meta['display']}** for the **{meta['tier']}** tier "
        f"of the reference architecture, covering the *{meta['category']}* "
        f"capability block. It ships with production-ready defaults for K3s and "
        f"a Rancher-compatible `questions.yaml`, so operators can deploy the "
        f"component from the Rancher UI with guided prompts for every "
        f"configuration variable."
    )

    readme_path.write_text(
        README_TEMPLATE.format(
            name=chart_name, short_name=short_name, display=meta["display"],
            tagline=meta["tagline"], tier=meta["tier"], category=meta["category"],
            namespace=namespace, iso_str=iso_str, iso_rows=iso_rows,
            badge_color=badge_color, description_block=description_block,
            source=SOURCE_REPO, repo_url=REPO_URL, rel_path=rel_path,
            maintainer_name=MAINTAINER["name"],
            maintainer_email=MAINTAINER["email"],
            maintainer_url=MAINTAINER["url"],
        ),
        encoding="utf-8",
    )


def package_chart(chart_name: str, chart_data: dict) -> pathlib.Path:
    meta = CHART_META[chart_name]
    src = ROOT / meta["path"] / "manifests"
    chart_readme = ROOT / meta["path"] / "README.md"
    version = chart_data["version"]
    out_tgz = CHARTS_DIR / f"{chart_name}-{version}.tgz"

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    if out_tgz.exists():
        out_tgz.unlink()

    with tarfile.open(out_tgz, "w:gz") as tar:
        for p in sorted(src.rglob("*")):
            if p.is_dir():
                continue
            arcname = f"{chart_name}/{p.relative_to(src).as_posix()}"
            tar.add(p, arcname=arcname)
        if chart_readme.exists():
            tar.add(chart_readme, arcname=f"{chart_name}/README.md")

    return out_tgz


def file_digest(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_index(packaged: list[tuple[str, dict, pathlib.Path]]) -> pathlib.Path:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000000000Z")
    entries: dict[str, list[dict]] = {}

    for chart_name, data, tgz in packaged:
        entry = {
            "apiVersion": data["apiVersion"],
            "name": data["name"],
            "type": data.get("type", "application"),
            "version": data["version"],
            "appVersion": data["appVersion"],
            "kubeVersion": data["kubeVersion"],
            "description": data["description"],
            "icon": data["icon"],
            "home": data["home"],
            "sources": data["sources"],
            "keywords": data["keywords"],
            "maintainers": data["maintainers"],
            "annotations": data["annotations"],
            "urls": [f"{REPO_URL}/charts/{tgz.name}"],
            "created": now,
            "digest": file_digest(tgz),
        }
        if "dependencies" in data:
            entry["dependencies"] = data["dependencies"]
        entries.setdefault(chart_name, []).append(entry)

    index = {"apiVersion": "v1", "generated": now, "entries": entries}
    path = DOCS / "index.yaml"
    path.write_text(yaml_dump(index), encoding="utf-8")
    return path


# ─────────────────────────────────────────────── docs/index.html rewrite ──

def render_index_html(packaged: list[tuple[str, dict, pathlib.Path]]) -> None:
    html_path = DOCS / "index.html"
    html = html_path.read_text(encoding="utf-8")

    items = []
    for chart_name, data, tgz in sorted(
        packaged,
        key=lambda x: (
            {"edge": 0, "platform": 1, "enterprise": 2}[CHART_META[x[0]]["tier"]],
            CHART_META[x[0]]["category"],
            x[0],
        ),
    ):
        meta = CHART_META[chart_name]
        items.append(
            "  { "
            f'name: "{chart_name}", '
            f'display: "{meta["display"]}", '
            f'tier: "{meta["tier"]}", '
            f'category: "{meta["category"]}", '
            f'iso: "{", ".join(meta["iso_clauses"])}", '
            f'version: "{data["version"]}", '
            f'appVersion: "{data["appVersion"]}", '
            f'desc: {json.dumps(meta["tagline"])}, '
            f'icon: "{REPO_URL}/icons/{chart_name}.svg", '
            f'tgz:  "{REPO_URL}/charts/{tgz.name}" '
            "}"
        )
    new_array = "const charts = [\n" + ",\n".join(items) + "\n];"

    html_new = re.sub(
        r"const charts = \[.*?^\];",
        lambda m: new_array,
        html,
        count=1,
        flags=re.DOTALL | re.MULTILINE,
    )

    new_render_js = '''function renderCards(filter) {
  const container = document.getElementById('cards-container');
  const filtered = filter === 'all' ? charts : charts.filter(c => c.tier === filter);

  container.innerHTML = filtered.map(c => `
    <div class="card">
      <div class="card-head">
        <img class="card-icon" src="${c.icon}" alt="${c.name} icon" loading="lazy" onerror="this.style.display='none'"/>
        <div class="card-titles">
          <div class="card-name">${c.name}</div>
          <div class="card-display">${c.display}</div>
        </div>
      </div>
      <div class="card-desc">${c.desc}</div>
      <div class="card-tags">
        <span class="tag tag-${c.tier}">${c.tier}</span>
        <span class="tag tag-iso">${c.category}</span>
        ${c.iso && c.iso \!== '\\u2014' ? `<span class="tag tag-iso">${c.iso}</span>` : ''}
      </div>
      <div class="card-footer">
        <span class="card-version">v${c.version} \\u00b7 app ${c.appVersion}</span>
        <a class="card-dl" href="${c.tgz}" title="Download chart">
          <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M7.25 1.75a.75.75 0 011.5 0v7.69l2.22-2.22a.75.75 0 111.06 1.06l-3.5 3.5a.75.75 0 01-1.06 0l-3.5-3.5a.75.75 0 111.06-1.06l2.22 2.22V1.75zM2.25 13.5a.75.75 0 000 1.5h11.5a.75.75 0 000-1.5H2.25z"/></svg>
          .tgz
        </a>
      </div>
    </div>
  `).join('');
}'''
    html_new = re.sub(
        r"function renderCards\(filter\) \{.*?\n\}",
        lambda m: new_render_js,
        html_new,
        count=1,
        flags=re.DOTALL,
    )

    extra_css = """
    /* --- Card (augmented) --- */
    .card { display: flex; flex-direction: column; gap: .6rem; }
    .card-head { display: flex; align-items: center; gap: .8rem; }
    .card-icon {
      width: 40px; height: 40px; border-radius: 8px; flex-shrink: 0;
      background: #f9fafb; object-fit: contain;
      border: 1px solid #e5e7eb;
    }
    .card-titles { min-width: 0; }
    .card-display {
      font-size: .75rem; color: #6b7280; font-weight: 500;
      margin-top: .1rem;
    }
    .card-footer {
      display: flex; align-items: center; justify-content: space-between;
      border-top: 1px solid #f3f4f6; padding-top: .6rem; margin-top: .2rem;
    }
    .card-version {
      font-family: 'JetBrains Mono', monospace; font-size: .7rem;
      color: #6b7280;
    }
    .card-dl {
      display: inline-flex; align-items: center; gap: .3rem;
      font-size: .75rem; font-weight: 600; color: #b91c1c;
      padding: .25rem .55rem; border: 1px solid #fecaca;
      border-radius: 6px; transition: background .2s, color .2s;
    }
    .card-dl:hover { background: #fef2f2; }
    .card-dl svg { width: 12px; height: 12px; }
"""
    html_new = html_new.replace("</style>", extra_css + "  </style>", 1)

    from collections import Counter
    counts = Counter(CHART_META[n]["tier"] for n, _, _ in packaged)
    total = sum(counts.values())
    html_new = re.sub(
        r'onclick="showTier\(\'all\'\)">All <span class="tab-count">\d+</span>',
        f'onclick="showTier(\'all\')">All <span class="tab-count">{total}</span>',
        html_new,
    )
    for tier, label in (("edge", "Edge"), ("platform", "Platform"), ("enterprise", "Enterprise")):
        html_new = re.sub(
            rf'onclick="showTier\(\'{tier}\'\)">{label} <span class="tab-count">\d+</span>',
            f'onclick="showTier(\'{tier}\')">{label} <span class="tab-count">{counts.get(tier, 0)}</span>',
            html_new,
        )

    html_path.write_text(html_new, encoding="utf-8")


def main() -> int:
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    for chart_name in CHART_META:
        (ICONS_DIR / f"{chart_name}.svg").write_text(
            make_icon_svg(chart_name), encoding="utf-8"
        )
    print(f"[icons] wrote {len(CHART_META)} SVG icons \u2192 {ICONS_DIR.relative_to(ROOT)}")

    enriched: list[tuple[str, dict]] = []
    for chart_name in CHART_META:
        _, data = enrich_chart_yaml(chart_name)
        ensure_readme(chart_name, data)
        enriched.append((chart_name, data))
    print(f"[chart.yaml] enriched {len(enriched)} charts (version \u2192 {NEW_CHART_VERSION})")

    packaged: list[tuple[str, dict, pathlib.Path]] = []
    for chart_name, data in enriched:
        tgz = package_chart(chart_name, data)
        packaged.append((chart_name, data, tgz))
    print(f"[package] wrote {len(packaged)} .tgz \u2192 {CHARTS_DIR.relative_to(ROOT)}")

    idx = build_index(packaged)
    print(f"[index]   wrote {idx.relative_to(ROOT)}")

    render_index_html(packaged)
    print(f"[html]    refreshed {DOCS.relative_to(ROOT)}/index.html")

    return 0


if __name__ == "__main__":
    sys.exit(main())
