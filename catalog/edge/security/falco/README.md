# Falco — Runtime Security Monitoring

| Field | Value |
|-------|-------|
| **Tier** | Edge |
| **Category** | Security |
| **RA Component** | Security Monitoring |
| **ISO/IEC 42001** | B.6.2.6.7 |
| **Helm Chart** | `falcosecurity/falco` |
| **K3S Compatible** | Yes (requires kernel module or eBPF driver) |

---

## Description

Falco is a cloud-native **runtime security monitoring** tool that detects anomalous activity in containers and Kubernetes workloads by analysing system calls. In the reference architecture, it is the primary implementation of the **Security Monitoring** component at the Edge tier.

Its key roles are:

- **Adversarial activity detection**: identifies unexpected process executions, file access, or network connections that could indicate adversarial ML attacks (data poisoning, model stealing).
- **Container escape monitoring**: detects privilege escalation or container breakout attempts on edge nodes.
- **Audit trail generation**: Falco alerts are forwarded to Fluent Bit → Loki, contributing to the event log required by B.6.2.8.1.
- **Industrial perimeter protection**: combined with K3S network policies, enforces ISA/IEC 62443 zone segmentation at the workload level.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Falco Addresses It |
|--------|-------------|------------------------|
| B.6.2.6.7 | Threat Detection | Runtime detection of adversarial/anomalous behaviour against AI workloads |
| B.6.2.8.1 | Event Logs | Security events forwarded to centralised log sink |

---

## Prerequisites

- K3S node with Linux kernel ≥ 5.8 (for eBPF driver) or kernel headers (for kernel module)
- `helm` CLI available
- Fluent Bit deployed for log forwarding (recommended)
- Sufficient node privileges: Falco requires privileged DaemonSet

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Installation (K3S / Helm)

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

helm install falco falcosecurity/falco \
  --namespace falco \
  --create-namespace \
  --set driver.kind=ebpf \
  -f values.yaml
```

> **K3S Note**: K3S uses containerd as the container runtime. Set `containerd.enabled=true` in Falco's values to ensure correct socket path (`/run/k3s/containerd/containerd.sock`).

---

## Key Configuration Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Driver | kernel module / eBPF | **eBPF** — preferred for modern kernels; avoids kernel module compilation |
| Alert output | stdout / file / gRPC | **Falco Sidekick → Fluent Bit** for centralised log aggregation |
| Custom rules | None / AI-specific | Add rules for ML model file access patterns |
| Falcosidekick | Optional | **Recommended** — routes alerts to Loki, Slack, or alerting systems |

---

## Related Solutions

- [Fluent Bit](../../monitoring/fluent-bit/README.md) — log forwarding for Falco alerts
- [Keycloak](../../../enterprise/access-management/keycloak/README.md) — IAM complement to runtime security
- [Loki](../../../platform/monitoring/loki/README.md) — centralised log storage for Falco events
