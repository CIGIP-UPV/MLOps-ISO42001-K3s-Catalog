# Laboratory validation run: summary

| Phase | PASS | FAIL | SKIP |
|---|---|---|---|
| installation | 3 | 0 | 0 |
| traceability | 35 | 0 | 0 |
| smoke | 1 | 0 | 0 |
| e2e | 4 | 1 | 0 |
| netpol | 5 | 1 | 0 |

| ID | Result | Name | Seconds | Evidence | Detail |
|---|---|---|---|---|---|
| INST-00 | PASS | install.sh, all phases | 89 | state/install-summary.txt | [19:53:16] INFO  === Done. Run log: /root/MLOps-ISO42001-K3s-Catalog/docs/lab-validation/raw/lab-20260924T195147/install.jsonl ===   ok      |
| INST-01 | PASS | platform-timescaledb | 9 | install.jsonl | pods ready 1/1 |
| INST-02 | PASS | edge-postgresql-sync | 1 | install.jsonl | pods ready 0/11 |
| T-B.6.1.2.2 | PASS | B.6.1.2.2 Resources: Monitoring Performance | 0 | trace/traceability.tsv | 20 resources |
| T-B.6.1.3.1 | PASS | B.6.1.3.1 Resources: Access Control | 0 | trace/traceability.tsv | 14 resources |
| T-B.6.1.3.2 | PASS | B.6.1.3.2 Resources: Version Control | 0 | trace/traceability.tsv | 6 resources |
| T-B.6.1.3.3 | PASS | B.6.1.3.3 Resources: Human Oversight / Feedback | 0 | trace/traceability.tsv | 11 resources |
| T-B.6.1.3.4 | PASS | B.6.1.3.4 Resources: Inventory / Registry | 0 | trace/traceability.tsv | 8 resources |
| T-B.6.1.4.1 | PASS | B.6.1.4.1 Resources: Security of AI Assets | 0 | trace/traceability.tsv | 14 resources |
| T-B.6.2.3.1 | PASS | B.6.2.3.1 Planning: System Documentation | 0 | trace/traceability.tsv | 14 resources |
| T-B.6.2.5.1 | PASS | B.6.2.5.1 Planning: Deployment Plan | 0 | trace/traceability.tsv | 4 resources |
| T-B.6.2.6.1 | PASS | B.6.2.6.1 Operation: Infrastructure Monitoring | 0 | trace/traceability.tsv | 27 resources |
| T-B.6.2.6.2 | PASS | B.6.2.6.2 Operation: Model Performance | 0 | trace/traceability.tsv | 29 resources |
| T-B.6.2.6.3 | PASS | B.6.2.6.3 Operation: KPI Assessment (OEE) | 0 | trace/traceability.tsv | 10 resources |
| T-B.6.2.6.4 | PASS | B.6.2.6.4 Operation: Retraining / Lifecycle | 0 | trace/traceability.tsv | 32 resources |
| T-B.6.2.6.5 | PASS | B.6.2.6.5 Operation: Update & Repair Plan | 0 | trace/traceability.tsv | 1 resources |
| T-B.6.2.6.6 | PASS | B.6.2.6.6 Operation: Incident Communication | 0 | trace/traceability.tsv | 14 resources |
| T-B.6.2.6.7 | PASS | B.6.2.6.7 Operation: Security Monitoring | 0 | trace/traceability.tsv | 6 resources |
| T-B.6.2.8.1 | PASS | B.6.2.8.1 Operation: Logging / Audit Trail | 0 | trace/traceability.tsv | 52 resources |
| T-B.8.0.2.1 | PASS | B.8.0.2.1 Continual Improvement: Roles | 0 | trace/traceability.tsv | 10 resources |
| T-B.8.0.4.1 | PASS | B.8.0.4.1 Continual Improvement: Helpdesk | 0 | trace/traceability.tsv | 14 resources |
| T-B.8.0.5.1 | PASS | B.8.0.5.1 Continual Improvement: Alerts | 0 | trace/traceability.tsv | 37 resources |
| T-CMP-01 | PASS | CMP-01 Input Data Monitoring | 0 | trace/traceability.tsv | 17 resources |
| T-CMP-02 | PASS | CMP-02 Data Stock | 0 | trace/traceability.tsv | 33 resources |
| T-CMP-03 | PASS | CMP-03 Version Control | 0 | trace/traceability.tsv | 6 resources |
| T-CMP-04 | PASS | CMP-04 Model | 0 | trace/traceability.tsv | 6 resources |
| T-CMP-05 | PASS | CMP-05 Document Store | 0 | trace/traceability.tsv | 5 resources |
| T-CMP-06 | PASS | CMP-06 Information Centre | 0 | trace/traceability.tsv | 3 resources |
| T-CMP-07 | PASS | CMP-07 User Access & Oversight | 0 | trace/traceability.tsv | 10 resources |
| T-CMP-08 | PASS | CMP-08 Infrastructure Technical Monitoring | 0 | trace/traceability.tsv | 20 resources |
| T-CMP-09 | PASS | CMP-09 Logger | 0 | trace/traceability.tsv | 9 resources |
| T-CMP-10 | PASS | CMP-10 Model Technical Performance Monitoring | 0 | trace/traceability.tsv | 32 resources |
| T-CMP-11 | PASS | CMP-11 Goal-Oriented Monitoring | 0 | trace/traceability.tsv | 24 resources |
| T-CMP-12 | PASS | CMP-12 Feedback Interface | 0 | trace/traceability.tsv | 3 resources |
| T-CMP-13 | PASS | CMP-13 AI Helpdesk | 0 | trace/traceability.tsv | 14 resources |
| T-CMP-14 | PASS | CMP-14 Retraining Recommendation | 0 | trace/traceability.tsv | 9 resources |
| T-CMP-15 | PASS | CMP-15 Security Monitoring | 0 | trace/traceability.tsv | 20 resources |
| T-iso42001=true | PASS | iso42001=true all catalog resources | 0 | trace/traceability.tsv | 143 resources |
| S21 | PASS | Feedback interface health, sign-in and denied access without credentials | 5 | cmp12/S21-feedback.txt | sign-in of a user without a role of the interface (data-scientist): 403 (expected 403) sign-in of lab-operator (operator): 200 (expected 200 |
| E17 | PASS | Operator verdict on a real prediction, stored in the platform data stock | 13 | cmp12/E17-verdict.txt | 9-24 19:53:39.995321+00:00", "site_id": "lab-edge-01", "source_id": 4, "machine_id": "cnc-01", "model_name": "zdm-anomaly-detector", "model_ |
| E18 | PASS | Verdict in the Grafana panel of disagreement rate by model version | 2 | cmp12/E18-dashboard.txt | dashboard: ZDM: Operator Feedback (CMP-12); panel: Operator disagreement rate by model version model_version / incorrect / correct / uncerta |
| E19 | FAIL | Training uses the operator verdicts as labels | 901 | cmp12/E19-training.txt |     obj, end = self.raw_decode(s, idx=_w(s, 0).end())   File "/usr/lib/python3.10/json/decoder.py", line 355, in raw_decode     raise JSONDe |
| E20 | PASS | Suspension of the version in service stops it at the edge; resuming restores it | 54 | cmp12/E20-suspension.txt | {"ts": "2026-09-24T20:09:42Z", "component": "edge-mlflow-sync", "event": "version_resumed", "model_name": "zdm-anomaly-detector", "model_ver |
| E21 | PASS | Events of the feedback loop in Loki | 26 | cmp12/E21-loki.txt | version_resumed: 1 log lines feedback_labels_loaded: 1 log lines schema_applied: 3 log lines event types found in Loki: 9/9 |
| N-CANARY | FAIL | NetworkPolicies are enforced on every node (pod behind a deny-all policy) | 48 | netpol/N-CANARY.txt | edgenode01: pod 10.42.2.27:8080 from another namespace: without policy CONNECTED, with a deny-all ingress policy CONNECTED kb2: pod 10.42.0. |
| N14 | PASS | feedback -> platform TimescaleDB (feedback conduit) (expected: allow) | 0 | netpol/N14.txt | CONNECTED |
| N15 | PASS | feedback -> edge PostgreSQL (no conduit into the edge) (expected: deny) | 0 | netpol/N15.txt | destination on edgenode01, which does not enforce NetworkPolicies (N-CANARY); BLOCKED |
| N16 | PASS | feedback -> platform service PostgreSQL (same namespace as TimescaleDB, not allowed) (expected: deny) | 0 | netpol/N16.txt | BLOCKED |
| N17 | PASS | feedback -> Keycloak (sign-in conduit) (expected: allow) | 0 | netpol/N17.txt | CONNECTED |
| N18 | PASS | feedback -> MLflow (suspension tags) (expected: allow) | 0 | netpol/N18.txt | CONNECTED |
