# Questionnaire 05 — ISO/IEC 42001 Compliance Mapping

Use this questionnaire to verify that your component selection satisfies each ISO/IEC 42001 Annex B requirement. This document can serve as evidence during internal reviews or external audits.

**Instructions**: For each requirement, check the box if the corresponding component is deployed and configured. Add a note explaining the gap if a component is not deployed.

---

## B.6.1 — Oversight and Control

### B.6.1.2.2 — Integration of Metrics
*The RA must provide users with the ability to integrate metrics into the various phases of the AI lifecycle.*

- [ ] **Prometheus** deployed and scraping metrics from all tiers
- [ ] **Grafana** dashboards configured for model technical performance
- [ ] **FastAPI model server** `/metrics` endpoint active
- [ ] **Prometheus Agent** at edge forwarding metrics to platform

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.1.3.1 — Human Oversight
*The RA must provide users with the ability to monitor decisions made by the AI system.*

- [ ] **Grafana** dashboard showing recent predictions visible to authorised users
- [ ] **Keycloak** roles configured to restrict access to oversight interfaces
- [ ] **Feedback Interface** (Grafana annotation panel) allowing operators to review predictions

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.1.3.2 — Version Control
*The RA must provide users with the ability to view current version of the deployed AI application.*

- [ ] **MLflow Model Registry** tracking all model versions
- [ ] **FastAPI model server** exposes `/version` endpoint
- [ ] Version history accessible from Grafana Information Centre panel

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.1.3.3 — Usability and Controllability
*The RA must provide users with the ability to interact with and control the AI system.*

- [ ] **Grafana Feedback Interface** operational
- [ ] **Zammad AI Helpdesk** reachable by all relevant user roles
- [ ] **Keycloak** role assignments reviewed and documented

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.1.3.4 — Release Criteria
*The RA must ensure release criteria are taken into account before deployment.*

- [ ] **MLflow model staging gates** configured (Staging → Production requires approval)
- [ ] Performance thresholds documented in MLflow and in the Deployment Plan (MinIO)
- [ ] Model promotion approval workflow documented and tested

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

## B.6.2 — AI System Lifecycle

### B.6.2.3.1 — System Architecture Documentation
*The RA must ensure availability of the final system architecture documentation.*

- [ ] Architecture diagram stored in **MinIO Document Store** (`iso42001-docs/architecture/`)
- [ ] Document version controlled and accessible to compliance officer role

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.2.5.1 — Deployment Plan
*The RA must ensure availability of the deployment plan.*

- [ ] Deployment plan document stored in **MinIO** (`iso42001-docs/deployment-plan/`)
- [ ] Plan includes verification/validation metrics, performance metrics, approvals
- [ ] Completed Questionnaire 01 stored alongside deployment plan

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.2.6.1 — Error Monitoring
*The RA must provide mechanisms for monitoring general and technical errors.*

- [ ] **Prometheus** alerting rules configured for infrastructure errors
- [ ] **Loki** log queries available for error-level events
- [ ] **Grafana** alert routing to Zammad for critical errors

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.2.6.2 — Technical Performance Monitoring
*The RA must provide mechanisms for monitoring AI system technical performance.*

- [ ] **Prometheus** model metrics (latency, accuracy, error rate) active
- [ ] **Grafana** model performance dashboard deployed
- [ ] Alerting thresholds set for model degradation indicators

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.2.6.3 — Goal-oriented Performance Monitoring
*The RA must enable overview of decisions and predictions for subsequent analysis.*

- [ ] **Grafana** KPI dashboard (OEE, availability, downtime) deployed
- [ ] **TimescaleDB** storing historical predictions and KPIs
- [ ] Business KPIs baseline established and documented

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.2.6.4 — Retraining Monitoring
*The RA must provide mechanisms to detect drift and recommend/trigger retraining.*

- [ ] **Node-RED** input data validation rules configured
- [ ] **Retraining job** (CronJob or triggered) deployed in Platform tier
- [ ] **MLflow** tracking retraining runs and linking to drift signals
- [ ] **Feedback Interface** collecting operator labels for retraining

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.2.6.5 — Update and Repair Plan
*The RA must ensure availability of the update and repair plan.*

- [ ] Update/repair plan document stored in **MinIO** (`iso42001-docs/update-repair-plan/`)
- [ ] Plan includes rollback procedures linked to MLflow model versioning

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.2.6.6 — AI Helpdesk
*The RA must provide an AI helpdesk for assistance and incident reporting.*

- [ ] **Zammad** deployed and accessible to all AI system users
- [ ] Ticket categories configured (Prediction Error, Adverse Treatment, System Outage)
- [ ] SLA targets defined and configured in Zammad

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.2.6.7 — Threat Detection
*The RA must provide mechanisms for detecting attacks on the AI system.*

- [ ] **Falco** deployed on all edge nodes with AI workloads
- [ ] **Keycloak** enforcing authentication on all API endpoints
- [ ] **Node-RED** data validation filtering anomalous inputs
- [ ] Falco alerts forwarded to Loki and/or Zammad

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.6.2.8.1 — Event Logs
*The RA must provide mechanisms for automatically storing event logs.*

- [ ] **Fluent Bit** running as DaemonSet on edge nodes
- [ ] **Loki** receiving and storing logs from all tiers
- [ ] Log retention period configured (recommended ≥ 90 days)
- [ ] **Keycloak** authentication events forwarded to Loki

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

## B.8 — Transparency and Communication

### B.8.0.2.1 — User Information
*The RA must allow users to input all necessary types of information.*

- [ ] **Grafana** Information Centre panel shows AI system status and predictions
- [ ] **Keycloak** user account console accessible to all users
- [ ] User documentation available in MinIO or Zammad knowledge base

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.8.0.4.1 — Display of Adverse Treatment
*The RA must allow users to indicate adverse treatment caused by the AI system.*

- [ ] **Zammad** ticket category "Adverse Treatment" configured
- [ ] Users trained on how to report adverse treatment incidents
- [ ] Adverse treatment reports linked to model version in MLflow for traceability

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

### B.8.0.5.1 — Incident Communication
*The RA must provide mechanisms for communicating AI system incidents.*

- [ ] **Grafana Alertmanager** configured to create **Zammad** tickets automatically
- [ ] Incident notification workflow tested end-to-end
- [ ] Incident communication contacts documented in MinIO

**Deployed by**: ___________ **Date**: ___________
**Gap/Note**: ___________

---

## Compliance Summary

| Total Requirements | Fully Addressed | Partially Addressed | Not Yet Addressed |
|-------------------|-----------------|---------------------|-------------------|
| 18 | | | |

**Compliance officer**: ___________ **Review date**: ___________

**Next review scheduled**: ___________

> Save this completed document to MinIO (`iso42001-docs/compliance-review/YYYY-MM-DD-review.md`) as evidence of the compliance assessment.
