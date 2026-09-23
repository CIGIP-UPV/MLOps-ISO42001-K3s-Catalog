# MinIO Docs Overlay: `enterprise-minio-overlay`

> Document store buckets for ISO/IEC 42001 compliance documentation, model cards and audit evidence, with versioning and object locking.

[![Tier](https://img.shields.io/badge/tier-enterprise-92400e)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `enterprise`
- **Category**: `Document Store`
- **Namespace**: `minio`
- **Reference architecture component**: `CMP-05` Document Store (mandatory)
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.2.3.1`, `B.6.2.6.5`

The **Document Store** keeps the documentation that ISO/IEC 42001 requires for the AI system: system and architecture documentation, the deployment plan, the update and repair plan, risk assessments, model cards and audit evidence. It reuses the object storage of the platform (`platform-minio`) instead of running a second MinIO: this chart only provisions the enterprise buckets in it.

A Job, run on every install and upgrade, creates (idempotently):

| Bucket | Versioning | Object locking | Default retention | Content |
|--------|------------|----------------|-------------------|---------|
| `iso42001-docs` | yes | yes | governance, 365 days | `architecture/`, `deployment-plan/`, `update-repair-plan/`, `risk-assessment/`, `compliance-review/` |
| `model-cards` | yes | no | none | Model cards and evaluation reports |
| `audit-evidence` | yes | yes | governance, 1825 days | Exported logs, drift reports, sign-offs |

It also creates the read-only policy `iso42001-docs-read` for auditors. With object locking, a stored version cannot be deleted or overwritten until its retention expires (WORM); deleting an object only adds a delete marker and the protected version remains. Object locking can only be enabled when a bucket is created, so the Job reports `object_lock: unavailable` if a bucket already existed without it.

Earlier versions of this chart only rendered a ConfigMap with bucket definitions that nothing read, so the document store buckets were never created with the declared protection.

---

## Quick start

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install enterprise-minio-overlay cigip-upv/enterprise-minio-overlay -n minio

kubectl -n minio logs job/enterprise-minio-overlay-provision-1
```

Prerequisites: `platform-minio` in the `minio` namespace and its root credentials Secret `platform-minio-root`.

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml);
the Rancher questionnaire lives in [`questions.yaml`](./manifests/questions.yaml).
Buckets, folders and retention periods are declared in `buckets`; use the
`compliance` retention mode only when no one, not even the MinIO administrator,
may remove evidence before the retention ends.

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.2.3.1` | Planning: System Documentation (versioned, immutable documentation store) |
| `B.6.2.6.5` | Operation: Update & Repair Plan (plan kept under retention) |

```bash
kubectl get job,configmap,pod -n minio -l mlops-iso42001.cigip-upv.es/chart=enterprise-minio-overlay
```

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
