#!/usr/bin/env python3
"""Builds docs/lab-validation/ADDENDUM_CMP12.md and results_cmp12.json from
the laboratory evidence of the feedback interface (CMP-12), the local
evidence and the catalog metadata. The texts are in
tools/report/addendum_texts.py. Usage, from the repository root:

    python3 docs/lab-validation/tools/build_addendum.py
"""
import importlib.util, json, pathlib, re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[3]
LAB = ROOT / "docs/lab-validation"
RAW = LAB / "raw"
RUN_INSTALL = RAW / "lab-20260924T175818"   # phase 3: nine charts
RUN_FIX = RAW / "lab-20260924T195147"       # phases 3, 6 and 8 after the fixes
RUN_TESTS = RAW / "lab-20260924T202458"     # phase 8 of reference
RUN_BEFORE = RAW / "lab-20260924T081803"    # 2.0.0 validation (traceability before CMP-12)

spec = importlib.util.spec_from_file_location("publish", ROOT / "infrastructure/publish.py")
publish = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publish)
TEXTS = {}
exec((LAB / "tools/report/addendum_texts.py").read_text(), TEXTS)


def results(run):
    return [json.loads(l) for l in open(run / "results.jsonl")]


def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    return "\n".join(out + ["| " + " | ".join(esc(x) for x in r) + " |" for r in rows])


def trace(run):
    rows = {}
    for l in (run / "trace/traceability.tsv").read_text().splitlines()[1:]:
        k, label, n, cmd = l.split("\t")
        rows[k] = {"label": label, "resources": int(n), "command": cmd}
    return rows


def np_nodes(run, tid):
    f = run / f"netpol/{tid}.txt"
    m = re.search(r"client node: (\S+); destination node\(s\): (.+)", f.read_text()) if f.exists() else None
    return (m.group(1), m.group(2).strip()) if m else ("", "")


# ---- chart metadata
name = "enterprise-feedback-interface"
meta = publish.CHART_META[name]
chart_dir = ROOT / meta["path"] / "manifests"
chart = yaml.safe_load((chart_dir / "Chart.yaml").read_text())
values = yaml.safe_load((chart_dir / "values.yaml").read_text())
chart_info = {"name": name, "version": chart["version"], "appVersion": str(chart["appVersion"]),
              "image": f'{values["image"]["repository"]}:{values["image"]["tag"]}', "tier": meta["tier"],
              "namespace": meta["namespace"], "category": meta["category"], "components": meta["components"],
              "clauses": meta["iso_clauses"], "path": meta["path"], "dependencies": "ninguna (chart propio)"}
totals = {t: sum(1 for m in publish.CHART_META.values() if m["tier"] == t) for t in ("edge", "platform", "enterprise")}

# ---- installation
install = []
for run, note in ((RUN_INSTALL, "fase 3 inicial (nueve charts)"), (RUN_FIX, "fase 3 tras las correcciones")):
    for l in open(run / "install.jsonl"):
        r = json.loads(l)
        install.append({**r, "run": run.name, "note": note,
                        "install_script_seconds": next(x["seconds"] for x in results(run) if x["id"] == "INST-00")})

# ---- tests
tests = [r for r in results(RUN_TESTS) if r["phase"] in ("smoke", "e2e")]
net = [r for r in results(RUN_TESTS) if r["phase"] == "netpol"]
canary = (RUN_TESTS / "netpol/N-CANARY.txt").read_text()
before, after = trace(RUN_BEFORE), trace(RUN_FIX)
coverage = json.load(open(RUN_FIX / "trace/traceability.json"))["coverage_by_namespace"]
cov = {k: v for k, v in coverage.items() if k != "argocd"}
cov_obj, cov_lab = sum(v["objects"] for v in cov.values()), sum(v["with_iso42001_label"] for v in cov.values())
unit = (LAB / "local-evidence/cmp12-unit-tests.txt").read_text()
unit_passed = re.search(r"(\d+) passed", unit).group(1)

cmp12_row = {"component": "CMP-12 Feedback Interface", "layer_level": "Entorno; empresa", "criticality": "Recomendado",
             "charts": [f"{name} (empresa)"], "clauses": meta["iso_clauses"],
             "lab_resources": after["CMP-12"]["resources"],
             "coverage": "cubierto: veredictos del operario sobre las predicciones consolidadas, usados como etiquetas por el entrenamiento, y suspensión de la versión en servicio"}

data = {
    "report": "docs/lab-validation/ADDENDUM_CMP12.md",
    "runs": TEXTS["RUNS"],
    "design": TEXTS["DESIGN"],
    "chart": chart_info,
    "changed_charts": TEXTS["CHANGED_CHARTS"],
    "installation": install,
    "tests": [{**r, "summary": TEXTS["TEST_SUMMARY"].get(r["id"], "")} for r in tests],
    "unit_tests": {"passed": int(unit_passed), "evidence": "local-evidence/cmp12-unit-tests.txt", "where": "local"},
    "network_policies": {"canary": canary, "tests": [{**r, "client_node": np_nodes(RUN_TESTS, r["id"])[0],
                                                      "destination_nodes": np_nodes(RUN_TESTS, r["id"])[1]} for r in net]},
    "traceability": {"before_run": RUN_BEFORE.name, "after_run": RUN_FIX.name,
                     "queries": [{"key": k, "label": v["label"], "before": before.get(k, {}).get("resources"),
                                  "after": v["resources"], "command": v["command"]} for k, v in after.items()],
                     "coverage_catalog_namespaces": {"objects": cov_obj, "with_iso42001_label": cov_lab},
                     "coverage_feedback_namespace": coverage.get("feedback")},
    "catalog_totals": {"charts": sum(totals.values()), "by_tier": totals,
                       "deployed_in_laboratory": 28, "not_deployed": ["platform-rancher", "platform-argocd", "edge-mongodb"]},
    "table30_row": cmp12_row,
    "incidents": TEXTS["INCIDENTS"],
    "limitations": [dict(zip(("topic", "detail"), l)) for l in TEXTS["LIMITATIONS"]],
}

# ---- Markdown
md = [TEXTS["INTRO"]]
A = md.append
A("\n## 1. Diseño aprobado y decisiones\n")
A(table(["Decisión", "Elegida", "Alternativa descartada y motivo"], [list(d) for d in TEXTS["DESIGN"]]))
A(TEXTS["DESIGN_FLOW"])
A("\n## 2. Metadatos del chart\n")
A(table(["Campo", "Valor"], [["Chart", name], ["Versión (app)", f'{chart_info["version"]} ({chart_info["appVersion"]})'],
                             ["Imagen", chart_info["image"] + " (la misma que el servidor del modelo y el entrenamiento; código en un ConfigMap)"],
                             ["Dependencia de terceros", chart_info["dependencies"]], ["Nivel", "empresa"],
                             ["Namespace", chart_info["namespace"]], ["Categoría", chart_info["category"]],
                             ["Componentes", ", ".join(chart_info["components"])], ["Cláusulas ISO/IEC 42001", ", ".join(chart_info["clauses"])],
                             ["Ruta", chart_info["path"]]]))
A("\n**Charts modificados para el componente:**\n")
A(table(["Chart", "Cambio"], [list(c) for c in TEXTS["CHANGED_CHARTS"]]))
A("\n## 3. Resultado de la instalación\n")
A("Comando: `run-lab-validation.sh --phases \"3 ...\" --edge-nodes edgenode01 --skip-chart platform-argocd --skip-chart edge-mongodb --only-chart ...` (fase 3, que ejecuta `install.sh` con `--only` por chart y `--separate-tiers`). Fuente: `install.jsonl` de cada ejecución.\n")
A(table(["Ejecución", "Chart", "Namespace", "Resultado", "Tiempo (s)", "Pods listos"],
        [[r["run"], r["chart"], r["namespace"], "correcto" if r["result"] == "ok" else "fallido", r["seconds"], r["pods_ready"]] for r in install]))
A(TEXTS["INSTALL_NOTES"])
A("\n## 4. Pruebas de la interfaz y del bucle de retroalimentación\n")
A(f"Ejecución de referencia `raw/{RUN_TESTS.name}` (fase 8). Pruebas unitarias de la aplicación: {unit_passed} de {unit_passed} correctas, en local (`local-evidence/cmp12-unit-tests.txt`).\n")
A(table(["ID", "Prueba", "Resultado", "Tiempo (s)", "Comando", "Evidencia resumida"],
        [[r["id"], r["name"], r["result"], r["seconds"], r["command"], TEXTS["TEST_SUMMARY"].get(r["id"], "")] for r in tests]))
A(TEXTS["TEST_NOTES"])
A("\n## 5. Trazabilidad por etiqueta iso42001\n")
A(f"Fase 6 completa en `raw/{RUN_FIX.name}` (después de CMP-12), comparada con `raw/{RUN_BEFORE.name}` (validación de la versión 2.0.0). Recursos: pods, servicios, deployments y statefulsets con la etiqueta.\n")
A(table(["Clave", "Descripción", "Antes", "Después", "Comando"],
        [[k, v["label"], before.get(k, {}).get("resources", "-"), v["resources"], v["command"]] for k, v in after.items()]))
A(TEXTS["TRACE_NOTES"].format(cov_lab=cov_lab, cov_obj=cov_obj, pct=round(100 * cov_lab / cov_obj),
                             fb_obj=coverage["feedback"]["objects"], fb_lab=coverage["feedback"]["with_iso42001_label"]))
A("\n## 6. Pruebas de red\n")
A(f"Ejecución `raw/{RUN_TESTS.name}`. Clientes en un nodo que aplica NetworkPolicy, tras esperar 15 s a la sincronización del controlador.\n")
A("```\n" + "\n".join(l for l in canary.splitlines() if l.startswith(("edgenode01", "kb2", "worker1"))) + "\n```\n")
A(table(["ID", "Prueba", "Resultado", "Nodo cliente", "Nodo destino", "Salida"],
        [[r["id"], r["name"], r["result"], np_nodes(RUN_TESTS, r["id"])[0] or "-", np_nodes(RUN_TESTS, r["id"])[1] or "-",
          "ver el bloque del canario" if r["id"] == "N-CANARY" else r["detail"][:140]] for r in net]))
A(TEXTS["NET_NOTES"])
A("\n## 7. Totales del catálogo y fila de la Tabla 30\n")
A(f"**{sum(totals.values())} charts**: {totals['edge']} de edge, {totals['platform']} de plataforma y {totals['enterprise']} de empresa. "
  "Desplegados en el laboratorio: 28 (los 27 de la validación de la versión 2.0.0 más `enterprise-feedback-interface`); siguen sin desplegar "
  "`platform-rancher`, `platform-argocd` y `edge-mongodb`, por los motivos del informe principal. Con este chart, los 15 componentes de la "
  "arquitectura tienen al menos un chart.\n")
A(table(["Componente", "Capa y nivel (arquitectura)", "Criticidad", "Chart(s)", "Cláusulas", "Recursos en el laboratorio", "Cobertura"],
        [[cmp12_row["component"], cmp12_row["layer_level"], cmp12_row["criticality"], ", ".join(cmp12_row["charts"]),
          ", ".join(cmp12_row["clauses"]), cmp12_row["lab_resources"], cmp12_row["coverage"]]]))
A("\n## 8. Incidencias encontradas y correcciones\n")
A(table(["Incidencia", "Evidencia", "Causa", "Corrección"], [list(i) for i in TEXTS["INCIDENTS"]]))
A(TEXTS["INCIDENT_NOTES"])
A("\n## 9. Limitaciones\n")
for t, d in TEXTS["LIMITATIONS"]:
    A(f"- **{t}.** {d}.")
A("\n## Anexo. Ejecuciones\n")
A(table(["Ejecución", "Contenido"], [list(r) for r in TEXTS["RUNS"]]))

(LAB / "ADDENDUM_CMP12.md").write_text("\n".join(md).rstrip() + "\n")
(LAB / "results_cmp12.json").write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str) + "\n")
print("addendum and results_cmp12.json written")
