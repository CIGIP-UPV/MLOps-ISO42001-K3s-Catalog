# Deployment Questionnaire — MLflow (Platform AI Lifecycle)

Answer these questions before deploying MLflow on the platform tier. *(ISO/IEC 42001: B.6.1.3.2, B.6.1.3.4, B.6.2.6.4)*

---

## Section 1: Model Governance & Release Criteria

**Q1. Who is authorised to approve a model for production deployment?** *(B.6.1.3.4)*

- [ ] Data scientist only
- [ ] Data scientist + production manager (recommended)
- [ ] Data scientist + compliance officer + production manager
- [ ] Automatic approval if metrics exceed threshold (document threshold value below)

> **Document the approval policy** in the Deployment Plan stored in MinIO Document Store.

**Q2. What performance threshold must a model meet before promotion to Production?**

Specify the metric and threshold for your use case:

| Metric | Threshold |
|--------|-----------|
| (e.g.) F1 Score | ≥ 0.85 |
| (e.g.) MAE | ≤ 0.05 |
| (e.g.) False Negative Rate | ≤ 0.10 |
| Custom: _________ | _________ |

**Q3. How long should previous model versions be retained in the registry?**

- [ ] Indefinitely — full audit trail (recommended for ISO/IEC 42001 compliance)
- [ ] Last 5 versions — balance between auditability and storage
- [ ] Last 3 versions — minimal retention

---

## Section 2: Retraining Policy

**Q4. What event(s) should trigger a retraining run?** *(B.6.2.6.4)*

- [ ] Scheduled (e.g., monthly) — configure as a CronJob in K3S
- [ ] Data drift detected by Input Data Monitoring (Node-RED alert)
- [ ] Model performance degradation (Prometheus metric threshold crossed)
- [ ] Manual trigger by data scientist
- [ ] Production incident reported in Zammad helpdesk

**Q5. When retraining is triggered, what data scope is used?**

- [ ] Full historical dataset (from TimescaleDB)
- [ ] Sliding window (last N days): _____ days
- [ ] Incremental (only new samples since last training)

---

## Section 3: Infrastructure

**Q6. Is MinIO already deployed on the platform tier?**

- [ ] Yes — provide the MinIO endpoint and access credentials below
- [ ] No — deploy MinIO first (see [MinIO README](../../data-management/minio/README.md))

MinIO endpoint: `http://minio.platform.svc:9000` (adjust as needed)
MLflow bucket name: `mlflow-artifacts`

**Q7. Is PostgreSQL available for MLflow metadata?**

- [ ] Yes — provide connection string below
- [ ] No — deploy PostgreSQL first (see [PostgreSQL README](../../data-management/postgresql/README.md))

**Q8. Should MLflow UI be accessible to users in the enterprise tier?**

- [ ] Yes — expose via Ingress with authentication (Keycloak OIDC proxy recommended)
- [ ] No — internal access only (data scientists only, via kubectl port-forward)

---

## Recommended Configuration Summary

```yaml
# values.yaml — MLflow (Platform)
backendStore:
  databaseMigration: true
  postgres:
    enabled: true
    host: postgresql.platform.svc
    port: 5432
    database: mlflow
    user: mlflow
    password: ""           # Use a Kubernetes Secret

artifactRoot:
  s3:
    enabled: true
    bucket: mlflow-artifacts
    awsAccessKeyId: ""     # MinIO access key — use a Kubernetes Secret
    awsSecretAccessKey: "" # MinIO secret key — use a Kubernetes Secret
  s3EnvVars:
    - name: MLFLOW_S3_ENDPOINT_URL
      value: http://minio.platform.svc:9000

ingress:
  enabled: true            # Q8: set to false for internal-only access
  annotations:
    kubernetes.io/ingress.class: traefik
  hosts:
    - host: mlflow.platform.local
      paths:
        - path: /
```
