#!/usr/bin/env python3
"""Sum of the CPU and memory requests of the catalog versus the free
allocatable resources of the cluster (exit code 3 when it does not fit)."""
import glob, json, os, re, shutil, subprocess, sys, tempfile
import yaml

root, out = sys.argv[1:3]

def qty(v, mem):
    v = str(v)
    if mem:
        m = re.match(r"^([0-9.]+)([A-Za-z]*)$", v)
        n, u = float(m.group(1)), m.group(2)
        return n * {"": 1, "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "K": 1e3, "M": 1e6, "G": 1e9}[u]
    return float(v[:-1]) / 1000 if v.endswith("m") else float(v)

def requests_of(spec, replicas):
    c = m = 0.0
    for ctr in spec.get("containers", []):
        rq = (ctr.get("resources") or {}).get("requests") or {}
        c += replicas * qty(rq.get("cpu", "0"), False)
        m += replicas * qty(rq.get("memory", "0"), True)
    return c, m

nodes = json.loads(subprocess.run(["kubectl", "get", "nodes", "-o", "json"], capture_output=True, text=True).stdout)["items"]
n_nodes = len(nodes)
per, tot_c, tot_m = {}, 0.0, 0.0
for cy in sorted(glob.glob(f"{root}/catalog/*/*/*/manifests/Chart.yaml")):
    name = yaml.safe_load(open(cy))["name"]
    if name == "platform-rancher":
        continue
    tmp = tempfile.mkdtemp()
    try:
        shutil.copytree(os.path.dirname(cy), f"{tmp}/c", ignore=shutil.ignore_patterns("charts"))
        subprocess.run(["helm", "dependency", "build", f"{tmp}/c"], capture_output=True)
        vals = [f"{root}/docs/lab-validation/lab-values/{name}.yaml"]
        args = ["helm", "template", name, f"{tmp}/c"] + sum((["-f", v] for v in vals if os.path.exists(v)), [])
        rendered = subprocess.run(args, capture_output=True, text=True).stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    c = m = 0.0
    for doc in yaml.safe_load_all(rendered):
        if not isinstance(doc, dict):
            continue
        kind, spec = doc.get("kind"), doc.get("spec") or {}
        if kind in ("Deployment", "StatefulSet"):
            dc, dm = requests_of(spec["template"]["spec"], spec.get("replicas", 1) or 0)
        elif kind == "DaemonSet":
            dc, dm = requests_of(spec["template"]["spec"], n_nodes)
        else:
            continue
        c, m = c + dc, m + dm
    per[name] = {"cpu": round(c, 2), "memory_gib": round(m / 2**30, 2)}
    tot_c, tot_m = tot_c + c, tot_m + m

alloc_c = sum(qty(n["status"]["allocatable"]["cpu"], False) for n in nodes)
alloc_m = sum(qty(n["status"]["allocatable"]["memory"], True) for n in nodes)
pods = json.loads(subprocess.run(["kubectl", "get", "pods", "-A", "-o", "json"], capture_output=True, text=True).stdout)["items"]
used_c = used_m = 0.0
for p in pods:
    if p["status"].get("phase") in ("Succeeded", "Failed"):
        continue
    if (p["metadata"].get("labels") or {}).get("iso42001") == "true":
        continue  # already installed catalog pods are part of the estimate
    c, m = requests_of(p["spec"], 1)
    used_c, used_m = used_c + c, used_m + m

res = {"nodes": n_nodes,
       "catalog_requests_cpu": round(tot_c, 2), "catalog_requests_memory_gib": round(tot_m / 2**30, 2),
       "allocatable_cpu": round(alloc_c, 2), "allocatable_memory_gib": round(alloc_m / 2**30, 2),
       "requested_by_other_pods_cpu": round(used_c, 2), "requested_by_other_pods_memory_gib": round(used_m / 2**30, 2),
       "free_cpu": round(alloc_c - used_c, 2), "free_memory_gib": round((alloc_m - used_m) / 2**30, 2)}
res["fits"] = res["free_cpu"] >= res["catalog_requests_cpu"] and res["free_memory_gib"] >= res["catalog_requests_memory_gib"]
res["per_chart"] = dict(sorted(per.items(), key=lambda kv: -kv[1]["memory_gib"]))
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "per_chart"}, indent=1))
print("largest requests:", list(res["per_chart"].items())[:6])
sys.exit(0 if res["fits"] else 3)
