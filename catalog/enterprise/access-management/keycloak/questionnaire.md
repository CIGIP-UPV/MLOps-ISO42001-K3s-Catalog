# Deployment Questionnaire — Keycloak (Enterprise IAM)

Answer these questions before deploying Keycloak. *(ISO/IEC 42001: B.6.1.3.1, B.6.1.3.3, B.8.0.2.1)*

---

## Section 1: Identity Source

**Q1. Where are user identities managed in your organisation?**

- [ ] No existing directory — Keycloak will be the identity source (create users manually)
- [ ] Microsoft Active Directory / LDAP — configure Keycloak User Federation
- [ ] Azure Active Directory — configure OIDC broker federation
- [ ] Google Workspace — configure OIDC broker federation
- [ ] Other: ___________

**Q2. How many users will authenticate through Keycloak?**

- [ ] < 50 — single-instance Keycloak, minimal resources
- [ ] 50–500 — single-instance with database backend
- [ ] > 500 — consider Keycloak cluster mode

---

## Section 2: Role Design

**Q3. Which roles are needed for the AI system?** *(B.6.1.3.1 — segregation of duties)*

- [ ] `operator` — machine operators viewing predictions and providing feedback
- [ ] `data-scientist` — model training, evaluation, MLflow access
- [ ] `compliance-officer` — audit log access, model approval, ISO documentation
- [ ] `production-manager` — KPI dashboards, model promotion approval
- [ ] `admin` — full platform administration
- [ ] Custom roles: ___________

**Q4. Should any roles require multi-factor authentication (MFA)?**

- [ ] Yes — `admin` and `compliance-officer` roles minimum (recommended)
- [ ] Yes — all roles
- [ ] No — single-factor authentication sufficient for internal deployment

---

## Section 3: Applications to Protect

**Q5. Which applications will use Keycloak for authentication?** *(select all that apply)*

- [ ] Grafana (OIDC)
- [ ] MLflow (via oauth2-proxy)
- [ ] MinIO console (native OIDC)
- [ ] FastAPI inference API (JWT validation)
- [ ] Zammad helpdesk (SAML/OIDC)
- [ ] Custom React frontend (OIDC)
- [ ] Other: ___________

---

## Section 4: Security & Compliance

**Q6. Is TLS/HTTPS available for the Keycloak endpoint?**

- [ ] Yes — provide certificate source: cert-manager / pre-existing / Let's Encrypt
- [ ] No — **do not deploy Keycloak in production without TLS**; set up cert-manager first

**Q7. Should authentication events be forwarded to the audit log?** *(B.6.2.8.1)*

- [ ] Yes — configure Keycloak event listener → Loki (via Fluent Bit)
- [ ] Keycloak internal event log is sufficient

---

## Recommended Configuration Summary

```yaml
# values.yaml — Keycloak (Enterprise)
auth:
  adminUser: admin
  adminPassword: ""        # Use Kubernetes Secret

postgresql:
  enabled: false           # Use external PostgreSQL
  # Configure externalDatabase section

ingress:
  enabled: true
  annotations:
    kubernetes.io/ingress.class: traefik
    cert-manager.io/cluster-issuer: letsencrypt   # Q6
  hostname: keycloak.enterprise.local
  tls: true

keycloakConfigCli:
  enabled: true            # Import realm configuration automatically

extraEnvVars:
  - name: KEYCLOAK_EXTRA_ARGS
    value: "--features=token-exchange"   # Enable for service-to-service auth
```
