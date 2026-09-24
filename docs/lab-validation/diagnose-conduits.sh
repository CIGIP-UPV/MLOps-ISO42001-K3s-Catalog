#!/usr/bin/env bash
# =============================================================================
# diagnose-conduits.sh: checks, node by node, the conduits that the edge
# namespace uses (consolidation, version sync, metrics, logs), from a pod of
# the edge namespace pinned to each node and, as a control, from a namespace
# without policies. Also saves the logs of the last failed consolidation and
# version sync runs.
#
# Run it on the K3s server, with kubectl pointing at the cluster:
#   sudo -E ./docs/lab-validation/diagnose-conduits.sh
# Only temporary pods (label lab-validation=test) and a temporary namespace
# are created; they are removed at the end.
#
# Output: docs/lab-validation/raw/diag-conduits-<timestamp>.txt
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${ROOT}/docs/lab-validation/raw/diag-conduits-$(date +%Y%m%dT%H%M%S).txt"
mkdir -p "$(dirname "${OUT}")"
[[ -z "${KUBECONFIG:-}" && -r /etc/rancher/k3s/k3s.yaml ]] && export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
IMAGE="public.ecr.aws/docker/library/busybox:1.36"
TARGETS="platform-timescaledb.platform.svc.cluster.local:5432 platform-mlflow.mlops.svc.cluster.local:5000 platform-prometheus-prometheus.monitoring.svc.cluster.local:9090 platform-loki.monitoring.svc.cluster.local:3100 edge-postgresql.edge.svc.cluster.local:5432"

probe() {
  # probe NAMESPACE NODE: one pod on NODE that tries every target
  local ns=$1 node=$2 name cmd="" t
  name="diag-conduits-$(printf '%s' "$node" | tr -c 'a-z0-9-' '-' | cut -c1-30 | sed 's/-*$//')"
  for t in ${TARGETS}; do
    cmd="${cmd} if nc -z -w 5 ${t%:*} ${t##*:}; then echo '${t} CONNECTED'; else echo '${t} BLOCKED'; fi;"
  done
  kubectl -n "$ns" delete pod "$name" --ignore-not-found --wait=true >/dev/null 2>&1
  kubectl -n "$ns" run "$name" --image="${IMAGE}" --restart=Never --labels=lab-validation=test \
    --overrides="{\"spec\": {\"nodeName\": \"${node}\"}}" --command -- sh -c "sleep 15; ${cmd}" >/dev/null \
    || { echo "  ${ns} on ${node}: could not create the test pod"; return; }
  local i=0 phase=""
  while [[ $i -lt 60 ]]; do
    phase=$(kubectl -n "$ns" get pod "$name" -o jsonpath='{.status.phase}' 2>/dev/null)
    [[ "$phase" == Succeeded || "$phase" == Failed ]] && break
    sleep 3; i=$((i + 1))
  done
  kubectl -n "$ns" logs "$name" 2>&1 | sed "s/^/  ${ns} on ${node}: /"
  kubectl -n "$ns" delete pod "$name" --wait=false >/dev/null 2>&1
}

last_logs() {
  # last_logs NAMESPACE PREFIX STATUS: logs of the last two pods of a CronJob with that status
  local p
  for p in $(kubectl -n "$1" get pods --sort-by=.metadata.creationTimestamp --no-headers 2>/dev/null \
             | awk -v pre="$2" -v st="$3" 'index($1, pre) == 1 && $3 == st {print $1}' | tail -2); do
    echo "--- ${1}/${p} (node $(kubectl -n "$1" get pod "$p" -o jsonpath='{.spec.nodeName}'))"
    kubectl -n "$1" logs "$p" --tail 15 2>&1 | cut -c1-400
  done
}

{
  echo "## date"; date -u
  echo; echo "## nodes"; kubectl get nodes -o wide
  kubectl create namespace lab-np-outside --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  echo; echo "## conduits from the edge namespace (policies apply) and from a namespace without policies (control)"
  for node in $(kubectl get nodes -o jsonpath='{.items[*].metadata.name}'); do
    probe edge "$node"
    probe lab-np-outside "$node"
  done
  kubectl delete namespace lab-np-outside --wait=false >/dev/null 2>&1
  echo; echo "## consolidation (edge-postgresql-sync): recent runs"
  kubectl -n edge get pods --sort-by=.metadata.creationTimestamp -o wide --no-headers 2>/dev/null | awk '$1 ~ /^edge-postgresql-sync-/' | tail -8
  last_logs edge edge-postgresql-sync- Error
  last_logs edge edge-postgresql-sync- Completed
  echo; echo "## version sync (edge-mlflow-sync): recent runs"
  kubectl -n edge get pods --sort-by=.metadata.creationTimestamp -o wide --no-headers 2>/dev/null | awk '$1 ~ /^edge-mlflow-sync-/' | tail -4
  last_logs edge edge-mlflow-sync- Error
  last_logs edge edge-mlflow-sync- Completed
  echo; echo "## remote-write of the edge Prometheus agent (last errors)"
  kubectl -n edge logs deploy/edge-prometheus-agent-server -c prometheus-server --tail 200 2>/dev/null | grep -iE 'error|failed' | tail -3 | cut -c1-300
} 2>&1 | tee "${OUT}"

echo
echo "Saved to ${OUT}"
