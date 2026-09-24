# Fluent Bit: Log Collector and Forwarder

| Field | Value |
|-------|-------|
| **Chart** | `edge-fluent-bit` |
| **Tier** | Edge (DaemonSet on every node) |
| **Namespace** | `logging` |
| **Category** | Monitoring · Logging |
| **RA Component** | Logger (CMP-09, edge and platform) |
| **ISO/IEC 42001** | B.6.2.8.1 |
| **Helm Chart** | `fluent/fluent-bit` (wrapped), image from `cr.fluentbit.io` |
| **K3S Compatible** | Yes |

---

## Description

Fluent Bit is a lightweight **log collector and forwarder** deployed as a DaemonSet. In the reference architecture it implements the **Logger** component at the edge and platform levels: it runs on every node, not only on edge nodes, so the logs of platform workloads are collected too.

Its key roles are:

- **Log collection**: tails the container logs of every pod on the node (`/var/log/containers`, CRI format), including the JSON event lines of the catalog jobs (version sync, data consolidation, training, drift check).
- **API audit trail**: tails the Kubernetes API audit log (`/var/log/kubernetes/audit/audit.log`, written by the audit policy installed by `setup-ubuntu.sh` or `enable-audit.sh`) and ships it with `job=kube-apiserver-audit`.
- **Log enrichment**: adds Kubernetes metadata and labels every Loki stream with `namespace`, `pod`, `container`, `chart` and `tier` (the last two from the iso42001 labels of the pod).
- **Store and forward**: a filesystem buffer (`storage.path /var/log/flb-storage/`, up to 1 GiB per output) keeps logs while Loki is unreachable. Earlier versions wrote every log line to an unbounded plain file on the host instead.

Output: `platform-loki.monitoring.svc.cluster.local:3100`.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Fluent Bit Addresses It |
|--------|-------------|------------------------------|
| B.6.2.8.1 | Operation: Logging / Audit Trail | Captures and forwards the logs of every node and the API audit log to Loki |

---

## Prerequisites

- `platform-loki` in the `monitoring` namespace.
- The API audit policy on the server node (optional; the audit input is empty otherwise).
- NetworkPolicy allowing `logging` to reach `monitoring` on 3100 (in `infrastructure/01-network-policies.yaml`).

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install edge-fluent-bit cigip-upv/edge-fluent-bit -n logging

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=edge-fluent-bit
```

---

## Key Configuration Decisions

| Decision | Options | Choice in this chart |
|----------|---------|----------------------|
| Scope | Edge nodes only / every node | **Every node**: CMP-09 covers edge and platform |
| Output destination | Loki / Elasticsearch / stdout | **Loki**, queried from Grafana |
| Buffering | None / plain file / filesystem storage | **Filesystem storage** with a size limit |
| Stream labels | Auto Kubernetes labels / selected keys | Selected keys (low cardinality), including the catalog chart |

---

## Related Solutions

- [Loki](../../../platform/monitoring/loki/README.md): centralised log storage (output destination)
- [Grafana](../../../platform/monitoring/grafana/README.md): log visualisation (Security Events and Audit Trail dashboard)
- [Falco](../../security/falco/README.md): security events reach Loki through Falcosidekick
