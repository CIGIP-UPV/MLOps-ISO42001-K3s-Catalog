#!/usr/bin/env python3
"""
verify_charts.py: static verification of every chart in CHART_META.

For each chart, on a temporary copy (the source tree is never modified):

    1. helm dependency build, helm lint and helm template (Kubernetes 1.32);
    2. kubeconform validation of the rendered manifests (CRDs are skipped,
       custom resources are validated against the datreeio CRD catalogue);
    3. traceability labels: every rendered resource, and the pod template of
       every workload, must carry ``iso42001: "true"`` plus one label per
       ISO/IEC 42001 clause declared in CHART_META;
    4. questions.yaml: valid YAML, valid Rancher types, and every variable
       resolvable in the chart values (subchart defaults included);
    5. list of container images.

Optionally (--post-render) the manifests are passed through
iso42001-postrender.py first, which is what install.sh does.

Run:
    python3 infrastructure/verify_charts.py [--post-render] [--json out.json] [chart ...]
Requires helm, kubeconform and PyYAML.
"""

from __future__ import annotations

import argparse
import glob
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("publish", ROOT / "infrastructure" / "publish.py")
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)
CHART_META = publish.CHART_META

KUBE_VERSION = "1.32.6"
CRD_SCHEMAS = "https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json"
POSTRENDER = ROOT / "infrastructure" / "iso42001-postrender.py"
WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "ReplicaSet"}
RANCHER_TYPES = {"string", "multiline", "boolean", "int", "float", "enum", "password",
                 "storageclass", "hostname", "pvc", "secret"}
LABEL_VALUE = re.compile(r"^(([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9])?$")

# Values needed only to render charts whose upstream templates refuse to
# render without a secret. They are never used for an installation.
RENDER_ONLY = {}


def sh(cmd, cwd=None, stdin=None, env=None):
    return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, env=env)


def pod_template_labels(doc):
    kind, spec = doc.get("kind"), doc.get("spec") or {}
    if kind == "CronJob":
        tpl = ((spec.get("jobTemplate") or {}).get("spec") or {}).get("template") or {}
    elif kind in WORKLOADS:
        tpl = spec.get("template") or {}
    elif kind in ("Prometheus", "Alertmanager"):
        return ((spec.get("podMetadata") or {}).get("labels")) or {}
    else:
        return None
    return ((tpl.get("metadata") or {}).get("labels")) or {}


def images(doc):
    found = []

    def walk(o):
        if isinstance(o, dict):
            for key in ("containers", "initContainers"):
                for c in o.get(key) or []:
                    if isinstance(c, dict) and c.get("image"):
                        found.append(c["image"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(doc.get("spec") or {})
    if doc.get("kind") in ("Prometheus", "Alertmanager") and (doc.get("spec") or {}).get("image"):
        found.append(doc["spec"]["image"])
    return found


def merged_values(chart_dir: pathlib.Path):
    vals = yaml.safe_load((chart_dir / "values.yaml").read_text()) or {}
    chart = yaml.safe_load((chart_dir / "Chart.yaml").read_text())
    deps = []
    for dep in chart.get("dependencies") or []:
        key = dep.get("alias") or dep["name"]
        deps.append(key)
        for tgz in glob.glob(str(chart_dir / "charts" / f"{dep['name']}-*.tgz")):
            with tarfile.open(tgz) as t:
                sub = yaml.safe_load(t.extractfile(f"{dep['name']}/values.yaml").read()) or {}
            base = vals.setdefault(key, {})

            def deep(a, b):
                for k, v in b.items():
                    if k not in a:
                        a[k] = v
                    elif isinstance(a[k], dict) and isinstance(v, dict):
                        deep(a[k], v)
            deep(base, sub)
    return vals, deps


def split_path(p):
    out = []
    for part in re.split(r"(?<!\\)\.", p):
        part = part.replace("\\.", ".")
        m = re.match(r"^(.*?)((\[\d+\])*)$", part)
        out.append(m.group(1))
        out += [int(i) for i in re.findall(r"\[(\d+)\]", m.group(2))]
    return out


def has_path(d, parts):
    cur = d
    for k in parts:
        if isinstance(k, int):
            if isinstance(cur, list):
                if len(cur) > k:
                    cur = cur[k]
                    continue
                return True  # list exists; a new index is a legitimate override
            return False
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return False
    return True


def unknown_subchart_keys(chart_dir: pathlib.Path):
    """Keys set for a subchart that the subchart defaults do not know about.

    Upstream charts without a values schema silently ignore such keys, so a
    typo or a key removed upstream means the setting never takes effect.
    Keys below an empty dict/list or a non-dict default are accepted.
    """
    own = yaml.safe_load((chart_dir / "values.yaml").read_text()) or {}
    chart = yaml.safe_load((chart_dir / "Chart.yaml").read_text())
    unknown = []
    for dep in chart.get("dependencies") or []:
        key = dep.get("alias") or dep["name"]
        tgzs = glob.glob(str(chart_dir / "charts" / f"{dep['name']}-*.tgz"))
        if key not in own or not tgzs:
            continue
        with tarfile.open(tgzs[0]) as t:
            upstream = yaml.safe_load(t.extractfile(f"{dep['name']}/values.yaml").read()) or {}

        def walk(mine, theirs, path):
            if not isinstance(mine, dict) or not isinstance(theirs, dict) or not theirs:
                return
            for k, v in mine.items():
                if k == "global":
                    continue
                if k not in theirs:
                    unknown.append(f"{path}.{k}")
                else:
                    walk(v, theirs[k], f"{path}.{k}")
        walk(own[key], upstream, key)
    return unknown


def check_questions(chart_dir: pathlib.Path):
    res = {"valid_yaml": True, "variables": 0, "resolved": 0, "unresolved": []}
    try:
        data = yaml.safe_load((chart_dir / "questions.yaml").read_text()) or {}
    except Exception as e:  # noqa: BLE001
        res["valid_yaml"] = False
        res["unresolved"].append(repr(e))
        return res
    vals, _ = merged_values(chart_dir)
    items = []
    for q in data.get("questions") or []:
        items.append(q)
        items += q.get("subquestions") or []
    for q in items:
        var, typ = q.get("variable"), q.get("type")
        res["variables"] += 1
        if typ not in RANCHER_TYPES or (typ == "enum" and not q.get("options")):
            res["unresolved"].append(f"{var}: invalid type {typ}")
        elif var and has_path(vals, split_path(var)):
            res["resolved"] += 1
        else:
            res["unresolved"].append(f"{var}: not in values")
    return res


def verify(chart_name: str, post_render: bool, workdir: pathlib.Path):
    meta = CHART_META[chart_name]
    src = ROOT / meta["path"] / "manifests"
    ns = meta["namespace"]
    out = {"chart": chart_name, "namespace": ns}
    dst = workdir / chart_name
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("charts", "*.bak"))

    chart = yaml.safe_load((dst / "Chart.yaml").read_text())
    if chart.get("dependencies"):
        r = sh(["helm", "dependency", "build", str(dst)])
        out["dependency_build"] = r.returncode == 0
        if r.returncode:
            out["error"] = r.stderr.strip()[-400:]
            return out
        lock = yaml.safe_load((dst / "Chart.lock").read_text()) if (dst / "Chart.lock").exists() else {}
        out["dependencies"] = [f"{d['name']}@{d['version']}" for d in (lock or {}).get("dependencies", [])]
    else:
        out["dependency_build"] = True
        out["dependencies"] = []

    r = sh(["helm", "lint", str(dst), "--kube-version", KUBE_VERSION] + sum((["--set", s] for s in RENDER_ONLY.get(chart_name, [])), []))
    out["lint"] = r.returncode == 0
    if r.returncode:
        out["lint_error"] = (r.stdout + r.stderr).strip()[-400:]

    cmd = ["helm", "template", chart_name, str(dst), "-n", ns, "--kube-version", KUBE_VERSION]
    for s in RENDER_ONLY.get(chart_name, []):
        cmd += ["--set", s]
    if post_render:
        env = dict(os.environ, ISO42001_CHART_DIR=str(dst))
        cmd += ["--post-renderer", str(POSTRENDER)]
        r = sh(cmd, env=env)
    else:
        r = sh(cmd)
    out["template"] = r.returncode == 0
    if r.returncode:
        out["template_error"] = r.stderr.strip()[-400:]
        return out
    rendered = r.stdout
    (workdir / f"{chart_name}.yaml").write_text(rendered)

    kc = sh(["kubeconform", "-kubernetes-version", KUBE_VERSION.rsplit(".", 1)[0] + ".0", "-strict", "-summary",
             "-skip", "CustomResourceDefinition", "-schema-location", "default",
             "-schema-location", CRD_SCHEMAS, "-output", "json", "-"], stdin=rendered)
    try:
        kcj = json.loads(kc.stdout)
        out["kubeconform"] = kcj.get("summary", {})
        out["kubeconform_errors"] = [f"{x.get('kind')}/{x.get('name')}: {x.get('msg')}"[:300]
                                     for x in kcj.get("resources", []) if x.get("status") in ("statusError", "statusInvalid")]
    except json.JSONDecodeError:
        out["kubeconform"] = {"raw": (kc.stdout + kc.stderr)[-400:]}
        out["kubeconform_errors"] = ["unparseable output"]

    required = publish.iso_labels(chart_name)
    docs = [d for d in yaml.safe_load_all(rendered) if isinstance(d, dict) and d.get("kind")]
    res_ok, res_missing, pods_total, pods_ok, pods_missing, bad_values = 0, [], 0, 0, [], []
    for d in docs:
        md = d.get("metadata") or {}
        labels = md.get("labels") or {}
        ident = f"{d['kind']}/{md.get('name')}"
        if all(labels.get(k) == v for k, v in required.items()):
            res_ok += 1
        else:
            res_missing.append(ident)
        for k, v in labels.items():
            if not LABEL_VALUE.match(str(v)) or len(str(v)) > 63:
                bad_values.append(f"{ident}: {k}={v}")
        pl = pod_template_labels(d)
        if pl is not None:
            pods_total += 1
            if all(pl.get(k) == v for k, v in required.items()):
                pods_ok += 1
            else:
                pods_missing.append(ident)
    out["resources"] = len(docs)
    out["labelled_resources"] = res_ok
    out["unlabelled_resources"] = res_missing
    out["workloads"] = pods_total
    out["labelled_pod_templates"] = pods_ok
    out["unlabelled_pod_templates"] = pods_missing
    out["invalid_label_values"] = bad_values
    out["kinds"] = dict(sorted({d["kind"]: sum(1 for x in docs if x["kind"] == d["kind"]) for d in docs}.items()))
    out["images"] = sorted({i for d in docs for i in images(d)})
    out["questions"] = check_questions(dst)
    out["unknown_values_keys"] = unknown_subchart_keys(dst)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("charts", nargs="*")
    ap.add_argument("--post-render", action="store_true")
    ap.add_argument("--json")
    args = ap.parse_args()
    names = args.charts or list(CHART_META)
    results, failed = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for n in names:
            r = verify(n, args.post_render, pathlib.Path(tmp))
            results.append(r)
            ok = (r.get("dependency_build") and r.get("lint") and r.get("template")
                  and not r.get("kubeconform_errors") and r.get("labelled_resources") == r.get("resources")
                  and r.get("labelled_pod_templates") == r.get("workloads")
                  and not r["questions"]["unresolved"] and not r["unknown_values_keys"]
                  if "questions" in r else False)
            failed += 0 if ok else 1
            q = r.get("questions", {})
            print(f"{'OK  ' if ok else 'FAIL'} {n:32} dep={int(bool(r.get('dependency_build')))} "
                  f"lint={int(bool(r.get('lint')))} tpl={int(bool(r.get('template')))} "
                  f"kc_err={len(r.get('kubeconform_errors', []))} "
                  f"labels={r.get('labelled_resources', 0)}/{r.get('resources', 0)} "
                  f"pods={r.get('labelled_pod_templates', 0)}/{r.get('workloads', 0)} "
                  f"questions={q.get('resolved', 0)}/{q.get('variables', 0)} "
                  f"unknown_keys={len(r.get('unknown_values_keys', []))}")
    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(results, indent=1))
    print(f"\n{len(names) - failed}/{len(names)} charts pass every check")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
