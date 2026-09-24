#!/usr/bin/env python3
"""Summary of the Prometheus /api/v1/targets answer read from stdin."""
import collections, json, sys
targets = json.load(sys.stdin)["data"]["activeTargets"]
count = collections.Counter((t["labels"].get("job", "?"), t["health"]) for t in targets)
for (job, health), n in sorted(count.items()):
    print(f"{health:8} {n:3}  {job}")
up = sum(n for (_, h), n in count.items() if h == "up")
print(f"up {up} of {len(targets)} targets")
for t in targets:
    if t["health"] != "up":
        print("down:", t["labels"].get("job"), t.get("scrapeUrl"), (t.get("lastError") or "")[:160])
sys.exit(0 if up else 1)
