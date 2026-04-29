# Argo CD — `platform-argocd`

> GitOps controller that reconciles the declared state of the catalog against the cluster, providing an immutable change-management audit trail.

[\![Tier](https://img.shields.io/badge/tier-platform-1e40af)](#) [\![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [\![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `platform`
- **Category**: `Orchestration`
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.2.5.1`, `B.6.2.6.4`, `B.6.2.8.1`

This chart packages **Argo CD** for the **platform** tier of the reference architecture, covering the *Orchestration* capability block. It ships with production-ready defaults for K3s and a Rancher-compatible `questions.yaml`, so operators can deploy the component from the Rancher UI with guided prompts for every configuration variable.

---

## Quick start

```bash
# Add the Helm repository
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm repo update

# Install this chart
helm install argocd cigip-upv/platform-argocd \
  --namespace platform \
  --create-namespace
```

Alternatively, clone the repository and install from the manifests folder:

```bash
git clone https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog
cd MLOps-ISO42001-K3s-Catalog/catalog/platform/orchestration/argocd/manifests
helm dependency update .
helm install argocd . -n platform --create-namespace
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml).
For a Rancher-driven deployment, the friendly questionnaire lives in
[`questions.yaml`](./manifests/questions.yaml); Rancher will render one form
field per declared question when the chart is installed from the catalog.

Override any value at install time:

```bash
helm install argocd cigip-upv/platform-argocd \
  --namespace platform --create-namespace \
  --set someKey=someValue
```

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.2.5.1` | Planning — Deployment Plan |
| `B.6.2.6.4` | Operation — Retraining / Lifecycle |
| `B.6.2.8.1` | Operation — Logging / Audit Trail |

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#iso-42001-annex-b-coverage).

---

## Maintainer

- **CIGIP-UPV** — *https://cigip.webs.upv.es/* — `cigip@upv.es`

Released under the Apache 2.0 License.
