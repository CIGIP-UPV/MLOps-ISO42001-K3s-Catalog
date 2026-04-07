# Questionnaire 01 — Deployment Scope

This questionnaire determines which tiers and components of the reference architecture to deploy in your context. Complete this before proceeding to tier-specific questionnaires.

---

## Section 1: Organisational Context

**Q1.1. What is the size of your organisation?**

- [ ] SME (< 250 employees) — prioritise MVP: Edge + essential Platform components
- [ ] Mid-size (250–1000 employees) — full three-tier deployment recommended
- [ ] Large enterprise (> 1000 employees) — full deployment with high-availability configurations

**Q1.2. What is your target use case for the AI system?** *(select primary)*

- [ ] Predictive maintenance (PdM) — CNC, stamping press, conveyor systems
- [ ] Quality control / visual inspection
- [ ] Process optimisation (yield, energy, scheduling)
- [ ] Anomaly detection (production deviations)
- [ ] Other: ___________

**Q1.3. What is your certification intent?**

- [ ] ISO/IEC 42001 formal certification (external audit) — full compliance mapping required
- [ ] Internal alignment with ISO/IEC 42001 — pragmatic compliance
- [ ] No certification intent — deploy best practices only

> Your answer to Q1.3 determines the priority of compliance-mapping activities in Questionnaire 05.

---

## Section 2: Infrastructure Readiness

**Q2.1. What computing infrastructure is available at the production site?**

- [ ] Industrial PC / mini PC at machine level (≤ 8 GB RAM) — Edge tier only
- [ ] On-premises server room (rack server, ≥ 32 GB RAM) — Edge + Platform
- [ ] Private cloud or data centre — full three-tier deployment
- [ ] Hybrid (on-prem + public cloud) — Edge on-prem, Platform/Enterprise in cloud

**Q2.2. Is Kubernetes (K3S or standard) already running at your site?**

- [ ] No — K3S installation guide: [Install K3S](https://docs.k3s.io/quick-start)
- [ ] K3S already running — proceed directly to component selection
- [ ] Standard Kubernetes — solutions are compatible; Helm charts work without modification

**Q2.3. What is the network connectivity between tiers?**

- [ ] Reliable LAN (< 1 ms latency) — streaming data flows are viable
- [ ] WAN / VPN (10–100 ms latency) — batch sync preferred between Edge and Platform
- [ ] Intermittent (cellular, satellite) — **critical**: Edge must be fully autonomous; buffering required
- [ ] Air-gapped (no internet) — all container images must be mirrored locally

---

## Section 3: Tier Selection

Based on your answers above, select the tiers you will deploy:

**Q3.1. Will you deploy an Edge tier?**

- [ ] **Yes** — proceed to [Questionnaire 02](./02-edge-requirements.md)
- [ ] No — platform-only deployment (latency constraints acceptable)

**Q3.2. Will you deploy a Platform tier?**

- [ ] **Yes** — proceed to [Questionnaire 03](./03-platform-requirements.md)
- [ ] No — edge-only MVP (defer platform to future iteration)

**Q3.3. Will you deploy an Enterprise tier?**

- [ ] **Yes** — proceed to [Questionnaire 04](./04-enterprise-requirements.md)
- [ ] No — enterprise functions handled by existing IT systems (ERP, SCADA)

---

## Section 4: MVP vs Full Deployment

**Q4.1. Are you deploying a Minimum Viable Product (MVP) first?**

- [ ] **Yes** — use the MVP component set below
- [ ] No — deploy the full reference architecture

### MVP Component Set (Edge + Minimal Platform)

If budget or timeline constraints apply, the following minimal set addresses the core ISO/IEC 42001 requirements:

| Component | Tool | Required Requirement |
|-----------|------|----------------------|
| Data ingestion | Node-RED | B.6.2.6.4 |
| Edge inference | FastAPI + model | B.6.1.2.2 |
| Edge storage | PostgreSQL | B.6.2.8.1 |
| Security monitoring | Falco | B.6.2.6.7 |
| Log forwarding | Fluent Bit | B.6.2.8.1 |
| Version control | MLflow (platform) | B.6.1.3.2 |
| Monitoring | Prometheus + Grafana | B.6.1.2.2 |
| Log aggregation | Loki | B.6.2.8.1 |

Components deferred from MVP (document deferral in the Deployment Plan):
- Keycloak (use basic auth initially)
- Zammad (use email for incident tracking initially)
- TimescaleDB (use PostgreSQL at platform initially)

---

## Output: Deployment Plan Summary

Complete this table and save it to the MinIO Document Store as `deployment-plan-v1.md` *(satisfies B.6.2.5.1)*:

| Tier | Deploy? | Components Selected | Target Date |
|------|---------|---------------------|-------------|
| Edge | | | |
| Platform | | | |
| Enterprise | | | |

**Architecture decision rationale**: *(document the reasons for included/excluded components)*

**Compliance officer sign-off**: ___________  **Date**: ___________
