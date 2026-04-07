# Questionnaire 04 — Enterprise Tier Requirements

Complete this questionnaire to configure the Enterprise tier deployment.

---

## Section 1: User Base & Identity

**Q4.1. How many users will interact with the AI system interfaces?**

- [ ] < 20 (small team) — Keycloak single instance, minimal resources
- [ ] 20–200 — Keycloak with PostgreSQL backend
- [ ] > 200 — Keycloak cluster mode; integrate with existing LDAP/AD

**Q4.2. Does your organisation have an existing identity directory?**

- [ ] Microsoft Active Directory — configure Keycloak LDAP federation
- [ ] Azure AD — configure OIDC broker
- [ ] None — Keycloak as standalone identity provider
- [ ] Other IAM already in place — evaluate if Keycloak is still needed

---

## Section 2: Governance Interfaces

**Q4.3. Which enterprise-facing interfaces are needed?**

- [ ] **Grafana** KPI dashboards for production managers *(required — B.6.2.6.3)*
- [ ] **Grafana** Operator Feedback panel *(required — B.6.1.3.3)*
- [ ] **Zammad** AI Helpdesk *(required — B.6.2.6.6)*
- [ ] **MinIO Document Store** for compliance documentation *(required — B.6.2.3.1)*
- [ ] Custom React information centre (see reference architecture validation)
- [ ] ERP/MES integration API endpoints

**Q4.4. Does the enterprise tier need to integrate with existing systems?**

- [ ] ERP (SAP, Oracle, Microsoft Dynamics) — configure REST API adapter in Node-RED or middleware
- [ ] MES (Siemens Opcenter, Tulip, custom) — OPC-UA or REST integration
- [ ] SCADA (Ignition, WinCC) — MQTT or OPC-UA bridge
- [ ] Business Intelligence (Power BI, Tableau) — expose TimescaleDB or Grafana API

---

## Section 3: Compliance & Documentation

**Q4.5. Who is responsible for ISO/IEC 42001 compliance management?**

| Role | Name | Keycloak Role |
|------|------|---------------|
| Compliance Officer | | `compliance-officer` |
| Data Scientist (model approval) | | `data-scientist` |
| Production Manager (business approval) | | `production-manager` |
| System Administrator | | `admin` |

**Q4.6. What documents must be maintained in the Document Store?** *(B.6.2.3.1, B.6.2.5.1, B.6.2.6.5)*

- [ ] System Architecture Documentation
- [ ] Deployment Plan
- [ ] Update and Repair Plan
- [ ] Risk Assessment
- [ ] ALTAI Self-assessment
- [ ] Model Cards (per model version)
- [ ] Completed compliance questionnaires (this document series)
- [ ] Audit reports and evidence

---

## Section 4: Enterprise Component Selection

| Component | Deploy? | Notes |
|-----------|---------|-------|
| Keycloak | **Yes** | B.6.1.3.1 (required) |
| Zammad | **Yes** | B.6.2.6.6 (required) |
| MinIO (Document Store) | **Yes** | B.6.2.3.1 (required) |
| Grafana (Enterprise dashboards) | **Yes** | Shared with Platform tier or separate instance |
| ERP/MES integration adapter | Yes / No | Q4.4 — scope depends on existing systems |

---

## Output Summary

Save this questionnaire to MinIO as `enterprise-deployment-config.md` *(supports B.6.2.5.1)*.

Proceed to:
- [Questionnaire 05 — ISO/IEC 42001 Compliance](./05-iso42001-compliance.md) *(final step)*
