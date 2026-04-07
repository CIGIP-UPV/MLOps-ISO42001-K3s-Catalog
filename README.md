# K3S Solution Catalog for ISO/IEC 42001-Compliant Industrial AI Systems

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![GitHub](https://img.shields.io/badge/GitHub-CIGIP--UPV-181717?logo=github)](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog)

A structured catalog of K3S-compatible solutions for designing, deploying, and governing AI systems in manufacturing environments in conformity with **ISO/IEC 42001:2023**.

**Repository**: [https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog)

This catalog is a companion resource to the reference architecture described in:

> *Reference Architecture for the Design and Implementation of AI Systems in Manufacturing in Conformity to ISO/IEC 42001* — Mateo-Casali et al.

---

## Overview

The catalog organises solutions along **two dimensions**:

| Dimension | Values |
|-----------|--------|
| **Deployment Tier** | Edge · Platform · Enterprise |
| **Functional Category** | Data Ingestion · AI Inference · Monitoring · Security · Storage · AI Lifecycle · Access Management · Helpdesk · Dashboards |

Every solution entry maps to one or more **ISO/IEC 42001 Annex B requirements** and includes a **deployment questionnaire** to guide configuration decisions before installation.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  ENTERPRISE TIER    Keycloak · Zammad · MinIO · Grafana     │
├─────────────────────────────────────────────────────────────┤
│  PLATFORM TIER      Rancher · MLflow · Prometheus · Loki    │
│                     Grafana · MinIO · TimescaleDB           │
├─────────────────────────────────────────────────────────────┤
│  EDGE TIER          Node-RED · FastAPI Model · Fluent Bit   │
│                     Falco · PostgreSQL · Prometheus Agent   │
├─────────────────────────────────────────────────────────────┤
│  DEVICE TIER        Sensors · CNC · IoT · PLCs             │
│                     (outside K3S scope — protocol adapters) │
└─────────────────────────────────────────────────────────────┘
```

All tiers run on **K3S** (lightweight Kubernetes), which is the orchestration layer assumed throughout this catalog. The Platform tier may be managed via **Rancher**.

---

## Repository Structure

```
k3s-iso42001-catalog/
├── catalog/
│   ├── edge/                  # Edge tier solutions
│   │   ├── data-ingestion/    # Node-RED, Kafka, Mosquitto
│   │   ├── ai-inference/      # FastAPI model server
│   │   ├── monitoring/        # Fluent Bit, Prometheus Agent
│   │   ├── security/          # Falco
│   │   └── storage/           # PostgreSQL, MongoDB
│   ├── platform/              # Platform tier solutions
│   │   ├── ai-lifecycle/      # MLflow, Training Jobs
│   │   ├── monitoring/        # Prometheus, Grafana, Loki
│   │   ├── data-management/   # MinIO, TimescaleDB, PostgreSQL
│   │   └── orchestration/     # Rancher
│   └── enterprise/            # Enterprise tier solutions
│       ├── access-management/ # Keycloak
│       ├── helpdesk/          # Zammad
│       ├── document-store/    # MinIO
│       └── dashboards/        # Grafana
├── questionnaires/            # Deployment decision guides
│   ├── 01-deployment-scope.md
│   ├── 02-edge-requirements.md
│   ├── 03-platform-requirements.md
│   ├── 04-enterprise-requirements.md
│   └── 05-iso42001-compliance.md
├── compliance/
│   └── iso42001-mapping.md    # Full component → clause matrix
└── templates/
    ├── solution-template/     # Template for new solution entries
    └── k3s-manifests/         # Reusable base manifests
```

---

## Quick Start: Where Do I Begin?

1. **Start with the deployment questionnaires** in [`questionnaires/`](./questionnaires/01-deployment-scope.md). Answer the scope questions to determine which tiers and components you need.
2. **Browse the catalog** by tier in [`catalog/`](./catalog/README.md) or use the [compliance matrix](./compliance/iso42001-mapping.md) to select components by ISO/IEC 42001 clause.
3. **Follow the installation guide** in each solution's `README.md` and answer its embedded questionnaire.
4. **Apply the K3S manifests** provided in each solution's `manifests/` directory.

---

## ISO/IEC 42001 Coverage Summary

| Requirement | Keyword | Primary Component(s) |
|-------------|---------|----------------------|
| B.6.1.2.2 | Performance Monitoring | Prometheus, Grafana |
| B.6.1.3.1 | Human Oversight | Keycloak, Grafana Feedback |
| B.6.1.3.2 | Version Control | MLflow |
| B.6.1.3.3 | Usability & Controllability | Grafana, Information Centre |
| B.6.1.3.4 | Release Criteria | MLflow, GitOps |
| B.6.2.3.1 | Architecture Documentation | MinIO (Document Store) |
| B.6.2.5.1 | Deployment Plan | MinIO (Document Store) |
| B.6.2.6.1 | Error Monitoring | Prometheus, Loki |
| B.6.2.6.2 | Technical Performance Monitoring | Prometheus, Grafana |
| B.6.2.6.3 | Goal-oriented Performance Monitoring | Grafana, TimescaleDB |
| B.6.2.6.4 | Retraining Monitoring | Node-RED, MLflow |
| B.6.2.6.5 | Update & Repair Plan | MinIO (Document Store) |
| B.6.2.6.6 | AI Helpdesk | Zammad |
| B.6.2.6.7 | Threat Detection | Falco, Keycloak |
| B.6.2.8.1 | Event Logs | Fluent Bit, Loki |
| B.8.0.2.1 | User Information | Keycloak, Grafana |
| B.8.0.4.1 | Adverse Treatment | Zammad |
| B.8.0.5.1 | Incident Communication | Zammad, Grafana Alerting |

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md) and the [`templates/solution-template/`](./templates/solution-template/README.md) directory to add new solutions following the catalog's standard format.

---

## Related Standards

- **ISO/IEC 42001:2023** — AI Management Systems
- **ISO/IEC 42010** — Architecture Description
- **ISA/IEC 62443** — Industrial Cybersecurity
- **EU AI Act** — Risk-based AI regulation
- **ALTAI** — Assessment List for Trustworthy AI

---

## License

This catalog is provided as an open reference resource. See [`LICENSE`](./LICENSE) for details.
