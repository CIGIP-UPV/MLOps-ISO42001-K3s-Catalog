# Laboratory validation run: instructions

These instructions run the laboratory validation of the catalog (thesis,
chapter 7) on the K3s cluster of the laboratory (`kb2` and `worker1-kb2`).
One script, [`run-lab-validation.sh`](./run-lab-validation.sh), installs the
catalog and collects the evidence; the results are then committed and pushed
so that the analysis and the report can be completed.

## What the script does

| Phase | Content | Evidence (under `raw/<run-id>/`) |
|-------|---------|----------------------------------|
| 1 | Environment: OS, kernel, K3s, kubectl, Helm, Rancher and cert-manager versions; nodes (CPU, RAM); storage classes; existing namespaces and releases | `env/` |
| 2 | Edge label on the nodes (all nodes by default), optional API audit (`--enable-audit`), estimate of the CPU and memory the catalog requests versus what is free | `state/edge-label.txt`, `env/resource-estimate.json` |
| 3 | `infrastructure/install.sh` in the recommended order, with the laboratory values in `lab-values/`; result, time and ready pods per chart | `install.log`, `install.jsonl`, `state/after-install-*` |
| 4 | Smoke test of every chart (S01 to S20) | `smoke/` |
| 5 | End-to-end test (E01 to E16): OPC UA simulator, gateway, ingestion, consolidation, training, MLflow, propagation to the edge, inference, metrics, induced drift, Evidently, retraining recommendation, new version at the edge, logs in Loki | `e2e/` |
| 6 | Traceability queries per ISO/IEC 42001 clause and component, label coverage per namespace | `trace/` |
| 7 | NetworkPolicy tests (N00 control, N01 to N12): default deny and allowed conduits | `netpol/` |

Every test writes one line to `results.jsonl` (PASS, FAIL, or SKIP when a
precondition is not met, with the reason) and `summary.md` lists them all.
The script never prints or saves the value of a Secret.

It takes about 60 to 90 minutes, most of it image downloads, the 5 minutes of
simulated plant data that the first training needs and the 5 minutes of
drifted data.

## Changes the script makes in the cluster

- Namespaces of the catalog (`edge`, `logging`, `falco`, `platform`, `mlops`,
  `minio`, `monitoring`, `argocd`, `openbao`, `security`, `helpdesk`), their
  NetworkPolicies and the Secrets the charts read (random passwords generated
  once).
- The 29 Helm releases of the catalog (`platform-rancher` is skipped because a
  Rancher server is already running).
- The label `node-role.kubernetes.io/edge=true` on every node.
- In the existing `cert-manager` namespace: the platform internal CA (one
  Certificate with its Secret and two ClusterIssuers). The cert-manager
  installed with Rancher is not modified.
- OpenBao is initialised with one unseal key; the laboratory unseal key and root
  token are kept in the Secret `openbao/openbao-lab-init` (never printed).
  Use `--no-openbao-init` to skip this.
- The OPC PLC simulator (`deployment/opc-plc` in `edge`) stays running after the
  test. Temporary test pods, the test Certificate, the Argo CD test
  Application and its namespace `argocd-smoke` are removed.
- With `--enable-audit` only: `/etc/rancher/k3s/audit-policy.yaml`, new
  `kube-apiserver-arg` entries in `/etc/rancher/k3s/config.yaml` (a backup is
  kept) and a restart of the `k3s` service. The API server is unavailable for
  a few seconds; running pods are not affected.

Nothing that exists before the run is deleted.

## Before you start

1. Push the branch `lab-validation` to GitHub. The Argo CD smoke test (S15)
   syncs a chart of this repository from that branch, so the repository must
   be public and the branch pushed.
2. On `kb2`, make sure these commands are available:

   ```bash
   kubectl version --client && helm version --short
   python3 -c 'import yaml' || sudo apt-get install -y python3-yaml
   command -v openssl curl git
   ```

3. Clone or update the repository on `kb2` and check out the branch:

   ```bash
   git clone https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog.git
   cd MLOps-ISO42001-K3s-Catalog
   git checkout lab-validation && git pull
   ```

4. Point `kubectl` and `helm` at the cluster. As root on the K3s server:

   ```bash
   export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
   kubectl get nodes
   ```

   Both `kb2` and `worker1-kb2` must be `Ready`.

## Run

Recommended (includes the API audit log, which needs root):

```bash
sudo -E ./docs/lab-validation/run-lab-validation.sh --enable-audit
```

Without the audit change (no restart of k3s):

```bash
sudo -E ./docs/lab-validation/run-lab-validation.sh
```

`sudo -E` keeps `KUBECONFIG`. Leave it running; the progress is printed and
also written to `raw/<run-id>/run.log`.

### If the resource estimate does not fit

Before installing anything, the script compares the CPU and memory requests of
the catalog with what is free in the cluster. If they do not fit, it stops
without installing and writes `raw/<run-id>/env/resource-estimate.json` (with
the requests of every chart). Commit and push that run as it is, so the
decision can be taken with the numbers; or, if you prefer to go ahead, re-run
with `--force`.

### Re-running only the tests

After an installation, the tests can be repeated without installing again:

```bash
sudo -E ./docs/lab-validation/run-lab-validation.sh --phases "4 5 6 7"
```

Leave at least 15 minutes between two runs of phase 5: a retraining started
within the cooldown (15 minutes in `lab-values/`) blocks a new one by design,
and E13 and E14 are then recorded as `SKIP` with that reason. Every run keeps
its own evidence directory; commit them all.

## After the run: commit and push the evidence

```bash
git add docs/lab-validation/raw/
git commit -m "Add laboratory validation evidence"
git push
```

Before committing, the script checks the evidence for key material and prints
a warning if it finds any; do not commit if it does.

## Troubleshooting

- **Image pulls fail with `429 Too Many Requests`**: anonymous Docker Hub
  pulls are limited per IP. Official images are already pulled from the public
  ECR mirror, but Bitnami, Grafana, Loki, TimescaleDB, Node-RED and Evidently
  come from Docker Hub. Add Docker Hub credentials or a mirror to
  `/etc/rancher/k3s/registries.yaml` on both nodes, restart `k3s` /
  `k3s-agent`, and re-run the script (installed releases are upgraded in
  place).
- **S15 (Argo CD) fails with a repository error**: the branch is not pushed or
  the repository is private; pass another public branch with `--branch`.
- **A chart failed during the installation**: the run continues with the next
  chart; the reason is in `install.jsonl` and `state/*-warning-events.txt`.

## Undoing the installation (only if needed)

The run does not remove anything. To remove the catalog later:

```bash
for r in $(helm list -A -o json | python3 -c 'import json,sys;[print(x["namespace"]+"/"+x["name"]) for x in json.load(sys.stdin) if x["name"].startswith(("edge-","platform-","enterprise-"))]'); do
  helm uninstall -n "${r%%/*}" "${r##*/}"
done
kubectl delete -f infrastructure/01-network-policies.yaml
kubectl delete -f docs/lab-validation/manifests/opc-plc-simulator.yaml
```

The namespaces, their PersistentVolumeClaims (data) and the Secrets are kept by
these commands; deleting them removes the data of the catalog.
