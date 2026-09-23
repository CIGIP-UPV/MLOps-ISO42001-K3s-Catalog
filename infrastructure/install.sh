#!/usr/bin/env bash
# =============================================================================
# MLOps ISO/IEC 42001 K3s Catalog: installer
#
# Installs the charts of this catalog, in the recommended order, on a K3s
# cluster:
#
#   base        namespaces, NetworkPolicies, Prometheus Operator CRDs and the
#               Secrets every chart reads (generated once, never printed)
#   security    security and governance: platform-cert-manager,
#               platform-openbao, platform-postgresql (metadata store that
#               Keycloak needs), enterprise-keycloak, platform-argocd
#   data        data and model: MinIO, TimescaleDB, monitoring (Prometheus,
#               Loki, Grafana), MLflow, training jobs, Evidently
#   edge        edge data stock, brokers, OPC UA gateway, Node-RED, model
#               server, version sync, data consolidation, agents, Falco
#   enterprise  document store, dashboards, Zammad
#
# Every release is installed with helm upgrade --install --wait and the
# iso42001 post-renderer (traceability labels on every object). One JSON line
# per chart (result, time, ready pods) is appended to the run log.
#
# Usage:
#   ./install.sh [options] [phase ...]        (default: all phases)
#
# Options:
#   --source local|repo     charts from catalog/ (default) or the Helm repo
#   --only CHART            install only these charts (repeatable)
#   --skip CHART            skip these charts (repeatable)
#   --timeout DURATION      helm --timeout per chart (default 15m)
#   --use-existing-cert-manager
#                           the cluster already runs cert-manager (for
#                           example with Rancher): only create the platform CA
#   --with-rancher          also install platform-rancher (never when a
#                           Rancher server is already present)
#   --site-id ID            edge site identifier (default edge-site-01)
#   --values-dir DIR        extra values: DIR/<chart>.yaml is passed with -f
#   --log FILE              run log (default ./install-<timestamp>.jsonl)
#   --dry-run               print the plan; change nothing
#   -h, --help
#
# Prerequisites: kubectl and helm pointing at the cluster, python3 with
# PyYAML (post-renderer), openssl, and at least one node labelled
# ${EDGE_NODE_LABEL:-node-role.kubernetes.io/edge=true} for the edge phase.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INFRA="${ROOT}/infrastructure"
POSTRENDER="${INFRA}/iso42001-postrender.py"
EDGE_NODE_LABEL="${EDGE_NODE_LABEL:-node-role.kubernetes.io/edge=true}"
REPO_ALIAS="cigip-upv"
REPO_URL="https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog"

SOURCE="local"
TIMEOUT="15m"
SITE_ID="edge-site-01"
DRY_RUN=false
USE_EXISTING_CM=false
WITH_RANCHER=false
VALUES_DIR=""
ONLY=()
SKIP=()
PHASES=()
RUN_LOG="${PWD}/install-$(date +%Y%m%dT%H%M%S).jsonl"

log()  { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
info() { log "INFO  $*"; }
warn() { log "WARN  $*"; }
die()  { log "ERROR $*" >&2; exit 1; }

# -----------------------------------------------------------------------------
# Catalog: chart -> namespace (mirrors CHART_META in publish.py)
# -----------------------------------------------------------------------------
ns_of() {
  case "$1" in
    platform-cert-manager) echo cert-manager ;;
    platform-openbao) echo openbao ;;
    platform-postgresql|platform-timescaledb) echo platform ;;
    enterprise-keycloak) echo security ;;
    platform-argocd) echo argocd ;;
    platform-minio|enterprise-minio-overlay) echo minio ;;
    platform-prometheus|platform-loki|platform-grafana|enterprise-grafana-dashboards) echo monitoring ;;
    platform-mlflow|platform-training-jobs|platform-evidently) echo mlops ;;
    platform-rancher) echo cattle-system ;;
    edge-fluent-bit) echo logging ;;
    edge-falco) echo falco ;;
    enterprise-zammad) echo helpdesk ;;
    edge-*) echo edge ;;
    *) die "unknown chart $1" ;;
  esac
}
# Read through indirect expansion in run_phase.
# shellcheck disable=SC2034
PHASE_security=(platform-cert-manager platform-openbao platform-postgresql enterprise-keycloak platform-argocd)
# shellcheck disable=SC2034
PHASE_data=(platform-minio platform-timescaledb platform-prometheus platform-loki platform-grafana
            platform-mlflow platform-training-jobs platform-evidently)
# shellcheck disable=SC2034
PHASE_edge=(edge-postgresql edge-mongodb edge-mosquitto edge-rabbitmq edge-kafka edge-opc-ua-gateway
            edge-node-red edge-fastapi-model edge-mlflow-sync edge-postgresql-sync
            edge-prometheus-agent edge-fluent-bit edge-falco)
# shellcheck disable=SC2034
PHASE_enterprise=(enterprise-minio-overlay enterprise-grafana-dashboards enterprise-zammad)
ALL_PHASES=(security data edge enterprise)

chart_dir() {
  # catalog/<tier>/<category>/<name>/manifests of a chart (local source)
  local name=$1
  grep -l "^name: ${name}$" "${ROOT}"/catalog/*/*/*/manifests/Chart.yaml | head -1 | xargs dirname
}

# -----------------------------------------------------------------------------
# Arguments
# -----------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source) SOURCE="$2"; shift 2 ;;
    --only) ONLY+=("$2"); shift 2 ;;
    --skip) SKIP+=("$2"); shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --site-id) SITE_ID="$2"; shift 2 ;;
    --log) RUN_LOG="$2"; shift 2 ;;
    --values-dir) VALUES_DIR="$(cd "$2" && pwd)"; shift 2 ;;
    --use-existing-cert-manager) USE_EXISTING_CM=true; shift ;;
    --with-rancher) WITH_RANCHER=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) sed -n '2,50p' "$0"; exit 0 ;;
    base|security|data|edge|enterprise) PHASES+=("$1"); shift ;;
    --all) shift ;;
    *) die "unknown argument: $1 (see --help)" ;;
  esac
done
if [[ ${#PHASES[@]} -eq 0 ]]; then PHASES=(base "${ALL_PHASES[@]}"); fi
[[ "${SOURCE}" == local || "${SOURCE}" == repo ]] || die "--source must be local or repo"

selected() {
  local c=$1 x
  if [[ ${#SKIP[@]} -gt 0 ]]; then
    for x in "${SKIP[@]}"; do [[ "$x" == "$c" ]] && return 1; done
  fi
  [[ ${#ONLY[@]} -eq 0 ]] && return 0
  for x in "${ONLY[@]}"; do [[ "$x" == "$c" ]] && return 0; done
  return 1
}

# -----------------------------------------------------------------------------
# Preflight
# -----------------------------------------------------------------------------
HAS_RANCHER=false
HAS_FOREIGN_CM=false
preflight() {
  for t in kubectl helm python3 openssl; do command -v "$t" >/dev/null || die "$t not found"; done
  python3 -c 'import yaml' 2>/dev/null || die "python3 needs PyYAML (pip install pyyaml) for the post-renderer"
  kubectl version >/dev/null 2>&1 || die "kubectl cannot reach the cluster"
  info "Cluster: $(kubectl version -o json | python3 -c 'import json,sys;print(json.load(sys.stdin)["serverVersion"]["gitVersion"])'), helm $(helm version --short)"

  if kubectl -n cattle-system get deploy rancher >/dev/null 2>&1; then
    HAS_RANCHER=true
    info "Rancher server detected in cattle-system: platform-rancher will not be installed."
  fi
  if kubectl get crd certificates.cert-manager.io >/dev/null 2>&1 \
     && ! helm -n cert-manager status platform-cert-manager >/dev/null 2>&1; then
    HAS_FOREIGN_CM=true
    if ${USE_EXISTING_CM}; then
      info "cert-manager already installed: platform-cert-manager will only create the platform CA."
    elif printf '%s\n' "${PHASES[@]}" | grep -qx security && selected platform-cert-manager; then
      die "cert-manager is already installed (not by this catalog). Re-run with --use-existing-cert-manager to only add the platform CA, or --skip platform-cert-manager."
    fi
  fi
  if printf '%s\n' "${PHASES[@]}" | grep -qx edge; then
    local n
    n=$(kubectl get nodes -l "${EDGE_NODE_LABEL}" --no-headers 2>/dev/null | wc -l | tr -d ' ')
    [[ "$n" -ge 1 ]] || die "no node labelled ${EDGE_NODE_LABEL}; label the edge node(s) first: kubectl label node <node> ${EDGE_NODE_LABEL}"
    info "Edge nodes (${EDGE_NODE_LABEL}): ${n}"
  fi
  if [[ "${SOURCE}" == repo ]]; then
    helm repo add "${REPO_ALIAS}" "${REPO_URL}" --force-update >/dev/null
    helm repo update "${REPO_ALIAS}" >/dev/null
  fi
}

# -----------------------------------------------------------------------------
# Secrets (generated once; existing Secrets are kept; values never printed)
# -----------------------------------------------------------------------------
rand() { openssl rand -hex 16; }
secret_exists() { kubectl -n "$1" get secret "$2" >/dev/null 2>&1; }
secret_get() { kubectl -n "$1" get secret "$2" -o "jsonpath={.data.$3}" | base64 -d; }
ensure_secret() {
  # ensure_secret NAMESPACE NAME KEY=VALUE ...
  local ns=$1 name=$2; shift 2
  if secret_exists "$ns" "$name"; then
    info "secret ${ns}/${name}: kept"
    return
  fi
  local args=() kv
  for kv in "$@"; do args+=("--from-literal=${kv}"); done
  kubectl -n "$ns" create secret generic "$name" "${args[@]}" \
    --dry-run=client -o yaml \
    | kubectl label --local -f - -o yaml \
        app.kubernetes.io/part-of=iso42001-ai-system \
        mlops-iso42001.cigip-upv.es/managed-by=install.sh \
    | kubectl apply -f - >/dev/null
  info "secret ${ns}/${name}: created"
}

create_secrets() {
  info "=== Secrets ==="
  # Platform data stores (sources of the shared passwords)
  ensure_secret platform platform-postgresql-auth "postgres-password=$(rand)"
  ensure_secret platform platform-postgresql-app-passwords \
    "MLFLOW_DB_PASSWORD=$(rand)" "KEYCLOAK_DB_PASSWORD=$(rand)" \
    "ZAMMAD_DB_PASSWORD=$(rand)" "GRAFANA_DB_PASSWORD=$(rand)"
  ensure_secret platform platform-timescaledb-auth \
    "postgres-password=$(rand)" "sync-password=$(rand)" "ml-password=$(rand)" "grafana-password=$(rand)"
  ensure_secret minio platform-minio-root "rootUser=minio-admin" "rootPassword=$(rand)"
  ensure_secret minio platform-minio-users "mlflow=$(rand)" "loki=$(rand)"
  ensure_secret edge edge-postgresql-auth "postgres-password=$(rand)" "password=$(rand)"

  # Copies for the consumers in other namespaces
  ensure_secret mlops platform-mlflow-db "username=mlflow" \
    "password=$(secret_get platform platform-postgresql-app-passwords MLFLOW_DB_PASSWORD)"
  ensure_secret mlops platform-mlflow-s3 "AWS_ACCESS_KEY_ID=mlflow" \
    "AWS_SECRET_ACCESS_KEY=$(secret_get minio platform-minio-users mlflow)"
  ensure_secret mlops platform-ml-db "password=$(secret_get platform platform-timescaledb-auth ml-password)"
  ensure_secret monitoring platform-loki-s3 "LOKI_S3_ACCESS_KEY=loki" \
    "LOKI_S3_SECRET_KEY=$(secret_get minio platform-minio-users loki)"
  ensure_secret monitoring platform-grafana-admin "admin-user=admin" "admin-password=$(rand)"
  ensure_secret monitoring platform-grafana-datasources \
    "TIMESCALEDB_PASSWORD=$(secret_get platform platform-timescaledb-auth grafana-password)" \
    "EDGEPG_PASSWORD=$(secret_get edge edge-postgresql-auth password)"
  ensure_secret edge edge-postgresql-sync-target \
    "password=$(secret_get platform platform-timescaledb-auth sync-password)"
  ensure_secret edge edge-mongodb-auth "mongodb-root-password=$(rand)" "mongodb-passwords=$(rand)"
  ensure_secret edge edge-mosquitto-users "gateway=$(rand)" "nodered=$(rand)"
  ensure_secret edge edge-rabbitmq-auth "RABBITMQ_DEFAULT_USER=edge" \
    "RABBITMQ_DEFAULT_PASS=$(rand)" "RABBITMQ_ERLANG_COOKIE=$(rand)$(rand)"
  ensure_secret edge edge-node-red-admin "password=$(rand)"
  ensure_secret security enterprise-keycloak-admin "admin-password=$(rand)"
  ensure_secret security enterprise-keycloak-db \
    "password=$(secret_get platform platform-postgresql-app-passwords KEYCLOAK_DB_PASSWORD)"
  ensure_secret helpdesk enterprise-zammad-db \
    "postgresql-pass=$(secret_get platform platform-postgresql-app-passwords ZAMMAD_DB_PASSWORD)"
  ensure_secret helpdesk enterprise-zammad-redis "redis-password=$(rand)"
}

# -----------------------------------------------------------------------------
# Base: namespaces, NetworkPolicies, Prometheus Operator CRDs, Secrets
# -----------------------------------------------------------------------------
phase_base() {
  info "=== Base ==="
  kubectl apply -f "${INFRA}/00-namespaces.yaml"
  kubectl apply -f "${INFRA}/01-network-policies.yaml"
  # Several charts ship ServiceMonitors: the CRDs must exist before them.
  info "Prometheus Operator CRDs (from platform-prometheus)"
  local d kps; d=$(mktemp -d)
  kps=$(ls "$(resolve_chart platform-prometheus "$d")"/charts/kube-prometheus-stack-*.tgz)
  helm show crds "$kps" | kubectl apply --server-side --force-conflicts -f - >/dev/null
  rm -rf "$d"
  create_secrets
}

# -----------------------------------------------------------------------------
# Chart resolution and installation
# -----------------------------------------------------------------------------
resolve_chart() {
  # Prints a directory with the chart and its dependencies ready to install.
  local name=$1 work=$2
  if [[ -d "${work}/${name}" ]]; then echo "${work}/${name}"; return; fi
  if [[ "${SOURCE}" == local ]]; then
    local src; src=$(chart_dir "$name")
    cp -R "$src" "${work}/${name}"
    rm -rf "${work}/${name}/charts"
    if grep -q '^dependencies:' "${work}/${name}/Chart.yaml"; then
      helm dependency build "${work}/${name}" >/dev/null
    fi
  else
    helm pull "${REPO_ALIAS}/${name}" --untar --untardir "${work}" >/dev/null
  fi
  echo "${work}/${name}"
}

extra_args() {
  local c=$1
  if [[ -n "${VALUES_DIR}" && -f "${VALUES_DIR}/${c}.yaml" ]]; then
    echo "-f ${VALUES_DIR}/${c}.yaml"
  fi
  case "$c" in
    platform-cert-manager) ${HAS_FOREIGN_CM} && echo "--set cert-manager.enabled=false" ;;
    edge-postgresql-sync) echo "--set siteId=${SITE_ID}" ;;
    edge-opc-ua-gateway) echo "--set siteId=${SITE_ID}" ;;
    edge-prometheus-agent) echo "--set prometheus.server.global.external_labels.site_id=${SITE_ID}" ;;
  esac
}

ready_pods() {
  # "<ready>/<expected>" pods of a release (completed Job pods excluded)
  kubectl get pods -A -l "mlops-iso42001.cigip-upv.es/chart=$1" -o json 2>/dev/null | python3 -c '
import json, sys
pods = [p for p in json.load(sys.stdin)["items"] if p["status"].get("phase") not in ("Succeeded",)]
ready = sum(1 for p in pods if any(c["type"] == "Ready" and c["status"] == "True" for c in p["status"].get("conditions", [])))
print(f"{ready}/{len(pods)}")'
}

install_chart() {
  local c=$1 work=$2 ns
  ns=$(ns_of "$1")
  selected "$c" || { info "skip ${c} (not selected)"; return 0; }
  if [[ "$c" == platform-rancher ]]; then
    { ${WITH_RANCHER} && ! ${HAS_RANCHER}; } || { info "skip platform-rancher"; return 0; }
  fi
  if ${DRY_RUN}; then info "plan: ${c} -> namespace ${ns}"; return 0; fi

  local dir start end rc out
  dir=$(resolve_chart "$c" "$work")
  info "install ${c} -> ${ns}"
  start=$(date +%s)
  set +e
  # shellcheck disable=SC2046
  out=$(ISO42001_CHART_DIR="$dir" helm upgrade --install "$c" "$dir" -n "$ns" --create-namespace \
        --wait --timeout "${TIMEOUT}" --post-renderer "${POSTRENDER}" $(extra_args "$c") 2>&1)
  rc=$?
  set -e
  end=$(date +%s)
  local pods; pods=$(ready_pods "$c")
  if [[ $rc -eq 0 ]]; then info "  ok in $((end - start)) s, pods ready ${pods}"
  else warn "  FAILED in $((end - start)) s (pods ready ${pods}): $(echo "$out" | tail -2 | tr '\n' ' ')"; fi
  python3 - "$RUN_LOG" "$c" "$ns" "$start" "$end" "$rc" "$pods" "$out" <<'PY'
import json, sys
log, chart, ns, start, end, rc, pods, out = sys.argv[1:9]
rec = {"chart": chart, "namespace": ns, "start": int(start), "seconds": int(end) - int(start),
       "result": "ok" if rc == "0" else "failed", "pods_ready": pods,
       "message": "" if rc == "0" else out.strip().splitlines()[-1][:500]}
open(log, "a").write(json.dumps(rec) + "\n")
PY
  return 0
}

run_phase() {
  local phase=$1 work=$2
  local var="PHASE_${phase}[@]"
  info "=== Phase ${phase} ==="
  for c in "${!var}"; do
    install_chart "$c" "$work"
    if [[ "$c" == platform-cert-manager ]] && ! ${DRY_RUN} && selected "$c"; then
      # Second pass right away: the platform CA issuers need the
      # cert-manager API, and platform-openbao needs the platform CA.
      info "platform-cert-manager: second pass (platform CA)"
      install_chart "$c" "$work"
    fi
  done
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
  info "MLOps ISO/IEC 42001 K3s catalog installer (source: ${SOURCE}, phases: ${PHASES[*]})"
  preflight
  WORK_DIR=$(mktemp -d)
  trap 'rm -rf "${WORK_DIR}"' EXIT
  for p in "${PHASES[@]}"; do
    if [[ "$p" == base ]]; then
      if ${DRY_RUN}; then info "plan: base"; else phase_base; fi
    else
      run_phase "$p" "${WORK_DIR}"
    fi
  done
  ${DRY_RUN} && return 0
  info "=== Done. Run log: ${RUN_LOG} ==="
  python3 - "$RUN_LOG" <<'PY'
import json, sys
recs = [json.loads(l) for l in open(sys.argv[1])] if __import__("os").path.exists(sys.argv[1]) else []
for r in recs:
    print(f"  {r['result']:6} {r['chart']:32} {r['namespace']:13} {r['seconds']:5d} s  pods {r['pods_ready']}")
failed = [r["chart"] for r in recs if r["result"] != "ok"]
print(f"  {len(recs) - len(failed)}/{len(recs)} releases ok" + (f"; failed: {', '.join(failed)}" if failed else ""))
PY
}

main
