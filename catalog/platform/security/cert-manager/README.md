# cert-manager: `platform-cert-manager`

> Automated X.509 certificate provisioning and renewal (ACME, self-signed, OpenBao PKI) for every ingress endpoint in the reference architecture.

[![Tier](https://img.shields.io/badge/tier-platform-1e40af)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `platform`
- **Category**: `Security`
- **Namespace**: `cert-manager`
- **Reference architecture components**: `CMP-15` Security Monitoring
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.1.4.1`, `B.6.2.3.1`

This chart packages **cert-manager** for the **platform** tier of the reference architecture, covering the *Security* capability block. It ships with defaults for K3s and a Rancher-compatible `questions.yaml`, so operators can deploy the component from the Rancher UI with guided prompts.

---

## Quick start

```bash
# Add the Helm repository
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm repo update

# Install this chart
helm install platform-cert-manager cigip-upv/platform-cert-manager \
  --namespace cert-manager \
  --create-namespace
```

Alternatively, clone the repository and install from the manifests folder:

```bash
git clone https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog
cd MLOps-ISO42001-K3s-Catalog/catalog/platform/security/cert-manager/manifests
helm dependency build .
helm install platform-cert-manager . -n cert-manager --create-namespace
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
| `B.6.1.4.1` | Resources: Security of AI Assets |
| `B.6.2.3.1` | Planning: System Documentation |

Every resource rendered by this chart carries the label `iso42001: "true"` and
one label per clause and component, for example:

```bash
kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.4.1
```

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
