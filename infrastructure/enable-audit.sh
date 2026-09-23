#!/usr/bin/env bash
# =============================================================================
# enable-audit.sh: enable Kubernetes API auditing on an existing K3s server
# (ISO/IEC 42001 B.6.2.8.1). New servers get it from setup-ubuntu.sh.
#
# Run on the K3s server node, as root:
#   sudo ./enable-audit.sh            # show what would change (dry run)
#   sudo ./enable-audit.sh --apply    # install the policy and restart k3s
#
# The restart briefly interrupts the API server; running pods are not
# affected. The previous config.yaml is kept as config.yaml.bak-<timestamp>.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
POLICY_SRC="${SCRIPT_DIR}/audit-policy.yaml"
POLICY_DST="/etc/rancher/k3s/audit-policy.yaml"
CONFIG="/etc/rancher/k3s/config.yaml"
LOG_DIR="/var/log/kubernetes/audit"
ARGS=(
  "audit-policy-file=${POLICY_DST}"
  "audit-log-path=${LOG_DIR}/audit.log"
  "audit-log-maxage=90"
  "audit-log-maxbackup=10"
  "audit-log-maxsize=100"
)

apply=false
[[ "${1:-}" == "--apply" ]] && apply=true

if grep -Eq '^kube-apiserver-arg:[[:space:]]*\[' "${CONFIG}" 2>/dev/null; then
  echo "${CONFIG} uses an inline list for kube-apiserver-arg; convert it to a block list first." >&2
  exit 1
fi

[[ $EUID -eq 0 ]] || { echo "Run as root (sudo)." >&2; exit 1; }
command -v k3s >/dev/null || { echo "k3s is not installed on this node." >&2; exit 1; }
systemctl is-enabled k3s >/dev/null 2>&1 || { echo "No k3s server service on this node (agent node?)." >&2; exit 1; }

missing=()
for a in "${ARGS[@]}"; do
  grep -qF -- "${a}" "${CONFIG}" 2>/dev/null || missing+=("${a}")
done

echo "Policy file : ${POLICY_DST} ($( [[ -f ${POLICY_DST} ]] && echo present || echo missing ))"
echo "Log dir     : ${LOG_DIR} ($( [[ -d ${LOG_DIR} ]] && echo present || echo missing ))"
echo "Config file : ${CONFIG}"
if [[ ${#missing[@]} -eq 0 ]]; then
  echo "kube-apiserver-arg entries already present."
else
  echo "kube-apiserver-arg entries to add:"
  printf '  - %s\n' "${missing[@]}"
fi

if ! ${apply}; then
  echo "Dry run: nothing changed. Re-run with --apply to install and restart k3s."
  exit 0
fi

mkdir -p "$(dirname "${POLICY_DST}")" "${LOG_DIR}"
install -m 0600 "${POLICY_SRC}" "${POLICY_DST}"
if [[ ${#missing[@]} -gt 0 ]]; then
  [[ -f ${CONFIG} ]] && cp -p "${CONFIG}" "${CONFIG}.bak-$(date +%Y%m%d%H%M%S)"
  touch "${CONFIG}"
  if grep -q '^kube-apiserver-arg:' "${CONFIG}"; then
    # Append to the existing list, right after its key.
    tmp="$(mktemp)"
    awk -v add="$(printf '  - "%s"\\n' "${missing[@]}")" '
      { print }
      /^kube-apiserver-arg:/ { printf "%s", add }' "${CONFIG}" > "${tmp}"
    cat "${tmp}" > "${CONFIG}" && rm -f "${tmp}"
  else
    {
      echo "kube-apiserver-arg:"
      printf '  - "%s"\n' "${missing[@]}"
    } >> "${CONFIG}"
  fi
fi

echo "Restarting k3s..."
systemctl restart k3s
for _ in $(seq 1 60); do
  k3s kubectl get --raw /readyz >/dev/null 2>&1 && break
  sleep 2
done
k3s kubectl get --raw /readyz >/dev/null && echo "API server ready."
sleep 5
if [[ -s "${LOG_DIR}/audit.log" ]]; then
  echo "Audit log is being written: $(wc -l < "${LOG_DIR}/audit.log") events so far."
else
  echo "WARNING: ${LOG_DIR}/audit.log is empty; check: journalctl -u k3s | grep -i audit" >&2
  exit 1
fi
