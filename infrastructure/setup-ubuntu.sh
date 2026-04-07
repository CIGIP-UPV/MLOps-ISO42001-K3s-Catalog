#!/usr/bin/env bash
# =============================================================================
# MLOps ISO 42001 K3S Catalog — Ubuntu 24.04 Environment Setup
#
# Prepares a fresh Ubuntu 24.04 LTS server for deploying the reference
# architecture. Installs and configures:
#   1. System prerequisites and kernel parameters
#   2. Container runtime dependencies
#   3. K3S (lightweight Kubernetes)
#   4. Helm v3 (package manager)
#   5. Rancher CLI (cluster management)
#   6. Additional tools (kubectl aliases, k9s, jq, yq)
#
# Usage:
#   chmod +x setup-ubuntu.sh
#
#   # Full setup (K3S server + all tools):
#   ./setup-ubuntu.sh --server
#
#   # K3S agent node (joins existing cluster):
#   ./setup-ubuntu.sh --agent --server-url https://<server-ip>:6443 --token <node-token>
#
#   # Only install tools (no K3S):
#   ./setup-ubuntu.sh --tools-only
#
# Requirements:
#   - Ubuntu 24.04 LTS (amd64 or arm64)
#   - Root or sudo access
#   - Internet connectivity
#
# ISO/IEC 42001 Note:
#   This script supports B.6.2.5.1 (Deployment Plan) by providing a
#   reproducible, auditable environment setup process.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — EDIT THESE BEFORE RUNNING
# ---------------------------------------------------------------------------
K3S_VERSION="${K3S_VERSION:-v1.30.2+k3s1}"
HELM_VERSION="${HELM_VERSION:-v3.15.3}"
RANCHER_CLI_VERSION="${RANCHER_CLI_VERSION:-v2.9.0}"
K9S_VERSION="${K9S_VERSION:-v0.32.5}"

# K3S server options
K3S_CLUSTER_CIDR="${K3S_CLUSTER_CIDR:-10.42.0.0/16}"
K3S_SERVICE_CIDR="${K3S_SERVICE_CIDR:-10.43.0.0/16}"

# K3S agent options (only for --agent mode)
K3S_SERVER_URL="${K3S_SERVER_URL:-}"
K3S_TOKEN="${K3S_TOKEN:-}"

# Node role label (used by the catalog for scheduling)
NODE_ROLE="${NODE_ROLE:-}"    # Set to 'edge', 'platform', or leave empty

# ---------------------------------------------------------------------------
# Colours and logging
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $*"; }
info() { echo -e "${GREEN}[$(date '+%H:%M:%S')] ✓${NC} $*"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] ⚠${NC} $*"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ✗${NC} $*" >&2; }

check_root() {
  if [[ $EUID -ne 0 ]]; then
    err "This script must be run as root or with sudo."
    exit 1
  fi
}

check_ubuntu() {
  if ! grep -qi "ubuntu" /etc/os-release 2>/dev/null; then
    err "This script is designed for Ubuntu. Detected: $(cat /etc/os-release | grep PRETTY_NAME)"
    exit 1
  fi
  local version
  version=$(grep VERSION_ID /etc/os-release | cut -d'"' -f2)
  log "Detected Ubuntu $version"
}

detect_arch() {
  ARCH=$(uname -m)
  case "$ARCH" in
    x86_64)  ARCH_ALT="amd64" ;;
    aarch64) ARCH_ALT="arm64" ;;
    *)       err "Unsupported architecture: $ARCH"; exit 1 ;;
  esac
  log "Architecture: $ARCH ($ARCH_ALT)"
}

# ---------------------------------------------------------------------------
# Phase 1: System prerequisites
# ---------------------------------------------------------------------------
install_prerequisites() {
  log "=== Phase 1: System Prerequisites ==="

  log "Updating package index..."
  apt-get update -qq

  log "Installing base packages..."
  apt-get install -y -qq \
    apt-transport-https \
    ca-certificates \
    curl \
    wget \
    gnupg \
    lsb-release \
    software-properties-common \
    git \
    jq \
    unzip \
    open-iscsi \
    nfs-common \
    bash-completion \
    net-tools \
    dnsutils \
    htop \
    iotop \
    sysstat \
    logrotate \
    fail2ban \
    ufw \
    > /dev/null

  info "Base packages installed."
}

# ---------------------------------------------------------------------------
# Phase 2: Kernel parameters and system tuning
# ---------------------------------------------------------------------------
configure_system() {
  log "=== Phase 2: System Configuration ==="

  # Kernel modules required by K3S and container networking
  log "Loading kernel modules..."
  cat > /etc/modules-load.d/k3s.conf <<'EOF'
overlay
br_netfilter
ip_tables
ip_vs
ip_vs_rr
ip_vs_wrr
ip_vs_sh
nf_conntrack
EOF

  modprobe overlay
  modprobe br_netfilter
  modprobe ip_vs
  modprobe ip_vs_rr
  modprobe ip_vs_wrr
  modprobe ip_vs_sh
  modprobe nf_conntrack
  info "Kernel modules loaded."

  # Sysctl parameters for Kubernetes networking
  log "Configuring kernel parameters..."
  cat > /etc/sysctl.d/99-k3s.conf <<'EOF'
# IPv4 forwarding (required for pod networking)
net.ipv4.ip_forward = 1

# Bridge netfilter (required for iptables-based service routing)
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1

# Increase inotify limits (for large number of pods/containers)
fs.inotify.max_user_watches  = 524288
fs.inotify.max_user_instances = 512

# Increase file descriptor limits
fs.file-max = 2097152

# Increase connection tracking table size
net.netfilter.nf_conntrack_max = 131072

# Increase ARP cache size (for large clusters)
net.ipv4.neigh.default.gc_thresh1 = 4096
net.ipv4.neigh.default.gc_thresh2 = 8192
net.ipv4.neigh.default.gc_thresh3 = 16384

# Reduce swap usage (Kubernetes works better without swap)
vm.swappiness = 10

# Increase PID limit
kernel.pid_max = 65536
EOF

  sysctl --system > /dev/null 2>&1
  info "Kernel parameters configured."

  # Disable swap (Kubernetes requirement)
  log "Disabling swap..."
  swapoff -a || true
  sed -i '/\sswap\s/s/^/#/' /etc/fstab
  info "Swap disabled."

  # Configure open file limits
  log "Configuring ulimits..."
  cat > /etc/security/limits.d/99-k3s.conf <<'EOF'
* soft nofile 65536
* hard nofile 65536
* soft nproc  65536
* hard nproc  65536
EOF
  info "Ulimits configured."

  # Enable and configure iscsid (for Longhorn storage, if used)
  systemctl enable --now iscsid 2>/dev/null || true
  info "iSCSI daemon enabled."
}

# ---------------------------------------------------------------------------
# Phase 3: Firewall
# ---------------------------------------------------------------------------
configure_firewall() {
  log "=== Phase 3: Firewall Configuration ==="

  log "Configuring UFW rules for K3S..."

  # Allow SSH
  ufw allow 22/tcp comment "SSH" > /dev/null

  # K3S API server
  ufw allow 6443/tcp comment "K3S API server" > /dev/null

  # Flannel VXLAN (K3S default CNI)
  ufw allow 8472/udp comment "K3S Flannel VXLAN" > /dev/null

  # Kubelet metrics
  ufw allow 10250/tcp comment "Kubelet metrics" > /dev/null

  # Traefik Ingress (K3S default)
  ufw allow 80/tcp comment "Traefik HTTP" > /dev/null
  ufw allow 443/tcp comment "Traefik HTTPS" > /dev/null

  # NodePort range (for services exposed via NodePort)
  ufw allow 30000:32767/tcp comment "Kubernetes NodePort range" > /dev/null

  # Etcd (for multi-server HA setups)
  ufw allow 2379:2380/tcp comment "Etcd client/peer" > /dev/null

  # MQTT (if edge node with Mosquitto)
  ufw allow 1883/tcp comment "MQTT" > /dev/null

  # Enable UFW (non-interactive)
  echo "y" | ufw enable > /dev/null 2>&1 || true
  info "Firewall configured and enabled."
}

# ---------------------------------------------------------------------------
# Phase 4: Install K3S
# ---------------------------------------------------------------------------
install_k3s_server() {
  log "=== Phase 4: K3S Server Installation ==="

  if command -v k3s &>/dev/null; then
    warn "K3S is already installed: $(k3s --version)"
    return 0
  fi

  log "Installing K3S ${K3S_VERSION} (server mode)..."

  curl -sfL https://get.k3s.io | \
    INSTALL_K3S_VERSION="$K3S_VERSION" \
    INSTALL_K3S_EXEC="server" \
    K3S_KUBECONFIG_MODE="644" \
    sh -s - \
      --cluster-cidr="$K3S_CLUSTER_CIDR" \
      --service-cidr="$K3S_SERVICE_CIDR" \
      --write-kubeconfig-mode=644 \
      --disable=servicelb \
      --kube-apiserver-arg="audit-log-path=/var/log/kubernetes/audit.log" \
      --kube-apiserver-arg="audit-log-maxage=90" \
      --kube-apiserver-arg="audit-log-maxbackup=10" \
      --kube-apiserver-arg="audit-log-maxsize=100"

  # Create audit log directory
  mkdir -p /var/log/kubernetes

  # Wait for K3S to be ready
  log "Waiting for K3S to be ready..."
  local retries=30
  until kubectl get nodes &>/dev/null || [[ $retries -eq 0 ]]; do
    sleep 2
    retries=$((retries - 1))
  done

  if kubectl get nodes &>/dev/null; then
    info "K3S server installed and running."
    kubectl get nodes
  else
    err "K3S did not start within expected time. Check: journalctl -u k3s"
    exit 1
  fi

  # Configure kubectl for current user
  setup_kubeconfig
}

install_k3s_agent() {
  log "=== Phase 4: K3S Agent Installation ==="

  if [[ -z "$K3S_SERVER_URL" ]] || [[ -z "$K3S_TOKEN" ]]; then
    err "Agent mode requires --server-url and --token."
    err "Get the token from the server: cat /var/lib/rancher/k3s/server/node-token"
    exit 1
  fi

  if command -v k3s &>/dev/null; then
    warn "K3S is already installed: $(k3s --version)"
    return 0
  fi

  log "Installing K3S ${K3S_VERSION} (agent mode)..."
  log "  Server URL: $K3S_SERVER_URL"

  curl -sfL https://get.k3s.io | \
    INSTALL_K3S_VERSION="$K3S_VERSION" \
    K3S_URL="$K3S_SERVER_URL" \
    K3S_TOKEN="$K3S_TOKEN" \
    sh -

  info "K3S agent installed. Node will join the cluster."
}

# ---------------------------------------------------------------------------
# Phase 5: kubectl configuration
# ---------------------------------------------------------------------------
setup_kubeconfig() {
  log "Configuring kubectl..."

  # Set KUBECONFIG for root
  export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

  # Add KUBECONFIG to profile for persistence
  if ! grep -q "KUBECONFIG" /etc/profile.d/k3s.sh 2>/dev/null; then
    cat > /etc/profile.d/k3s.sh <<'EOF'
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# kubectl aliases
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgpa='kubectl get pods --all-namespaces'
alias kgs='kubectl get svc'
alias kgn='kubectl get nodes'
alias kga='kubectl get all'
alias kd='kubectl describe'
alias kl='kubectl logs'
alias klf='kubectl logs -f'
alias kns='kubectl config set-context --current --namespace'

# Helm aliases
alias h='helm'
alias hls='helm list --all-namespaces'
alias hst='helm status'
EOF
  fi

  # Enable kubectl bash completion
  if command -v kubectl &>/dev/null; then
    kubectl completion bash > /etc/bash_completion.d/kubectl 2>/dev/null || true
  fi

  # Copy kubeconfig for the invoking user (if running via sudo)
  if [[ -n "${SUDO_USER:-}" ]]; then
    local user_home
    user_home=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    mkdir -p "$user_home/.kube"
    cp /etc/rancher/k3s/k3s.yaml "$user_home/.kube/config"
    chown -R "$SUDO_USER":"$SUDO_USER" "$user_home/.kube"
    info "Kubeconfig copied to $user_home/.kube/config"
  fi

  info "kubectl configured with aliases."
}

# ---------------------------------------------------------------------------
# Phase 6: Helm
# ---------------------------------------------------------------------------
install_helm() {
  log "=== Phase 6: Helm Installation ==="

  if command -v helm &>/dev/null; then
    warn "Helm is already installed: $(helm version --short)"
    return 0
  fi

  log "Installing Helm ${HELM_VERSION}..."
  curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | \
    DESIRED_VERSION="$HELM_VERSION" bash

  # Bash completion
  helm completion bash > /etc/bash_completion.d/helm 2>/dev/null || true

  info "Helm installed: $(helm version --short)"
}

# ---------------------------------------------------------------------------
# Phase 7: Rancher CLI
# ---------------------------------------------------------------------------
install_rancher_cli() {
  log "=== Phase 7: Rancher CLI Installation ==="

  if command -v rancher &>/dev/null; then
    warn "Rancher CLI is already installed: $(rancher --version)"
    return 0
  fi

  local rancher_url="https://github.com/rancher/cli/releases/download/${RANCHER_CLI_VERSION}/rancher-linux-${ARCH_ALT}-${RANCHER_CLI_VERSION}.tar.gz"

  log "Downloading Rancher CLI ${RANCHER_CLI_VERSION}..."
  curl -fsSL "$rancher_url" -o /tmp/rancher-cli.tar.gz

  tar -xzf /tmp/rancher-cli.tar.gz -C /tmp/
  mv "/tmp/rancher-${RANCHER_CLI_VERSION}/rancher" /usr/local/bin/rancher
  chmod +x /usr/local/bin/rancher
  rm -rf /tmp/rancher-cli.tar.gz "/tmp/rancher-${RANCHER_CLI_VERSION}"

  # Bash completion
  rancher completion bash > /etc/bash_completion.d/rancher 2>/dev/null || true

  info "Rancher CLI installed: $(rancher --version)"
}

# ---------------------------------------------------------------------------
# Phase 8: Additional tools
# ---------------------------------------------------------------------------
install_additional_tools() {
  log "=== Phase 8: Additional Tools ==="

  # yq — YAML processor (useful for editing values.yaml)
  if ! command -v yq &>/dev/null; then
    log "Installing yq..."
    curl -fsSL "https://github.com/mikefarah/yq/releases/latest/download/yq_linux_${ARCH_ALT}" \
      -o /usr/local/bin/yq
    chmod +x /usr/local/bin/yq
    info "yq installed."
  fi

  # k9s — TUI for Kubernetes cluster management
  if ! command -v k9s &>/dev/null; then
    log "Installing k9s ${K9S_VERSION}..."
    local k9s_arch="$ARCH_ALT"
    curl -fsSL "https://github.com/derailed/k9s/releases/download/${K9S_VERSION}/k9s_Linux_${k9s_arch}.tar.gz" \
      -o /tmp/k9s.tar.gz
    tar -xzf /tmp/k9s.tar.gz -C /usr/local/bin/ k9s
    chmod +x /usr/local/bin/k9s
    rm -f /tmp/k9s.tar.gz
    info "k9s installed."
  fi

  info "Additional tools installed."
}

# ---------------------------------------------------------------------------
# Phase 9: Node labels
# ---------------------------------------------------------------------------
apply_node_labels() {
  log "=== Phase 9: Node Labels ==="

  if [[ -z "$NODE_ROLE" ]]; then
    warn "No NODE_ROLE specified. Skipping node labels."
    warn "Label manually with:"
    warn "  kubectl label node \$(hostname) node-role.kubernetes.io/edge=true"
    warn "  kubectl label node \$(hostname) node-role.kubernetes.io/platform=true"
    return 0
  fi

  local node_name
  node_name=$(hostname)

  log "Labelling node $node_name with role=$NODE_ROLE..."
  kubectl label node "$node_name" "node-role.kubernetes.io/${NODE_ROLE}=true" --overwrite
  info "Node labelled: node-role.kubernetes.io/${NODE_ROLE}=true"
}

# ---------------------------------------------------------------------------
# Phase 10: Verification
# ---------------------------------------------------------------------------
verify_installation() {
  log "=== Phase 10: Verification ==="

  echo ""
  log "Installed components:"

  # K3S
  if command -v k3s &>/dev/null; then
    info "K3S:         $(k3s --version 2>/dev/null | head -1)"
  else
    warn "K3S:         Not installed"
  fi

  # kubectl
  if command -v kubectl &>/dev/null; then
    info "kubectl:     $(kubectl version --client --short 2>/dev/null || kubectl version --client 2>/dev/null | head -1)"
  else
    warn "kubectl:     Not installed"
  fi

  # Helm
  if command -v helm &>/dev/null; then
    info "Helm:        $(helm version --short 2>/dev/null)"
  else
    warn "Helm:        Not installed"
  fi

  # Rancher CLI
  if command -v rancher &>/dev/null; then
    info "Rancher CLI: $(rancher --version 2>/dev/null)"
  else
    warn "Rancher CLI: Not installed"
  fi

  # k9s
  if command -v k9s &>/dev/null; then
    info "k9s:         $(k9s version --short 2>/dev/null || echo 'installed')"
  else
    warn "k9s:         Not installed"
  fi

  # yq
  if command -v yq &>/dev/null; then
    info "yq:          $(yq --version 2>/dev/null)"
  else
    warn "yq:          Not installed"
  fi

  # jq
  if command -v jq &>/dev/null; then
    info "jq:          $(jq --version 2>/dev/null)"
  else
    warn "jq:          Not installed"
  fi

  # Cluster status
  echo ""
  if kubectl get nodes &>/dev/null 2>&1; then
    log "Cluster status:"
    kubectl get nodes -o wide
    echo ""
    log "System pods:"
    kubectl get pods -n kube-system
  fi

  # Print node token (for agent nodes to join)
  if [[ -f /var/lib/rancher/k3s/server/node-token ]]; then
    echo ""
    log "Agent join token (save this for adding agent nodes):"
    echo "  $(cat /var/lib/rancher/k3s/server/node-token)"
    echo ""
    log "To add an agent node, run on the other machine:"
    echo "  ./setup-ubuntu.sh --agent --server-url https://$(hostname -I | awk '{print $1}'):6443 --token <token>"
  fi
}

# ---------------------------------------------------------------------------
# Print summary and next steps
# ---------------------------------------------------------------------------
print_summary() {
  echo ""
  echo "==========================================================================="
  echo "  MLOps ISO 42001 K3S Catalog — Setup Complete"
  echo "==========================================================================="
  echo ""
  echo "  Next steps:"
  echo ""
  echo "  1. Log out and back in (or source /etc/profile.d/k3s.sh) to load aliases"
  echo ""
  echo "  2. Label this node for the catalog tier scheduling:"
  echo "     kubectl label node \$(hostname) node-role.kubernetes.io/edge=true"
  echo "     kubectl label node \$(hostname) node-role.kubernetes.io/platform=true"
  echo ""
  echo "  3. Deploy the catalog infrastructure:"
  echo "     cd <catalog-root>/infrastructure"
  echo "     ./install.sh --all"
  echo ""
  echo "  4. (Optional) Connect Rancher CLI to a Rancher server:"
  echo "     rancher login https://rancher.platform.local --token <bearer-token>"
  echo ""
  echo "  5. (Optional) Open the k9s dashboard:"
  echo "     k9s"
  echo ""
  echo "==========================================================================="
}

# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------
parse_args() {
  MODE=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --server)
        MODE="server"
        shift
        ;;
      --agent)
        MODE="agent"
        shift
        ;;
      --tools-only)
        MODE="tools"
        shift
        ;;
      --server-url)
        K3S_SERVER_URL="$2"
        shift 2
        ;;
      --token)
        K3S_TOKEN="$2"
        shift 2
        ;;
      --node-role)
        NODE_ROLE="$2"
        shift 2
        ;;
      --help|-h)
        echo "Usage: $0 [--server | --agent | --tools-only] [options]"
        echo ""
        echo "Modes:"
        echo "  --server        Install K3S server + all tools (default)"
        echo "  --agent         Install K3S agent (joins existing cluster)"
        echo "  --tools-only    Install only tools (helm, rancher, k9s, yq)"
        echo ""
        echo "Options:"
        echo "  --server-url    K3S server URL (required for --agent)"
        echo "  --token         K3S node token (required for --agent)"
        echo "  --node-role     Node role label: edge, platform (optional)"
        echo ""
        echo "Environment variables:"
        echo "  K3S_VERSION           K3S version (default: $K3S_VERSION)"
        echo "  HELM_VERSION          Helm version (default: $HELM_VERSION)"
        echo "  RANCHER_CLI_VERSION   Rancher CLI version (default: $RANCHER_CLI_VERSION)"
        echo "  K3S_CLUSTER_CIDR      Pod CIDR (default: $K3S_CLUSTER_CIDR)"
        echo "  K3S_SERVICE_CIDR      Service CIDR (default: $K3S_SERVICE_CIDR)"
        exit 0
        ;;
      *)
        err "Unknown argument: $1"
        echo "Use --help for usage information."
        exit 1
        ;;
    esac
  done

  # Default to server mode
  MODE="${MODE:-server}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  parse_args "$@"

  echo ""
  echo "==========================================================================="
  echo "  MLOps ISO 42001 K3S Catalog — Ubuntu 24.04 Setup"
  echo "  Mode: $MODE"
  echo "==========================================================================="
  echo ""

  check_root
  check_ubuntu
  detect_arch

  case "$MODE" in
    server)
      install_prerequisites
      configure_system
      configure_firewall
      install_k3s_server
      install_helm
      install_rancher_cli
      install_additional_tools
      apply_node_labels
      verify_installation
      print_summary
      ;;
    agent)
      install_prerequisites
      configure_system
      configure_firewall
      install_k3s_agent
      install_helm
      install_rancher_cli
      install_additional_tools
      verify_installation
      print_summary
      ;;
    tools)
      install_prerequisites
      detect_arch
      install_helm
      install_rancher_cli
      install_additional_tools
      verify_installation
      ;;
    *)
      err "Invalid mode: $MODE"
      exit 1
      ;;
  esac
}

main "$@"
