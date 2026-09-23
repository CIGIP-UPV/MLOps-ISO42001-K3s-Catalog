# Argo CD: `platform-argocd`

> GitOps controller that reconciles the declared state of the catalog against the cluster, providing an immutable change-management audit trail.

[![Tier](https://img.shields.io/badge/tier-platform-1e40af)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `platform`
- **Category**: `Orchestration`
- **Namespace**: `argocd`
- **Reference architecture components**: `CMP-03` Version Control
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.2.5.1`, `B.6.2.6.4`, `B.6.2.8.1`

This chart packages **Argo CD** for the **platform** tier of the reference architecture, covering the *Orchestration* capability block. It ships with defaults for K3s and a Rancher-compatible `questions.yaml`, so operators can deploy the component from the Rancher UI with guided prompts.

---

## Quick start

```bash
# Add the Helm repository
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm repo update

# Install this chart
helm install platform-argocd cigip-upv/platform-argocd \
  --namespace argocd \
  --create-namespace
```

Alternatively, clone the repository and install from the manifests folder:

```bash
git clone https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog
cd MLOps-ISO42001-K3s-Catalog/catalog/platform/orchestration/argocd/manifests
helm dependency build .
helm install platform-argocd . -n argocd --create-namespace
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml).
For a Rancher-driven deployment, the friendly questionnaire lives in
[`questions.yaml`](./manifests/questions.yaml); Rancher will render one form
field per declared question when the chart is installed from the catalog.

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.2.5.1` | Planning: Deployment Plan |
| `B.6.2.6.4` | Operation: Retraining / Lifecycle |
| `B.6.2.8.1` | Operation: Logging / Audit Trail |

Every resource rendered by this chart carries the label `iso42001: "true"` and
one label per clause and component, for example:

```bash
kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.5.1
```

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
