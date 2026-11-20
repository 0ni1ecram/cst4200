"""Dump a compact readable spec-sheet per frame for authoring the page configs."""
# ---- pack path shim: all paths resolve relative to this pack ----
import os
import pathlib as _pathlib
ROOT = _pathlib.Path(__file__).resolve().parents[1]
TMP = ROOT / "work"
TMP.mkdir(parents=True, exist_ok=True)
# -------------------------------------------------------------------
import json, re, textwrap
from bs4 import BeautifulSoup

F = json.load(open(os.fspath(TMP / "frames.json")))
soup_map = {}
doc = BeautifulSoup(open("output/wireframes.html", encoding="utf-8").read(), "html.parser")
for sec in doc.select("section.frame"):
    soup_map[sec.select_one(".fid").get_text(strip=True)] = sec

out = []
for f in F:
    sec = soup_map[f["id"]]
    out.append("=" * 78)
    out.append("FRAME %s  [%s]  %s" % (f["id"], f["phase"], f["title"]))
    out.append("LEDE: " + textwrap.fill(f["lede"], 100).replace("\n", "\n      "))
    for i, reg in enumerate(f["regions"]):
        r = sec.select(".reg")[i]
        out.append("  REG%d an=%s kinds=%s" % (i, reg["an"] or "-", reg["kinds"]))
        out.append("      label: " + reg["label"])
        if reg["ths"]:
            out.append("      TH: " + " | ".join(reg["ths"]))
            for row in reg["rows"]:
                out.append("      ROW: " + " | ".join(row))
        for el in r.select(".fld"):
            out.append("      FLD: " + el.get_text(" ", strip=True))
        for el in r.select(".chips"):
            out.append("      CHIPS: " + " ~ ".join(c.get_text("", strip=True) for c in el.select(".chip")))
        for el in r.select(".kpi"):
            out.append("      KPI: " + el.get_text(" ", strip=True))
        for el in r.select(".tree"):
            out.append("      TREE: " + el.get_text(" | ", strip=True)[:300])
        for el in r.select(".gantt > div"):
            out.append("      GANTT: " + el.get_text(" ", strip=True) + " :: " + (el.select_one(".bar") or "").get("style", "") if hasattr(el.select_one(".bar"), "get") else "")
        for el in r.select(".kan > div"):
            out.append("      KAN: " + el.get_text(" / ", strip=True))
        for el in r.select(".ph"):
            out.append("      PH: " + el.get_text(" ", strip=True) + " h=" + (el.get("style") or ""))
        for el in r.select(".heat"):
            out.append("      HEAT: n=%d" % len(el.select("i")))
        for el in r.select(".row"):
            pass
    out.append("  SRCS: " + "; ".join(f["srcs"]))
    out.append("  ACTIONS: " + "; ".join(f["actions"]))
    out.append("  RULES:")
    for x in f["rules"]:
        out.append("    - " + textwrap.fill(x, 100).replace("\n", "\n      "))
    out.append("  ROLES/STATES: " + "; ".join(f["roles"]))
open(os.fspath(TMP / "frames_detail.txt"), "w").write("\n".join(out))
print(len(F), "frames ->", os.fspath(TMP / "frames_detail.txt"), sum(len(x) for x in out), "chars")
