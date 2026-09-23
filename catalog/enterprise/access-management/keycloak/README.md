# Keycloak: Identity and Access Management

| Field | Value |
|-------|-------|
| **Chart** | `enterprise-keycloak` |
| **Tier** | Enterprise |
| **Namespace** | `security` |
| **Category** | Access Management · Security |
| **RA Component** | User Access & Oversight (CMP-07) |
| **ISO/IEC 42001** | B.6.1.3.1 · B.8.0.2.1 |
| **Helm Chart** | `bitnami/keycloak` (wrapped), image `bitnamilegacy/keycloak:24.0.5-debian-12-r0` |
| **K3S Compatible** | Yes |

---

## Description

Keycloak is the **Identity and Access Management (IAM)** platform implementing the **User Access & Oversight** component. It provides centralised authentication, authorisation and identity federation for the interfaces of the AI system.

What the chart deploys:

- **Keycloak 24** in production mode behind a proxy (`proxy: edge`), with non-strict hostnames (`KC_HOSTNAME_STRICT=false`) so it is reachable through port-forward when no ingress is enabled.
- **Database** on the platform PostgreSQL (`platform-postgresql.platform`, database and role `keycloak`, created by `platform-postgresql`); no bundled PostgreSQL.
- **Realm `ai-system`**, imported by keycloak-config-cli: realm roles (see below), OIDC clients `grafana`, `mlflow`, `minio` and `zammad`, login and admin events enabled (90-day expiry).
- **Prometheus metrics** with a ServiceMonitor.

Single sign-on is **not** switched on in the other charts by default: Grafana, Argo CD and the rest ship the OIDC settings disabled or documented, to be enabled once Keycloak and its client secrets are in place.

Bitnami moved its versioned images to `docker.io/bitnamilegacy`, which receives no new security patches; 24.0.0 was never published there, so 24.0.5 is used.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Keycloak Addresses It |
|--------|-------------|---------------------------|
| B.6.1.3.1 | Resources: Access Control | Role-based access to the AI system interfaces, segregation of duties |
| B.8.0.2.1 | Continual Improvement: Roles | Realm roles for the actors of the AI system; account console for users |

---

## Role Structure (realm `ai-system`)

| Role | Access | Description |
|------|--------|-------------|
| `operator` | Grafana dashboards | Machine operators viewing predictions |
| `data-scientist` | MLflow UI, training jobs, Grafana | Model training, evaluation and promotion |
| `compliance-officer` | Audit logs (Loki), document store (MinIO), MLflow | ISO/IEC 42001 compliance review and model approval |
| `production-manager` | KPI dashboards, AI Helpdesk | Business performance oversight |
| `admin` | All components | Platform administration |

---

## Prerequisites

- `platform-postgresql` (database `keycloak`).
- Secrets `enterprise-keycloak-admin` (key `admin-password`) and `enterprise-keycloak-db` (key `password`), created by `infrastructure/install.sh`.
- For users outside the cluster: an ingress with TLS (cert-manager) and a DNS name.

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install enterprise-keycloak cigip-upv/enterprise-keycloak -n security

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=enterprise-keycloak
```

---

## Integration Points

| System | Integration Method | State in the catalog |
|--------|-------------------|----------------------|
| Grafana | OIDC (generic OAuth) | Client defined; disabled in `platform-grafana` until enabled |
| Argo CD | OIDC | Documented in `platform-argocd`; not configured by default |
| MLflow | OIDC proxy (oauth2-proxy) | Client defined; no proxy shipped |
| MinIO | OIDC (native support) | Client defined; not configured by default |
| Zammad | OIDC | Client defined; not configured by default |

---

## Related Solutions

- [Grafana](../../../platform/monitoring/grafana/README.md): OIDC integration for dashboards
- [PostgreSQL (platform)](../../../platform/data-management/postgresql/README.md): Keycloak database
- [OpenBao](../../../platform/security/openbao/README.md): secrets management
- [Zammad](../../helpdesk/zammad/README.md): helpdesk
