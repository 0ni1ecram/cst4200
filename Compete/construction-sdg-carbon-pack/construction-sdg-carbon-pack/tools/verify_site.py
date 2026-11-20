"""verify_site.py — structural assertions over the emitted site (independent of gen_site)."""
# ---- pack path shim: all paths resolve relative to this pack ----
import os
import pathlib as _pathlib
ROOT = _pathlib.Path(__file__).resolve().parents[1]
TMP = ROOT / "work"
TMP.mkdir(parents=True, exist_ok=True)
# -------------------------------------------------------------------
import os, re, glob, sys
from bs4 import BeautifulSoup

SITE = os.path.join(os.fspath(ROOT), "output", "site")
SCHEMA = json = __import__("json").load(open(os.fspath(TMP / "schema.json"), encoding="utf-8"))
TBL = {t["name"]: {c["n"] for c in t["cols"]} for t in SCHEMA["tables"]}
ALLCOLS = {n for s in TBL.values() for n in s} | set(TBL)

pages = sorted(glob.glob(os.path.join(SITE, "pages", "*.html")))
index = os.path.join(SITE, "index.html")
print("pages:", len(pages), "| index:", os.path.isfile(index))
rows = {}
problems = []
for p in pages + [index]:
    soup = BeautifulSoup(open(p, encoding="utf-8").read(), "html.parser")
    b = os.path.basename(p)
    if soup.find("script"):
        problems.append((b, "has <script>"))
    for el in soup.find_all(True):
        for a in list(el.attrs):
            if a.startswith("on"):
                problems.append((b, "inline handler " + a))
    tables = soup.select("table.grid")
    bodyrows = [len(t.select("tbody tr")) for t in tables]
    rows[b] = bodyrows
    if p != index:
        need = {".crumbs": 1, "h1 .fid": 1, ".lede": 1, ".srcs-strip": 1, ".prevnext": 1,
                ".pgfoot": 1, ".rail": 1, ".topbar": 1, ".an": 1}
        for sel, _ in need.items():
            if sel == ".an":
                continue
            if not soup.select(sel):
                problems.append((b, "missing " + sel))
        if not bodyrows or max(bodyrows) < 6:
            problems.append((b, "no table with >=6 rows (max=%s)" % (max(bodyrows) if bodyrows else 0)))
        if not (soup.select(".empty") or soup.select(".skeleton") or soup.select(".banner")):
            problems.append((b, "no empty/loading/error state shown"))
print("pages with >=6-row table:", sum(1 for b, r in rows.items() if r and max(r) >= 6))
print("max table rows per page (sample):")
for b in list(rows)[:26]:
    print("  %-62s %s" % (b, rows[b]))
print("problems:", len(problems))
for pr in problems:
    print("  ", pr)
sys.exit(1 if problems else 0)
