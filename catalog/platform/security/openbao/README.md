# OpenBao — `platform-openbao`

> Centralised secrets manager with KV, PKI and database engines; provides dynamic credentials and encryption keys to every tier via External Secrets. Open-source (MPL 2.0) Vault-compatible alternative.

[\![Tier](https://img.shields.io/badge/tier-platform-1e40af)](#) [\![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [\![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `platform`
- **Category**: `Security`
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.1.3.3`, `B.6.1.4.1`, `B.8.0.2.1`

This chart packages **OpenBao** for the **platform** tier of the catalog, covering the *Security* capability block. OpenBao is the Linux Foundation Edge community fork of HashiCorp Vault under MPL 2.0; its API and CLI are drop-in compatible with Vault, so existing integrations (cert-manager, External Secrets Operator, Agent Injector) work unchanged. The chart ships with production-ready defaults for K3s and a Rancher-compatible `questions.yaml`, so operators can deploy the component from the Rancher UI with guided prompts for every configuration variable.

---

## Quick start

```bash
# Add the Helm repository
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm repo update

# Install this chart
helm install openbao cigip-upv/platform-openbao \
  --namespace platform \
  --create-namespace
```

Alternatively, clone the repository and install from the manifests folder:

```bash
git clone https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog
cd MLOps-ISO42001-K3s-Catalog/catalog/platform/security/openbao/manifests
helm dependency update .
helm install openbao . -n platform --create-namespace
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml).
For a Rancher-driven deployment, the friendly questionnaire lives in
[`questions.yaml`](./manifests/questions.yaml); Rancher will render one form
field per declared question when the chart is installed from the catalog.

Override any value at install time:

```bash
helm install openbao cigip-upv/platform-openbao \
  --namespace platform --create-namespace \
  --set someKey=someValue
```

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.1.3.3` | Resources — Human Oversight / Feedback |
| `B.6.1.4.1` | ISO/IEC 42001 Annex B requirement |
| `B.8.0.2.1` | Continual Improvement — Roles |

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#iso-42001-annex-b-coverage).

---

## Maintainer

- **CIGIP-UPV** — *https://cigip.webs.upv.es/* — `cigip@upv.es`

Released under the Apache 2.0 License.
