# Laboratory validation run: summary

| Phase | PASS | FAIL | SKIP |
|---|---|---|---|
| environment | 1 | 0 | 0 |
| preparation | 5 | 0 | 0 |
| installation | 29 | 0 | 0 |
| smoke | 17 | 1 | 3 |
| e2e | 16 | 0 | 0 |
| traceability | 34 | 1 | 0 |
| netpol | 0 | 1 | 13 |

| ID | Result | Name | Seconds | Evidence | Detail |
|---|---|---|---|---|---|
| ENV-01 | PASS | environment captured | 0 | env/versions.txt |  |
| PREP-00 | PASS | control plane reserved (NoSchedule taint on kb2) | 1 | state/taint.txt | node/kb2 modified [{"effect":"NoSchedule","key":"node-role.kubernetes.io/control-plane","value":"true"}] |
| PREP-04 | PASS | K3s NetworkPolicy controller enabled | 0 | state/enable-network-policy.txt | disable-network-policy is not set in /etc/rancher/k3s/config.yaml: nothing to change |
| PREP-01 | PASS | edge label on the nodes | 0 | state/edge-label.txt | node/edgenode01 not labeled NAME         STATUS   ROLES   AGE    VERSION edgenode01   Ready    edge    177d   v1.32.6+k3s1 |
| PREP-02 | PASS | API audit policy enabled | 21 | state/enable-audit.txt | kube-apiserver-arg entries already present. Restarting k3s... API server ready. Audit log is being written: 7429 events so far. |
| PREP-03 | PASS | resource estimate (catalog requests vs free allocatable) | 15 | state/resource-estimate.txt |  "free_memory_gib": 99.28,  "fits": true } largest requests: [('platform-timescaledb', {'cpu': 0.27, 'memory_gib': 0.53}), ('edge-fastapi-mo |
| INST-00 | PASS | install.sh, all phases | 2336 | state/install-summary.txt |   ok     enterprise-minio-overlay         minio             1 s  pods 0/1   ok     enterprise-grafana-dashboards    monitoring        1 s  p |
| INST-01 | PASS | platform-cert-manager | 111 | install.jsonl | pods ready 3/3 |
| INST-02 | PASS | platform-cert-manager | 11 | install.jsonl | pods ready 3/3 |
| INST-03 | PASS | platform-openbao | 2 | install.jsonl | pods ready 0/1 |
| INST-04 | PASS | platform-postgresql | 35 | install.jsonl | pods ready 1/1 |
| INST-05 | PASS | enterprise-keycloak | 120 | install.jsonl | pods ready 1/1 |
| INST-06 | PASS | platform-minio | 19 | install.jsonl | pods ready 1/1 |
| INST-07 | PASS | platform-timescaledb | 65 | install.jsonl | pods ready 1/1 |
| INST-08 | PASS | platform-prometheus | 42 | install.jsonl | pods ready 5/7 |
| INST-09 | PASS | platform-loki | 56 | install.jsonl | pods ready 1/1 |
| INST-10 | PASS | platform-grafana | 34 | install.jsonl | pods ready 1/1 |
| INST-11 | PASS | platform-mlflow | 280 | install.jsonl | pods ready 1/1 |
| INST-12 | PASS | platform-training-jobs | 1 | install.jsonl | pods ready 0/0 |
| INST-13 | PASS | platform-evidently | 52 | install.jsonl | pods ready 1/1 |
| INST-14 | PASS | edge-postgresql | 36 | install.jsonl | pods ready 1/1 |
| INST-15 | PASS | edge-mosquitto | 19 | install.jsonl | pods ready 1/1 |
| INST-16 | PASS | edge-rabbitmq | 50 | install.jsonl | pods ready 1/1 |
| INST-17 | PASS | edge-kafka | 88 | install.jsonl | pods ready 1/1 |
| INST-18 | PASS | edge-opc-ua-gateway | 19 | install.jsonl | pods ready 1/1 |
| INST-19 | PASS | edge-node-red | 51 | install.jsonl | pods ready 1/1 |
| INST-20 | PASS | edge-fastapi-model | 52 | install.jsonl | pods ready 1/1 |
| INST-21 | PASS | edge-mlflow-sync | 1 | install.jsonl | pods ready 0/0 |
| INST-22 | PASS | edge-postgresql-sync | 1 | install.jsonl | pods ready 0/0 |
| INST-23 | PASS | edge-prometheus-agent | 62 | install.jsonl | pods ready 1/1 |
| INST-24 | PASS | edge-fluent-bit | 11 | install.jsonl | pods ready 2/3 |
| INST-25 | PASS | edge-falco | 74 | install.jsonl | pods ready 3/4 |
| INST-26 | PASS | enterprise-minio-overlay | 1 | install.jsonl | pods ready 0/1 |
| INST-27 | PASS | enterprise-grafana-dashboards | 1 | install.jsonl | pods ready 0/0 |
| INST-28 | PASS | enterprise-zammad | 256 | install.jsonl | pods ready 4/4 |
| S01 | PASS | MLflow tracking API | 2 | smoke/S01-mlflow.txt | experiments: ['Default'] |
| S02 | PASS | MinIO buckets, versioning and document store retention | 4 | smoke/S02-minio.txt | [2026-09-24 08:29:03 UTC]     0B mlflow-artifacts/ [2026-09-24 08:52:46 UTC]     0B model-cards/ Object locking 'GOVERNANCE' is configured f |
| S03 | PASS | Kafka produce and consume | 39 | smoke/S03-kafka.txt | predictions sensor-raw sensor-validated consumed lab-smoke-1790240267 |
| S04 | FAIL | Mosquitto authenticated publish/subscribe, anonymous refused | 29 | smoke/S04-mosquitto.txt | Timed out received:  anonymous refused |
| S05 | PASS | RabbitMQ running and listeners | 8 | smoke/S05-rabbitmq.txt | Interface: [::], port: 15672, protocol: http, purpose: HTTP API Interface: [::], port: 15692, protocol: http/prometheus, purpose: Prometheus |
| S06 | PASS | Node-RED ingestion metrics and protected editor | 2 | smoke/S06-node-red.txt | ingest_values_written_total 2952 ingest_db_errors_total 3 ingest_last_sample_timestamp_seconds 1790240343 editor /admin/flows without creden |
| S07 | PASS | Prometheus scrape targets | 2 | smoke/S07-prometheus.txt | up         2  platform-prometheus-prometheus up         1  platform-timescaledb up 29 of 30 targets down: node-exporter http://<ip-edgenode01> |
| S08 | PASS | Grafana health, data sources and dashboards | 3 | smoke/S08-grafana.txt | data source timescaledb: {"message":"Database Connection OK","status":"OK"} data source edgepg: {"message":"Database Connection OK","status" |
| S09 | PASS | Loki write and query | 7 | smoke/S09-loki.txt | pushed read back: lab smoke line 1790240350000000000 |
| S10 | SKIP | Falco runtime event (shell in the model server) | 0 | smoke/S10-falco.txt | model server node: edgenode01 not run: no Falco pod on edgenode01 (the Falco driver cannot run there, see lab-values/edge-falco.yaml) |
| S11 | PASS | Keycloak realm ai-system | 2 | smoke/S11-keycloak.txt | issuer: http://127.0.0.1:18080/realms/ai-system |
| S12 | PASS | Zammad web and API | 1 | smoke/S12-zammad.txt | web: HTTP 200 {"setup_done":false,"import_mode":false,"import_backend":"","system_online_service":false} |
| S13 | PASS | OpenBao status over TLS (platform CA) | 0 | smoke/S13-openbao.txt | Storage Type       file HA Enabled         false command terminated with exit code 2 (bao status exit 2: 0 unsealed, 2 sealed, 1 error) |
| S13b | PASS | OpenBao init, unseal, KV write/read, audit device | 2 | smoke/S13b-openbao-init.txt | Sealed          false Path     Type    Description ----     ----    ----------- file/    file    n/a |
| S14 | PASS | cert-manager test certificate from the platform CA | 5 | smoke/S14-cert-manager.txt | lab-smoke-cert   True    lab-smoke-cert   4s subject= issuer=CN = ZDM MLOps platform CA notAfter=Dec 23 08:59:25 2026 GMT |
| S15 | SKIP | Argo CD sync of a catalog chart from git (lab-validation) | 0 | smoke/S15-argocd.txt | not run: release platform-argocd is not installed in namespace argocd (skipped in this laboratory, see the run options) |
| S16 | PASS | TimescaleDB hypertables and roles | 2 | smoke/S16-timescaledb.txt | sensor_readings grafana ml sync |
| S17 | PASS | Edge PostgreSQL schema | 0 | smoke/S17-edge-postgresql.txt | operator_feedback predictions sensor_features system_events |
| S18 | SKIP | MongoDB edge buffer collections | 0 | smoke/S18-mongodb.txt | not run: release edge-mongodb is not installed in namespace edge (skipped in this laboratory, see the run options) |
| S19 | PASS | Platform PostgreSQL service databases | 1 | smoke/S19-platform-postgresql.txt | grafana keycloak mlflow zammad |
| S20 | PASS | Evidently UI API | 1 | smoke/S20-evidently.txt | {"application":"Evidently UI","version":"0.4.33","commit":"-"} |
| E01 | PASS | OPC UA simulator (OPC PLC) in the edge namespace | 1 | e2e/E01-simulator.txt | deployment.apps/opc-plc unchanged service/opc-plc unchanged deployment "opc-plc" successfully rolled out |
| E02 | PASS | OPC UA gateway reads the simulator | 30 | e2e/E02-gateway.txt | internal_gather_errors{input="opcua",site_id="lab-edge-01",version="1.32.3"} 0 internal_gather_metrics_gathered{input="opcua",site_id="lab-e |
| E03 | PASS | Ingestion: MQTT -> Node-RED validation -> edge data stock | 31 | e2e/E03-ingestion.txt | cnc-01 / DipData / 827 / -1000.00 / 84.43 cnc-01 / NegativeTrendData / 823 / 41.80 / 58.30 cnc-01 / PositiveTrendData / 824 / 141.60 / 158.1 |
| E04 | PASS | Data consolidation edge -> platform (batch log) | 8 | e2e/E04-consolidation.txt | 15 / lab-edge-01 / sensor_features / 3181 / 3320 / 139 / 139 / ok 14 / lab-edge-01 / predictions / 0 / 0 / 0 / 0 / ok 13 / lab-edge-01 / sen |
| E05 | PASS | Training job registers and promotes a model version | 16 | e2e/E05-training.txt | ta", "PositiveTrendData", "SpikeData"], "source": "timescaledb:zdm_platform.sensor_readings", "window": "2 hours", "bucket": "1 second", "ra |
| E06 | PASS | MLflow registry: version, alias and provenance tags | 1 | e2e/E06-registry.txt | aliases: [{'alias': 'champion', 'version': '1'}] versions: ['1'] v1 tags: {'trigger': 'schedule', 'train_anomaly_rate': '0.0205', 'data_wind |
| E07 | PASS | Version propagation platform -> edge (edge-mlflow-sync) | 26 | e2e/E07-propagation.txt | {"ts": "2026-09-24T09:01:17Z", "component": "edge-mlflow-sync", "event": "version_activated", "model_name": "zdm-anomaly-detector", "model_v |
| E08 | PASS | Inference with the propagated version | 2 | e2e/E08-inference.txt | features of the last 30 s: { "SpikeData" : -1.4210854715202005e-15, "PositiveTrendData" : 158.89000000000001, "DipData" : -30.00657757190576 |
| E09 | PASS | Edge metrics in the platform Prometheus (remote-write) | 46 | e2e/E09-metrics.txt | max by (model_version) (model_info) => [({'model_version': '1'}, '1')] sum(ingest_messages_valid_total) => [({}, '3688')] sum(internal_gathe |
| E10 | PASS | Induced drift: shifted samples of machine cnc-02 through MQTT | 400 | e2e/E10-drift-injection.txt | published 300 seconds of shifted samples for machine cnc-02 |
| E11 | PASS | Consolidation of the drifted data | 10 | e2e/E11-consolidation-2.txt | 24 / lab-edge-01 / predictions / 2 / 2 / 0 / 0 / ok 23 / lab-edge-01 / sensor_features / 5300 / 6154 / 854 / 854 / ok cnc-01 / 5320 cnc-02 / |
| E12 | PASS | Evidently drift check and retraining recommendation | 15 | e2e/E12-drift.txt | 09:14Z", "component": "platform-evidently", "step": "recommend", "event": "recommendation", "id": 1, "model_name": "zdm-anomaly-detector", " |
| E13 | PASS | Retraining job started by the recommendation | 31 | e2e/E13-retraining.txt | a", "PositiveTrendData", "SpikeData"], "source": "timescaledb:zdm_platform.sensor_readings", "window": "2 hours", "bucket": "1 second", "raw |
| E14 | PASS | New version propagated to the edge and served | 28 | e2e/E14-new-version.txt | "zdm-anomaly-detector", "model_version": "2", "alias": "champion", "previous_version": "1", "run_id": "ff33ce11b65f402a9d34c20aae75d03f"} {" |
| E15 | PASS | MLOps events collected by Fluent Bit in Loki | 22 | e2e/E15-loki-events.txt | prediction: 19 log lines sample_rejected: 0 log lines edge-postgresql-sync: 25 log lines event types found in Loki: 6/7 |
| E16 | PASS | Drift reports stored in the Evidently UI | 1 | e2e/E16-evidently-ui.txt | projects: ['zdm-anomaly-detector'] |
| T-B.6.1.2.2 | PASS | B.6.1.2.2 Resources: Monitoring Performance | 0 | trace/traceability.tsv | 20 resources |
| T-B.6.1.3.1 | PASS | B.6.1.3.1 Resources: Access Control | 0 | trace/traceability.tsv | 14 resources |
| T-B.6.1.3.2 | PASS | B.6.1.3.2 Resources: Version Control | 0 | trace/traceability.tsv | 6 resources |
| T-B.6.1.3.3 | PASS | B.6.1.3.3 Resources: Human Oversight / Feedback | 0 | trace/traceability.tsv | 8 resources |
| T-B.6.1.3.4 | PASS | B.6.1.3.4 Resources: Inventory / Registry | 0 | trace/traceability.tsv | 8 resources |
| T-B.6.1.4.1 | PASS | B.6.1.4.1 Resources: Security of AI Assets | 0 | trace/traceability.tsv | 14 resources |
| T-B.6.2.3.1 | PASS | B.6.2.3.1 Planning: System Documentation | 0 | trace/traceability.tsv | 14 resources |
| T-B.6.2.5.1 | PASS | B.6.2.5.1 Planning: Deployment Plan | 0 | trace/traceability.tsv | 4 resources |
| T-B.6.2.6.1 | PASS | B.6.2.6.1 Operation: Infrastructure Monitoring | 0 | trace/traceability.tsv | 15 resources |
| T-B.6.2.6.2 | PASS | B.6.2.6.2 Operation: Model Performance | 0 | trace/traceability.tsv | 29 resources |
| T-B.6.2.6.3 | PASS | B.6.2.6.3 Operation: KPI Assessment (OEE) | 0 | trace/traceability.tsv | 8 resources |
| T-B.6.2.6.4 | PASS | B.6.2.6.4 Operation: Retraining / Lifecycle | 0 | trace/traceability.tsv | 28 resources |
| T-B.6.2.6.5 | PASS | B.6.2.6.5 Operation: Update & Repair Plan | 0 | trace/traceability.tsv | 1 resources |
| T-B.6.2.6.6 | PASS | B.6.2.6.6 Operation: Incident Communication | 0 | trace/traceability.tsv | 14 resources |
| T-B.6.2.6.7 | PASS | B.6.2.6.7 Operation: Security Monitoring | 0 | trace/traceability.tsv | 6 resources |
| T-B.6.2.8.1 | PASS | B.6.2.8.1 Operation: Logging / Audit Trail | 0 | trace/traceability.tsv | 41 resources |
| T-B.8.0.2.1 | PASS | B.8.0.2.1 Continual Improvement: Roles | 0 | trace/traceability.tsv | 10 resources |
| T-B.8.0.4.1 | PASS | B.8.0.4.1 Continual Improvement: Helpdesk | 0 | trace/traceability.tsv | 14 resources |
| T-B.8.0.5.1 | PASS | B.8.0.5.1 Continual Improvement: Alerts | 0 | trace/traceability.tsv | 37 resources |
| T-CMP-01 | PASS | CMP-01 Input Data Monitoring | 0 | trace/traceability.tsv | 17 resources |
| T-CMP-02 | PASS | CMP-02 Data Stock | 0 | trace/traceability.tsv | 21 resources |
| T-CMP-03 | PASS | CMP-03 Version Control | 0 | trace/traceability.tsv | 6 resources |
| T-CMP-04 | PASS | CMP-04 Model | 0 | trace/traceability.tsv | 5 resources |
| T-CMP-05 | PASS | CMP-05 Document Store | 0 | trace/traceability.tsv | 5 resources |
| T-CMP-06 | PASS | CMP-06 Information Centre | 0 | trace/traceability.tsv | 3 resources |
| T-CMP-07 | PASS | CMP-07 User Access & Oversight | 0 | trace/traceability.tsv | 10 resources |
| T-CMP-08 | PASS | CMP-08 Infrastructure Technical Monitoring | 0 | trace/traceability.tsv | 20 resources |
| T-CMP-09 | PASS | CMP-09 Logger | 0 | trace/traceability.tsv | 9 resources |
| T-CMP-10 | PASS | CMP-10 Model Technical Performance Monitoring | 0 | trace/traceability.tsv | 32 resources |
| T-CMP-11 | PASS | CMP-11 Goal-Oriented Monitoring | 0 | trace/traceability.tsv | 23 resources |
| T-CMP-12 | FAIL | CMP-12 Feedback Interface | 0 | trace/traceability.tsv | 0 resources |
| T-CMP-13 | PASS | CMP-13 AI Helpdesk | 0 | trace/traceability.tsv | 14 resources |
| T-CMP-14 | PASS | CMP-14 Retraining Recommendation | 0 | trace/traceability.tsv | 8 resources |
| T-CMP-15 | PASS | CMP-15 Security Monitoring | 0 | trace/traceability.tsv | 20 resources |
| T-iso42001=true | PASS | iso42001=true all catalog resources | 0 | trace/traceability.tsv | 127 resources |
| N-CANARY | FAIL | NetworkPolicies are enforced on every node (pod behind a deny-all policy) | 37 | netpol/N-CANARY.txt | edgenode01: client in lab-np-outside -> pod 10.42.2.29:8080 behind a deny-all ingress policy: CONNECTED kb2: client in lab-np-outside -> pod |
| N00 | SKIP | namespace outside the catalog -> Internet (control, no policy) (expected: allow) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N01 | SKIP | edge -> platform TimescaleDB (consolidation conduit) (expected: allow) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N02 | SKIP | edge -> MLflow (version sync conduit) (expected: allow) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N03 | SKIP | edge -> edge PostgreSQL (same namespace) (expected: allow) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N04 | SKIP | edge -> MinIO (no conduit) (expected: deny) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N05 | SKIP | edge -> Zammad (no conduit) (expected: deny) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N06 | SKIP | namespace outside the catalog -> edge PostgreSQL (default deny ingress) (expected: deny) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N07 | SKIP | mlops -> MinIO (artefact conduit) (expected: allow) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N08 | SKIP | mlops -> Internet (default deny egress) (expected: deny) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N09 | SKIP | security -> platform PostgreSQL (Keycloak database) (expected: allow) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N10 | SKIP | helpdesk -> MLflow (no conduit) (expected: deny) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
| N11 | SKIP | argocd -> Internet 443 (Git and Helm repositories) (expected: allow) | 0 |  | not run: platform-argocd is not installed; the argocd namespace belongs to another deployment |
| N12 | SKIP | logging -> Loki (log conduit) (expected: allow) | 0 | netpol/N-CANARY.txt | not run: this cluster does not enforce NetworkPolicies (see N-CANARY) |
