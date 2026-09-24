# Laboratory validation run: summary

| Phase | PASS | FAIL | SKIP |
|---|---|---|---|
| smoke | 18 | 0 | 3 |
| netpol | 0 | 1 | 13 |

| ID | Result | Name | Seconds | Evidence | Detail |
|---|---|---|---|---|---|
| S01 | PASS | MLflow tracking API | 2 | smoke/S01-mlflow.txt | experiments: ['zdm-drift-monitoring', 'zdm-anomaly-detection', 'Default'] |
| S02 | PASS | MinIO buckets, versioning and document store retention | 11 | smoke/S02-minio.txt | [2026-09-24 08:29:03 UTC]     0B mlflow-artifacts/ [2026-09-24 08:52:46 UTC]     0B model-cards/ Object locking 'GOVERNANCE' is configured f |
| S03 | PASS | Kafka produce and consume | 37 | smoke/S03-kafka.txt | predictions sensor-raw sensor-validated consumed lab-smoke-1790241698 |
| S04 | PASS | Mosquitto authenticated publish/subscribe, anonymous refused | 7 | smoke/S04-mosquitto.txt | received: hello (after 1 publish attempts) anonymous refused |
| S05 | PASS | RabbitMQ running and listeners | 8 | smoke/S05-rabbitmq.txt | Interface: [::], port: 15672, protocol: http, purpose: HTTP API Interface: [::], port: 15692, protocol: http/prometheus, purpose: Prometheus |
| S06 | PASS | Node-RED ingestion metrics and protected editor | 1 | smoke/S06-node-red.txt | ingest_values_written_total 9780 ingest_db_errors_total 5 ingest_last_sample_timestamp_seconds 1790241750 editor /admin/flows without creden |
| S07 | PASS | Prometheus scrape targets | 1 | smoke/S07-prometheus.txt | up         2  platform-prometheus-prometheus up         1  platform-timescaledb up 29 of 30 targets down: node-exporter http://<ip-edgenode01> |
| S08 | PASS | Grafana health, data sources and dashboards | 3 | smoke/S08-grafana.txt | data source timescaledb: {"message":"Database Connection OK","status":"OK"} data source edgepg: {"message":"Database Connection OK","status" |
| S09 | PASS | Loki write and query | 6 | smoke/S09-loki.txt | pushed read back: lab smoke line 1790241756000000000 |
| S10 | SKIP | Falco runtime event (shell in the model server) | 0 | smoke/S10-falco.txt | model server node: edgenode01 not run: no Falco pod on edgenode01 (the Falco driver cannot run there, see lab-values/edge-falco.yaml) |
| S11 | PASS | Keycloak realm ai-system | 1 | smoke/S11-keycloak.txt | issuer: http://127.0.0.1:18080/realms/ai-system |
| S12 | PASS | Zammad web and API | 1 | smoke/S12-zammad.txt | web: HTTP 200 {"setup_done":false,"import_mode":false,"import_backend":"","system_online_service":false} |
| S13 | PASS | OpenBao status over TLS (platform CA) | 1 | smoke/S13-openbao.txt | Cluster Name    vault-cluster-946f1225 Cluster ID      523286c1-1a1b-4be3-a030-a6a8bbe114e8 HA Enabled      false (bao status exit 0: 0 unse |
| S13b | PASS | OpenBao init, unseal, KV write/read, audit device | 1 | smoke/S13b-openbao-init.txt | Sealed          false Path     Type    Description ----     ----    ----------- file/    file    n/a |
| S14 | PASS | cert-manager test certificate from the platform CA | 3 | smoke/S14-cert-manager.txt | lab-smoke-cert   True    lab-smoke-cert   2s subject= issuer=CN = ZDM MLOps platform CA notAfter=Dec 23 09:22:48 2026 GMT |
| S15 | SKIP | Argo CD sync of a catalog chart from git (lab-validation) | 0 | smoke/S15-argocd.txt | not run: release platform-argocd is not installed in namespace argocd (skipped in this laboratory, see the run options) |
| S16 | PASS | TimescaleDB hypertables and roles | 1 | smoke/S16-timescaledb.txt | sensor_readings grafana ml sync |
| S17 | PASS | Edge PostgreSQL schema | 0 | smoke/S17-edge-postgresql.txt | operator_feedback predictions sensor_features system_events |
| S18 | SKIP | MongoDB edge buffer collections | 0 | smoke/S18-mongodb.txt | not run: release edge-mongodb is not installed in namespace edge (skipped in this laboratory, see the run options) |
| S19 | PASS | Platform PostgreSQL service databases | 0 | smoke/S19-platform-postgresql.txt | grafana keycloak mlflow zammad |
| S20 | PASS | Evidently UI API | 1 | smoke/S20-evidently.txt | {"application":"Evidently UI","version":"0.4.33","commit":"-"} |
| N-CANARY | FAIL | NetworkPolicies are enforced on every node (pod behind a deny-all policy) | 36 | netpol/N-CANARY.txt | edgenode01: client in lab-np-outside -> pod 10.42.2.53:8080 behind a deny-all ingress policy: CONNECTED kb2: client in lab-np-outside -> pod |
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
