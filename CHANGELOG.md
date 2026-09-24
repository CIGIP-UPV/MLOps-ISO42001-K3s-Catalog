# Changelog

All notable changes to this catalog are documented here. Versions follow
[Semantic Versioning](https://semver.org/); every release is archived on
Zenodo under the concept DOI
[10.5281/zenodo.19882677](https://doi.org/10.5281/zenodo.19882677).

## [Unreleased]

Closes the last component of the reference architecture without a chart,
CMP-12 Feedback Interface. The catalog has 31 charts.

### Added

- `enterprise-feedback-interface` (namespace `feedback`): operators review the
  predictions consolidated in the platform and record a verdict (correct,
  incorrect or uncertain, with an optional corrected label and comment);
  supervisors can suspend and resume the model version in service. Sign-in
  against the `ai-system` realm of Keycloak (new client `feedback-interface`),
  signed session cookie with CSRF protection, JSON events and Prometheus
  metrics; unit tests in `tests/`.
- Schema Jobs in `platform-timescaledb` and `edge-postgresql`: an idempotent
  schema is applied after every install and upgrade, so existing
  installations receive new tables, columns, roles and grants without
  restarting the database.
- Operator Feedback dashboard (disagreement rate by model version).
- Laboratory phase 8 of `run-lab-validation.sh` and its option `--only-chart`.

### Changed

- `edge-fastapi-model` records the input features of every prediction, and
  `edge-postgresql-sync` consolidates them (column `predictions.features`).
- `platform-training-jobs` uses the latest operator verdict of each
  prediction as a label: it measures the agreement of the candidate with the
  operators and, with `releaseCriteria.feedback`, can block its release.
- `edge-mlflow-sync` propagates the `suspended` tag of the served version;
  `edge-fastapi-model` answers 503 while it is suspended.
- `install.sh` adds the keys a new version needs to Secrets that already
  exist, keeping their values.

### Fixed

- The Keycloak realm import listed `openid` as a default client scope of the
  Grafana client; that scope does not exist, and every upgrade of
  `enterprise-keycloak` failed in its import Job.
- `edge-mlflow-sync` runs are serialised with a lock on the model store: a
  run started by hand during a scheduled run downloaded the same version into
  the same directory and one of them failed.

## [2.0.0] - 2026-09-24

Validated release: the catalog was installed and tested end to end on a
three-node K3s laboratory cluster with an NVIDIA Jetson as the edge device.
The report and the evidence are in `docs/lab-validation/`.

### Breaking changes

- `infrastructure/install.sh` is rewritten: it installs the catalog's own
  charts (not third-party charts) in phases (`base`, `security`, `data`,
  `edge`, `enterprise`), in the namespaces of `infrastructure/00-namespaces.yaml`,
  and generates the Secrets the charts read. Its options changed; see
  `install.sh --help`.
- Every chart moves to version 0.3.0. Credentials are read from Secrets
  (`existingSecret`), never from values; several values keys, image
  repositories and the variable names of the `questions.yaml` files changed.
- `platform-timescaledb` no longer uses the deprecated `timescaledb-single`
  chart: it ships its own StatefulSet. Data of a 1.x installation must be
  migrated.
- `edge-opc-ua-gateway` uses Telegraf instead of Neuron, whose open-source
  edition has no OPC UA driver.
- Every catalog namespace denies all traffic by default; only the conduits in
  `infrastructure/01-network-policies.yaml` are allowed.

### Added

- `edge-postgresql-sync`: consolidation of the edge data stock into the
  platform data stock, in logged, idempotent batches.
- `edge-mlflow-sync`: propagation of the promoted model version from MLflow to
  the edge model server (Version Control at the edge).
- Traceability labels on every rendered object (`iso42001=true` plus one label
  per ISO/IEC 42001 clause and per architecture component), generated from
  `CHART_META` and applied by `infrastructure/iso42001-postrender.py`.
- `infrastructure/verify_charts.py`: lint, render, kubeconform, label,
  questionnaire and values checks for every chart.
- API audit policy (`infrastructure/audit-policy.yaml`) and
  `infrastructure/enable-audit.sh`; NetworkPolicies for every catalog
  namespace and, apart, for namespaces shared with Rancher.
- `install.sh` options `--separate-tiers` (keeps platform and enterprise pods
  off the edge nodes), `--values-dir`, `--use-existing-cert-manager`, `--log`
  and `--dry-run`; namespaces whose charts are all skipped are left alone.
- The GitHub Pages workflow builds and publishes the chart packages with their
  dependencies.
- Laboratory validation (`docs/lab-validation/`): report, structured results,
  runner, node diagnosis, laboratory values and raw evidence.

### Changed

- Working model lifecycle: training job with release criteria, drift check
  with Evidently that records a retraining recommendation and starts the
  retraining, and a FastAPI model server that serves the propagated version.
- Node-RED ships a declarative input data validation flow (CMP-01).
- The document store applies object lock and versioning (CMP-05); Loki stores
  its data in MinIO.
- Grafana dashboards are importable and the Prometheus alert rules use metrics
  the catalog exposes.
- Keycloak runs 25.0.6 and exposes its metrics on the management port.
- Docker official images are pulled from the public ECR mirror; Bitnami images
  from `bitnamilegacy`.

### Fixed

- Charts that did not install or run: images no longer published, missing
  Secrets, ignored values keys, missing templates (cert-manager issuers,
  OpenBao TLS, Argo CD bootstrap), Falco rules that did not compile, the
  Mosquitto message size limit and password file, Node-RED file permissions,
  the Rancher Kubernetes version constraint and the Zammad 10.x layout.
- `publish.py` packages the wrapper charts with their subcharts, so the
  published packages exist and install.
- `install.sh` registers the repositories of the chart dependencies before
  building them.

### Security

- The NetworkPolicies of the Bitnami subcharts are disabled: they allowed
  ingress from every namespace and cancelled the default deny.
- The Kubernetes API rule of the NetworkPolicies opens port 6443 only; it
  also opened 443 to any address.

### Known limitations

- CMP-12 (Feedback Interface) has no chart.
- `edge-mongodb` uses Bitnami images published for amd64 only.
- On the laboratory edge device (NVIDIA JetPack kernel) Falco cannot run (no
  BTF) and NetworkPolicies are not enforced (no `hash:ip` ipset type).
- `platform-argocd` and `platform-rancher` were not deployed in the
  laboratory validation.

## [1.0.1] - 2026-06-03 and [1.0.0] - 2026-04-29

First public versions; see the corresponding GitHub releases and Zenodo
records.

[2.0.0]: https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog/compare/v1.0.1...v2.0.0
