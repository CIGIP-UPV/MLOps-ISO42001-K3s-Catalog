# Keycloak — Identity & Access Management

| Field | Value |
|-------|-------|
| **Tier** | Enterprise |
| **Category** | Access Management · Security |
| **RA Component** | User Access and Oversight · Security Monitoring |
| **ISO/IEC 42001** | B.6.1.3.1 · B.6.1.3.3 · B.8.0.2.1 |
| **Helm Chart** | `bitnami/keycloak` |
| **K3S Compatible** | Yes |

---

## Description

Keycloak is the **Identity and Access Management (IAM)** platform implementing the **User Access and Oversight** component across the enterprise and platform tiers. It provides centralised authentication, authorisation, and identity federation for all AI system interfaces.

Its key roles in the reference architecture are:

- **Single Sign-On (SSO)**: unified login across Grafana, MLflow UI, MinIO console, and any custom React frontends via OpenID Connect (OIDC) / OAuth 2.0.
- **Role-Based Access Control (RBAC)**: defines roles (operator, data scientist, compliance officer, admin) and grants access to specific AI system functions based on role — implementing segregation of duties required by B.6.1.3.1.
- **User activity auditing**: Keycloak logs all authentication and authorisation events, contributing to the audit trail required by B.6.2.8.1.
- **API security**: protects the FastAPI inference endpoints and MLflow API via bearer token validation.
- **Federated identity**: integrates with enterprise LDAP/Active Directory for manufacturing plant environments.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Keycloak Addresses It |
|--------|-------------|---------------------------|
| B.6.1.3.1 | Human Oversight | Enforces role-based access to AI system controls and oversight dashboards |
| B.6.1.3.3 | Usability & Controllability | Controlled interaction with AI system via authenticated sessions |
| B.8.0.2.1 | User Information | Users can access their roles, permissions, and interaction history via Keycloak account console |

---

## Recommended Role Structure

| Role | Access | Description |
|------|--------|-------------|
| `operator` | Grafana dashboards, Feedback Interface | Machine operators viewing predictions and annotating feedback |
| `data-scientist` | MLflow UI, Training Jobs, Grafana | Model training, evaluation, and promotion |
| `compliance-officer` | Audit logs (Loki), Document Store (MinIO), MLflow approval | ISO/IEC 42001 compliance review and model approval |
| `production-manager` | KPI dashboards, model promotion approval, AI Helpdesk | Business performance oversight and decision approval |
| `admin` | All components | Platform administration |

---

## Prerequisites

- K3S enterprise cluster with persistent volumes
- PostgreSQL for Keycloak metadata storage
- TLS certificate (cert-manager or pre-existing) — Keycloak requires HTTPS in production
- DNS entry for Keycloak external hostname

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Installation (K3S / Helm)

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

helm install keycloak bitnami/keycloak \
  --namespace security \
  --create-namespace \
  -f values.yaml
```

---

## Integration Points

| System | Integration Method | Purpose |
|--------|-------------------|---------|
| Grafana | OIDC provider | SSO and role mapping |
| MLflow | OIDC proxy (oauth2-proxy) | Protect MLflow UI |
| MinIO | OIDC (native support) | Object storage access control |
| FastAPI | JWT bearer token validation | API endpoint protection |
| Zammad | SAML / OIDC | Helpdesk SSO |

---

## Related Solutions

- [Grafana](../../../platform/monitoring/grafana/README.md) — OIDC integration for dashboard SSO
- [MLflow](../../../platform/ai-lifecycle/mlflow/README.md) — OIDC proxy authentication
- [MinIO](../../../platform/data-management/minio/README.md) — OIDC-based access control
- [Zammad](../helpdesk/zammad/README.md) — SSO integration for helpdesk
