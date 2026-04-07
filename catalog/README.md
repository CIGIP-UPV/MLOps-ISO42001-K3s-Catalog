# Catalog Index

This index provides a cross-reference of all solutions by **Deployment Tier** and **Functional Category**.

## Full Matrix: Tier × Category

| Category | Edge | Platform | Enterprise |
|----------|------|----------|------------|
| **Data Ingestion** | [Node-RED](./edge/data-ingestion/node-red/README.md) · [Kafka](./edge/data-ingestion/kafka/README.md) · [Mosquitto (MQTT)](./edge/data-ingestion/mosquitto/README.md) | — | — |
| **AI Inference** | [FastAPI Model Server](./edge/ai-inference/fastapi-model/README.md) | [FastAPI Model Server (Cloud)](./platform/ai-lifecycle/mlflow/README.md) | — |
| **AI Lifecycle** | — | [MLflow](./platform/ai-lifecycle/mlflow/README.md) · [Training Jobs](./platform/ai-lifecycle/training-jobs/README.md) | — |
| **Monitoring** | [Prometheus Agent](./edge/monitoring/prometheus-agent/README.md) · [Fluent Bit](./edge/monitoring/fluent-bit/README.md) | [Prometheus](./platform/monitoring/prometheus/README.md) · [Grafana](./platform/monitoring/grafana/README.md) · [Loki](./platform/monitoring/loki/README.md) | [Grafana](./enterprise/dashboards/grafana/README.md) |
| **Security** | [Falco](./edge/security/falco/README.md) | — | [Keycloak](./enterprise/access-management/keycloak/README.md) |
| **Storage** | [PostgreSQL](./edge/storage/postgresql/README.md) · [MongoDB](./edge/storage/mongodb/README.md) | [TimescaleDB](./platform/data-management/timescaledb/README.md) · [PostgreSQL](./platform/data-management/postgresql/README.md) · [MinIO](./platform/data-management/minio/README.md) | [MinIO (Document Store)](./enterprise/document-store/minio/README.md) |
| **Access Management** | — | — | [Keycloak](./enterprise/access-management/keycloak/README.md) |
| **Helpdesk** | — | — | [Zammad](./enterprise/helpdesk/zammad/README.md) |
| **Orchestration** | K3S (built-in) | [Rancher](./platform/orchestration/rancher/README.md) | — |

---

## ISO/IEC 42001 Requirement → Solution Lookup

| Req. ID | Keyword | Solution(s) |
|---------|---------|-------------|
| B.6.1.2.2 | Integration of Metrics | Prometheus Agent · Prometheus · Grafana |
| B.6.1.3.1 | Human Oversight | Keycloak · Grafana |
| B.6.1.3.2 | Version Control | MLflow |
| B.6.1.3.3 | Usability & Controllability | Grafana · Zammad |
| B.6.1.3.4 | Release Criteria | MLflow · Training Jobs |
| B.6.2.3.1 | Architecture Documentation | MinIO (Document Store) |
| B.6.2.5.1 | Deployment Plan | MinIO (Document Store) |
| B.6.2.6.1 | Error Monitoring | Prometheus · Loki |
| B.6.2.6.2 | Technical Performance Monitoring | Prometheus · Grafana |
| B.6.2.6.3 | Goal-oriented Performance Monitoring | Grafana · TimescaleDB |
| B.6.2.6.4 | Retraining Monitoring | Node-RED · MLflow · Training Jobs |
| B.6.2.6.5 | Update & Repair Plan | MinIO (Document Store) |
| B.6.2.6.6 | AI Helpdesk | Zammad |
| B.6.2.6.7 | Threat Detection | Falco · Keycloak |
| B.6.2.8.1 | Event Logs | Fluent Bit · Loki |
| B.8.0.2.1 | User Information | Keycloak · Grafana |
| B.8.0.4.1 | Display of Adverse Treatment | Zammad |
| B.8.0.5.1 | Incident Communication | Zammad · Grafana Alerting |

---

## Solutions by Tier

### Edge Tier
- [`data-ingestion/node-red`](./edge/data-ingestion/node-red/README.md)
- [`data-ingestion/kafka`](./edge/data-ingestion/kafka/README.md)
- [`data-ingestion/mosquitto`](./edge/data-ingestion/mosquitto/README.md)
- [`ai-inference/fastapi-model`](./edge/ai-inference/fastapi-model/README.md)
- [`monitoring/fluent-bit`](./edge/monitoring/fluent-bit/README.md)
- [`monitoring/prometheus-agent`](./edge/monitoring/prometheus-agent/README.md)
- [`security/falco`](./edge/security/falco/README.md)
- [`storage/postgresql`](./edge/storage/postgresql/README.md)
- [`storage/mongodb`](./edge/storage/mongodb/README.md)

### Platform Tier
- [`ai-lifecycle/mlflow`](./platform/ai-lifecycle/mlflow/README.md)
- [`ai-lifecycle/training-jobs`](./platform/ai-lifecycle/training-jobs/README.md)
- [`monitoring/prometheus`](./platform/monitoring/prometheus/README.md)
- [`monitoring/grafana`](./platform/monitoring/grafana/README.md)
- [`monitoring/loki`](./platform/monitoring/loki/README.md)
- [`data-management/minio`](./platform/data-management/minio/README.md)
- [`data-management/timescaledb`](./platform/data-management/timescaledb/README.md)
- [`data-management/postgresql`](./platform/data-management/postgresql/README.md)
- [`orchestration/rancher`](./platform/orchestration/rancher/README.md)

### Enterprise Tier
- [`access-management/keycloak`](./enterprise/access-management/keycloak/README.md)
- [`helpdesk/zammad`](./enterprise/helpdesk/zammad/README.md)
- [`document-store/minio`](./enterprise/document-store/minio/README.md)
- [`dashboards/grafana`](./enterprise/dashboards/grafana/README.md)
