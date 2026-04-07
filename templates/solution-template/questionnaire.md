# Deployment Questionnaire — [Solution Name]

> **Instructions**: Copy this template alongside the solution README. Structure questions by functional area. Each question should directly influence a configuration value in `manifests/values.yaml`. Delete this instruction block before publishing.

Answer these questions before deploying [Solution Name]. *(ISO/IEC 42001: list relevant clauses)*

---

## Section 1: [Functional Area Name]

**Q1. [Question text ending with a question mark?]**

- [ ] Option A — *description and implication*
- [ ] Option B — *description and implication*
- [ ] Option C — *description and implication*

> **Guidance**: *Explain why this question matters and how the answer affects the deployment.*

**Q2. [Question text]**

- [ ] Option A
- [ ] Option B

---

## Section 2: Security & Compliance

**Q[n]. Which ISO/IEC 42001 requirements does this deployment need to satisfy?**

*(Link back to the specific clauses this solution addresses)*

- [ ] B.x.x.x — *description* — *which configuration option enables this*
- [ ] B.x.x.x — *description* — *which configuration option enables this*

---

## Section 3: Resource Constraints

**Q[n]. What resources are available for this component?**

| Resource | Available | Minimum Required |
|----------|-----------|-----------------|
| CPU cores | | |
| RAM (GB) | | |
| Storage (GB) | | |

---

## Recommended Configuration Summary

```yaml
# values.yaml — [Solution Name]
# Fill in based on your questionnaire answers

key1: value1       # Q1: set to X if answer was Option A
key2: value2       # Q2: adjust based on available resources

resources:
  requests:
    cpu: "Xm"
    memory: "XMi"
  limits:
    cpu: "Xm"
    memory: "XMi"
```
