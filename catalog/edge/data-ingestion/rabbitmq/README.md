# RabbitMQ: `edge-rabbitmq`

> Lightweight AMQP message broker for edge ingestion with store-and-forward buffering, management UI and Prometheus metrics.

[![Tier](https://img.shields.io/badge/tier-edge-065f46)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `edge`
- **Category**: `Data Ingestion`
- **Namespace**: `edge`
- **Reference architecture component**: `CMP-01` Input Data Monitoring
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.2.6.4`, `B.6.2.8.1`

This chart packages **RabbitMQ 3.13** (official image, pulled from its public ECR mirror `public.ecr.aws/docker/library/rabbitmq:3.13-management`) for the **edge** tier. Together with **Mosquitto (MQTT)** and **Kafka**, it completes the edge messaging stack: RabbitMQ provides reliable AMQP queuing and acts as a local **store-and-forward** buffer that absorbs messages when upstream connectivity to the platform is interrupted.

The chart is self-contained (no external chart dependencies). Broker credentials are read with `envFrom` from the Secret `edge-rabbitmq-auth` (keys `RABBITMQ_DEFAULT_USER`, `RABBITMQ_DEFAULT_PASS`, `RABBITMQ_ERLANG_COOKIE`), created by `infrastructure/install.sh`. Earlier versions referenced a Secret that no template created, so the pod could not start.

---

## Quick start

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm repo update

helm install edge-rabbitmq cigip-upv/edge-rabbitmq -n edge

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=edge-rabbitmq
```

Alternatively, install from the manifests folder of a clone of the repository:

```bash
helm install edge-rabbitmq catalog/edge/data-ingestion/rabbitmq/manifests -n edge
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml);
the Rancher questionnaire lives in [`questions.yaml`](./manifests/questions.yaml).

| Area | Variable | Default | Notes |
|------|----------|---------|-------|
| Broker | `config.amqpPort` | `5672` | AMQP listener |
| Management | `config.managementEnabled` / `config.managementPort` | `true` / `15672` | Web console and HTTP API |
| Metrics | `config.metricsEnabled` / `config.metricsPort` | `true` / `15692` | Prometheus endpoint, scraped by the edge Prometheus Agent |
| MQTT bridge | `config.mqttEnabled` | `false` | Use the Mosquitto chart for pure MQTT |
| Buffering | `config.diskFreeLimit` | `1GB` | Back-pressure threshold (store-and-forward) |
| Credentials | `auth.existingSecret` | `edge-rabbitmq-auth` | Created by `install.sh`; no password in the values |
| Storage | `persistence.size` | `2Gi` | PVC for `/var/lib/rabbitmq` |

---

## Role in the reference architecture

In the **FACTOR** use case (Chapter 7), the edge messaging layer is described as a
stack composed of *RabbitMQ, Mosquitto (MQTT) and Kafka* that enables decoupled,
high-frequency communication with sensors and the CNC controller, and acts as a
local buffer under the **store-and-forward** strategy when upstream connectivity
is lost. This chart provides the RabbitMQ component of that stack. The laboratory
ingestion flow of the catalog uses MQTT (gateway to Node-RED); RabbitMQ is
available for AMQP producers.

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.2.6.4` | Operation: Retraining / Lifecycle (data ingestion for the learning loop) |
| `B.6.2.8.1` | Operation: Logging / Audit Trail (broker logs and Prometheus metrics) |

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
