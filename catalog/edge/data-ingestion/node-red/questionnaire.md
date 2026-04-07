# Deployment Questionnaire — Node-RED (Edge)

Answer these questions before deploying Node-RED at the edge. Your answers determine the recommended configuration.

---

## Section 1: Device Connectivity

**Q1. What industrial protocols do your machines use?**

- [ ] OPC-UA (install `node-red-contrib-opcua`)
- [ ] MQTT (built-in)
- [ ] Modbus TCP/RTU (install `node-red-contrib-modbus`)
- [ ] REST/HTTP (built-in)
- [ ] Siemens S7 (install `node-red-contrib-s7`)
- [ ] Other: ___________

**Q2. How many concurrent data sources (machines/sensors) will Node-RED handle?**

- [ ] < 10 — standard deployment, 1 replica
- [ ] 10–50 — consider increasing CPU limits; 1 replica sufficient
- [ ] > 50 — consider horizontal scaling or multiple Node-RED instances

---

## Section 2: Data Quality & Input Monitoring

**Q3. What types of data quality issues do you expect from sensors?** *(ISO/IEC 42001: B.6.2.6.4, B.6.2.6.7)*

- [ ] Missing values / null readings
- [ ] Out-of-range values (e.g., impossible temperature readings)
- [ ] Schema violations (unexpected fields or types)
- [ ] Signal noise / high-frequency spikes
- [ ] None anticipated

> **If any box is checked**: configure validation nodes in Node-RED flows before forwarding data to the inference endpoint. See the `Input Data Monitoring` flow template in `manifests/`.

**Q4. Should Node-RED drop or quarantine invalid data?**

- [ ] Drop silently (log only)
- [ ] Quarantine to a separate storage topic for review
- [ ] Halt ingestion and raise an alert

---

## Section 3: Buffering & Connectivity

**Q5. Is the edge-to-platform connection reliable?**

- [ ] Yes, stable LAN/WAN — minimal buffering needed
- [ ] Intermittent (e.g., cellular, VPN) — **enable local buffering (PostgreSQL/MongoDB)**
- [ ] Mostly offline, batch sync — **enable persistent queue; configure sync jobs**

**Q6. What is the maximum acceptable data loss window during connectivity outage?**

- [ ] < 1 minute — requires in-memory queue only
- [ ] 1–60 minutes — configure Node-RED file-based queue or PostgreSQL sink
- [ ] > 60 minutes — configure MongoDB persistent buffer with TTL index

---

## Section 4: Downstream Routing

**Q7. Where does Node-RED forward normalised data?** *(select all that apply)*

- [ ] Kafka topic (recommended for decoupling)
- [ ] FastAPI inference endpoint (direct HTTP call)
- [ ] PostgreSQL (local feature store)
- [ ] MQTT broker for re-publishing
- [ ] Platform-tier endpoint via HTTP/REST

---

## Section 5: Security

**Q8. Will Node-RED's admin UI be accessible from outside the edge node?**

- [ ] No — internal only; skip external authentication
- [ ] Yes — **enable basic authentication at minimum; consider reverse proxy with TLS**

> ISO/IEC 42001 B.6.1.3.1 requires that access to system controls be restricted. The Node-RED admin UI constitutes a control surface.

**Q9. Should flows be version-controlled?**

- [ ] Yes — export flows to Git (integrate with MLflow or GitLab via Node-RED's Projects feature)
- [ ] No — manual backup sufficient for this deployment

---

## Recommended Configuration Summary

Based on your answers, fill in the following before applying `manifests/values.yaml`:

```yaml
# values.yaml — Node-RED (Edge)
persistence:
  enabled: true          # Required if Q5 answer is intermittent or offline
  size: 2Gi              # Adjust based on Q6 answer

auth:
  enabled: true          # Required if Q8 answer is "Yes"

resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "1000m"         # Increase if Q2 > 50 sources
    memory: "1Gi"
```
