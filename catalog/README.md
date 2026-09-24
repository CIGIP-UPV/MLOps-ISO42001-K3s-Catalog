# Catalog Index

Cross-reference of the 31 charts of the catalog by **deployment tier** and **functional category**, with the reference architecture components (CMP, Annex A of the thesis) and the ISO/IEC 42001 Annex B requirements each one covers. Tables generated from `CHART_META` in [`infrastructure/publish.py`](../infrastructure/publish.py).

## Tier × Category

| Category | Edge | Platform | Enterprise |
|----------|------|----------|------------|
| **AI Inference** | [FastAPI Model Server](./edge/ai-inference/fastapi-model/README.md) | none | none |
| **AI Lifecycle** | none | [MLflow](./platform/ai-lifecycle/mlflow/README.md) · [Training Jobs](./platform/ai-lifecycle/training-jobs/README.md) · [Evidently AI](./platform/ai-lifecycle/evidently/README.md) | none |
| **Access Management** | none | none | [Keycloak](./enterprise/access-management/keycloak/README.md) |
| **Dashboards** | none | none | [Grafana Dashboards (Overlay)](./enterprise/dashboards/grafana/README.md) |
| **Data Ingestion** | [Apache Kafka (Edge)](./edge/data-ingestion/kafka/README.md) · [Eclipse Mosquitto](./edge/data-ingestion/mosquitto/README.md) · [RabbitMQ (Edge)](./edge/data-ingestion/rabbitmq/README.md) · [Node-RED](./edge/data-ingestion/node-red/README.md) · [OPC-UA Gateway](./edge/data-ingestion/opc-ua-gateway/README.md) | none | none |
| **Data Management** | none | [MinIO](./platform/data-management/minio/README.md) · [PostgreSQL (Platform)](./platform/data-management/postgresql/README.md) · [TimescaleDB](./platform/data-management/timescaledb/README.md) | none |
| **Document Store** | none | none | [MinIO Docs Overlay](./enterprise/document-store/minio/README.md) |
| **Helpdesk** | none | none | [Zammad](./enterprise/helpdesk/zammad/README.md) |
| **Human Oversight** | none | none | [Feedback Interface](./enterprise/human-oversight/feedback-interface/README.md) |
| **Monitoring** | [Fluent Bit](./edge/monitoring/fluent-bit/README.md) · [Prometheus Agent](./edge/monitoring/prometheus-agent/README.md) | [Grafana](./platform/monitoring/grafana/README.md) · [Loki](./platform/monitoring/loki/README.md) · [Prometheus + Alertmanager](./platform/monitoring/prometheus/README.md) | none |
| **Orchestration** | none | [Rancher](./platform/orchestration/rancher/README.md) · [Argo CD](./platform/orchestration/argocd/README.md) | none |
| **Security** | [Falco](./edge/security/falco/README.md) | [OpenBao](./platform/security/openbao/README.md) · [cert-manager](./platform/security/cert-manager/README.md) | none |
| **Storage** | [MongoDB (Edge Buffer)](./edge/storage/mongodb/README.md) · [PostgreSQL (Edge Cache)](./edge/storage/postgresql/README.md) · [Edge Data Consolidation](./edge/storage/postgresql-sync/README.md) | none | none |
| **Version Control** | [Edge Version Control (MLflow Sync)](./edge/version-control/mlflow-sync/README.md) | none | none |

K3s itself (with its Traefik ingress, containerd and the kube-router network policy controller) is the orchestration base of every tier.

---

## Charts by Tier

### Edge tier

| Chart | Namespace | Components | ISO/IEC 42001 |
|-------|-----------|------------|---------------|
| [`edge-fastapi-model`](./edge/ai-inference/fastapi-model/README.md) | `edge` | CMP-04, CMP-10 | B.6.2.6.2, B.6.2.6.4 |
| [`edge-kafka`](./edge/data-ingestion/kafka/README.md) | `edge` | CMP-01 | B.6.2.6.4, B.6.2.8.1 |
| [`edge-mosquitto`](./edge/data-ingestion/mosquitto/README.md) | `edge` | CMP-01 | B.6.1.3.1, B.6.2.6.4 |
| [`edge-rabbitmq`](./edge/data-ingestion/rabbitmq/README.md) | `edge` | CMP-01 | B.6.2.6.4, B.6.2.8.1 |
| [`edge-node-red`](./edge/data-ingestion/node-red/README.md) | `edge` | CMP-01 | B.6.2.6.4 |
| [`edge-opc-ua-gateway`](./edge/data-ingestion/opc-ua-gateway/README.md) | `edge` | CMP-01 | B.6.1.3.1, B.6.2.6.4 |
| [`edge-fluent-bit`](./edge/monitoring/fluent-bit/README.md) | `logging` | CMP-09 | B.6.2.8.1 |
| [`edge-prometheus-agent`](./edge/monitoring/prometheus-agent/README.md) | `edge` | CMP-08, CMP-10 | B.6.1.2.2, B.6.2.6.1 |
| [`edge-falco`](./edge/security/falco/README.md) | `falco` | CMP-15 | B.6.2.6.7, B.6.2.8.1 |
| [`edge-mongodb`](./edge/storage/mongodb/README.md) | `edge` | CMP-02 | B.6.2.6.1 |
| [`edge-postgresql`](./edge/storage/postgresql/README.md) | `edge` | CMP-02 | B.6.2.6.1, B.6.2.6.3, B.6.2.8.1 |
| [`edge-postgresql-sync`](./edge/storage/postgresql-sync/README.md) | `edge` | CMP-02 | B.6.2.6.1, B.6.2.8.1 |
| [`edge-mlflow-sync`](./edge/version-control/mlflow-sync/README.md) | `edge` | CMP-03 | B.6.1.3.2, B.6.2.6.4, B.6.2.8.1 |

### Platform tier

| Chart | Namespace | Components | ISO/IEC 42001 |
|-------|-----------|------------|---------------|
| [`platform-mlflow`](./platform/ai-lifecycle/mlflow/README.md) | `mlops` | CMP-03 | B.6.1.3.2, B.6.1.3.4, B.6.2.6.4 |
| [`platform-training-jobs`](./platform/ai-lifecycle/training-jobs/README.md) | `mlops` | CMP-04, CMP-14 | B.6.2.6.4 |
| [`platform-evidently`](./platform/ai-lifecycle/evidently/README.md) | `mlops` | CMP-10, CMP-14 | B.6.2.6.2, B.6.2.8.1, B.8.0.5.1 |
| [`platform-minio`](./platform/data-management/minio/README.md) | `minio` | CMP-02, CMP-05 | B.6.2.3.1, B.6.2.5.1 |
| [`platform-postgresql`](./platform/data-management/postgresql/README.md) | `platform` | CMP-02 | B.6.1.3.4 |
| [`platform-timescaledb`](./platform/data-management/timescaledb/README.md) | `platform` | CMP-02, CMP-11 | B.6.2.6.1, B.6.2.6.3 |
| [`platform-grafana`](./platform/monitoring/grafana/README.md) | `monitoring` | CMP-06, CMP-10, CMP-11 | B.6.1.3.1, B.6.1.3.3, B.6.2.6.2 |
| [`platform-loki`](./platform/monitoring/loki/README.md) | `monitoring` | CMP-09 | B.6.2.8.1 |
| [`platform-prometheus`](./platform/monitoring/prometheus/README.md) | `monitoring` | CMP-08, CMP-10, CMP-11 | B.6.1.2.2, B.6.2.6.2, B.8.0.5.1 |
| [`platform-rancher`](./platform/orchestration/rancher/README.md) | `cattle-system` | none | B.6.2.5.1 |
| [`platform-argocd`](./platform/orchestration/argocd/README.md) | `argocd` | CMP-03 | B.6.2.5.1, B.6.2.6.4, B.6.2.8.1 |
| [`platform-openbao`](./platform/security/openbao/README.md) | `openbao` | CMP-07, CMP-15 | B.6.1.3.3, B.6.1.4.1, B.8.0.2.1 |
| [`platform-cert-manager`](./platform/security/cert-manager/README.md) | `cert-manager` | CMP-15 | B.6.1.4.1, B.6.2.3.1 |

### Enterprise tier

| Chart | Namespace | Components | ISO/IEC 42001 |
|-------|-----------|------------|---------------|
| [`enterprise-keycloak`](./enterprise/access-management/keycloak/README.md) | `security` | CMP-07 | B.6.1.3.1, B.8.0.2.1 |
| [`enterprise-grafana-dashboards`](./enterprise/dashboards/grafana/README.md) | `monitoring` | CMP-06, CMP-11 | B.6.1.3.3, B.6.2.6.2 |
| [`enterprise-minio-overlay`](./enterprise/document-store/minio/README.md) | `minio` | CMP-05 | B.6.2.3.1, B.6.2.6.5 |
| [`enterprise-zammad`](./enterprise/helpdesk/zammad/README.md) | `helpdesk` | CMP-13 | B.6.2.6.6, B.8.0.4.1, B.8.0.5.1 |
| [`enterprise-feedback-interface`](./enterprise/human-oversight/feedback-interface/README.md) | `feedback` | CMP-12 | B.6.1.3.3, B.6.2.6.4 |

`edge-fluent-bit` and `edge-falco` are edge charts that run as DaemonSets on every node, so they also cover the platform nodes (Logger and Security Monitoring at platform level).

---

## ISO/IEC 42001 Requirement → Chart Lookup

| Requirement | Label | Charts |
|-------------|-------|--------|
| B.6.1.2.2 | Resources: Monitoring Performance | `edge-prometheus-agent`, `platform-prometheus` |
| B.6.1.3.1 | Resources: Access Control | `edge-mosquitto`, `edge-opc-ua-gateway`, `platform-grafana`, `enterprise-keycloak` |
| B.6.1.3.2 | Resources: Version Control | `edge-mlflow-sync`, `platform-mlflow` |
| B.6.1.3.3 | Resources: Human Oversight / Feedback | `platform-grafana`, `platform-openbao`, `enterprise-grafana-dashboards`, `enterprise-feedback-interface` |
| B.6.1.3.4 | Resources: Inventory / Registry | `platform-mlflow`, `platform-postgresql` |
| B.6.1.4.1 | Resources: Security of AI Assets | `platform-openbao`, `platform-cert-manager` |
| B.6.2.3.1 | Planning: System Documentation | `platform-minio`, `platform-cert-manager`, `enterprise-minio-overlay` |
| B.6.2.5.1 | Planning: Deployment Plan | `platform-minio`, `platform-rancher`, `platform-argocd` |
| B.6.2.6.1 | Operation: Infrastructure Monitoring | `edge-prometheus-agent`, `edge-mongodb`, `edge-postgresql`, `edge-postgresql-sync`, `platform-timescaledb` |
| B.6.2.6.2 | Operation: Model Performance | `edge-fastapi-model`, `platform-evidently`, `platform-grafana`, `platform-prometheus`, `enterprise-grafana-dashboards` |
| B.6.2.6.3 | Operation: KPI Assessment (OEE) | `edge-postgresql`, `platform-timescaledb` |
| B.6.2.6.4 | Operation: Retraining / Lifecycle | `edge-fastapi-model`, `edge-kafka`, `edge-mosquitto`, `edge-rabbitmq`, `edge-node-red`, `edge-opc-ua-gateway`, `edge-mlflow-sync`, `platform-mlflow`, `platform-training-jobs`, `platform-argocd`, `enterprise-feedback-interface` |
| B.6.2.6.5 | Operation: Update & Repair Plan | `enterprise-minio-overlay` |
| B.6.2.6.6 | Operation: Incident Communication | `enterprise-zammad` |
| B.6.2.6.7 | Operation: Security Monitoring | `edge-falco` |
| B.6.2.8.1 | Operation: Logging / Audit Trail | `edge-kafka`, `edge-rabbitmq`, `edge-fluent-bit`, `edge-falco`, `edge-postgresql`, `edge-postgresql-sync`, `edge-mlflow-sync`, `platform-evidently`, `platform-loki`, `platform-argocd` |
| B.8.0.2.1 | Continual Improvement: Roles | `platform-openbao`, `enterprise-keycloak` |
| B.8.0.4.1 | Continual Improvement: Helpdesk | `enterprise-zammad` |
| B.8.0.5.1 | Continual Improvement: Alerts | `platform-evidently`, `platform-prometheus`, `enterprise-zammad` |

Requirement labels and the full coverage summary are in the root [`README.md`](../README.md#isoiec-42001-coverage-summary).
