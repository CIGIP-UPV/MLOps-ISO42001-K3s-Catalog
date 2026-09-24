# Laboratory validation run: instructions

These instructions run the laboratory validation of the catalog (thesis,
chapter 7) on the K3s cluster of the laboratory: `kb2` (control plane, a
Hyper-V virtual machine), `worker1-kb2` (amd64 worker) and `edgenode01` (arm64
Jetson, the edge device).
One script, [`run-lab-validation.sh`](./run-lab-validation.sh), installs the
catalog and collects the evidence; the results are then committed and pushed
so that the analysis and the report can be completed.

## What the script does

| Phase | Content | Evidence (under `raw/<run-id>/`) |
|-------|---------|----------------------------------|
| 1 | Environment: OS, kernel, K3s, kubectl, Helm, Rancher and cert-manager versions; nodes (CPU, RAM); storage classes; existing namespaces and releases | `env/` |
| 2 | Control plane reserved (`--taint-control-plane`), NetworkPolicy controller enabled (`--enable-network-policy`), edge label on the edge nodes, API audit (`--enable-audit`), estimate of the CPU and memory the catalog requests versus what is free | `state/`, `env/resource-estimate.json` |
| 3 | `infrastructure/install.sh` in the recommended order, with the laboratory values in `lab-values/`; result, time and ready pods per chart | `install.log`, `install.jsonl`, `state/after-install-*` |
| 4 | Smoke test of every chart (S01 to S20) | `smoke/` |
| 5 | End-to-end test (E01 to E16): OPC UA simulator, gateway, ingestion, consolidation, training, MLflow, propagation to the edge, inference, metrics, induced drift, Evidently, retraining recommendation, new version at the edge, logs in Loki | `e2e/` |
| 6 | Traceability queries per ISO/IEC 42001 clause and component, label coverage per namespace | `trace/` |
| 7 | NetworkPolicy tests: a canary that checks that policies are enforced (N-CANARY), an Internet control (N00) and the default deny and allowed conduits (N01 to N12) | `netpol/` |

Every test writes one line to `results.jsonl` (PASS, FAIL, or SKIP when a
precondition is not met, with the reason) and `summary.md` lists them all.
The script never prints or saves the value of a Secret.

It takes about 60 to 90 minutes, most of it image downloads, the 5 minutes of
simulated plant data that the first training needs and the 5 minutes of
drifted data.

## The laboratory cluster and the options used

The diagnosis of the nodes (`raw/diag-*.txt`, made with
[`diagnose-cluster.sh`](./diagnose-cluster.sh)) showed what the run has to take
into account:

| Finding | Option or setting |
|---------|-------------------|
| `kb2` is a small virtual machine (4 vCPU, 8 GiB, 64 % memory in use) that runs the control plane and the Rancher agent | `--taint-control-plane kb2`: only the DaemonSets of the catalog (Falco, Fluent Bit, node-exporter) run on it |
| K3s runs with `disable-network-policy: true`: no NetworkPolicy is enforced | `--enable-network-policy`; the N-CANARY test checks that they are enforced, otherwise N01 to N12 are SKIP |
| `edgenode01` is the edge device; `worker1-kb2` hosts the platform and enterprise tiers | `--edge-nodes edgenode01` (the platform and enterprise pods are kept off it) |
| An Argo CD that is not the catalog's already runs in `argocd` | `--skip-chart platform-argocd`: nothing is installed or changed in `argocd`; S15 is SKIP |
| `edgenode01` is arm64 and the Bitnami MongoDB images are amd64 only | `--skip-chart edge-mongodb`; S18 is SKIP (MongoDB is not part of the end-to-end flow) |
| The kernel of `edgenode01` (5.15-tegra) has no BTF, which the Falco `modern_ebpf` driver needs | Falco runs on the amd64 nodes only (`lab-values/edge-falco.yaml`); S10 is SKIP because the model server runs on `edgenode01` |
| Another node-exporter already uses host port 9100 | the catalog's node-exporter listens on 9101 (`lab-values/platform-prometheus.yaml`) |
| No cert-manager in the cluster | the catalog installs its own |

## Changes the script makes in the cluster

- Namespaces of the catalog (`edge`, `logging`, `falco`, `platform`, `mlops`,
  `minio`, `monitoring`, `openbao`, `security`, `helpdesk`), their
  NetworkPolicies and the Secrets the charts read (random passwords generated
  once). The existing `monitoring` namespace is shared: it gets the label and
  the policies of the catalog; the releases already there are not modified.
  Namespaces whose charts are all skipped (`argocd` here) are not touched.
- The Helm releases of the catalog except the skipped ones (`platform-rancher`
  is skipped too: the cluster is managed by an external Rancher).
- The label `node-role.kubernetes.io/edge=true` on the edge nodes.
- With `--taint-control-plane kb2`: the taint
  `node-role.kubernetes.io/control-plane=true:NoSchedule` on `kb2`. Pods
  already running there are not moved. Undo with
  `kubectl taint nodes kb2 node-role.kubernetes.io/control-plane=true:NoSchedule-`.
- With `--enable-network-policy`: the line `disable-network-policy: true` is
  removed from `/etc/rancher/k3s/config.yaml` (a backup is kept next to it) and
  `k3s` is restarted. From then on every NetworkPolicy of the cluster is
  enforced, including those that the existing Argo CD already has in its
  namespace; namespaces without policies are not affected. Undo by restoring
  the backup and restarting `k3s`.
- cert-manager: if the cluster already runs one, only the platform internal CA
  is added; otherwise the catalog installs it.
- OpenBao is initialised with one unseal key; the laboratory unseal key and root
  token are kept in the Secret `openbao/openbao-lab-init` (never printed).
  Use `--no-openbao-init` to skip this.
- The OPC PLC simulator (`deployment/opc-plc` in `edge`) stays running after the
  test. Temporary test pods, the test Certificate, the Argo CD test
  Application and its namespace `argocd-smoke` are removed.
- With `--enable-audit` only: `/etc/rancher/k3s/audit-policy.yaml`, new
  `kube-apiserver-arg` entries in `/etc/rancher/k3s/config.yaml` (a backup is
  kept) and a restart of the `k3s` service. The API server is unavailable for
  a few seconds each time `k3s` restarts; running pods are not affected.

Nothing that exists before the run is deleted.

## Before you start

1. Push the branch `lab-validation` to GitHub.
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

On `kb2`, with the options of this laboratory (see the table above):

```bash
sudo -E ./docs/lab-validation/run-lab-validation.sh \
  --enable-audit --enable-network-policy \
  --taint-control-plane kb2 --edge-nodes edgenode01 \
  --skip-chart platform-argocd --skip-chart edge-mongodb
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
- **S15 (Argo CD) fails with a repository error** (only when `platform-argocd`
  is installed): the branch is not pushed or the repository is private; pass
  another public branch with `--branch`.
- **N-CANARY fails**: NetworkPolicies are not enforced on at least one node (the
  controller is still disabled, or that node cannot run it); the evidence says
  which node, and N01 to N12 are then SKIP.
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
