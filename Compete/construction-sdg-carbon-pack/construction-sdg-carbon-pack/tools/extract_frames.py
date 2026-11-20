"""Extract frame metadata from output/wireframes.html -> /tmp/qwenwork/frames.json"""
# ---- pack path shim: all paths resolve relative to this pack ----
import os
import pathlib as _pathlib
ROOT = _pathlib.Path(__file__).resolve().parents[1]
TMP = ROOT / "work"
TMP.mkdir(parents=True, exist_ok=True)
# -------------------------------------------------------------------
import json, re, html
from bs4 import BeautifulSoup

SRC = "output/wireframes.html"
OUT = os.fspath(TMP / "frames.json")

soup = BeautifulSoup(open(SRC, encoding="utf-8").read(), "html.parser")
frames = []
for sec in soup.select("section.frame"):
    fid = sec.select_one(".fid").get_text(strip=True)
    ft = sec.select_one(".ft").get_text(strip=True)
    fp = sec.select_one(".fp").get_text(strip=True)
    fb = sec.select_one(".fb")
    note = fb.select_one(".note")
    lede = note.get_text(" ", strip=True) if note else ""
    regs = []
    for reg in fb.select(".reg"):
        rl = reg.select_one(".rl")
        an = reg.select_one(".an")
        kinds = []
        for cls in ("gantt", "kan", "heat", "tree", "kpis", "chips", "flds", "ph"):
            if reg.select("." + cls):
                kinds.append(cls)
        if reg.select("table.w"):
            kinds.append("table")
        ths = [t.get_text(" ", strip=True) for t in reg.select("table.w th")]
        tbody = []
        for tr in reg.select("table.w tr")[1:]:
            tbody.append([td.get_text(" ", strip=True) for td in tr.select("td")])
        regs.append({
            "an": an.get_text(strip=True) if an else None,
            "label": rl.get_text(" ", strip=True) if rl else "",
            "kinds": kinds, "ths": ths, "rows": tbody,
            "html": str(reg),
        })
    spec = fb.select_one(".spec")
    srcs, actions, rules, roles = [], [], [], []
    if spec:
        for h4 in spec.select("h4"):
            txt = h4.get_text(" ", strip=True)
            nxt = h4.find_next_sibling()
            if txt.startswith("Data sources"):
                srcs = [s.get_text(" ", strip=True).strip()
                        for s in nxt.select(".src")]
            else:
                items = [li.get_text(" ", strip=True) for li in nxt.select("li")]
                if "Primary actions" in txt:
                    actions = items
                elif "Validation" in txt:
                    rules = items
                elif "Roles" in txt:
                    roles = items
    frames.append({"id": fid, "title": ft, "phase": fp, "lede": lede,
                   "regions": regs, "srcs": srcs, "actions": actions,
                   "rules": rules, "roles": roles})

json.dump(frames, open(OUT, "w"), indent=1)
print("frames:", len(frames))
for f in frames:
    print(f['id'], '|', f['phase'], '|', f['title'], '| regs=%d' % len(f['regions']),
          '| srcs=%d' % len(f['srcs']), '| an=%s' % ",".join(r["an"] or "-" for r in f["regions"]))
print("phases:", sorted({f["phase"] for f in frames}))
