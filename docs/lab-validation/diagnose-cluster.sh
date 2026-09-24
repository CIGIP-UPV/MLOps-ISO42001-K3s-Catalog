#!/usr/bin/env bash
# =============================================================================
# diagnose-cluster.sh: read-only diagnosis of a laboratory node before the
# validation run (docs/lab-validation/LAB_RUN_INSTRUCTIONS.md).
#
# Run it as root on every node (the K3s server and the agents):
#   sudo -E ./docs/lab-validation/diagnose-cluster.sh
# On the server it also inspects the cluster (nodes, real usage, namespaces,
# releases, CRDs, network policies, Internet access from a pod and the Docker
# Hub pull limit). The only change is a temporary pod that is removed at once.
# Lines with tokens, secrets or passwords are filtered out.
#
# Output: docs/lab-validation/raw/diag-<host>-<timestamp>.txt
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${ROOT}/docs/lab-validation/raw/diag-$(hostname)-$(date +%Y%m%dT%H%M%S).txt"
mkdir -p "$(dirname "${OUT}")"
[[ -z "${KUBECONFIG:-}" && -r /etc/rancher/k3s/k3s.yaml ]] && export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

section() { printf '\n## %s\n' "$1"; }
nosecrets() { grep -viE 'token|secret|password|passwd'; }

{
  section "host"
  hostname; date -u; uname -r
  grep PRETTY_NAME /etc/os-release
  nproc; free -h
  df -h / /var/lib/rancher 2>/dev/null
  section "BTF (Falco modern_ebpf)"
  ls -l /sys/kernel/btf/vmlinux 2>&1
  section "time sync"
  timedatectl | grep -E 'synchronized|NTP'
  section "k3s"
  k3s --version 2>&1 | head -1
  for s in k3s k3s-agent; do printf '%s: %s\n' "$s" "$(systemctl is-active "$s" 2>/dev/null)"; done
  section "k3s config (filtered)"
  nosecrets < /etc/rancher/k3s/config.yaml 2>&1
  for s in k3s k3s-agent; do systemctl cat "$s" 2>/dev/null | grep -A15 ExecStart= | nosecrets; done
  section "registries.yaml"
  ls -l /etc/rancher/k3s/registries.yaml 2>&1
  section "audit policy"
  ls -l /etc/rancher/k3s/audit-policy.yaml /var/log/kubernetes/audit 2>&1

  if kubectl get nodes >/dev/null 2>&1; then
    section "nodes"; kubectl get nodes -o wide
    section "taints"; kubectl get nodes -o custom-columns=NODE:.metadata.name,TAINTS:.spec.taints
    section "edge label"; kubectl get nodes -L node-role.kubernetes.io/edge
    section "real usage"; kubectl top nodes 2>&1; kubectl top pods -A --sort-by=memory 2>&1 | head -30
    section "pods per node"; kubectl get pods -A -o wide --no-headers | awk '{print $8}' | sort | uniq -c
    section "requests per node"; kubectl describe nodes | grep -A9 'Allocated resources'
    section "namespaces"; kubectl get ns
    section "helm"; helm version --short 2>&1; helm list -A 2>&1
    section "CRDs of interest"; kubectl get crd -o name | grep -E 'monitoring.coreos.com|cert-manager.io|argoproj.io|falco' || echo none
    section "storage classes"; kubectl get storageclass
    section "Rancher"; kubectl -n cattle-system get pods -o wide 2>&1
    section "cert-manager"; kubectl get deploy -A -o wide 2>/dev/null | grep -i cert-manager || echo none
    section "network policies"; kubectl get networkpolicy -A 2>&1
    section "Internet from a pod"
    kubectl run diag-net --rm -i --restart=Never --image=public.ecr.aws/docker/library/busybox:1.36 --command -- sh -c \
      'nslookup github.com >/dev/null 2>&1 && echo DNS-OK || echo DNS-FAIL
       nc -z -w5 github.com 443 && echo GITHUB-OK || echo GITHUB-FAIL
       nc -z -w5 registry-1.docker.io 443 && echo DOCKERHUB-OK || echo DOCKERHUB-FAIL' 2>&1 | grep -E 'OK|FAIL|rror'
    section "Docker Hub anonymous pull limit"
    python3 -c 'import json, urllib.request
t = json.load(urllib.request.urlopen("https://auth.docker.io/token?service=registry.docker.io&scope=repository:ratelimitpreview/test:pull"))["token"]
r = urllib.request.Request("https://registry-1.docker.io/v2/ratelimitpreview/test/manifests/latest", method="HEAD", headers={"Authorization": "Bearer " + t})
h = urllib.request.urlopen(r).headers
print("limit:", h.get("ratelimit-limit"), "remaining:", h.get("ratelimit-remaining"))' 2>&1
  else
    section "cluster"; echo "kubectl cannot reach the cluster from this node (expected on agents)"
  fi
} 2>&1 | tee "${OUT}"

echo
echo "Saved to ${OUT}"
