# Deployment Questionnaire — Zammad (AI Helpdesk)

Answer these questions before deploying Zammad. *(ISO/IEC 42001: B.6.2.6.6, B.8.0.4.1, B.8.0.5.1)*

---

## Section 1: Incident Scope

**Q1. What types of AI system incidents should be tracked in Zammad?** *(select all that apply)*

- [ ] Prediction errors reported by operators
- [ ] Adverse treatment caused by AI decisions *(B.8.0.4.1 — required)*
- [ ] System outages or unavailability *(B.8.0.5.1)*
- [ ] Data quality problems
- [ ] Access and permission requests
- [ ] Compliance and audit queries
- [ ] Retraining requests from production staff

**Q2. Should Grafana alerts automatically create Zammad tickets?** *(B.8.0.5.1)*

- [ ] Yes — configure Grafana webhook contact point to Zammad API *(recommended)*
- [ ] No — manual ticket creation only

---

## Section 2: Users & Notifications

**Q3. Who will use the AI Helpdesk?**

- [ ] Machine operators (production floor)
- [ ] Maintenance technicians
- [ ] Production managers
- [ ] Data scientists
- [ ] Compliance officers / auditors

**Q4. How should incident notifications be sent?**

- [ ] Email — configure SMTP relay; provide SMTP server details
- [ ] Slack / Teams integration
- [ ] In-app notifications only
- [ ] No outbound notifications

---

## Section 3: SLA & Compliance Requirements

**Q5. What response time SLA applies to AI-related incidents?**

| Incident Priority | Response Time SLA |
|-------------------|-------------------|
| Critical (system down) | _____ hours |
| High (prediction failure) | _____ hours |
| Medium (data quality) | _____ business days |
| Low (information request) | _____ business days |

**Q6. How long should incident records be retained?** *(B.6.2.8.1 — audit evidence)*

- [ ] 1 year
- [ ] 3 years (recommended for ISO/IEC 42001 audit cycles)
- [ ] 5+ years (regulatory requirement in some sectors)

---

## Section 4: Authentication

**Q7. Should Zammad use Keycloak SSO?**

- [ ] Yes — configure SAML or OIDC integration with Keycloak *(recommended)*
- [ ] No — Zammad local authentication

---

## Recommended Configuration Summary

```yaml
# values.yaml — Zammad (Enterprise)
ingress:
  enabled: true
  annotations:
    kubernetes.io/ingress.class: traefik
  hosts:
    - host: helpdesk.enterprise.local
      paths:
        - path: /

zammad:
  smtp:
    enabled: true              # Q4: enable for email notifications
    host: smtp.plant.local
    port: 587

postgresql:
  enabled: false               # Use external PostgreSQL
  # Configure externalPostgresql section

elasticsearch:
  enabled: true                # Required for full-text search

resources:
  zammad:
    requests:
      cpu: "500m"
      memory: "1Gi"
    limits:
      cpu: "1500m"
      memory: "2Gi"
```
