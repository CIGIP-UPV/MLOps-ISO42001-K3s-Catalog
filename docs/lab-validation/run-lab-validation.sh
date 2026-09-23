#!/usr/bin/env bash
# =============================================================================
# run-lab-validation.sh: laboratory validation of the catalog (thesis ch. 7)
#
# Runs next to the K3s cluster of the laboratory and collects the evidence of
# the validation under docs/lab-validation/raw/<run-id>/:
#
#   1. environment      versions, nodes (CPU, RAM), storage classes, existing
#                       namespaces and releases, Rancher
#   2. preparation      edge label on the nodes, resource estimate, optional
#                       API audit (--enable-audit)
#   3. installation     infrastructure/install.sh in the recommended order,
#                       with timing and ready pods per chart
#   4. smoke tests      one functional check per chart
#   5. end-to-end test  OPC UA simulator -> gateway -> ingestion -> edge data
#                       stock -> consolidation -> training -> MLflow ->
#                       propagation to the edge -> inference -> metrics ->
#                       induced drift -> Evidently -> retraining
#                       recommendation -> new version at the edge -> logs
#   6. traceability     kubectl queries per ISO/IEC 42001 clause and component
#   7. network policies default deny and allowed conduits
#
# Every test appends one JSON line to results.jsonl (id, phase, name, result,
# seconds, evidence file, command, detail). No Secret value is printed or
# written to the evidence.
#
# Usage (see docs/lab-validation/LAB_RUN_INSTRUCTIONS.md):
#   ./docs/lab-validation/run-lab-validation.sh [options]
#
# Options:
#   --enable-audit       run infrastructure/enable-audit.sh --apply first
#                        (needs root; restarts the k3s service)
#   --skip-install       do not run install.sh (re-run the tests only)
#   --force              install even if the resource estimate does not fit
#   --no-openbao-init    do not initialise and unseal OpenBao
#   --branch NAME        git branch that Argo CD syncs in its smoke test
#                        (default: the branch checked out here)
#   --edge-nodes "A B"   nodes labelled as edge (default: every node)
#   --phases "4 5"       run only these phases (4 smoke, 5 e2e, 6 trace,
#                        7 netpol); implies --skip-install
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LAB="${ROOT}/docs/lab-validation"
RUN_ID="lab-$(date +%Y%m%dT%H%M%S)"
OUT="${LAB_OUT_DIR:-${LAB}/raw}/${RUN_ID}"
RESULTS="${OUT}/results.jsonl"

ENABLE_AUDIT=false
SKIP_INSTALL=false
FORCE=false
OPENBAO_INIT=true
BRANCH="$(git -C "${ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo lab-validation)"
EDGE_NODES=""
PHASES="1 2 3 4 5 6 7"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --enable-audit) ENABLE_AUDIT=true; shift ;;
    --skip-install) SKIP_INSTALL=true; shift ;;
    --force) FORCE=true; shift ;;
    --no-openbao-init) OPENBAO_INIT=false; shift ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --edge-nodes) EDGE_NODES="$2"; shift 2 ;;
    --phases) PHASES="$2"; SKIP_INSTALL=true; shift 2 ;;
    -h|--help) sed -n '2,45p' "$0"; exit 0 ;;
    *) echo "unknown option $1" >&2; exit 1 ;;
  esac
done
${SKIP_INSTALL} && PHASES="${PHASES//3/}"

mkdir -p "${OUT}"/{env,state,smoke,e2e,trace,netpol}
exec > >(tee -a "${OUT}/run.log") 2>&1

TOOLS_IMAGE="public.ecr.aws/docker/library/busybox:1.36"
MQTT_IMAGE="public.ecr.aws/docker/library/eclipse-mosquitto:2.0"
MC_IMAGE="quay.io/minio/mc:RELEASE.2024-11-21T17-21-54Z"
MODEL="zdm-anomaly-detector"

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

# ---------------------------------------------------------------------------
# Result recording and helpers
# ---------------------------------------------------------------------------
record() {
  # record ID PHASE NAME RESULT SECONDS EVIDENCE COMMAND [DETAIL]
  python3 - "$RESULTS" "$@" <<'PY'
import json, sys
path, tid, phase, name, result, secs, evidence, cmd = sys.argv[1:9]
detail = sys.argv[9] if len(sys.argv) > 9 else ""
open(path, "a").write(json.dumps({"id": tid, "phase": phase, "name": name, "result": result,
    "seconds": int(float(secs)), "evidence": evidence, "command": cmd, "detail": detail[-600:]}) + "\n")
PY
  log "${4} ${1} ${3}"
}

run_test() {
  # run_test ID PHASE NAME EVIDENCE "readable command" FUNCTION [ARGS...]
  # PASS when FUNCTION returns 0; its output is the evidence.
  local tid=$1 phase=$2 name=$3 ev=$4 shown=$5 fn=$6; shift 6
  local start rc out
  start=$(date +%s)
  # port-forwards opened by FUNCTION live in this subshell: close them there
  out=$("$fn" "$@" 2>&1; r=$?; cleanup_pf; exit $r); rc=$?
  { echo "# ${tid}: ${name}"; echo "\$ ${shown}"; echo "${out}"; echo "(exit ${rc})"; } > "${OUT}/${ev}"
  record "$tid" "$phase" "$name" "$([[ $rc -eq 0 ]] && echo PASS || echo FAIL)" "$(( $(date +%s) - start ))" "$ev" "$shown" \
    "$(printf '%s' "$out" | tail -4 | tr '\n' ' ')"
  return $rc
}

wait_for() {
  # wait_for SECONDS COMMAND...: retry every 5 s until the command succeeds
  local limit=$1 t=0; shift
  until "$@" >/dev/null 2>&1; do
    sleep 5; t=$((t + 5)); [[ $t -ge $limit ]] && return 1
  done
  return 0
}

PF_PIDS=""
port_forward() {
  # port_forward NS TARGET LOCAL:REMOTE
  kubectl -n "$1" port-forward "$2" "$3" >/dev/null 2>&1 &
  PF_PIDS="${PF_PIDS} $!"
  local port=${3%%:*} t=0
  until curl -s -o /dev/null "http://127.0.0.1:${port}/" 2>/dev/null; do
    sleep 1; t=$((t + 1)); [[ $t -ge 30 ]] && return 1
  done
  return 0
}
cleanup_pf() { for p in ${PF_PIDS}; do kill "$p" 2>/dev/null; done; PF_PIDS=""; }
trap cleanup_pf EXIT

secret_env() {
  # secret_env VAR SECRET KEY ... -> JSON env with secretKeyRef (values never read here)
  python3 - "$@" <<'PY'
import json, sys
a = sys.argv[1:]
print(json.dumps([{"name": a[i], "valueFrom": {"secretKeyRef": {"name": a[i + 1], "key": a[i + 2]}}}
                  for i in range(0, len(a), 3)]))
PY
}

tmp_pod() {
  # tmp_pod NS NAME IMAGE SHELL_COMMAND [ENV_JSON]: short-lived pod, prints its log
  local ns=$1 name=$2 image=$3 cmd=$4 env=${5:-[]} phase
  kubectl -n "$ns" delete pod "$name" --ignore-not-found --wait=true >/dev/null 2>&1
  python3 - "$name" "$image" "$cmd" "$env" <<'PY' | kubectl -n "$ns" apply -f - >/dev/null
import json, sys
name, image, cmd, env = sys.argv[1:5]
print(json.dumps({"apiVersion": "v1", "kind": "Pod",
  "metadata": {"name": name, "labels": {"lab-validation": "test"}},
  "spec": {"restartPolicy": "Never", "terminationGracePeriodSeconds": 1,
           "containers": [{"name": "t", "image": image, "command": ["sh", "-c", cmd], "env": json.loads(env)}]}}))
PY
  local t=0
  while :; do
    phase=$(kubectl -n "$ns" get pod "$name" -o jsonpath='{.status.phase}' 2>/dev/null)
    [[ "$phase" == Succeeded || "$phase" == Failed ]] && break
    sleep 3; t=$((t + 3)); [[ $t -ge 420 ]] && break
  done
  kubectl -n "$ns" logs "$name" 2>&1
  kubectl -n "$ns" delete pod "$name" --wait=false >/dev/null 2>&1
  [[ "$phase" == Succeeded ]]
}

psql_edge() { kubectl -n edge exec edge-postgresql-0 -c postgresql -- sh -c "PGPASSWORD=\"\$POSTGRES_PASSWORD\" psql -U edge_app -d zdm_edge -tA -F ' | ' -c \"$1\""; }
psql_ts()   { kubectl -n platform exec platform-timescaledb-0 -c timescaledb -- psql -U postgres -d zdm_platform -tA -F ' | ' -c "$1"; }
job_from() {
  # job_from NS CRONJOB JOB: create a Job from a CronJob and wait for it
  kubectl -n "$1" delete job "$3" --ignore-not-found >/dev/null 2>&1
  kubectl -n "$1" create job --from="cronjob/$2" "$3" >/dev/null || return 1
  kubectl -n "$1" wait "job/$3" --for=condition=complete --timeout=900s
}
phase_on() { [[ " ${PHASES} " == *" $1 "* ]]; }

# ===========================================================================
# 1. Environment
# ===========================================================================
phase_environment() {
  log "=== 1. Environment (${RUN_ID}) ==="
  {
    echo "date: $(date -Is 2>/dev/null || date)"
    echo "host: $(hostname)"
    grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release 2>/dev/null
    echo "kernel: $(uname -r)"
    echo "k3s: $(k3s --version 2>/dev/null | head -1)"
    echo "kubectl client: $(kubectl version --client -o json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)["clientVersion"]["gitVersion"])')"
    echo "kubernetes server: $(kubectl version -o json 2>/dev/null | python3 -c 'import json,sys;print(json.load(sys.stdin)["serverVersion"]["gitVersion"])')"
    echo "helm: $(helm version --short 2>/dev/null)"
    echo "rancher: $(kubectl -n cattle-system get deploy rancher -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo 'not found')"
    echo "cert-manager: $(kubectl get deploy -A -l app.kubernetes.io/name=cert-manager -o jsonpath='{range .items[*]}{.metadata.namespace}/{.metadata.name} {.spec.template.spec.containers[0].image}{"\n"}{end}' 2>/dev/null)"
    echo "catalog commit: $(git -C "${ROOT}" rev-parse HEAD 2>/dev/null) (${BRANCH})"
  } > "${OUT}/env/versions.txt"
  kubectl get nodes -o json | python3 -c '
import json, sys
rows = []
for n in json.load(sys.stdin)["items"]:
    i, c, a = n["status"]["nodeInfo"], n["status"]["capacity"], n["status"]["allocatable"]
    rows.append({"name": n["metadata"]["name"],
                 "roles": sorted(k.split("/")[1] for k in n["metadata"]["labels"] if k.startswith("node-role.kubernetes.io/")),
                 "os": i["osImage"], "kernel": i["kernelVersion"], "arch": i["architecture"], "kubelet": i["kubeletVersion"],
                 "runtime": i["containerRuntimeVersion"], "cpu": c["cpu"], "memory": c["memory"],
                 "allocatable_cpu": a["cpu"], "allocatable_memory": a["memory"], "ephemeral_storage": c.get("ephemeral-storage")})
json.dump(rows, sys.stdout, indent=1)' > "${OUT}/env/nodes.json"
  kubectl get nodes -o wide > "${OUT}/env/nodes.txt" 2>&1
  kubectl get sc > "${OUT}/env/storageclasses.txt" 2>&1
  kubectl get ns > "${OUT}/env/namespaces-before.txt" 2>&1
  helm list -A > "${OUT}/env/helm-releases-before.txt" 2>&1
  cat "${OUT}/env/versions.txt"
  record ENV-01 environment "environment captured" PASS 0 env/versions.txt "see env/ (versions, nodes, storage classes, namespaces, releases)"
}

# ===========================================================================
# 2. Preparation
# ===========================================================================
label_edge() {
  local nodes="${EDGE_NODES:-$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')}"
  # shellcheck disable=SC2086
  kubectl label node ${nodes} node-role.kubernetes.io/edge=true --overwrite && kubectl get nodes -l node-role.kubernetes.io/edge=true
}
estimate() { python3 "${LAB}/tools/estimate_resources.py" "${ROOT}" "${OUT}/env/resource-estimate.json"; }

phase_preparation() {
  log "=== 2. Preparation ==="
  run_test PREP-01 preparation "edge label on the nodes" state/edge-label.txt \
    "kubectl label node <nodes> node-role.kubernetes.io/edge=true --overwrite" label_edge
  if ${ENABLE_AUDIT}; then
    run_test PREP-02 preparation "API audit policy enabled" state/enable-audit.txt \
      "infrastructure/enable-audit.sh --apply" "${ROOT}/infrastructure/enable-audit.sh" --apply
    wait_for 180 kubectl get --raw /readyz
  else
    record PREP-02 preparation "API audit policy enabled" SKIP 0 "" "infrastructure/enable-audit.sh --apply" "not requested (--enable-audit)"
  fi
  if ! run_test PREP-03 preparation "resource estimate (catalog requests vs free allocatable)" state/resource-estimate.txt \
       "docs/lab-validation/tools/estimate_resources.py" estimate; then
    if ! ${FORCE}; then
      log "The catalog requests more CPU or memory than the cluster has free. Nothing installed."
      log "Review env/resource-estimate.json, then re-run with --force or skip charts (see the instructions)."
      finish; exit 3
    fi
  fi
}

# ===========================================================================
# 3. Installation
# ===========================================================================
install_catalog() {
  local extra=""
  if kubectl get crd certificates.cert-manager.io >/dev/null 2>&1 \
     && ! helm -n cert-manager status platform-cert-manager >/dev/null 2>&1; then
    extra="--use-existing-cert-manager"
  fi
  echo "extra options: ${extra:-none}"
  # shellcheck disable=SC2086
  "${ROOT}/infrastructure/install.sh" --values-dir "${LAB}/lab-values" --site-id lab-edge-01 \
      --log "${OUT}/install.jsonl" ${extra} > "${OUT}/install.log" 2>&1
  local rc=$?
  tail -40 "${OUT}/install.log"
  return $rc
}

phase_install() {
  log "=== 3. Installation ==="
  run_test INST-00 installation "install.sh, all phases" state/install-summary.txt \
    "infrastructure/install.sh --values-dir docs/lab-validation/lab-values --site-id lab-edge-01 [--use-existing-cert-manager]" install_catalog
  python3 - "${OUT}/install.jsonl" "${RESULTS}" <<'PY'
import json, sys, os
if os.path.exists(sys.argv[1]):
    with open(sys.argv[2], "a") as out:
        for i, l in enumerate(open(sys.argv[1])):
            r = json.loads(l)
            out.write(json.dumps({"id": f"INST-{i + 1:02d}", "phase": "installation", "name": r["chart"],
                "result": "PASS" if r["result"] == "ok" else "FAIL", "seconds": r["seconds"], "evidence": "install.jsonl",
                "command": f"helm upgrade --install {r['chart']} ... -n {r['namespace']} --wait --post-renderer iso42001-postrender.py",
                "detail": f"pods ready {r['pods_ready']}" + (f"; {r['message']}" if r["message"] else "")}) + "\n")
PY
  snapshot state/after-install
}

snapshot() {
  local p=$1
  kubectl get pods -A -o wide > "${OUT}/${p}-pods.txt" 2>&1
  helm list -A > "${OUT}/${p}-helm.txt" 2>&1
  kubectl get events -A --field-selector type=Warning --sort-by=.lastTimestamp 2>/dev/null | tail -300 > "${OUT}/${p}-warning-events.txt"
  kubectl top nodes > "${OUT}/${p}-top-nodes.txt" 2>&1
  kubectl top pods -A --sort-by=memory > "${OUT}/${p}-top-pods.txt" 2>&1
  kubectl get pods -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{range .spec.containers[*]}{.image}{" "}{end}{"\n"}{end}' > "${OUT}/${p}-images.txt" 2>&1
}

# ===========================================================================
# 4. Smoke tests
# ===========================================================================
s_mlflow() {
  port_forward mlops svc/platform-mlflow 15000:5000 || return 1
  curl -sf -X POST http://127.0.0.1:15000/api/2.0/mlflow/experiments/search \
    -H 'Content-Type: application/json' -d '{"max_results": 20}' \
    | python3 -c 'import json,sys; print("experiments:", [e["name"] for e in json.load(sys.stdin)["experiments"]])'
}
s_minio() {
  tmp_pod minio lab-s02 "${MC_IMAGE}" \
    'mc alias set s http://platform-minio:9000 "$U" "$P" >/dev/null && mc ls s && mc retention info --default s/iso42001-docs && mc version info s/model-cards' \
    "$(secret_env U platform-minio-root rootUser P platform-minio-root rootPassword)"
}
s_kafka() {
  kubectl -n edge exec edge-kafka-controller-0 -c kafka -- bash -c '
    unset JMX_PORT KAFKA_JMX_OPTS
    m="lab-smoke-$(date +%s)"
    kafka-topics.sh --bootstrap-server localhost:9092 --list
    echo "$m" | kafka-console-producer.sh --bootstrap-server localhost:9092 --topic alerts
    kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic alerts --from-beginning --timeout-ms 20000 2>/dev/null | grep -q "$m" && echo "consumed $m"'
}
s_mosquitto() {
  tmp_pod edge lab-s04 "${MQTT_IMAGE}" '
    mosquitto_sub -h edge-mosquitto -u nodered -P "$NR" -t lab/smoke -C 1 -W 20 > /tmp/got & s=$!
    sleep 2; mosquitto_pub -h edge-mosquitto -u gateway -P "$GW" -t lab/smoke -m hello
    wait $s; echo "received: $(cat /tmp/got)"
    if mosquitto_pub -h edge-mosquitto -t lab/smoke -m anonymous 2>/dev/null; then echo "anonymous accepted"; exit 1; else echo "anonymous refused"; fi
    grep -q hello /tmp/got' \
    "$(secret_env GW edge-mosquitto-users gateway NR edge-mosquitto-users nodered)"
}
s_rabbitmq() { kubectl -n edge exec deploy/edge-rabbitmq -- sh -c 'rabbitmq-diagnostics -q check_running && rabbitmq-diagnostics -q listeners'; }
s_nodered() {
  port_forward edge svc/edge-node-red 11880:1880 || return 1
  curl -sf http://127.0.0.1:11880/metrics | grep -E '^ingest_'
  local code; code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:11880/admin/flows)
  echo "editor /admin/flows without credentials: HTTP ${code}"; [[ "$code" == 401 ]]
}
s_prometheus() {
  port_forward monitoring svc/platform-prometheus-prometheus 19090:9090 || return 1
  curl -sf http://127.0.0.1:19090/api/v1/targets | python3 "${LAB}/tools/targets_summary.py"
}
s_grafana() {
  port_forward monitoring svc/platform-grafana 13000:80 || return 1
  local gp; gp=$(kubectl -n monitoring get secret platform-grafana-admin -o jsonpath='{.data.admin-password}' | base64 -d)
  curl -sf http://127.0.0.1:13000/api/health; echo
  local u ok=0
  for u in prometheus loki timescaledb edgepg; do
    r=$(curl -s -u "admin:${gp}" "http://127.0.0.1:13000/api/datasources/uid/${u}/health")
    echo "data source ${u}: ${r}"; echo "$r" | grep -q '"status":"OK"' && ok=$((ok + 1))
  done
  curl -s -u "admin:${gp}" 'http://127.0.0.1:13000/api/search?query=ZDM' \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d), "ZDM dashboards:", [x["title"] for x in d]); sys.exit(0 if d else 1)' \
    && echo "healthy data sources: ${ok}/4" && [[ $ok -ge 2 ]]
}
s_loki() {
  port_forward monitoring svc/platform-loki 13100:3100 || return 1
  local ts; ts=$(date +%s)000000000
  curl -sf -H 'Content-Type: application/json' -X POST http://127.0.0.1:13100/loki/api/v1/push \
    -d "{\"streams\":[{\"stream\":{\"job\":\"lab-smoke\"},\"values\":[[\"${ts}\",\"lab smoke line ${ts}\"]]}]}" && echo "pushed"
  sleep 5
  curl -sfG http://127.0.0.1:13100/loki/api/v1/query_range --data-urlencode 'query={job="lab-smoke"}' \
    --data-urlencode "start=$(( $(date +%s) - 300 ))000000000" | grep -o "lab smoke line ${ts}" | head -1 | grep -q .  && echo "read back: lab smoke line ${ts}"
}
s_falco() {
  kubectl -n edge exec deploy/edge-fastapi-model -- sh -c 'id' >/dev/null 2>&1
  sleep 20
  kubectl -n falco logs -l app.kubernetes.io/name=falco -c falco --since=3m 2>/dev/null \
    | grep -E 'AI Container Shell Spawn|Terminal shell in container' | tail -3 | cut -c1-400 | grep .
}
s_keycloak() {
  port_forward security svc/enterprise-keycloak 18080:80 || return 1
  curl -sf http://127.0.0.1:18080/realms/ai-system/.well-known/openid-configuration \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print("issuer:", d["issuer"])'
}
s_zammad() {
  port_forward helpdesk svc/enterprise-zammad 18081:8080 || return 1
  local code; code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18081/)
  echo "web: HTTP ${code}"
  curl -s http://127.0.0.1:18081/api/v1/getting_started | head -c 300; echo
  [[ "$code" == 200 ]]
}
s_openbao_status() {
  kubectl -n openbao exec platform-openbao-0 -- bao status; local rc=$?
  echo "(bao status exit ${rc}: 0 unsealed, 2 sealed, 1 error)"; [[ $rc -ne 1 ]]
}
s_openbao_init() {
  set -e
  if ! kubectl -n openbao get secret openbao-lab-init >/dev/null 2>&1; then
    local f; f=$(mktemp)
    kubectl -n openbao exec platform-openbao-0 -- bao operator init -key-shares=1 -key-threshold=1 -format=json > "$f"
    kubectl -n openbao create secret generic openbao-lab-init --from-file=init.json="$f" >/dev/null
    rm -f "$f"
    echo "initialised; laboratory unseal key and root token stored in Secret openbao/openbao-lab-init (not printed)"
  fi
  local j key tok
  j=$(kubectl -n openbao get secret openbao-lab-init -o jsonpath='{.data.init\.json}' | base64 -d)
  key=$(printf '%s' "$j" | python3 -c 'import json,sys;print(json.load(sys.stdin)["unseal_keys_b64"][0])')
  tok=$(printf '%s' "$j" | python3 -c 'import json,sys;print(json.load(sys.stdin)["root_token"])')
  kubectl -n openbao exec platform-openbao-0 -- bao operator unseal "$key" >/dev/null || true
  kubectl -n openbao exec platform-openbao-0 -- env BAO_TOKEN="$tok" sh -c '
    bao secrets list | grep -q "^mlops-kv/" || bao secrets enable -path=mlops-kv -version=2 kv >/dev/null
    bao audit list 2>/dev/null | grep -q "^file/" || bao audit enable file file_path=/openbao/audit/audit.log >/dev/null
    bao kv put mlops-kv/lab/smoke value=ok >/dev/null
    echo "kv read back: $(bao kv get -field=value mlops-kv/lab/smoke)"
    bao status | grep -E "Initialized|Sealed"
    bao audit list'
  set +e
}
s_certmanager() {
  kubectl apply -f - <<'EOF'
apiVersion: cert-manager.io/v1
kind: Certificate
metadata: {name: lab-smoke-cert, namespace: platform, labels: {lab-validation: test}}
spec: {secretName: lab-smoke-cert, dnsNames: [lab-smoke.platform.svc], issuerRef: {name: platform-ca, kind: ClusterIssuer}}
EOF
  kubectl -n platform wait certificate/lab-smoke-cert --for=condition=Ready --timeout=120s; local rc=$?
  kubectl -n platform get certificate lab-smoke-cert
  kubectl -n platform get secret lab-smoke-cert -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -subject -issuer -enddate
  kubectl -n platform delete certificate lab-smoke-cert --wait=false >/dev/null
  kubectl -n platform delete secret lab-smoke-cert --ignore-not-found >/dev/null
  return $rc
}
s_argocd() {
  kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: {name: lab-smoke-dashboards, namespace: argocd, labels: {lab-validation: test}}
spec:
  project: default
  source:
    repoURL: https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog
    targetRevision: ${BRANCH}
    path: catalog/enterprise/dashboards/grafana/manifests
    helm: {releaseName: lab-smoke-dashboards}
  destination: {server: https://kubernetes.default.svc, namespace: argocd-smoke}
  syncPolicy: {automated: {prune: true}, syncOptions: [CreateNamespace=true]}
EOF
  local s=""
  for _ in $(seq 1 48); do
    s=$(kubectl -n argocd get application lab-smoke-dashboards -o jsonpath='{.status.sync.status}/{.status.health.status}' 2>/dev/null)
    [[ "$s" == Synced/Healthy ]] && break; sleep 5
  done
  echo "application status: ${s}"
  kubectl -n argocd get application lab-smoke-dashboards -o jsonpath='{.status.operationState.message}{"\n"}' 2>/dev/null
  kubectl -n argocd-smoke get configmaps 2>&1
  kubectl -n argocd delete application lab-smoke-dashboards --wait=true --timeout=90s >/dev/null 2>&1
  kubectl delete namespace argocd-smoke --wait=false >/dev/null 2>&1
  [[ "$s" == Synced/Healthy ]]
}
s_timescaledb() {
  psql_ts "SELECT hypertable_name FROM timescaledb_information.hypertables ORDER BY 1" &&
  psql_ts "SELECT rolname FROM pg_roles WHERE rolname IN ('sync','ml','grafana') ORDER BY 1"
}
s_edgepg() { psql_edge "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1"; }
s_mongodb() {
  kubectl -n edge exec deploy/edge-mongodb -c mongodb -- sh -c \
    'mongosh --quiet -u root -p "$MONGODB_ROOT_PASSWORD" --eval "db.getSiblingDB(\"edge_buffer\").getCollectionNames()"'
}
s_platformpg() {
  kubectl -n platform exec platform-postgresql-0 -c postgresql -- sh -c \
    "PGPASSWORD=\"\$POSTGRES_PASSWORD\" psql -U postgres -tAc \"SELECT datname FROM pg_database WHERE datname IN ('mlflow','keycloak','zammad','grafana') ORDER BY 1\""
}
s_evidently() {
  port_forward mlops svc/platform-evidently 18000:8000 || return 1
  curl -sf http://127.0.0.1:18000/api/version
}

phase_smoke() {
  log "=== 4. Smoke tests ==="
  local P=smoke
  run_test S01 $P "MLflow tracking API" smoke/S01-mlflow.txt "POST /api/2.0/mlflow/experiments/search (port-forward svc/platform-mlflow)" s_mlflow
  run_test S02 $P "MinIO buckets, versioning and document store retention" smoke/S02-minio.txt "mc ls; mc retention info --default s/iso42001-docs; mc version info s/model-cards (pod in minio)" s_minio
  run_test S03 $P "Kafka produce and consume" smoke/S03-kafka.txt "kafka-console-producer.sh / kafka-console-consumer.sh on topic alerts" s_kafka
  run_test S04 $P "Mosquitto authenticated publish/subscribe, anonymous refused" smoke/S04-mosquitto.txt "mosquitto_sub (nodered) + mosquitto_pub (gateway); anonymous mosquitto_pub" s_mosquitto
  run_test S05 $P "RabbitMQ running and listeners" smoke/S05-rabbitmq.txt "rabbitmq-diagnostics check_running; listeners" s_rabbitmq
  run_test S06 $P "Node-RED ingestion metrics and protected editor" smoke/S06-node-red.txt "GET /metrics; GET /admin/flows (expect 401)" s_nodered
  run_test S07 $P "Prometheus scrape targets" smoke/S07-prometheus.txt "GET /api/v1/targets (port-forward svc/platform-prometheus-prometheus)" s_prometheus
  run_test S08 $P "Grafana health, data sources and dashboards" smoke/S08-grafana.txt "GET /api/health; /api/datasources/uid/<uid>/health; /api/search?query=ZDM" s_grafana
  run_test S09 $P "Loki write and query" smoke/S09-loki.txt "POST /loki/api/v1/push; GET /loki/api/v1/query_range" s_loki
  run_test S10 $P "Falco runtime event (shell in the model server)" smoke/S10-falco.txt "kubectl exec deploy/edge-fastapi-model -- sh -c id; kubectl logs falco" s_falco
  run_test S11 $P "Keycloak realm ai-system" smoke/S11-keycloak.txt "GET /realms/ai-system/.well-known/openid-configuration" s_keycloak
  run_test S12 $P "Zammad web and API" smoke/S12-zammad.txt "GET /; GET /api/v1/getting_started" s_zammad
  run_test S13 $P "OpenBao status over TLS (platform CA)" smoke/S13-openbao.txt "kubectl exec platform-openbao-0 -- bao status" s_openbao_status
  if ${OPENBAO_INIT}; then
    run_test S13b $P "OpenBao init, unseal, KV write/read, audit device" smoke/S13b-openbao-init.txt "bao operator init/unseal; bao secrets enable kv; bao audit enable file; bao kv put/get" s_openbao_init
  else
    record S13b $P "OpenBao init and KV" SKIP 0 "" "" "--no-openbao-init"
  fi
  run_test S14 $P "cert-manager test certificate from the platform CA" smoke/S14-cert-manager.txt "kubectl apply Certificate (issuer platform-ca); kubectl wait --for=condition=Ready" s_certmanager
  run_test S15 $P "Argo CD sync of a catalog chart from git (${BRANCH})" smoke/S15-argocd.txt "kubectl apply Application lab-smoke-dashboards; wait Synced/Healthy" s_argocd
  run_test S16 $P "TimescaleDB hypertables and roles" smoke/S16-timescaledb.txt "psql: timescaledb_information.hypertables; pg_roles" s_timescaledb
  run_test S17 $P "Edge PostgreSQL schema" smoke/S17-edge-postgresql.txt "psql: information_schema.tables" s_edgepg
  run_test S18 $P "MongoDB edge buffer collections" smoke/S18-mongodb.txt "mongosh: getCollectionNames()" s_mongodb
  run_test S19 $P "Platform PostgreSQL service databases" smoke/S19-platform-postgresql.txt "psql: pg_database" s_platformpg
  run_test S20 $P "Evidently UI API" smoke/S20-evidently.txt "GET /api/version" s_evidently
  cleanup_pf
}

# ===========================================================================
# 5. End-to-end test
# ===========================================================================
edge_rows()    { psql_edge "SELECT count(*) FROM sensor_features" | tr -d '[:space:]'; }
edge_seconds() { psql_edge "SELECT count(DISTINCT date_trunc('second', timestamp)) FROM sensor_features WHERE machine_id='cnc-01'" | tr -d '[:space:]'; }
enough_data()  { [[ $(edge_seconds) -ge 300 ]]; }
served_version() { curl -s http://127.0.0.1:18001/version | python3 -c 'import json,sys;print(json.load(sys.stdin)["model_version"])' 2>/dev/null; }

e_sim() { kubectl apply -f "${LAB}/manifests/opc-plc-simulator.yaml" && kubectl -n edge rollout status deploy/opc-plc --timeout=300s; }
e_gateway() {
  sleep 30
  kubectl -n edge exec deploy/edge-opc-ua-gateway -- wget -qO- localhost:9273/metrics | grep -E 'internal_gather_(metrics_gathered|errors)\{input="opcua"' | tee /dev/stderr \
    | grep -Eq 'internal_gather_metrics_gathered\{input="opcua".*} [1-9]'
}
e_ingestion() {
  local a b; a=$(edge_rows); sleep 30; b=$(edge_rows)
  echo "sensor_features rows: ${a} -> ${b}"
  psql_edge "SELECT machine_id, feature_name, count(*), round(min(value)::numeric,2), round(max(value)::numeric,2) FROM sensor_features GROUP BY 1,2 ORDER BY 1,2"
  [[ "$b" -gt "$a" ]]
}
e_consolidation() {
  job_from edge edge-postgresql-sync "$1" && kubectl -n edge logs "job/$1" &&
  psql_ts "SELECT id, site_id, source_table, from_id, to_id, rows_read, rows_written, status FROM consolidation_batches ORDER BY id DESC LIMIT 4" &&
  psql_ts "SELECT machine_id, count(*) FROM sensor_readings GROUP BY 1 ORDER BY 1" &&
  [[ $(psql_ts "SELECT count(*) FROM sensor_readings" | tr -d '[:space:]') -gt 0 ]]
}
e_training() {
  job_from mlops platform-training-jobs e2e-train-1; local rc=$?
  kubectl -n mlops logs job/e2e-train-1 | grep '"component"'
  [[ $rc -eq 0 ]] && kubectl -n mlops logs job/e2e-train-1 | grep -q '"promoted_alias": "champion"'
}
e_registry() {
  port_forward mlops svc/platform-mlflow 15000:5000 || return 1
  curl -sf "http://127.0.0.1:15000/api/2.0/mlflow/registered-models/get?name=${MODEL}" \
    | python3 -c 'import json,sys; m=json.load(sys.stdin)["registered_model"]; print("aliases:", m.get("aliases")); print("versions:", [v["version"] for v in m.get("latest_versions", [])])'
  curl -sf "http://127.0.0.1:15000/api/2.0/mlflow/model-versions/get?name=${MODEL}&version=1" \
    | python3 -c 'import json,sys; v=json.load(sys.stdin)["model_version"]; print("v1 tags:", {t["key"]: t["value"] for t in v.get("tags", [])})'
}
e_propagation() {
  job_from edge edge-mlflow-sync "$1"; local rc=$?
  kubectl -n edge logs "job/$1"
  psql_edge "SELECT received_at, model_name, model_version, status, left(artefact_sha256, 12) FROM model_versions ORDER BY id"
  [[ $rc -eq 0 ]] && kubectl -n edge logs "job/$1" | grep -Eq 'version_activated|up_to_date'
}
e_inference() {
  port_forward edge svc/edge-fastapi-model 18001:8000 || return 1
  curl -sf http://127.0.0.1:18001/version; echo
  local f; f=$(psql_edge "SELECT json_object_agg(feature_name, v) FROM (SELECT feature_name, avg(value) v FROM sensor_features WHERE machine_id='cnc-01' AND timestamp > now() - interval '30 seconds' GROUP BY 1) s")
  echo "features of the last 30 s: ${f}"
  curl -sf http://127.0.0.1:18001/predict -H 'Content-Type: application/json' \
    -d "{\"samples\":[{\"machine_id\":\"cnc-01\",\"features\":${f}},{\"machine_id\":\"cnc-01\",\"features\":{\"SpikeData\":0,\"DipData\":-1000,\"PositiveTrendData\":0,\"NegativeTrendData\":0}}]}" || return 1
  echo; psql_edge "SELECT timestamp, model_version, label, round(score::numeric,4) FROM predictions ORDER BY id DESC LIMIT 4"
}
e_metrics() {
  port_forward monitoring svc/platform-prometheus-prometheus 19090:9090 || return 1
  sleep 45
  local q n=0
  for q in 'sum by (model_version, outcome) (model_predictions_total)' 'max by (model_version) (model_info)' \
           'sum(ingest_messages_valid_total)' 'sum(internal_gather_metrics_gathered{input="opcua"})'; do
    r=$(curl -sG http://127.0.0.1:19090/api/v1/query --data-urlencode "query=${q}" \
        | python3 -c 'import json,sys; r=json.load(sys.stdin)["data"]["result"]; print([(x["metric"], x["value"][1]) for x in r])')
    echo "${q} => ${r}"; [[ "$r" != "[]" ]] && n=$((n + 1))
  done
  echo "queries with data: ${n}/4"; [[ $n -ge 3 ]]
}
e_drift_inject() {
  tmp_pod edge lab-e10 "${MQTT_IMAGE}" '
    i=0
    while [ $i -lt 300 ]; do
      t=$(date +%s)
      for f in SpikeData DipData PositiveTrendData NegativeTrendData; do
        v=$(awk -v s=$RANDOM "BEGIN{srand(s); printf \"%.3f\", 400 + rand()*50}")
        mosquitto_pub -h edge-mosquitto -u gateway -P "$GW" -q 1 -t plant/cnc-02/opcua \
          -m "{\"fields\":{\"Quality\":\"The operation succeeded. StatusGood (0x0)\",\"$f\":$v},\"name\":\"opcua\",\"tags\":{\"machine_id\":\"cnc-02\",\"site_id\":\"lab-edge-01\"},\"timestamp\":$t}"
      done
      i=$((i+1)); sleep 1
    done
    echo "published ${i} seconds of shifted samples for machine cnc-02"' \
    "$(secret_env GW edge-mosquitto-users gateway)"
}
e_drift() {
  job_from mlops platform-evidently-drift e2e-drift-1; local rc=$?
  kubectl -n mlops logs job/e2e-drift-1 --all-containers | grep '"component"'
  psql_ts "SELECT id, model_version, round(drift_share::numeric,3), drifted_columns, recommended, action FROM retraining_recommendations ORDER BY id DESC LIMIT 3"
  [[ $rc -eq 0 ]] && psql_ts "SELECT recommended FROM retraining_recommendations ORDER BY id DESC LIMIT 1" | grep -q t
}
e_retraining() {
  local j; j=$(kubectl -n mlops get jobs --sort-by=.metadata.creationTimestamp -o name | grep 'platform-training-jobs-drift-' | tail -1)
  echo "retraining job started by the recommendation: ${j:-none}"
  [[ -n "$j" ]] || return 1
  kubectl -n mlops wait "$j" --for=condition=complete --timeout=900s; local rc=$?
  kubectl -n mlops logs "$j" | grep '"component"'
  [[ $rc -eq 0 ]] && kubectl -n mlops logs "$j" | grep -q '"trigger": "drift"\|"model_registered"'
}
e_new_version() {
  port_forward edge svc/edge-fastapi-model 18001:8000 || return 1
  local before after; before=$(served_version)
  job_from edge edge-mlflow-sync e2e-vsync-2; kubectl -n edge logs job/e2e-vsync-2
  after=$(served_version); echo "served version: ${before} -> ${after}"
  curl -sf http://127.0.0.1:18001/predict -H 'Content-Type: application/json' \
    -d '{"samples":[{"machine_id":"cnc-01","features":{"SpikeData":0,"DipData":0,"PositiveTrendData":100,"NegativeTrendData":100}}]}'; echo
  [[ -n "$after" && "$after" != "$before" ]]
}
e_loki() {
  port_forward monitoring svc/platform-loki 13100:3100 || return 1
  sleep 20
  local ev n ok=0
  for ev in model_registered version_activated recommendation drift_computed prediction sample_rejected edge-postgresql-sync; do
    n=$(curl -sG http://127.0.0.1:13100/loki/api/v1/query --data-urlencode "query=sum(count_over_time({namespace=~\"edge|mlops\"} |= \"${ev}\" [3h]))" \
        | python3 -c 'import json,sys; r=json.load(sys.stdin)["data"]["result"]; print(r[0]["value"][1] if r else 0)')
    echo "${ev}: ${n} log lines"; [[ "$n" != 0 ]] && ok=$((ok + 1))
  done
  echo "event types found in Loki: ${ok}/7"; [[ $ok -ge 4 ]]
}
e_evidently_ui() {
  port_forward mlops svc/platform-evidently 18000:8000 || return 1
  curl -sf http://127.0.0.1:18000/api/projects | python3 -c 'import json,sys; p=json.load(sys.stdin); print("projects:", [x["name"] for x in p]); sys.exit(0 if p else 1)'
}

phase_e2e() {
  log "=== 5. End-to-end test ==="
  local P=e2e
  run_test E01 $P "OPC UA simulator (OPC PLC) in the edge namespace" e2e/E01-simulator.txt "kubectl apply -f docs/lab-validation/manifests/opc-plc-simulator.yaml" e_sim
  run_test E02 $P "OPC UA gateway reads the simulator" e2e/E02-gateway.txt "wget localhost:9273/metrics in edge-opc-ua-gateway" e_gateway
  run_test E03 $P "Ingestion: MQTT -> Node-RED validation -> edge data stock" e2e/E03-ingestion.txt "psql: count(*) FROM sensor_features, 30 s apart" e_ingestion
  log "Waiting for 300 s of plant data of machine cnc-01 (1-second feature vectors)..."
  wait_for 900 enough_data
  run_test E04 $P "Data consolidation edge -> platform (batch log)" e2e/E04-consolidation.txt "kubectl create job --from=cronjob/edge-postgresql-sync; psql consolidation_batches" e_consolidation e2e-sync-1
  run_test E05 $P "Training job registers and promotes a model version" e2e/E05-training.txt "kubectl create job --from=cronjob/platform-training-jobs e2e-train-1" e_training
  run_test E06 $P "MLflow registry: version, alias and provenance tags" e2e/E06-registry.txt "GET /api/2.0/mlflow/registered-models/get; model-versions/get" e_registry
  run_test E07 $P "Version propagation platform -> edge (edge-mlflow-sync)" e2e/E07-propagation.txt "kubectl create job --from=cronjob/edge-mlflow-sync e2e-vsync-1; psql model_versions" e_propagation e2e-vsync-1
  run_test E08 $P "Inference with the propagated version" e2e/E08-inference.txt "GET /version; POST /predict (port-forward svc/edge-fastapi-model)" e_inference
  run_test E09 $P "Edge metrics in the platform Prometheus (remote-write)" e2e/E09-metrics.txt "PromQL on platform-prometheus: model_predictions_total, model_info, ingest_messages_valid_total" e_metrics
  run_test E10 $P "Induced drift: shifted samples of machine cnc-02 through MQTT" e2e/E10-drift-injection.txt "mosquitto_pub 300 s of shifted samples (pod in edge)" e_drift_inject
  run_test E11 $P "Consolidation of the drifted data" e2e/E11-consolidation-2.txt "kubectl create job --from=cronjob/edge-postgresql-sync e2e-sync-2" e_consolidation e2e-sync-2
  run_test E12 $P "Evidently drift check and retraining recommendation" e2e/E12-drift.txt "kubectl create job --from=cronjob/platform-evidently-drift e2e-drift-1; psql retraining_recommendations" e_drift
  run_test E13 $P "Retraining job started by the recommendation" e2e/E13-retraining.txt "kubectl get jobs (platform-training-jobs-drift-*); kubectl wait" e_retraining
  run_test E14 $P "New version propagated to the edge and served" e2e/E14-new-version.txt "kubectl create job --from=cronjob/edge-mlflow-sync e2e-vsync-2; GET /version; POST /predict" e_new_version
  run_test E15 $P "MLOps events collected by Fluent Bit in Loki" e2e/E15-loki-events.txt "LogQL count_over_time({namespace=~\"edge|mlops\"} |= <event> [3h])" e_loki
  run_test E16 $P "Drift reports stored in the Evidently UI" e2e/E16-evidently-ui.txt "GET /api/projects (port-forward svc/platform-evidently)" e_evidently_ui
  cleanup_pf
}

# ===========================================================================
# 6. Traceability queries
# ===========================================================================
phase_trace() {
  log "=== 6. Traceability ==="
  python3 "${LAB}/tools/traceability.py" "${ROOT}" "${OUT}/trace" "${RESULTS}"
}

# ===========================================================================
# 7. Network policies
# ===========================================================================
nc_test() {
  # nc_test ID NAME NS HOST PORT EXPECT(allow|deny)
  local tid=$1 name=$2 ns=$3 host=$4 port=$5 expect=$6 out res
  out=$(tmp_pod "$ns" "lab-np-$(echo "$tid" | tr 'A-Z' 'a-z')" "${TOOLS_IMAGE}" \
        "if nc -z -w 5 ${host} ${port}; then echo CONNECTED; else echo BLOCKED; fi" 2>&1)
  { echo "# ${tid}: ${name}"; echo "\$ nc -z -w 5 ${host} ${port}   (pod in namespace ${ns})"; echo "${out}"; } > "${OUT}/netpol/${tid}.txt"
  if [[ "$expect" == allow ]]; then echo "$out" | grep -q CONNECTED && res=PASS || res=FAIL
  else echo "$out" | grep -q BLOCKED && res=PASS || res=FAIL; fi
  record "$tid" netpol "${name} (expected: ${expect})" "$res" 0 "netpol/${tid}.txt" \
    "nc -z -w 5 ${host} ${port} from a pod in namespace ${ns}" "$(echo "$out" | tail -1)"
}

phase_netpol() {
  log "=== 7. Network policies ==="
  kubectl get networkpolicy -A > "${OUT}/netpol/policies.txt"
  kubectl create namespace lab-np-outside --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  nc_test N01 "edge -> platform TimescaleDB (consolidation conduit)" edge platform-timescaledb.platform.svc.cluster.local 5432 allow
  nc_test N02 "edge -> MLflow (version sync conduit)" edge platform-mlflow.mlops.svc.cluster.local 5000 allow
  nc_test N03 "edge -> edge PostgreSQL (same namespace)" edge edge-postgresql.edge.svc.cluster.local 5432 allow
  nc_test N04 "edge -> MinIO (no conduit)" edge platform-minio.minio.svc.cluster.local 9000 deny
  nc_test N05 "edge -> Zammad (no conduit)" edge enterprise-zammad.helpdesk.svc.cluster.local 8080 deny
  nc_test N06 "namespace outside the catalog -> edge PostgreSQL (default deny ingress)" lab-np-outside edge-postgresql.edge.svc.cluster.local 5432 deny
  nc_test N07 "mlops -> MinIO (artefact conduit)" mlops platform-minio.minio.svc.cluster.local 9000 allow
  nc_test N08 "mlops -> Internet (default deny egress)" mlops 1.1.1.1 443 deny
  nc_test N09 "security -> platform PostgreSQL (Keycloak database)" security platform-postgresql.platform.svc.cluster.local 5432 allow
  nc_test N10 "helpdesk -> MLflow (no conduit)" helpdesk platform-mlflow.mlops.svc.cluster.local 5000 deny
  nc_test N11 "argocd -> Internet 443 (Git and Helm repositories)" argocd 1.1.1.1 443 allow
  nc_test N12 "logging -> Loki (log conduit)" logging platform-loki.monitoring.svc.cluster.local 3100 allow
  kubectl delete namespace lab-np-outside --wait=false >/dev/null
}

# ===========================================================================
finish() {
  snapshot state/final
  local ns; for ns in edge minio mlops security helpdesk argocd logging; do
    kubectl -n "$ns" delete pod -l lab-validation=test --ignore-not-found --wait=false >/dev/null 2>&1
  done
  # Guard: no key material in the evidence.
  if grep -rlE -- '-----BEGIN [A-Z ]*PRIVATE KEY|root_token|unseal_keys' "${OUT}" 2>/dev/null; then
    log "WARNING: possible secret material in the files above; review them before committing."
  fi
  python3 "${LAB}/tools/summarise.py" "${RESULTS}" "${OUT}/summary.md"
  log "Evidence in ${OUT}"
}

phase_on 1 && phase_environment
phase_on 2 && phase_preparation
phase_on 3 && phase_install
phase_on 4 && phase_smoke
phase_on 5 && phase_e2e
phase_on 6 && phase_trace
phase_on 7 && phase_netpol
finish
