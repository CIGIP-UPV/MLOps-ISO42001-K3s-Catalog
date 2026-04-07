# Deployment Questionnaire — Falco (Edge Security Monitoring)

Answer these questions before deploying Falco at the edge. *(ISO/IEC 42001: B.6.2.6.7)*

---

## Section 1: Kernel & Driver Compatibility

**Q1. What Linux kernel version is running on the edge node?**

```bash
uname -r   # Run this command to check
```

- [ ] ≥ 5.8 — **use eBPF driver** (`driver.kind=ebpf`) — recommended, no compilation needed
- [ ] 4.x – 5.7 — use kernel module (`driver.kind=module`) — requires kernel headers installed
- [ ] < 4.x — **Falco not supported**; consider alternative intrusion detection tools

**Q2. Are kernel headers installed on the edge node?** *(only required for kernel module driver)*

- [ ] Yes — proceed with module driver if on older kernel
- [ ] No — install via: `apt install linux-headers-$(uname -r)` or equivalent

---

## Section 2: AI Workload Threat Profile

**Q3. Which AI-specific threats are you most concerned about?** *(B.6.2.6.7)*

- [ ] **Data poisoning**: adversarial manipulation of training or inference input data
- [ ] **Model stealing**: unauthorised read access to model files or API endpoints
- [ ] **Model inversion**: probing inference API to extract training data
- [ ] **Adversarial examples**: malformed inputs designed to mislead the model
- [ ] **Unauthorised container access**: shell spawning or file system tampering in AI containers
- [ ] **Exfiltration**: unexpected outbound network connections from AI workloads

> For each threat checked, consider adding a custom Falco rule in `manifests/custom_rules.yaml`.

---

## Section 3: Alert Routing

**Q4. Where should Falco security alerts be sent?**

- [ ] Loki (via Falco Sidekick) — integrates with Grafana dashboards
- [ ] Zammad helpdesk — creates incident tickets automatically *(B.6.2.6.6)*
- [ ] Prometheus Alertmanager — metric-based alerting
- [ ] Slack / Teams webhook — immediate human notification
- [ ] Log file only — minimal setup

**Q5. Should Falco alerts trigger automatic responses?**

- [ ] No — alerts for human review only *(recommended for initial deployment)*
- [ ] Yes — define automated remediation rules (e.g., kill suspicious pod)

> **Note**: Automated response rules must be documented in the Update & Repair Plan *(B.6.2.6.5)* stored in MinIO.

---

## Section 4: Resource Constraints

**Q6. What are the resource constraints on the edge node?**

- [ ] Constrained (≤ 4 CPU cores, ≤ 8 GB RAM) — reduce Falco's CPU limit; disable verbose rules
- [ ] Standard (4–8 CPU cores) — default resource limits are appropriate
- [ ] Ample resources — enable full rule set including additional community rules

---

## Recommended Configuration Summary

```yaml
# values.yaml — Falco (Edge)
driver:
  kind: ebpf            # Q1: use 'module' for kernels < 5.8

containerd:
  enabled: true
  socket: /run/k3s/containerd/containerd.sock   # K3S-specific path

falcosidekick:
  enabled: true         # Q4: enable if routing alerts externally
  config:
    loki:
      hostport: http://loki.platform.svc:3100   # adjust namespace

resources:
  requests:
    cpu: "100m"         # Q6: reduce to 50m on constrained nodes
    memory: "256Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
```
