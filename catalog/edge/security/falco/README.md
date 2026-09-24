# Falco: Runtime Security Monitoring

| Field | Value |
|-------|-------|
| **Chart** | `edge-falco` |
| **Tier** | Edge (DaemonSet on every node) |
| **Namespace** | `falco` |
| **Category** | Security |
| **RA Component** | Security Monitoring (CMP-15, edge and platform) |
| **ISO/IEC 42001** | B.6.2.6.7 · B.6.2.8.1 |
| **Helm Chart** | `falcosecurity/falco` (wrapped), images from `public.ecr.aws/falcosecurity` |
| **K3S Compatible** | Yes (modern eBPF driver, kernel >= 5.8 with BTF) |

---

## Description

Falco is a cloud-native **runtime security monitoring** tool that detects anomalous activity in containers by analysing system calls. In the reference architecture it implements the **Security Monitoring** component. It runs on every node (edge and platform), with the K3s containerd socket (`/run/k3s/containerd/containerd.sock`) as container engine.

Its key roles are:

- **Adversarial activity detection**: the default Falco rules plus three AI workload rules:
  - *Unexpected Model File Access*: read of `/models/` by a container other than the model server (`fastapi-model`) or the version sync job (`sync`);
  - *AI Container Shell Spawn*: shell started inside `fastapi-model`;
  - *Unexpected Outbound Connection from AI*: connection from `fastapi-model` outside the cluster networks (10.42.0.0/16, 10.43.0.0/16).
- **Container escape monitoring**: privilege escalation and container breakout rules of the default rule set.
- **Audit trail generation**: Falcosidekick sends events of priority `notice` and above to Loki (`platform-loki.monitoring:3100`, JSON), contributing to B.6.2.8.1.

The AI rules are validated with `falco -V` against the default rules. The previous outbound rule compared `fd.sip` with DNS names and failed to compile (`unrecognized IPv4 address`).

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Falco Addresses It |
|--------|-------------|------------------------|
| B.6.2.6.7 | Operation: Security Monitoring | Runtime detection of anomalous behaviour against AI workloads |
| B.6.2.8.1 | Operation: Logging / Audit Trail | Security events stored in Loki |

---

## Prerequisites

- Linux kernel >= 5.8 with BTF (Ubuntu 24.04) for the `modern_ebpf` driver.
- `platform-loki` for the events.
- Privileged DaemonSet allowed in the `falco` namespace; egress to the internet on 443 for falcoctl rule artefacts (in the NetworkPolicies).

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install edge-falco cigip-upv/edge-falco -n falco

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=edge-falco
```

---

## Key Configuration Decisions

| Decision | Options | Choice in this chart |
|----------|---------|----------------------|
| Driver | kmod / ebpf / modern_ebpf | **modern_ebpf**: built into Falco, no probe download or kernel headers |
| Scope | Edge nodes / every node | **Every node**: CMP-15 covers edge and platform |
| Alert output | stdout / Falcosidekick | **Falcosidekick to Loki** |
| Image registry | Docker Hub / public ECR | **Public ECR** (no anonymous Docker Hub rate limit) |

---

## Related Solutions

- [Loki](../../../platform/monitoring/loki/README.md): storage of Falco events
- [Grafana](../../../platform/monitoring/grafana/README.md): Security Events and Audit Trail dashboard
- [Keycloak](../../../enterprise/access-management/keycloak/README.md): identity management complement to runtime security
