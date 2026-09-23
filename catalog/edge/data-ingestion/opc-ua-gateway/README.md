# OPC-UA Gateway: `edge-opc-ua-gateway`

> OPC UA to MQTT/Kafka bridge (Telegraf) that reads tags from PLC/SCADA endpoints and forwards them into the edge event bus.

[![Tier](https://img.shields.io/badge/tier-edge-065f46)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `edge`
- **Category**: `Data Ingestion`
- **Namespace**: `edge`
- **Reference architecture**: *Industrial Protocol Gateway* subcomponent, feeding `CMP-01` Input Data Monitoring
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.1.3.1`, `B.6.2.6.4`

This chart is the protocol adapter between the **device** level (PLCs, CNC controllers, SCADA servers exposing OPC UA) and the **edge** event bus. It runs [Telegraf](https://github.com/influxdata/telegraf) (MIT) with the `inputs.opcua` plugin and publishes every sample as JSON on MQTT (`<topicPrefix>/<machine_id>/opcua`) and, optionally, on Kafka. Each sample carries the tags `site_id`, `machine_id` and the OPC UA node id, which the downstream flows keep for data provenance.

Earlier versions of this chart used the open-source edition of EMQX Neuron. That edition ships no OPC UA driver (only Modbus, MQTT, eKuiper, file, REST and monitor plugins; OPC UA is part of the commercial NeuronEX), so the gateway could not read OPC UA endpoints; the configuration file it mounted was not in Neuron's format either. Telegraf provides an open-source OPC UA client and is configured entirely from `values.yaml`.

The gateway also exposes its own health on `:9273/metrics` (Telegraf `internal` metrics: samples gathered, read errors and write errors per output), scraped by the edge Prometheus Agent.

---

## Quick start

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install edge-opc-ua-gateway cigip-upv/edge-opc-ua-gateway -n edge -f my-plant.yaml
```

`my-plant.yaml` lists the OPC UA endpoints and nodes of the site:

```yaml
siteId: plant-a
opcua:
  endpoints:
    - name: press-01
      url: opc.tcp://plc-01.plant.local:4840
      machineId: press-01
      securityPolicy: Basic256Sha256
      securityMode: SignAndEncrypt
      authMethod: UserName
      existingSecret: plc-01-credentials     # keys: username, password
      nodes:
        - { name: temperature, namespace: "2", identifierType: s, identifier: Channel1.Device1.Temperature }
        - { name: vibration,   namespace: "2", identifierType: s, identifier: Channel1.Device1.Vibration }
```

The defaults target the OPC PLC simulator used in the laboratory validation (`mcr.microsoft.com/iotedge/opc-plc`, nodes `SpikeData`, `DipData`, `PositiveTrendData` and `NegativeTrendData`).

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml);
the Rancher questionnaire lives in [`questions.yaml`](./manifests/questions.yaml).

| Area | Variable | Default |
|------|----------|---------|
| Site | `siteId` | `edge-site-01` |
| Sampling | `opcua.interval`, `opcua.timestamp` | `1s`, `source` |
| Endpoints | `opcua.endpoints[]` | OPC PLC simulator, security `None` |
| MQTT | `downstream.mqtt.host`, `topicPrefix`, `username`, `existingSecret` | `edge-mosquitto`, `plant`, `gateway`, `edge-mosquitto-users` |
| Kafka | `downstream.kafka.enabled`, `brokers`, `topic` | `false`, `edge-kafka:9092`, `sensor-raw` |

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.1.3.1` | Resources: Access Control (authenticated MQTT publishing; OPC UA security policies and user authentication) |
| `B.6.2.6.4` | Operation: Retraining / Lifecycle (fresh plant data for the learning loop) |

```bash
kubectl get deploy,svc,pod -n edge -l mlops-iso42001.cigip-upv.es/chart=edge-opc-ua-gateway
```

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
