#!/usr/bin/env python3
"""
publish.py: build the Helm repository under docs/ from the catalog/ sources.

CHART_META below is the single source of truth for chart metadata. From it
the script:

    1. Enriches every Chart.yaml with icon URL, keywords, kubeVersion,
       maintainers and ArtifactHub-compatible annotations (category, licence,
       tier, namespace, ISO/IEC 42001 Annex B clauses, reference architecture
       components, display name).

    2. Writes the managed ``iso42001Labels`` block at the top of every
       values.yaml. The block is a YAML anchor that each chart references to
       stamp the ``iso42001`` traceability labels on every resource it renders
       (own templates through the chart helpers, wrapper charts through the
       label hooks of the upstream chart). It also rewrites the
       ``# ISO/IEC 42001:`` line of the values.yaml header.

    3. Creates a README.md for every chart that does not already have one.

    4. Generates missing SVG icons under docs/icons/ (curated icons are kept).

    5. Packages each chart with ``helm dependency build`` and ``helm package``
       (so wrapper charts ship with their subcharts) into docs/charts/.

    6. Regenerates docs/index.yaml (Helm repository index).

    7. Refreshes docs/index.html (chart cards, tier counters, architecture
       overview and ISO/IEC 42001 coverage table).

All changes are local. No git commits, no pushes. The GitHub Pages workflow
runs this same script, so the published .tgz files are always built from the
committed sources.

Run:
    python3 infrastructure/publish.py                 # full build
    python3 infrastructure/publish.py --skip-package  # metadata only
    python3 infrastructure/publish.py --update-locks  # refresh Chart.lock files
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from typing import Any

import yaml


# ───────────────────────────────────────────────────────────── Paths / URLs ──

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
DOCS = ROOT / "docs"
CHARTS_DIR = DOCS / "charts"
ICONS_DIR = DOCS / "icons"

# CATALOG_REPO_URL overrides the published URL (e.g. to test a local copy).
REPO_URL = os.environ.get("CATALOG_REPO_URL", "https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog").rstrip("/")
REPO_ALIAS = "cigip-upv"
SOURCE_REPO = "https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog"
MAINTAINER = {
    "name": "CIGIP-UPV",
    "email": "cigip@upv.es",
    "url": "https://cigip.webs.upv.es/",
}

# Prefix shared by the Chart.yaml annotations and the traceability labels.
META_PREFIX = "mlops-iso42001.cigip-upv.es"


# ───────────────────────────────────────────────────────── Chart metadata ──

NEW_CHART_VERSION = "0.3.0"

# Each entry:
#   path        chart folder (README.md + manifests/)
#   tier        edge | platform | enterprise
#   namespace   namespace used by install.sh (see infrastructure/00-namespaces.yaml)
#   components  reference architecture components (Annex A of the thesis)
#   iso_clauses ISO/IEC 42001 Annex B clauses (keys of ISO_REQS)
CHART_META: dict[str, dict[str, Any]] = {
    # ── Edge ─────────────────────────────────────────────────────────────
    "edge-fastapi-model": {
        "path": "catalog/edge/ai-inference/fastapi-model",
        "tier": "edge", "namespace": "edge", "category": "AI Inference",
        "display": "FastAPI Model Server",
        "components": ["CMP-04", "CMP-10"],
        "iso_clauses": ["B.6.2.6.2", "B.6.2.6.4"],
        "ah_category": "ai-machine-learning",
        "tagline": "Edge inference service that serves the MLflow model version synchronised to the edge, with hot reload, version endpoint and Prometheus model metrics.",
        "keywords": ["iso42001", "edge", "ai-inference", "fastapi", "model-server", "mlops", "inference"],
    },
    "edge-kafka": {
        "path": "catalog/edge/data-ingestion/kafka",
        "tier": "edge", "namespace": "edge", "category": "Data Ingestion",
        "display": "Apache Kafka (Edge)",
        "components": ["CMP-01"],
        "iso_clauses": ["B.6.2.6.4", "B.6.2.8.1"],
        "ah_category": "streaming-messaging",
        "tagline": "Distributed event streaming on K3s with KRaft mode; pre-configured topics for sensor data, predictions and alerts.",
        "keywords": ["iso42001", "edge", "data-ingestion", "kafka", "streaming", "event-bus", "kraft"],
    },
    "edge-mosquitto": {
        "path": "catalog/edge/data-ingestion/mosquitto",
        "tier": "edge", "namespace": "edge", "category": "Data Ingestion",
        "display": "Eclipse Mosquitto",
        "components": ["CMP-01"],
        "iso_clauses": ["B.6.1.3.1", "B.6.2.6.4"],
        "ah_category": "streaming-messaging",
        "tagline": "Lightweight MQTT broker for plant-floor sensor telemetry with authentication and WebSocket support.",
        "keywords": ["iso42001", "edge", "mqtt", "data-ingestion", "broker", "sensors", "iot"],
    },
    "edge-rabbitmq": {
        "path": "catalog/edge/data-ingestion/rabbitmq",
        "tier": "edge", "namespace": "edge", "category": "Data Ingestion",
        "display": "RabbitMQ (Edge)",
        "components": ["CMP-01"],
        "iso_clauses": ["B.6.2.6.4", "B.6.2.8.1"],
        "ah_category": "streaming-messaging",
        "tagline": "Lightweight AMQP message broker for edge ingestion with store-and-forward buffering, management UI and Prometheus metrics.",
        "keywords": ["iso42001", "edge", "data-ingestion", "rabbitmq", "amqp", "broker", "message-queue", "store-and-forward"],
    },
    "edge-node-red": {
        "path": "catalog/edge/data-ingestion/node-red",
        "tier": "edge", "namespace": "edge", "category": "Data Ingestion",
        "display": "Node-RED",
        "components": ["CMP-01"],
        "iso_clauses": ["B.6.2.6.4"],
        "ah_category": "integration-delivery",
        "tagline": "Low-code flow editor for sensor data acquisition, MQTT routing and OPC-UA / REST integration.",
        "keywords": ["iso42001", "edge", "data-ingestion", "node-red", "low-code", "opc-ua", "mqtt"],
    },
    "edge-opc-ua-gateway": {
        "path": "catalog/edge/data-ingestion/opc-ua-gateway",
        "tier": "edge", "namespace": "edge", "category": "Data Ingestion",
        "display": "OPC-UA Gateway",
        "components": ["CMP-01"],
        "iso_clauses": ["B.6.1.3.1", "B.6.2.6.4"],
        "ah_category": "integration-delivery",
        "tagline": "OPC UA to MQTT/Kafka bridge (Telegraf) that reads tags from PLC/SCADA endpoints and forwards them into the edge event bus.",
        "keywords": ["iso42001", "edge", "data-ingestion", "opc-ua", "gateway", "telegraf", "plc", "scada"],
    },
    "edge-fluent-bit": {
        "path": "catalog/edge/monitoring/fluent-bit",
        "tier": "edge", "namespace": "logging", "category": "Monitoring",
        "display": "Fluent Bit",
        "components": ["CMP-09"],
        "iso_clauses": ["B.6.2.8.1"],
        "ah_category": "monitoring-logging",
        "tagline": "DaemonSet log forwarder shipping container logs to Loki with Kubernetes metadata for audit-trail compliance.",
        "keywords": ["iso42001", "edge", "monitoring", "logging", "fluent-bit", "audit-trail"],
    },
    "edge-prometheus-agent": {
        "path": "catalog/edge/monitoring/prometheus-agent",
        "tier": "edge", "namespace": "edge", "category": "Monitoring",
        "display": "Prometheus Agent",
        "components": ["CMP-08", "CMP-10"],
        "iso_clauses": ["B.6.1.2.2", "B.6.2.6.1"],
        "ah_category": "monitoring-logging",
        "tagline": "Prometheus in agent mode: scrapes edge workloads (including the model server metrics) and forwards them to the platform via remote-write.",
        "keywords": ["iso42001", "edge", "monitoring", "metrics", "prometheus", "remote-write"],
    },
    "edge-falco": {
        "path": "catalog/edge/security/falco",
        "tier": "edge", "namespace": "falco", "category": "Security",
        "display": "Falco",
        "components": ["CMP-15"],
        "iso_clauses": ["B.6.2.6.7", "B.6.2.8.1"],
        "ah_category": "security",
        "tagline": "Runtime threat detection with eBPF drivers and custom rules for AI model file access and container anomalies, on edge and platform nodes.",
        "keywords": ["iso42001", "edge", "security", "runtime-security", "falco", "ebpf"],
    },
    "edge-mongodb": {
        "path": "catalog/edge/storage/mongodb",
        "tier": "edge", "namespace": "edge", "category": "Storage",
        "display": "MongoDB (Edge Buffer)",
        "components": ["CMP-02"],
        "iso_clauses": ["B.6.2.6.1"],
        "ah_category": "database",
        "tagline": "Document buffer with TTL indexes for automatic cleanup of raw sensor events at the edge.",
        "keywords": ["iso42001", "edge", "storage", "mongodb", "document-store", "buffer"],
    },
    "edge-postgresql": {
        "path": "catalog/edge/storage/postgresql",
        "tier": "edge", "namespace": "edge", "category": "Storage",
        "display": "PostgreSQL (Edge Cache)",
        "components": ["CMP-02"],
        "iso_clauses": ["B.6.2.6.1", "B.6.2.6.3", "B.6.2.8.1"],
        "ah_category": "database",
        "tagline": "Edge data stock initialised with sensor readings, predictions, feedback, model version and audit tables.",
        "keywords": ["iso42001", "edge", "storage", "postgresql", "feature-store", "prediction-cache"],
    },
    "edge-postgresql-sync": {
        "path": "catalog/edge/storage/postgresql-sync",
        "tier": "edge", "namespace": "edge", "category": "Storage",
        "display": "Edge Data Consolidation",
        "components": ["CMP-02"],
        "iso_clauses": ["B.6.2.6.1", "B.6.2.8.1"],
        "ah_category": "database",
        "tagline": "Incremental, watermark-based consolidation of the edge data stock into the platform data stock, with a batch log for data provenance.",
        "keywords": ["iso42001", "edge", "storage", "postgresql", "data-consolidation", "sync"],
    },
    "edge-mlflow-sync": {
        "path": "catalog/edge/version-control/mlflow-sync",
        "tier": "edge", "namespace": "edge", "category": "Version Control",
        "display": "Edge Version Control (MLflow Sync)",
        "components": ["CMP-03"],
        "iso_clauses": ["B.6.1.3.2", "B.6.2.6.4", "B.6.2.8.1"],
        "ah_category": "ai-machine-learning",
        "tagline": "Propagates the model version promoted in the platform MLflow registry to the edge: downloads it, records the version history and hot-reloads the edge model server.",
        "keywords": ["iso42001", "edge", "version-control", "mlflow", "model-registry", "gitops"],
    },

    # ── Platform ─────────────────────────────────────────────────────────
    "platform-mlflow": {
        "path": "catalog/platform/ai-lifecycle/mlflow",
        "tier": "platform", "namespace": "mlops", "category": "AI Lifecycle",
        "display": "MLflow",
        "components": ["CMP-03"],
        "iso_clauses": ["B.6.1.3.2", "B.6.1.3.4", "B.6.2.6.4"],
        "ah_category": "ai-machine-learning",
        "tagline": "Experiment tracking, model registry and artefact storage backed by PostgreSQL and MinIO.",
        "keywords": ["iso42001", "platform", "ai-lifecycle", "mlflow", "model-registry", "experiment-tracking"],
    },
    "platform-training-jobs": {
        "path": "catalog/platform/ai-lifecycle/training-jobs",
        "tier": "platform", "namespace": "mlops", "category": "AI Lifecycle",
        "display": "Training Jobs",
        "components": ["CMP-04", "CMP-14"],
        "iso_clauses": ["B.6.2.6.4"],
        "ah_category": "ai-machine-learning",
        "tagline": "Model training pipeline: scheduled CronJob and on-demand Job that train on the consolidated platform data and register the model in MLflow.",
        "keywords": ["iso42001", "platform", "ai-lifecycle", "training", "retraining", "cronjob", "mlops"],
    },
    "platform-evidently": {
        "path": "catalog/platform/ai-lifecycle/evidently",
        "tier": "platform", "namespace": "mlops", "category": "AI Lifecycle",
        "display": "Evidently AI",
        "components": ["CMP-10", "CMP-14"],
        "iso_clauses": ["B.6.2.6.2", "B.6.2.8.1", "B.8.0.5.1"],
        "ah_category": "ai-machine-learning",
        "tagline": "Drift monitoring UI plus a scheduled drift check that records a retraining recommendation and, above the threshold, launches the retraining job.",
        "keywords": ["iso42001", "platform", "ai-lifecycle", "drift-detection", "monitoring", "mlops", "evidently"],
    },
    "platform-minio": {
        "path": "catalog/platform/data-management/minio",
        "tier": "platform", "namespace": "minio", "category": "Data Management",
        "display": "MinIO",
        "components": ["CMP-02", "CMP-05"],
        "iso_clauses": ["B.6.2.3.1", "B.6.2.5.1"],
        "ah_category": "storage",
        "tagline": "S3-compatible object storage with auto-provisioned buckets, policies and lifecycle rules.",
        "keywords": ["iso42001", "platform", "data-management", "minio", "s3", "object-storage"],
    },
    "platform-postgresql": {
        "path": "catalog/platform/data-management/postgresql",
        "tier": "platform", "namespace": "platform", "category": "Data Management",
        "display": "PostgreSQL (Platform)",
        "components": ["CMP-02"],
        "iso_clauses": ["B.6.1.3.4"],
        "ah_category": "database",
        "tagline": "Shared metadata store initialised with databases for MLflow, Keycloak, Zammad and Grafana.",
        "keywords": ["iso42001", "platform", "data-management", "postgresql", "metadata-store"],
    },
    "platform-timescaledb": {
        "path": "catalog/platform/data-management/timescaledb",
        "tier": "platform", "namespace": "platform", "category": "Data Management",
        "display": "TimescaleDB",
        "components": ["CMP-02", "CMP-11"],
        "iso_clauses": ["B.6.2.6.1", "B.6.2.6.3"],
        "ah_category": "database",
        "tagline": "Platform time-series data stock with hypertables for consolidated sensor readings, predictions and OEE KPIs.",
        "keywords": ["iso42001", "platform", "data-management", "timescaledb", "time-series", "oee", "kpi"],
    },
    "platform-grafana": {
        "path": "catalog/platform/monitoring/grafana",
        "tier": "platform", "namespace": "monitoring", "category": "Monitoring",
        "display": "Grafana",
        "components": ["CMP-06", "CMP-10", "CMP-11"],
        "iso_clauses": ["B.6.1.3.1", "B.6.1.3.3", "B.6.2.6.2"],
        "ah_category": "monitoring-logging",
        "tagline": "Dashboards for OEE, model health, infrastructure and operator feedback; Keycloak OIDC ready.",
        "keywords": ["iso42001", "platform", "monitoring", "dashboards", "grafana", "oidc"],
    },
    "platform-loki": {
        "path": "catalog/platform/monitoring/loki",
        "tier": "platform", "namespace": "monitoring", "category": "Monitoring",
        "display": "Loki",
        "components": ["CMP-09"],
        "iso_clauses": ["B.6.2.8.1"],
        "ah_category": "monitoring-logging",
        "tagline": "Centralised log aggregation stored in MinIO object storage with long retention for ISO/IEC 42001 audit-trail compliance.",
        "keywords": ["iso42001", "platform", "monitoring", "logging", "loki", "audit-trail"],
    },
    "platform-prometheus": {
        "path": "catalog/platform/monitoring/prometheus",
        "tier": "platform", "namespace": "monitoring", "category": "Monitoring",
        "display": "Prometheus + Alertmanager",
        "components": ["CMP-08", "CMP-10", "CMP-11"],
        "iso_clauses": ["B.6.1.2.2", "B.6.2.6.2", "B.8.0.5.1"],
        "ah_category": "monitoring-logging",
        "tagline": "kube-prometheus-stack with custom AI alert rules for latency, error rate and model drift.",
        "keywords": ["iso42001", "platform", "monitoring", "prometheus", "alertmanager", "kube-prometheus-stack"],
    },
    "platform-rancher": {
        "path": "catalog/platform/orchestration/rancher",
        "tier": "platform", "namespace": "cattle-system", "category": "Orchestration",
        "display": "Rancher",
        "components": [],
        "iso_clauses": ["B.6.2.5.1"],
        "ah_category": "integration-delivery",
        "tagline": "Multi-cluster Kubernetes management UI with audit logging and cert-manager TLS.",
        "keywords": ["iso42001", "platform", "orchestration", "rancher", "multi-cluster", "k3s"],
    },
    "platform-argocd": {
        "path": "catalog/platform/orchestration/argocd",
        "tier": "platform", "namespace": "argocd", "category": "Orchestration",
        "display": "Argo CD",
        "components": ["CMP-03"],
        "iso_clauses": ["B.6.2.5.1", "B.6.2.6.4", "B.6.2.8.1"],
        "ah_category": "integration-delivery",
        "tagline": "GitOps controller that reconciles the declared state of the catalog against the cluster, providing an immutable change-management audit trail.",
        "keywords": ["iso42001", "platform", "orchestration", "gitops", "argocd", "continuous-delivery"],
    },
    "platform-openbao": {
        "path": "catalog/platform/security/openbao",
        "tier": "platform", "namespace": "openbao", "category": "Security",
        "display": "OpenBao",
        "components": ["CMP-07", "CMP-15"],
        "iso_clauses": ["B.6.1.3.3", "B.6.1.4.1", "B.8.0.2.1"],
        "ah_category": "security",
        "tagline": "Centralised secrets manager with KV, PKI and database engines; provides dynamic credentials and encryption keys to every tier. Open-source (MPL 2.0) Vault-compatible alternative.",
        "keywords": ["iso42001", "platform", "security", "openbao", "secrets", "pki", "kms"],
    },
    "platform-cert-manager": {
        "path": "catalog/platform/security/cert-manager",
        "tier": "platform", "namespace": "cert-manager", "category": "Security",
        "display": "cert-manager",
        "components": ["CMP-15"],
        "iso_clauses": ["B.6.1.4.1", "B.6.2.3.1"],
        "ah_category": "security",
        "tagline": "Automated X.509 certificate provisioning and renewal (ACME, self-signed, OpenBao PKI) for every ingress endpoint in the reference architecture.",
        "keywords": ["iso42001", "platform", "security", "cert-manager", "tls", "acme", "letsencrypt", "pki"],
    },

    # ── Enterprise ───────────────────────────────────────────────────────
    "enterprise-keycloak": {
        "path": "catalog/enterprise/access-management/keycloak",
        "tier": "enterprise", "namespace": "security", "category": "Access Management",
        "display": "Keycloak",
        "components": ["CMP-07"],
        "iso_clauses": ["B.6.1.3.1", "B.8.0.2.1"],
        "ah_category": "security",
        "tagline": "Identity provider with AI system realm, RBAC roles and pre-configured OIDC clients.",
        "keywords": ["iso42001", "enterprise", "access-management", "keycloak", "identity", "oidc", "rbac"],
    },
    "enterprise-grafana-dashboards": {
        "path": "catalog/enterprise/dashboards/grafana",
        "tier": "enterprise", "namespace": "monitoring", "category": "Dashboards",
        "display": "Grafana Dashboards (Overlay)",
        "components": ["CMP-06", "CMP-11"],
        "iso_clauses": ["B.6.1.3.3", "B.6.2.6.2"],
        "ah_category": "monitoring-logging",
        "tagline": "Provisioned Grafana dashboards for OEE, model health, infrastructure, security events and the audit log.",
        "keywords": ["iso42001", "enterprise", "dashboards", "grafana", "oee", "feedback"],
    },
    "enterprise-minio-overlay": {
        "path": "catalog/enterprise/document-store/minio",
        "tier": "enterprise", "namespace": "minio", "category": "Document Store",
        "display": "MinIO Docs Overlay",
        "components": ["CMP-05"],
        "iso_clauses": ["B.6.2.3.1", "B.6.2.6.5"],
        "ah_category": "storage",
        "tagline": "Document store buckets for ISO/IEC 42001 compliance documentation, model cards and audit evidence, with versioning and object locking.",
        "keywords": ["iso42001", "enterprise", "document-store", "minio", "compliance", "audit-evidence"],
    },
    "enterprise-zammad": {
        "path": "catalog/enterprise/helpdesk/zammad",
        "tier": "enterprise", "namespace": "helpdesk", "category": "Helpdesk",
        "display": "Zammad",
        "components": ["CMP-13"],
        "iso_clauses": ["B.6.2.6.6", "B.8.0.4.1", "B.8.0.5.1"],
        "ah_category": "integration-delivery",
        "tagline": "Incident management with webhook integration for Prometheus alerts and SMTP notifications.",
        "keywords": ["iso42001", "enterprise", "helpdesk", "zammad", "ticketing", "incident-response"],
    },
}


# ─────────────────────────────────────────── ISO/IEC 42001 requirement names ──
# Single set of requirement labels used by every generated artefact
# (chart READMEs, root README, catalog README and docs/index.html).

ISO_REQS = {
    "B.6.1.2.2": "Resources: Monitoring Performance",
    "B.6.1.3.1": "Resources: Access Control",
    "B.6.1.3.2": "Resources: Version Control",
    "B.6.1.3.3": "Resources: Human Oversight / Feedback",
    "B.6.1.3.4": "Resources: Inventory / Registry",
    "B.6.1.4.1": "Resources: Security of AI Assets",
    "B.6.2.3.1": "Planning: System Documentation",
    "B.6.2.5.1": "Planning: Deployment Plan",
    "B.6.2.6.1": "Operation: Infrastructure Monitoring",
    "B.6.2.6.2": "Operation: Model Performance",
    "B.6.2.6.3": "Operation: KPI Assessment (OEE)",
    "B.6.2.6.4": "Operation: Retraining / Lifecycle",
    "B.6.2.6.5": "Operation: Update & Repair Plan",
    "B.6.2.6.6": "Operation: Incident Communication",
    "B.6.2.6.7": "Operation: Security Monitoring",
    "B.6.2.8.1": "Operation: Logging / Audit Trail",
    "B.8.0.2.1": "Continual Improvement: Roles",
    "B.8.0.4.1": "Continual Improvement: Helpdesk",
    "B.8.0.5.1": "Continual Improvement: Alerts",
}

# Reference architecture components (Annex A of the thesis).
COMPONENTS = {
    "CMP-01": "Input Data Monitoring",
    "CMP-02": "Data Stock",
    "CMP-03": "Version Control",
    "CMP-04": "Model",
    "CMP-05": "Document Store",
    "CMP-06": "Information Centre",
    "CMP-07": "User Access & Oversight",
    "CMP-08": "Infrastructure Technical Monitoring",
    "CMP-09": "Logger",
    "CMP-10": "Model Technical Performance Monitoring",
    "CMP-11": "Goal-Oriented Monitoring",
    "CMP-12": "Feedback Interface",
    "CMP-13": "AI Helpdesk",
    "CMP-14": "Retraining Recommendation",
    "CMP-15": "Security Monitoring",
}


# ─────────────────────────────────────────────────────────── SVG Icon set ──

TIER_COLORS = {
    "edge":       {"bg1": "#065f46", "bg2": "#10b981", "fg": "#ffffff"},
    "platform":   {"bg1": "#1e40af", "bg2": "#3b82f6", "fg": "#ffffff"},
    "enterprise": {"bg1": "#92400e", "bg2": "#f59e0b", "fg": "#ffffff"},
}

ICON_GLYPHS = {
    "edge-fastapi-model":       ("⚡", "API"),
    "edge-kafka":               ("≋", "KFK"),
    "edge-mosquitto":           ("◉", "MQTT"),
    "edge-rabbitmq":            ("✉", "AMQP"),
    "edge-node-red":            ("●", "NR"),
    "edge-opc-ua-gateway":      ("⧉", "OPC"),
    "edge-fluent-bit":          ("≡", "LOG"),
    "edge-prometheus-agent":    ("◇", "MET"),
    "edge-falco":               ("⬢", "SEC"),
    "edge-mongodb":             ("⬭", "NoSQL"),
    "edge-postgresql":          ("▣", "PG"),
    "edge-postgresql-sync":     ("⇄", "SYNC"),
    "edge-mlflow-sync":         ("⬇", "VER"),

    "platform-mlflow":          ("⚙", "ML"),
    "platform-training-jobs":   ("↻", "JOB"),
    "platform-evidently":       ("∿", "DRIFT"),
    "platform-minio":           ("▦", "S3"),
    "platform-postgresql":      ("▣", "PG"),
    "platform-timescaledb":     ("⌛", "TS"),
    "platform-grafana":         ("◈", "DASH"),
    "platform-loki":            ("≡", "LOG"),
    "platform-prometheus":      ("◇", "MET"),
    "platform-rancher":         ("⎈", "RNC"),
    "platform-argocd":          ("↻", "GIT"),
    "platform-openbao":         ("⛁", "BAO"),
    "platform-cert-manager":    ("✓", "TLS"),

    "enterprise-keycloak":      ("⬘", "IAM"),
    "enterprise-grafana-dashboards": ("◈", "OEE"),
    "enterprise-minio-overlay": ("▦", "DOC"),
    "enterprise-zammad":        ("✉", "HELP"),
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

README_TEMPLATE = """# {display}: `{name}`

> {tagline}

[![Tier](https://img.shields.io/badge/tier-{tier}-{badge_color})](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001]({source}).

---

## Overview

- **Tier**: `{tier}`
- **Category**: `{category}`
- **Namespace**: `{namespace}`
- **Reference architecture components**: {components_str}
- **ISO/IEC 42001 Annex B clauses covered**: {iso_str}

{description_block}

---

## Quick start

```bash
# Add the Helm repository
helm repo add {alias} {repo_url}
helm repo update

# Install this chart
helm install {name} {alias}/{name} \\
  --namespace {namespace} \\
  --create-namespace
```

Alternatively, clone the repository and install from the manifests folder:

```bash
git clone {source}
cd MLOps-ISO42001-K3s-Catalog/{rel_path}/manifests
helm dependency build .
helm install {name} . -n {namespace} --create-namespace
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml).
For a Rancher-driven deployment, the friendly questionnaire lives in
[`questions.yaml`](./manifests/questions.yaml); Rancher will render one form
field per declared question when the chart is installed from the catalog.

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
{iso_rows}

Every resource rendered by this chart carries the label `iso42001: "true"` and
one label per clause and component, for example:

```bash
kubectl get pods,svc,deploy,sts -A -l {prefix}/{first_clause}
```

The mapping is maintained at the catalog level in the root [`README.md`]({source}#isoiec-42001-coverage-summary).

---

## Maintainer

- **{maintainer_name}**, *{maintainer_url}*, `{maintainer_email}`

Released under the Apache 2.0 License.
"""


# ───────────────────────────────────────────────────────────────── Helpers ──

def yaml_dump(data: Any) -> str:
    return yaml.safe_dump(data, sort_keys=False, default_flow_style=False,
                          allow_unicode=True, width=120)


def iso_labels(chart_name: str) -> dict[str, str]:
    """Traceability labels stamped on every resource of a chart."""
    meta = CHART_META[chart_name]
    labels = {
        "iso42001": "true",
        f"{META_PREFIX}/chart": chart_name,
        f"{META_PREFIX}/tier": meta["tier"],
    }
    for clause in meta["iso_clauses"]:
        labels[f"{META_PREFIX}/{clause}"] = "true"
    for comp in meta["components"]:
        labels[f"{META_PREFIX}/{comp}"] = "true"
    return labels


LABEL_BLOCK_BEGIN = "# BEGIN iso42001-labels"
LABEL_BLOCK_END = "# END iso42001-labels"


def label_block(chart_name: str) -> str:
    lines = [
        f"{LABEL_BLOCK_BEGIN} (generated by infrastructure/publish.py from CHART_META; do not edit)",
        "# Traceability labels applied to every resource of this chart. Wrapper",
        "# charts reference the anchor from the label hooks of the upstream chart.",
        "iso42001Labels: &iso42001Labels",
    ]
    for k, v in iso_labels(chart_name).items():
        lines.append(f'  {k}: "{v}"')
    lines.append(LABEL_BLOCK_END)
    return "\n".join(lines) + "\n"


def sync_values(chart_name: str) -> None:
    """Write the managed label block and the ISO header line of values.yaml."""
    meta = CHART_META[chart_name]
    path = ROOT / meta["path"] / "manifests" / "values.yaml"
    text = path.read_text(encoding="utf-8")

    block = label_block(chart_name)
    pattern = re.compile(re.escape(LABEL_BLOCK_BEGIN) + r".*?" + re.escape(LABEL_BLOCK_END) + r"\n", re.DOTALL)
    if pattern.search(text):
        text = pattern.sub(lambda m: block, text, count=1)
    else:
        lines = text.splitlines(keepends=True)
        # Insert after the leading comment header (and the blank line after it).
        i = 0
        while i < len(lines) and lines[i].startswith("#"):
            i += 1
        head, tail = "".join(lines[:i]), "".join(lines[i:]).lstrip("\n")
        text = head + ("\n" if head else "") + block + "\n" + tail

    # Header: one canonical ISO line, continuation lines removed.
    iso_line = f"# ISO/IEC 42001: {', '.join(meta['iso_clauses'])}\n"
    out, skipping = [], False
    for line in text.splitlines(keepends=True):
        if line.startswith("# ISO/IEC 42001:") and not out_has_iso(out):
            out.append(iso_line)
            skipping = True
            continue
        if skipping and re.match(r"^#\s{3,}\S", line):
            continue
        skipping = False
        out.append(line)
    path.write_text("".join(out), encoding="utf-8")


def out_has_iso(out: list[str]) -> bool:
    return any(l.startswith("# ISO/IEC 42001:") for l in out)


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
        f"{META_PREFIX}/tier": meta["tier"],
        f"{META_PREFIX}/namespace": meta["namespace"],
        f"{META_PREFIX}/display-name": meta["display"],
        f"{META_PREFIX}/iso42001-clauses": ", ".join(meta["iso_clauses"]),
        f"{META_PREFIX}/ra-components": ", ".join(meta["components"]),
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


def ensure_readme(chart_name: str) -> None:
    meta = CHART_META[chart_name]
    chart_dir = ROOT / meta["path"]
    readme_path = chart_dir / "README.md"
    if readme_path.exists():
        return

    iso_rows = "\n".join(f"| `{c}` | {ISO_REQS[c]} |" for c in meta["iso_clauses"])
    iso_str = ", ".join(f"`{c}`" for c in meta["iso_clauses"])
    components_str = ", ".join(f"`{c}` {COMPONENTS[c]}" for c in meta["components"]) or "none (cross-cutting)"
    badge_color = {"edge": "065f46", "platform": "1e40af", "enterprise": "92400e"}[meta["tier"]]

    description_block = (
        f"This chart packages **{meta['display']}** for the **{meta['tier']}** tier "
        f"of the reference architecture, covering the *{meta['category']}* "
        f"capability block. It ships with defaults for K3s and a "
        f"Rancher-compatible `questions.yaml`, so operators can deploy the "
        f"component from the Rancher UI with guided prompts."
    )

    readme_path.write_text(
        README_TEMPLATE.format(
            name=chart_name, display=meta["display"],
            tagline=meta["tagline"], tier=meta["tier"], category=meta["category"],
            namespace=meta["namespace"], iso_str=iso_str, iso_rows=iso_rows,
            components_str=components_str, badge_color=badge_color,
            description_block=description_block, alias=REPO_ALIAS,
            source=SOURCE_REPO, repo_url=REPO_URL, rel_path=meta["path"],
            prefix=META_PREFIX, first_clause=meta["iso_clauses"][0],
            maintainer_name=MAINTAINER["name"],
            maintainer_email=MAINTAINER["email"],
            maintainer_url=MAINTAINER["url"],
        ),
        encoding="utf-8",
    )


def run(cmd: list[str], cwd: pathlib.Path | None = None) -> None:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stdout + res.stderr)
        raise SystemExit(f"command failed: {' '.join(cmd)}")


def ensure_repos() -> None:
    """helm repo add every dependency repository (needed to build from Chart.lock)."""
    urls = set()
    for meta in CHART_META.values():
        chart = yaml.safe_load((ROOT / meta["path"] / "manifests" / "Chart.yaml").read_text(encoding="utf-8"))
        for dep in chart.get("dependencies") or []:
            if dep.get("repository", "").startswith("http"):
                urls.add(dep["repository"].rstrip("/"))
    for url in sorted(urls):
        name = "dep-" + hashlib.sha1(url.encode()).hexdigest()[:10]
        run(["helm", "repo", "add", "--force-update", name, url])
    if urls:
        run(["helm", "repo", "update"])


def update_lock(chart_name: str) -> None:
    """Refresh Chart.lock in the source tree (helm dependency update)."""
    src = ROOT / CHART_META[chart_name]["path"] / "manifests"
    chart = yaml.safe_load((src / "Chart.yaml").read_text(encoding="utf-8"))
    if chart.get("dependencies"):
        run(["helm", "dependency", "update", str(src)])
        shutil.rmtree(src / "charts", ignore_errors=True)


def package_chart(chart_name: str) -> pathlib.Path:
    """helm dependency build + helm package on a clean copy of the chart."""
    meta = CHART_META[chart_name]
    src = ROOT / meta["path"] / "manifests"
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        dst = pathlib.Path(tmp) / chart_name
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("charts", "*.bak", "*.tgz"))
        readme = ROOT / meta["path"] / "README.md"
        if readme.exists():
            shutil.copy(readme, dst / "README.md")
        chart = yaml.safe_load((dst / "Chart.yaml").read_text(encoding="utf-8"))
        if chart.get("dependencies"):
            run(["helm", "dependency", "build", str(dst)])
        run(["helm", "package", str(dst), "-d", str(CHARTS_DIR)])
    return CHARTS_DIR / f"{chart_name}-{NEW_CHART_VERSION}.tgz"


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
        }
        if tgz.exists():
            entry["digest"] = file_digest(tgz)
        if "dependencies" in data:
            entry["dependencies"] = data["dependencies"]
        entries.setdefault(chart_name, []).append(entry)

    index = {"apiVersion": "v1", "generated": now, "entries": entries}
    path = DOCS / "index.yaml"
    path.write_text(yaml_dump(index), encoding="utf-8")
    return path


# ─────────────────────────────────────────────── docs/index.html rewrite ──

CARD_CSS_MARKER = "/* --- Card (augmented) --- */"
CARD_CSS = """    /* --- Card (augmented) --- */
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

RENDER_JS = '''function renderCards(filter) {
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
        ${c.cmp ? `<span class="tag tag-iso">${c.cmp}</span>` : ''}
        <span class="tag tag-iso">${c.iso}</span>
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


def short_name(chart_name: str) -> str:
    return chart_name.split("-", 1)[1]


def render_index_html(packaged: list[tuple[str, dict, pathlib.Path]]) -> None:
    html_path = DOCS / "index.html"
    html = html_path.read_text(encoding="utf-8")
    tier_order = {"edge": 0, "platform": 1, "enterprise": 2}

    items = []
    for chart_name, data, tgz in sorted(
        packaged,
        key=lambda x: (tier_order[CHART_META[x[0]]["tier"]], CHART_META[x[0]]["category"], x[0]),
    ):
        meta = CHART_META[chart_name]
        items.append(
            "  { "
            f'name: "{chart_name}", '
            f'display: "{meta["display"]}", '
            f'tier: "{meta["tier"]}", '
            f'category: "{meta["category"]}", '
            f'cmp: "{", ".join(meta["components"])}", '
            f'iso: "{", ".join(meta["iso_clauses"])}", '
            f'version: "{data["version"]}", '
            f'appVersion: "{data["appVersion"]}", '
            f'desc: {json.dumps(meta["tagline"])}, '
            f'icon: "{REPO_URL}/icons/{chart_name}.svg", '
            f'tgz:  "{REPO_URL}/charts/{tgz.name}" '
            "}"
        )
    new_array = "const charts = [\n" + ",\n".join(items) + "\n];"
    html = re.sub(r"const charts = \[.*?^\];", lambda m: new_array, html,
                  count=1, flags=re.DOTALL | re.MULTILINE)
    html = re.sub(r"function renderCards\(filter\) \{.*?\n\}", lambda m: RENDER_JS, html,
                  count=1, flags=re.DOTALL)

    # Card CSS: remove every previous copy, then insert exactly one.
    html = re.sub(r"\n?\s*/\* --- Card \(augmented\) --- \*/.*?\.card-dl svg \{[^}]*\}\n",
                  "\n", html, flags=re.DOTALL)
    html = html.replace("</style>", CARD_CSS + "  </style>", 1)

    counts = Counter(CHART_META[n]["tier"] for n, _, _ in packaged)
    html = re.sub(r"(showTier\('all'\)\">All <span class=\"tab-count\">)\d+",
                  lambda m: f"{m.group(1)}{sum(counts.values())}", html)
    for tier, label in (("edge", "Edge"), ("platform", "Platform"), ("enterprise", "Enterprise")):
        html = re.sub(rf"(showTier\('{tier}'\)\">{label} <span class=\"tab-count\">)\d+",
                      lambda m, t=tier: f"{m.group(1)}{counts.get(t, 0)}", html)

    # Architecture overview: one chip per chart of each tier.
    for tier in ("edge", "platform", "enterprise"):
        chips = "\n".join(
            f'        <span class="arch-comp">{short_name(n)}</span>'
            for n in CHART_META if CHART_META[n]["tier"] == tier
        )
        html = re.sub(
            rf'(<div class="arch-tier arch-tier-{tier}">.*?<div class="arch-components">\n).*?(\n      </div>)',
            lambda m: m.group(1) + chips + m.group(2), html, count=1, flags=re.DOTALL)

    # ISO/IEC 42001 coverage table.
    rows = []
    for clause, req in ISO_REQS.items():
        sols = [CHART_META[n]["display"] for n in CHART_META if clause in CHART_META[n]["iso_clauses"]]
        rows.append(f'        <tr><td class="iso-clause">{clause}</td><td>{req.replace("&", "&amp;")}</td>'
                    f'<td>{", ".join(sols).replace("&", "&amp;")}</td></tr>')
    html = re.sub(r'(<table class="iso-table">.*?<tbody>\n).*?(\n      </tbody>)',
                  lambda m: m.group(1) + "\n".join(rows) + m.group(2), html, count=1, flags=re.DOTALL)
    html = re.sub(r"to \d+ ISO/IEC 42001 Annex B requirements", f"to {len(ISO_REQS)} ISO/IEC 42001 Annex B requirements", html)

    html_path.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--skip-package", action="store_true", help="update metadata only; no helm package")
    parser.add_argument("--update-locks", action="store_true", help="run helm dependency update on the sources first")
    args = parser.parse_args()

    missing = [n for n in CHART_META if not (ROOT / CHART_META[n]["path"] / "manifests" / "Chart.yaml").exists()]
    if missing:
        raise SystemExit(f"CHART_META entries without a chart: {missing}")
    unknown = {c for m in CHART_META.values() for c in m["iso_clauses"]} - set(ISO_REQS)
    if unknown:
        raise SystemExit(f"clauses without a requirement label in ISO_REQS: {sorted(unknown)}")

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for chart_name in CHART_META:
        icon_path = ICONS_DIR / f"{chart_name}.svg"
        if icon_path.exists():  # respect manually-curated icons
            continue
        icon_path.write_text(make_icon_svg(chart_name), encoding="utf-8")
        written += 1
    print(f"[icons]   generated {written} new SVG icon(s); kept {len(CHART_META) - written} existing")

    enriched: list[tuple[str, dict]] = []
    for chart_name in CHART_META:
        _, data = enrich_chart_yaml(chart_name)
        sync_values(chart_name)
        ensure_readme(chart_name)
        enriched.append((chart_name, data))
    print(f"[chart]   enriched {len(enriched)} charts (version {NEW_CHART_VERSION}), label blocks synced")

    if args.update_locks or not args.skip_package:
        ensure_repos()
    if args.update_locks:
        for chart_name, _ in enriched:
            update_lock(chart_name)
        print("[locks]   Chart.lock files refreshed")

    packaged: list[tuple[str, dict, pathlib.Path]] = []
    for chart_name, data in enriched:
        tgz = CHARTS_DIR / f"{chart_name}-{NEW_CHART_VERSION}.tgz"
        if not args.skip_package:
            tgz = package_chart(chart_name)
        packaged.append((chart_name, data, tgz))
    if not args.skip_package:
        print(f"[package] wrote {len(packaged)} .tgz with helm package into {CHARTS_DIR.relative_to(ROOT)}")

    idx = build_index(packaged)
    print(f"[index]   wrote {idx.relative_to(ROOT)}")

    render_index_html(packaged)
    print(f"[html]    refreshed {DOCS.relative_to(ROOT)}/index.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
