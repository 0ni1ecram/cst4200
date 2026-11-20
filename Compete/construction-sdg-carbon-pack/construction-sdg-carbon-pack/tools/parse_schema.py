"""Parse IDEA_COMP01_SCHEMA.html -> schema.json (authoritative field list)."""
# ---- pack path shim: all paths resolve relative to this pack ----
import os
import pathlib as _pathlib
ROOT = _pathlib.Path(__file__).resolve().parents[1]
TMP = ROOT / "work"
TMP.mkdir(parents=True, exist_ok=True)
# -------------------------------------------------------------------
import json, re, sys, collections

SRC = os.fspath(ROOT / "data" / "IDEA_COMP01_SCHEMA.html")
html = open(SRC, encoding="utf-8").read()

start = html.index("const SCHEMA = [") + len("const SCHEMA = ")
# slice to the matching closing bracket of the array
depth, i = 0, start
while True:
    ch = html[i]
    if ch == "[":
        depth += 1
    elif ch == "]":
        depth -= 1
        if depth == 0:
            break
    i += 1
raw = html[start:i + 1]
raw = re.sub(r"\s*/\*.*?\*/", "", raw, flags=re.S)      # strip block comments
raw = re.sub(r"([{,\[]\s*)(\w+)\s*:", r'\1"\2":', raw)   # quote keys only after { , [
raw = re.sub(r",\s*([}\]])", r"\1", raw)           # trailing commas
schema = json.loads(raw)

out = []
for t in schema:
    # ["col","TYPE",1] = PK · ["col","TYPE",0] = plain · ["col","TYPE",0,"table"] = FK -> table
    cols = [{"n": c[0], "ty": c[1], "pk": len(c) > 2 and c[2] == 1,
             "fk": c[3] if len(c) > 3 else None} for c in t["cols"]]
    out.append({"name": t["name"], "phase": t["phase"], "desc": t.get("desc", ""), "cols": cols})

phases = collections.Counter(t["phase"] for t in out)
print(f"tables={len(out)} cols={sum(len(t['cols']) for t in out)}")
print(f"fks={sum(1 for t in out for c in t['cols'] if c['fk'])}")
for p, n in phases.items():
    print(f"  phase {p:6s} tables={n}")
json.dump({"phases": dict(phases), "tables": out}, open(os.fspath(TMP / "schema.json"), "w"), indent=1)
print("wrote /tmp/qwenwork/schema.json")
