# RabbitMQ — `edge-rabbitmq`

> Lightweight AMQP message broker for edge ingestion with store-and-forward buffering, management UI and Prometheus metrics.

[![Tier](https://img.shields.io/badge/tier-edge-065f46)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `edge`
- **Category**: `Data Ingestion`
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.2.6.4`, `B.6.2.8.1`

This chart packages **RabbitMQ** for the **edge** tier of the reference architecture, covering the *Data Ingestion* capability block. Together with **Mosquitto (MQTT)** and **Kafka**, it completes the edge messaging stack of the reference architecture: RabbitMQ provides reliable AMQP queuing and acts as a local **store-and-forward** buffer that absorbs messages when upstream connectivity to the platform tier is interrupted.

It ships with production-ready defaults for K3s and a Rancher-compatible `questions.yaml`, so operators can deploy the component from the Rancher UI with guided prompts for every configuration variable. The chart is self-contained (no external chart dependencies), so it installs directly from the catalog without a prior `helm dependency build`.

---

## Quick start

```bash
# Add the Helm repository
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm repo update

# Install this chart
helm install rabbitmq cigip-upv/edge-rabbitmq \
  --namespace edge \
  --create-namespace \
  --set auth.password='<strong-password>'
```

Alternatively, clone the repository and install from the manifests folder:

```bash
git clone https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog
cd MLOps-ISO42001-K3s-Catalog/catalog/edge/data-ingestion/rabbitmq/manifests
helm install rabbitmq . -n edge --create-namespace \
  --set auth.password='<strong-password>'
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml).
For a Rancher-driven deployment, the friendly questionnaire lives in
[`questions.yaml`](./manifests/questions.yaml); Rancher will render one form
field per declared question when the chart is installed from the catalog.

Key options:

| Area | Variable | Default | Notes |
|------|----------|---------|-------|
| Broker | `config.amqpPort` | `5672` | AMQP listener |
| Management | `config.managementEnabled` / `config.managementPort` | `true` / `15672` | Web console + HTTP API |
| Metrics | `config.metricsEnabled` / `config.metricsPort` | `true` / `15692` | Prometheus endpoint |
| MQTT bridge | `config.mqttEnabled` | `false` | Use the Mosquitto chart for pure MQTT |
| Buffering | `config.diskFreeLimit` | `1GB` | Back-pressure threshold (store-and-forward) |
| Credentials | `auth.username` / `auth.password` | `edge` / — | Rendered into a Secret; set a strong password |
| Storage | `persistence.size` | `2Gi` | PVC for `/var/lib/rabbitmq` |

Override any value at install time:

```bash
helm install rabbitmq cigip-upv/edge-rabbitmq \
  --namespace edge --create-namespace \
  --set config.mqttEnabled=true
```

---

## Role in the reference architecture

In the **FACTOR** use case (Chapter 7), the edge messaging layer is described as a
stack composed of *RabbitMQ, Mosquitto (MQTT) and Kafka* that enables decoupled,
high-frequency communication with sensors and the CNC controller, and acts as a
local buffer under the **store-and-forward** strategy when upstream connectivity
is lost. This chart provides the RabbitMQ component of that stack.

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.2.6.4` | Operation — Retraining / Lifecycle (data ingestion for the learning loop) |
| `B.6.2.8.1` | Operation — Event Logs (broker logs and Prometheus metrics) |

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#iso-42001-annex-b-coverage).

---

## Maintainer

- **CIGIP-UPV** — *https://cigip.webs.upv.es/* — `cigip@upv.es`

Released under the Apache 2.0 License.
