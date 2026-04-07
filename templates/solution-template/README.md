# [Solution Name] — [Short Description]

> **Instructions**: Copy this template to `catalog/<tier>/<category>/<solution-name>/README.md` and fill in all fields. Delete this instruction block before publishing.

| Field | Value |
|-------|-------|
| **Tier** | Edge / Platform / Enterprise |
| **Category** | Data Ingestion / AI Inference / Monitoring / Security / Storage / AI Lifecycle / Access Management / Helpdesk / Dashboards |
| **RA Component** | *Name of the Reference Architecture component(s) this solution implements* |
| **ISO/IEC 42001** | *e.g., B.6.2.6.4 · B.6.2.8.1* |
| **Helm Chart** | *e.g., `bitnami/postgresql`* or `Custom manifest` |
| **K3S Compatible** | Yes / Yes (with caveats — describe below) / No |

---

## Description

*2–4 paragraphs describing:*
*1. What this solution is and what it does.*
*2. Its specific role(s) within the reference architecture.*
*3. Any K3S-specific considerations (storage class, privileged access, kernel requirements, etc.).*

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How [Solution Name] Addresses It |
|--------|-------------|----------------------------------|
| B.x.x.x | *Requirement keyword* | *Specific mechanism* |

---

## Prerequisites

*List all dependencies that must be deployed before this solution:*

- K3S cluster version ≥ x.x
- Persistent volumes available (storage class: `local-path` or specify)
- Other solutions: [link to their READMEs]
- Network requirements: ports, firewall rules
- Special hardware: GPU, kernel version, etc.

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md) for the pre-deployment decision guide.

---

## Installation (K3S / Helm)

```bash
helm repo add <repo-name> <repo-url>
helm repo update

helm install <release-name> <chart> \
  --namespace <namespace> \
  --create-namespace \
  -f values.yaml
```

*Or for custom manifests:*

```bash
kubectl apply -f manifests/
```

---

## Key Configuration Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| *Decision name* | *Option A / Option B* | *Recommended option and brief rationale* |

---

## Related Solutions

- [Solution A](../../path/to/solution-a/README.md) — *relationship description*
- [Solution B](../../path/to/solution-b/README.md) — *relationship description*
