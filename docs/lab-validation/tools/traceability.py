#!/usr/bin/env python3
"""Traceability queries: resources per ISO/IEC 42001 clause and per reference
architecture component, and label coverage per catalog namespace."""
import importlib.util, json, subprocess, sys
root, out, results = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("publish", f"{root}/infrastructure/publish.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
prefix = p.META_PREFIX

def count(selector, kinds="pods,svc,deploy,sts", ns=None):
    cmd = ["kubectl", "get", kinds] + (["-n", ns] if ns else ["-A"]) + ["-l", selector, "--no-headers"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return len([l for l in r.stdout.splitlines() if l.strip()]), " ".join(cmd)

rows = []
for key, label in list(p.ISO_REQS.items()) + list(p.COMPONENTS.items()):
    n, cmd = count(f"{prefix}/{key}")
    rows.append({"key": key, "label": label, "resources": n, "command": cmd})
n, cmd = count("iso42001=true")
rows.append({"key": "iso42001=true", "label": "all catalog resources", "resources": n, "command": cmd})

kinds = "pods,svc,deploy,sts,ds,cm,pvc,job,cronjob,sa,secret,ingress,networkpolicy"
coverage = {}
for ns in sorted({m["namespace"] for m in p.CHART_META.values()} - {"cattle-system"}):
    total, _ = count("lab-validation!=test,mlops-iso42001.cigip-upv.es/managed-by!=install.sh", kinds, ns)
    labelled, _ = count("iso42001=true", kinds, ns)
    coverage[ns] = {"objects": total, "with_iso42001_label": labelled}

json.dump({"queries": rows, "coverage_by_namespace": coverage}, open(f"{out}/traceability.json", "w"), indent=1)
with open(f"{out}/traceability.tsv", "w") as f:
    f.write("key\tlabel\tresources\tcommand\n")
    for r in rows:
        f.write(f"{r['key']}\t{r['label']}\t{r['resources']}\t{r['command']}\n")
with open(results, "a") as f:
    for r in rows:
        f.write(json.dumps({"id": f"T-{r['key']}", "phase": "traceability", "name": f"{r['key']} {r['label']}",
                            "result": "PASS" if r["resources"] > 0 else "FAIL", "seconds": 0,
                            "evidence": "trace/traceability.tsv", "command": r["command"],
                            "detail": f"{r['resources']} resources"}) + "\n")
print(open(f"{out}/traceability.tsv").read())
print(json.dumps(coverage, indent=1))
