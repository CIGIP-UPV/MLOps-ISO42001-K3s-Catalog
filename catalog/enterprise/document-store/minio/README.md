# MinIO Docs Overlay — `enterprise-minio-overlay`

> Overlay buckets for ISO/IEC 42001 compliance documentation, model cards and audit evidence with object locking.

[\![Tier](https://img.shields.io/badge/tier-enterprise-92400e)](#) [\![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [\![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [MLOps ISO/IEC 42001 K3s Catalog](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog) — a companion resource
to the reference architecture described in *Mateo-Casali et al. (2025), Reference
Architecture for the Design and Implementation of AI Systems in Manufacturing
in Conformity to ISO/IEC 42001*.

---

## Overview

- **Tier**: `enterprise`
- **Category**: `Document Store`
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.2.3.1`, `B.6.2.6.5`

This chart packages **MinIO Docs Overlay** for the **enterprise** tier of the reference architecture, covering the *Document Store* capability block. It ships with production-ready defaults for K3s and a Rancher-compatible `questions.yaml`, so operators can deploy the component from the Rancher UI with guided prompts for every configuration variable.

---

## Quick start

```bash
# Add the Helm repository
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm repo update

# Install this chart
helm install minio-overlay cigip-upv/enterprise-minio-overlay \
  --namespace enterprise \
  --create-namespace
```

Alternatively, clone the repository and install from the manifests folder:

```bash
git clone https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog
cd MLOps-ISO42001-K3s-Catalog/catalog/enterprise/document-store/minio/manifests
helm dependency update .
helm install minio-overlay . -n enterprise --create-namespace
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml).
For a Rancher-driven deployment, the friendly questionnaire lives in
[`questions.yaml`](./manifests/questions.yaml); Rancher will render one form
field per declared question when the chart is installed from the catalog.

Override any value at install time:

```bash
helm install minio-overlay cigip-upv/enterprise-minio-overlay \
  --namespace enterprise --create-namespace \
  --set someKey=someValue
```

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.2.3.1` | Planning — System Documentation |
| `B.6.2.6.5` | Operation — Update & Repair Plan |

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#iso-42001-annex-b-coverage).

---

## Maintainer

- **CIGIP-UPV** — *https://cigip.webs.upv.es/* — `cigip@upv.es`

Released under the Apache 2.0 License.
