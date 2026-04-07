#!/usr/bin/env bash
# =============================================================================
# MLOps ISO 42001 K3S Catalog — Master Installation Script
#
# This script deploys the full reference architecture stack on K3S.
# Edit the variables below before running.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh [--edge-only | --platform-only | --enterprise-only | --all]
#
# Prerequisites:
#   - K3S cluster running (https://docs.k3s.io/quick-start)
#   - kubectl configured and pointing to the cluster
#   - helm v3 installed
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — EDIT THESE BEFORE RUNNING
# ---------------------------------------------------------------------------
CATALOG_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EDGE_NODE_LABEL="node-role.kubernetes.io/edge=true"
PLATFORM_NODE_LABEL="node-role.kubernetes.io/platform=true"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
info() { log "INFO  $*"; }
warn() { log "WARN  $*"; }
err()  { log "ERROR $*" >&2; }

wait_for_ready() {
  local ns=$1 label=$2 timeout=${3:-300}
  info "Waiting for pods with label=$label in namespace=$ns (timeout=${timeout}s)..."
  kubectl wait --for=condition=Ready pod -l "$label" -n "$ns" --timeout="${timeout}s" 2>/dev/null || \
    warn "Some pods in $ns may not be ready yet. Check with: kubectl get pods -n $ns"
}

# ---------------------------------------------------------------------------
# Add Helm repositories
# ---------------------------------------------------------------------------
add_repos() {
  info "Adding Helm repositories..."
  helm repo add bitnami     https://charts.bitnami.com/bitnami          2>/dev/null || true
  helm repo add prometheus   https://prometheus-community.github.io/helm-charts 2>/dev/null || true
  helm repo add grafana      https://grafana.github.io/helm-charts      2>/dev/null || true
  helm repo add fluent       https://fluent.github.io/helm-charts       2>/dev/null || true
  helm repo add falcosecurity https://falcosecurity.github.io/charts    2>/dev/null || true
  helm repo add minio        https://charts.min.io/                     2>/dev/null || true
  helm repo add timescale    https://charts.timescale.com               2>/dev/null || true
  helm repo add zammad       https://zammad.github.io/zammad-helm       2>/dev/null || true
  helm repo add rancher-latest https://releases.rancher.com/server-charts/latest 2>/dev/null || true
  helm repo update
}

# ---------------------------------------------------------------------------
# Phase 0: Infrastructure (namespaces, network policies, storage)
# ---------------------------------------------------------------------------
deploy_infrastructure() {
  info "=== Phase 0: Infrastructure ==="
  kubectl apply -f "$CATALOG_ROOT/infrastructure/00-namespaces.yaml"
  kubectl apply -f "$CATALOG_ROOT/infrastructure/01-network-policies.yaml"
  kubectl apply -f "$CATALOG_ROOT/infrastructure/02-storage-classes.yaml"
  info "Infrastructure deployed."
}

# ---------------------------------------------------------------------------
# Phase 1: Edge Tier
# ---------------------------------------------------------------------------
deploy_edge() {
  info "=== Phase 1: Edge Tier ==="

  # 1a. MQTT Broker (if needed)
  info "Deploying Mosquitto MQTT broker..."
  kubectl apply -f "$CATALOG_ROOT/catalog/edge/data-ingestion/mosquitto/manifests/mosquitto-deployment.yaml"

  # 1b. Edge PostgreSQL
  info "Deploying Edge PostgreSQL..."
  helm upgrade --install postgresql-edge bitnami/postgresql \
    --namespace edge \
    -f "$CATALOG_ROOT/catalog/edge/storage/postgresql/manifests/values.yaml"

  # 1c. Edge MongoDB (optional buffer)
  info "Deploying Edge MongoDB..."
  helm upgrade --install mongodb-edge bitnami/mongodb \
    --namespace edge \
    -f "$CATALOG_ROOT/catalog/edge/storage/mongodb/manifests/values.yaml"

  # 1d. Node-RED
  info "Deploying Node-RED..."
  helm upgrade --install node-red node-red/node-red \
    --namespace edge \
    -f "$CATALOG_ROOT/catalog/edge/data-ingestion/node-red/manifests/values.yaml" || \
    warn "Node-RED Helm chart may need manual repo. Check README."

  # 1e. FastAPI Model Server
  info "Deploying FastAPI Model Server..."
  kubectl apply -f "$CATALOG_ROOT/catalog/edge/ai-inference/fastapi-model/manifests/fastapi-deployment.yaml"

  # 1f. Fluent Bit (logging)
  info "Deploying Fluent Bit..."
  helm upgrade --install fluent-bit fluent/fluent-bit \
    --namespace logging \
    -f "$CATALOG_ROOT/catalog/edge/monitoring/fluent-bit/manifests/values.yaml"

  # 1g. Prometheus Agent
  info "Deploying Prometheus Agent (edge)..."
  helm upgrade --install prometheus-agent prometheus/prometheus \
    --namespace monitoring \
    -f "$CATALOG_ROOT/catalog/edge/monitoring/prometheus-agent/manifests/values.yaml"

  # 1h. Falco (security)
  info "Deploying Falco..."
  helm upgrade --install falco falcosecurity/falco \
    --namespace falco \
    -f "$CATALOG_ROOT/catalog/edge/security/falco/manifests/values.yaml"

  info "Edge tier deployed."
}

# ---------------------------------------------------------------------------
# Phase 2: Platform Tier
# ---------------------------------------------------------------------------
deploy_platform() {
  info "=== Phase 2: Platform Tier ==="

  # 2a. Platform PostgreSQL (shared metadata store)
  info "Deploying Platform PostgreSQL..."
  helm upgrade --install postgresql-platform bitnami/postgresql \
    --namespace platform \
    -f "$CATALOG_ROOT/catalog/platform/data-management/postgresql/manifests/values.yaml"
  wait_for_ready platform app.kubernetes.io/name=postgresql 120

  # 2b. MinIO (object storage)
  info "Deploying MinIO..."
  helm upgrade --install minio minio/minio \
    --namespace minio \
    -f "$CATALOG_ROOT/catalog/platform/data-management/minio/manifests/values.yaml"

  # 2c. TimescaleDB
  info "Deploying TimescaleDB..."
  helm upgrade --install timescaledb timescale/timescaledb-single \
    --namespace platform \
    -f "$CATALOG_ROOT/catalog/platform/data-management/timescaledb/manifests/values.yaml"

  # 2d. Prometheus + Alertmanager (kube-prometheus-stack)
  info "Deploying Prometheus stack..."
  helm upgrade --install kube-prometheus-stack prometheus/kube-prometheus-stack \
    --namespace monitoring \
    -f "$CATALOG_ROOT/catalog/platform/monitoring/prometheus/manifests/values.yaml"

  # 2e. Loki (log aggregation)
  info "Deploying Loki..."
  helm upgrade --install loki grafana/loki \
    --namespace monitoring \
    -f "$CATALOG_ROOT/catalog/platform/monitoring/loki/manifests/values.yaml"

  # 2f. Grafana
  info "Deploying Grafana..."
  helm upgrade --install grafana grafana/grafana \
    --namespace monitoring \
    -f "$CATALOG_ROOT/catalog/platform/monitoring/grafana/manifests/values.yaml"

  # 2g. MLflow
  info "Deploying MLflow..."
  helm upgrade --install mlflow community-charts/mlflow \
    --namespace mlops \
    -f "$CATALOG_ROOT/catalog/platform/ai-lifecycle/mlflow/manifests/values.yaml" || \
    warn "MLflow Helm chart may need manual installation. Check README."

  # 2h. Training CronJob
  info "Deploying Training Jobs..."
  kubectl apply -f "$CATALOG_ROOT/catalog/platform/ai-lifecycle/training-jobs/manifests/training-cronjob.yaml"

  # 2i. Rancher (optional)
  # info "Deploying Rancher..."
  # helm upgrade --install rancher rancher-latest/rancher \
  #   --namespace cattle-system \
  #   -f "$CATALOG_ROOT/catalog/platform/orchestration/rancher/manifests/values.yaml"

  info "Platform tier deployed."
}

# ---------------------------------------------------------------------------
# Phase 3: Enterprise Tier
# ---------------------------------------------------------------------------
deploy_enterprise() {
  info "=== Phase 3: Enterprise Tier ==="

  # 3a. Keycloak (IAM)
  info "Deploying Keycloak..."
  helm upgrade --install keycloak bitnami/keycloak \
    --namespace security \
    -f "$CATALOG_ROOT/catalog/enterprise/access-management/keycloak/manifests/values.yaml"

  # 3b. Zammad (helpdesk)
  info "Deploying Zammad..."
  helm upgrade --install zammad zammad/zammad \
    --namespace helpdesk \
    -f "$CATALOG_ROOT/catalog/enterprise/helpdesk/zammad/manifests/values.yaml"

  info "Enterprise tier deployed."
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  local target="${1:---all}"

  info "MLOps ISO 42001 K3S Catalog — Installation"
  info "Target: $target"
  info "Catalog root: $CATALOG_ROOT"
  echo ""

  add_repos

  case "$target" in
    --edge-only)      deploy_infrastructure; deploy_edge ;;
    --platform-only)  deploy_infrastructure; deploy_platform ;;
    --enterprise-only) deploy_infrastructure; deploy_enterprise ;;
    --all)            deploy_infrastructure; deploy_edge; deploy_platform; deploy_enterprise ;;
    *)                err "Unknown target: $target"; echo "Usage: $0 [--edge-only|--platform-only|--enterprise-only|--all]"; exit 1 ;;
  esac

  echo ""
  info "=== Installation Complete ==="
  info "Verify with: kubectl get pods --all-namespaces"
  info ""
  info "Next steps:"
  info "  1. Update all 'CHANGE_ME' passwords in Kubernetes Secrets"
  info "  2. Configure DNS entries for *.edge.local, *.platform.local, *.enterprise.local"
  info "  3. Complete ISO/IEC 42001 compliance questionnaire"
  info "  4. Store deployment documentation in MinIO (iso42001-docs bucket)"
}

main "$@"
