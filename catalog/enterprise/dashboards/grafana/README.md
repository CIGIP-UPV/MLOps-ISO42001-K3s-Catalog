# Grafana Dashboards (Overlay) — `enterprise-grafana-dashboards`

> Pre-built dashboards for OEE, model health, security events and operator feedback.

[\![Tier](https://img.shields.io/badge/tier-enterprise-92400e)](#) [\![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [\![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `enterprise`
- **Category**: `Dashboards`
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.1.3.3`, `B.6.2.6.2`

This chart packages **Grafana Dashboards (Overlay)** for the **enterprise** tier of the reference architecture, covering the *Dashboards* capability block. It ships with production-ready defaults for K3s and a Rancher-compatible `questions.yaml`, so operators can deploy the component from the Rancher UI with guided prompts for every configuration variable.

---

## Quick start

```bash
# Add the Helm repository
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm repo update

# Install this chart
helm install grafana-dashboards cigip-upv/enterprise-grafana-dashboards \
  --namespace enterprise \
  --create-namespace
```

Alternatively, clone the repository and install from the manifests folder:

```bash
git clone https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog
cd MLOps-ISO42001-K3s-Catalog/catalog/enterprise/dashboards/grafana/manifests
helm dependency update .
helm install grafana-dashboards . -n enterprise --create-namespace
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml).
For a Rancher-driven deployment, the friendly questionnaire lives in
[`questions.yaml`](./manifests/questions.yaml); Rancher will render one form
field per declared question when the chart is installed from the catalog.

Override any value at install time:

```bash
helm install grafana-dashboards cigip-upv/enterprise-grafana-dashboards \
  --namespace enterprise --create-namespace \
  --set someKey=someValue
```

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.1.3.3` | Resources — Human Oversight / Feedback |
| `B.6.2.6.2` | Operation — Model Performance |

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#iso-42001-annex-b-coverage).

---

## Maintainer

- **CIGIP-UPV** — *https://cigip.webs.upv.es/* — `cigip@upv.es`

Released under the Apache 2.0 License.
