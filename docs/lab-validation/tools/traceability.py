#!/usr/bin/env python3
"""Traceability queries: resources per ISO/IEC 42001 clause and per reference
architecture component, and label coverage per catalog namespace (objects of
Helm releases that are not the catalog's, in a shared namespace, are counted
apart)."""
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
catalog_releases = set(p.CHART_META)
coverage = {}
for ns in sorted({m["namespace"] for m in p.CHART_META.values()} - {"cattle-system"}):
    r = subprocess.run(["kubectl", "get", kinds, "-n", ns, "-o", "json",
                        "-l", "lab-validation!=test,mlops-iso42001.cigip-upv.es/managed-by!=install.sh"],
                       capture_output=True, text=True)
    items = json.loads(r.stdout or '{"items": []}')["items"]
    c = {"objects": 0, "with_iso42001_label": 0, "other_releases": 0}
    for o in items:
        md = o["metadata"]
        release = (md.get("annotations") or {}).get("meta.helm.sh/release-name")
        owners = [x.get("kind") for x in md.get("ownerReferences") or []]
        if (md.get("labels") or {}).get("iso42001") == "true":
            c["with_iso42001_label"] += 1
        elif release and release not in catalog_releases:
            c["other_releases"] += 1   # objects of releases that are not the catalog's
            continue
        c["objects"] += 1
    coverage[ns] = c

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
