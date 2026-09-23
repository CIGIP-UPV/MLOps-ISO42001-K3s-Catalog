#!/usr/bin/env python3
"""Markdown summary of results.jsonl."""
import collections, json, os, sys
path, out = sys.argv[1:3]
recs = [json.loads(l) for l in open(path)] if os.path.exists(path) else []
by = collections.OrderedDict()
for r in recs:
    by.setdefault(r["phase"], []).append(r)
with open(out, "w") as f:
    f.write("# Laboratory validation run: summary\n\n| Phase | PASS | FAIL | SKIP |\n|---|---|---|---|\n")
    for phase, rs in by.items():
        c = collections.Counter(r["result"] for r in rs)
        f.write(f"| {phase} | {c['PASS']} | {c['FAIL']} | {c['SKIP']} |\n")
    f.write("\n| ID | Result | Name | Seconds | Evidence | Detail |\n|---|---|---|---|---|---|\n")
    for r in recs:
        d = r.get("detail", "").replace("|", "/").replace("\n", " ")[:140]
        f.write(f"| {r['id']} | {r['result']} | {r['name']} | {r['seconds']} | {r['evidence']} | {d} |\n")
print(open(out).read())
