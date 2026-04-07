# Questionnaire 02 — Edge Tier Requirements

Complete this questionnaire to configure the Edge tier deployment. *(Prerequisite: complete Questionnaire 01 first.)*

---

## Section 1: Hardware Profile

**Q2.1. What hardware runs the edge K3S node?**

| Specification | Your Value |
|---------------|------------|
| CPU cores | |
| RAM (GB) | |
| Storage (GB, SSD preferred) | |
| OS | Ubuntu 22.04 / RHEL / Other: ___ |
| GPU | None / NVIDIA ___ / AMD ___ |

**Q2.2. How many edge nodes will be in the K3S cluster?**

- [ ] 1 node (single-node edge) — acceptable for non-HA deployments
- [ ] 2–3 nodes — K3S HA mode available (etcd embedded)
- [ ] > 3 nodes — K3S HA cluster with external datastore

---

## Section 2: Device Tier Connectivity

**Q2.3. What protocols do your machines/sensors use?** *(determines Node-RED node packages to install)*

| Protocol | Machine/Sensor Type | Node-RED Package |
|----------|--------------------|-|
| OPC-UA | | `node-red-contrib-opcua` |
| MQTT | | Built-in |
| Modbus TCP | | `node-red-contrib-modbus` |
| Siemens S7 | | `node-red-contrib-s7` |
| REST/HTTP | | Built-in |
| Serial/RS232 | | `node-red-node-serialport` |

**Q2.4. What is the sensor sampling frequency?**

- [ ] < 1 Hz (slow processes — temperature, pressure snapshots)
- [ ] 1–10 Hz (standard monitoring)
- [ ] 10–1000 Hz (vibration, acoustic — requires edge pre-aggregation)
- [ ] > 1000 Hz (high-speed quality inspection — GPU and local storage required)

---

## Section 3: Inference Requirements

**Q2.5. What is the required response time for AI predictions?**

- [ ] < 100 ms — requires model optimisation (ONNX Runtime, quantisation)
- [ ] 100–500 ms — standard CPU inference; FastAPI service sufficient
- [ ] 500 ms – 5 s — relaxed latency; edge or platform inference both viable
- [ ] > 5 s — cloud inference may be sufficient; reconsider edge deployment

**Q2.6. Should inference operate without platform connectivity?**

- [ ] **Yes** — edge must be fully autonomous; model pre-loaded locally; buffering mandatory
- [ ] No — edge inference acceptable to fail if platform unreachable (not recommended)

---

## Section 4: Edge Component Selection

Based on your answers, select the edge components to deploy:

| Component | Deploy? | Notes |
|-----------|---------|-------|
| Node-RED (data ingestion + orchestration) | Yes / No | Required for all edge deployments |
| Mosquitto (MQTT broker) | Yes / No | Required if using MQTT devices |
| Kafka (event streaming) | Yes / No | Optional; recommended if > 50 data sources |
| FastAPI Model Server | Yes / No | Required for edge inference |
| PostgreSQL (feature cache) | Yes / No | Required if Q2.6 = Yes or Q2.4 > 10 Hz |
| MongoDB (buffer) | Yes / No | Alternative to PostgreSQL for document-style buffering |
| Fluent Bit (log forwarding) | **Yes** | Always required — B.6.2.8.1 |
| Prometheus Agent | Yes / No | Required for B.6.1.2.2 |
| Falco (security) | **Yes** | Always required — B.6.2.6.7 |

---

## Section 5: Resource Allocation

Based on selected components, verify that total resource requests fit within edge hardware (Q2.1):

| Component | CPU Request | Memory Request |
|-----------|------------|----------------|
| Node-RED | 500m | 512Mi |
| FastAPI Model Server | 500m | 512Mi |
| PostgreSQL | 250m | 256Mi |
| Fluent Bit | 100m | 128Mi |
| Prometheus Agent | 100m | 128Mi |
| Falco | 100m | 256Mi |
| **Total** | **~1550m** | **~1792Mi** |

> Minimum recommended edge hardware: **4 CPU cores, 4 GB RAM**. Reduce to 2 GB RAM by disabling Kafka and MongoDB if not needed.

---

## Output Summary

Save this completed questionnaire to MinIO as `edge-deployment-config.md` *(supports B.6.2.5.1)*.

Proceed to:
- [Questionnaire 03 — Platform Requirements](./03-platform-requirements.md) (if deploying Platform tier)
- Individual solution questionnaires for each selected component
