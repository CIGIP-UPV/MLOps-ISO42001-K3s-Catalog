# Questionnaire 03 — Platform Tier Requirements

Complete this questionnaire to configure the Platform tier deployment.

---

## Section 1: Cluster Configuration

**Q3.1. How will the platform K3S cluster be managed?**

- [ ] Standalone K3S (single server) — suitable for development/MVP
- [ ] K3S HA cluster (3 server nodes) — recommended for production
- [ ] **Rancher-managed K3S** — recommended for multi-cluster management and UI console

**Q3.2. What is the platform cluster's hardware specification?**

| Specification | Node 1 | Node 2 | Node 3 |
|---------------|--------|--------|--------|
| CPU cores | | | |
| RAM (GB) | | | |
| Storage (GB) | | | |

---

## Section 2: AI Lifecycle Requirements

**Q3.3. What is your model retraining frequency?**

- [ ] On-demand only (manual trigger)
- [ ] Weekly — configure MLflow + weekly CronJob
- [ ] Monthly — configure monthly CronJob
- [ ] Drift-triggered (continuous monitoring) — configure Prometheus alert → retraining pipeline

**Q3.4. How much training data is expected in the data warehouse?**

- [ ] < 10 GB — TimescaleDB single instance sufficient
- [ ] 10–500 GB — TimescaleDB with compression policies
- [ ] > 500 GB — consider object storage (MinIO) for cold data + TimescaleDB for hot data

**Q3.5. Do you require GPU support for model training?**

- [ ] No — CPU-only training (sklearn, lightweight LSTM)
- [ ] Yes — configure K3S GPU plugin for NVIDIA; install CUDA-enabled PyTorch container

---

## Section 3: Platform Component Selection

| Component | Deploy? | Rationale |
|-----------|---------|-----------|
| MLflow | **Yes** | B.6.1.3.2 — Version Control (required) |
| Training Jobs (CronJob) | Yes / No | Required if Q3.3 = scheduled retraining |
| Prometheus | **Yes** | B.6.1.2.2 (required) |
| Grafana | **Yes** | B.6.2.6.3 (required) |
| Loki | **Yes** | B.6.2.8.1 (required) |
| MinIO | **Yes** | B.6.2.3.1, B.6.2.5.1 (required) |
| TimescaleDB | Yes / No | Required if Q3.4 > 10 GB or Q3.3 = drift-triggered |
| PostgreSQL | **Yes** | MLflow metadata backend (required) |
| Rancher | Yes / No | Recommended for Q3.1 = Rancher-managed |

---

## Section 4: Data Flow Configuration

**Q3.6. How will edge data reach the platform?**

- [ ] **Kafka** (streaming) — Edge Kafka producer → Platform Kafka consumer → TimescaleDB
- [ ] **Batch sync** (PostgreSQL dump → Platform ingest) — for intermittent connectivity
- [ ] **Direct HTTP/REST** — Edge pushes to platform API endpoint
- [ ] **Fluent Bit → Loki** (log data only) + separate pipeline for sensor data

---

## Output Summary

Save this questionnaire to MinIO as `platform-deployment-config.md` *(supports B.6.2.5.1)*.

Proceed to:
- [Questionnaire 04 — Enterprise Requirements](./04-enterprise-requirements.md)
- [Questionnaire 05 — ISO/IEC 42001 Compliance](./05-iso42001-compliance.md)
