"""gen_site.py — emit the static visual demo site from the wireframe pack.

Sources of truth (never hand-copied):
  output/wireframes.html    -> 25 frames: id / title / phase group / lede / srcs
  /tmp/qwenwork/schema.json -> 45 tables, 320 columns, 84 FKs -> column validation
Output: output/site/index.html, output/site/pages/NN-<slug>.html, assets/site.css(+print.css)
"""
# ---- pack path shim: all paths resolve relative to this pack ----
import os
import pathlib as _pathlib
ROOT = _pathlib.Path(__file__).resolve().parents[1]
TMP = ROOT / "work"
TMP.mkdir(parents=True, exist_ok=True)
# -------------------------------------------------------------------
import json, re, os, html

WORK = os.fspath(ROOT)             # pack: tools/ sits one level below the root
WF_HTML = os.path.join(WORK, "output", "wireframes.html")
SCHEMA_JSON = os.fspath(TMP / "schema.json")
SITE = os.path.join(WORK, "output", "site")
PAGES = os.path.join(SITE, "pages")
ASSETS = os.path.join(SITE, "assets")

if not os.path.exists(SCHEMA_JSON):
    # /tmp can be cleaned between runs: rebuild the authoritative parse from the source ERD
    import subprocess, sys
    os.makedirs(os.path.dirname(SCHEMA_JSON), exist_ok=True)
    subprocess.run([sys.executable, os.path.join(os.fspath(ROOT / "tools"), "parse_schema.py")], check=True,
                   capture_output=True)
SCHEMA = json.load(open(SCHEMA_JSON, encoding="utf-8"))
TABLES = {t["name"]: t for t in SCHEMA["tables"]}
COLS = {t["name"]: {c["n"]: c for c in t["cols"]} for t in SCHEMA["tables"]}
TNUM = {n: len(t["cols"]) for n, t in TABLES.items()}
TFK = {n: sum(1 for c in t["cols"] if c["fk"]) for n, t in TABLES.items()}

PHASE_ORDER = ["core", "d12", "p34", "p5", "p67", "sdg", "cc"]
PHASE_LABEL = {
    "core": "Core spine", "d12": "D12 Design & Funding",
    "p34": "P34 Procurement & Planning", "p5": "P5 Construction",
    "p67": "P67 Handover & Operations", "sdg": "SDG layer",
    "cc": "Carbon credit layer",
}
PHASE_OF_LABEL = {v: k for k, v in PHASE_LABEL.items()}
PHASE_TABLES = {}
for _t in SCHEMA["tables"]:
    PHASE_TABLES.setdefault(_t["phase"], []).append(_t["name"])


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def spec_text(frame):
    """All prose the wireframe pack itself attaches to a frame (for the name whitelist)."""
    bits = [frame["lede"]] + frame["regions"]
    for _h, items in frame["specs"]:
        bits.extend(items)
    return " ".join(bits)


CFG = {}


def load_frames():
    """Parse wireframes.html -> ordered frame records. Nothing about the pack is hand-listed."""
    from bs4 import BeautifulSoup
    doc = BeautifulSoup(open(WF_HTML, encoding="utf-8").read(), "html.parser")
    out = []
    for sec in doc.select("section.frame"):
        fid = sec.select_one(".fid").get_text(strip=True)
        title = sec.select_one(".ft").get_text(strip=True)
        phase = sec.select_one(".fp").get_text(strip=True)
        fb = sec.select_one(".fb")
        note = fb.select_one(".note")
        srcs, specs = [], []
        for s in fb.select(".spec .srcs .src"):
            srcs.append(s.find(string=True, recursive=False).strip())
        for h4 in fb.select(".spec h4"):
            nxt = h4.find_next_sibling()
            specs.append((h4.get_text(" ", strip=True),
                          [li.get_text(" ", strip=True) for li in nxt.select("li")]))
        anns = sorted({int(x.get_text(strip=True)) for x in sec.select(".an")
                       if x.get_text(strip=True).isdigit()})
        out.append({
            "id": fid, "title": title, "phase": phase, "anns": anns,
            "phase_key": PHASE_OF_LABEL[phase],
            "lede": note.get_text(" ", strip=True) if note else "",
            "srcs": srcs, "specs": specs,
            "regions": [r.get_text(" ", strip=True) for r in fb.select(".reg > .rl")],
            "slug": slugify(title), "file": "%s-%s.html" % (fid, slugify(title)),
        })
    return out


FRAMES = load_frames()
PAGE_OF = {f["id"]: f["file"] for f in FRAMES}
BY_ID = {f["id"]: f for f in FRAMES}
TABLE_PAGES = {}
for _f in FRAMES:
    for _t in _f["srcs"]:
        TABLE_PAGES.setdefault(_t, []).append(_f["id"])
for _f in FRAMES:
    _f["srctok"] = set(re.findall(r"[A-Za-z][A-Za-z0-9_]*", spec_text(_f)))
# page that best represents each schema table (for cross-page table links)
TABLE_PRIMARY = {t: TABLE_PAGES[t][0] for t in TABLE_PAGES if TABLE_PAGES.get(t)}


# ------------------------------------------------------------- name validation
def check_col(table, col):
    if table not in COLS:
        raise AssertionError("table not in schema.json: " + table)
    if col not in COLS[table]:
        raise AssertionError("column not in schema.json: %s.%s" % (table, col))
    return col


# ---------------------------------------------------------------- primitives
def E(x):
    return html.escape(str(x), quote=True)


def ref(text):
    """Link 'frame NN' mentions inside prose to the generated page."""
    def sub(m):
        fid = m.group(1)
        if fid in PAGE_OF:
            return '<a href="%s">frame %s</a>' % (E(PAGE_OF[fid]), fid)
        return m.group(0)
    return re.sub(r"frame\s+(\d{2})", sub, E(text))


def tref(table, pre=""):
    """Link a schema table name to the page that carries it as a data source."""
    fid = TABLE_PRIMARY.get(table)
    inner = '<code class="tbl">%s</code>' % E(table)
    return '<a class="tblref" href="%s%s">%s</a>' % (pre, E(PAGE_OF[fid]), inner) if fid else inner


def ctype(table, col):
    return COLS[table][col]["ty"]


def cflag(table, col):
    c = COLS[table][col]
    return "pk" if c["pk"] else ("fk" if c["fk"] else "")


def ccode(table, col):
    """Schema-validated column token for inline use."""
    check_col(table, col)
    return '<code class="col" data-t="%s" data-c="%s" title="%s · %s">%s</code>' % (
        E(table), E(col), E(table), E(ctype(table, col)), E(col))


def pill(text, tone="n"):
    return '<span class="pill %s">%s</span>' % (tone, E(text))


def an(n):
    return "" if n in (None, "") else '<span class="an" title="wireframe annotation %s">%s</span>' % (E(n), E(n))


def kpis(items):
    out = ['<div class="kpi-strip">']
    for v, l, t in items:
        out.append('<div class="kpi %s"><span class="kv">%s</span><span class="kl">%s</span></div>'
                   % (t, E(v), ref(l)))
    return "".join(out) + "</div>"


def grid(cols, rows, cls="", foot=None, hint=None):
    """cols entries: (table, colname) -> schema column | ('^', label) -> synthetic."""
    h = ['<div class="tw"><table class="grid %s"><thead><tr>' % cls]
    for c in cols:
        if c[0] == "^":
            h.append('<th class="syn">%s</th>' % ref(c[1]))
        else:
            check_col(c[0], c[1])
            h.append('<th class="col %s" data-t="%s" data-c="%s" title="%s · %s · %s">%s%s</th>'
                     % (cflag(*c), E(c[0]), E(c[1]), E(c[0]), E(c[1]), E(ctype(*c)), E(c[1]),
                        '<i class="fkdot">→</i>' if cflag(c[0], c[1]) == "fk" else ""))
    h.append("</tr></thead><tbody>")
    for r in rows:
        h.append("<tr>")
        for cell in r:
            h.append("<td>%s</td>" % (cell[0] if isinstance(cell, tuple) else E(cell)))
        h.append("</tr>")
    h.append("</tbody>")
    if foot:
        h.append("<tfoot><tr>%s</tr></tfoot>"
                 % "".join("<td>%s</td>" % E(c) for c in foot))
    h.append("</table></div>")
    if hint:
        h.append('<p class="tblnote">%s</p>' % ref(hint))
    return "".join(h)


def chip(text, kind="", tip=""):
    return ('<span class="chip %s"%s>%s</span>'
            % (kind, ' title="%s"' % E(tip) if tip else "", ref(text)))


def colchips(table, names=None, caption=None):
    names = names or list(COLS[table])
    cs = []
    for n in names:
        check_col(table, n)
        c = COLS[table][n]
        kind = "pk" if c["pk"] else ("fk" if c["fk"] else "")
        tip = "%s.%s · %s%s" % (table, n, c["ty"], (" → " + c["fk"]) if c["fk"] else "")
        cs.append('<span class="chip %s" data-t="%s" data-c="%s" title="%s">%s%s</span>'
                  % (kind, E(table), E(n), E(tip), E(n),
                     "" if not c["fk"] else '<em class="tgt">→%s</em>' % E(c["fk"])))
    cap = '<span class="chipcap">%s</span>' % ref(caption) if caption else ""
    return '<div class="chips">%s%s</div>' % (cap, "".join(cs))


def fields(table, names, values, states=None, cols=2):
    """Form layout with input states: ro / empty / invalid / warn / select / bool / area / date."""
    states = states or {}
    out = ['<div class="fields f%d">' % cols]
    for n in names:
        check_col(table, n)
        c = COLS[table][n]
        st = states.get(n, "")
        v = values.get(n, "")
        if st == "select":
            inp = '<select class="in %s" disabled><option>%s</option></select>' % (st, E(v or "— choose —"))
        elif st == "bool":
            inp = ('<label class="sw"><input type="checkbox" %s><span></span></label>'
                   '<span class="swl">%s</span>'
                   % ("checked" if str(v).lower() in ("true", "1", "yes") else "", E(v or "false")))
        elif st == "area":
            inp = '<textarea class="in" rows="2" disabled>%s</textarea>' % E(v)
        elif st == "date":
            inp = '<input class="in %s" type="date" value="%s" disabled>' % (st, E(v))
        else:
            inp = ('<input class="in %s" value="%s" placeholder="%s"%s>'
                   % (st, E(v), "required — not set" if st == "empty" else "",
                      " readonly" if st in ("ro", "locked") else ""))
        out.append('<label class="fld %s%s"><span class="fname"><code class="col" data-t="%s" data-c="%s"'
                   '>%s</code></span><span class="fmeta">%s%s</span>%s</label>'
                   % (cflag(table, n) or "pl", " ro" if st in ("ro", "locked") else "",
                      E(table), E(n), E(n), E(c["ty"]),
                      " · →" + E(c["fk"]) if c["fk"] else "", inp))
    return "".join(out) + "</div>"


def bars(items, cap=None):
    out = ['<div class="bars">']
    for l, p, t, r in items:
        out.append('<div class="brow"><span class="bl">%s</span><span class="btrack">'
                   '<i class="bfill %s" style="width:%s%%"></i></span><span class="br">%s</span></div>'
                   % (E(l), t, p, E(r)))
    out.append("</div>")
    return "".join(out) + (('<p class="cap">%s</p>' % ref(cap)) if cap else "")


def sparkline(vals, widths=None, cls=""):
    n = max(vals) or 1
    bars_h = "".join('<i style="height:%d%%" title="%s"></i>'
                     % (max(6, int(v * 100.0 / n)), E(v)) for v in vals)
    return '<div class="spark %s">%s</div>' % (cls, bars_h)


def gauge(pct, big, small, tone="a"):
    """Conic-gradient ring — pure CSS, no chart library."""
    return ('<div class="gauge %s"><span class="ring" style="background:conic-gradient(var(--g-%s) '
            '%s%%, #e3e6eb %s%%)"><b>%s</b><i>%s</i></span></div>'
            % (tone, tone, pct, 100 - pct, E(big), E(small)))


def donut(segments, caption=""):
    acc, stops, legend = 0, [], []
    for p, col, l in segments:
        stops.append("%s %d%% %d%%" % (col, acc, acc + p))
        acc += p
        legend.append('<li><i style="background:%s"></i>%s <b>%d%%</b></li>' % (col, E(l), p))
    return ('<div class="donutwrap"><div class="donut" style="background:conic-gradient(%s)">'
            '<span><b>%d</b><i>tranches</i></span></div><ul class="dlegend">%s</ul></div>%s'
            % (", ".join(stops), len(segments), "".join(legend),
               ('<p class="cap">%s</p>' % ref(caption)) if caption else ""))


def gantt(tasks, months, cap=""):
    """tasks: (label, start_pct, end_pct, critical, pct_done, right)"""
    head = "".join("<i>%s</i>" % E(m) for m in months)
    rows = []
    for l, s, e, crit, done, right in tasks:
        cls = "crit" if crit else ""
        rows.append('<div class="grow"><span class="gl %s">%s</span><span class="gtrack">'
                    '<b class="gbar %s" style="left:%s%%;width:%s%%"><i class="gprog" '
                    'style="width:%s%%"></i></b></span><span class="gr %s">%s</span></div>'
                    % (cls, E(l), cls, s, max(e - s, 2), done, cls, E(right)))
    cap = ('<p class="cap">%s</p>' % ref(cap)) if cap else ""
    return ('<div class="gantt"><div class="ghead"><span class="gl">activity</span>'
            '<span class="gtrack monthgrid">%s</span><span class="gr">float</span></div>%s</div>%s'
            % (head, "".join(rows), cap))


def kanban(columns):
    """columns: (header, tone, [(title, code, meta, tone)])"""
    out = ['<div class="kanban">']
    for h, tone, cards in columns:
        cs = "".join('<article class="kcard %s"><b>%s</b><code>%s</code><p>%s</p></article>'
                     % (t, E(ti), E(co), ref(me)) for ti, co, me, t in cards)
        out.append('<div class="kcol %s"><header><span>%s</span><em>%d</em></header>%s%s</div>'
                   % (tone, E(h), len(cards), cs or "",
                      "" if cards else '<p class="kempty">nothing routed here</p>'))
    return "".join(out) + "</div>"


def stepper(steps, cur):
    out = ['<ol class="stepper">']
    for i, s in enumerate(steps):
        state = "done" if i < cur else ("now" if i == cur else "todo")
        out.append('<li class="%s"><span class="dot">%s</span><span class="sl">%s</span></li>'
                   % (state, "&#10003;" if state == "done" else i + 1, E(s)))
    return "".join(out) + "</ol>"


def heat(rows, columns, cells, cap=""):
    """cells: {(probability, impact): label} on a 5x5 ordinal grid."""
    body = []
    for r in range(rows, 0, -1):
        line = ['<tr><th class="hlab">%d</th>' % r]
        for c in range(1, columns + 1):
            hit = cells.get((r, c))
            lvl = min(4, int((r * c) ** 0.5))
            line.append('<td class="h%d">%s</td>' % (lvl, "<i>%s</i>" % E(hit) if hit else ""))
        body.append("".join(line) + "</tr>")
    xl = "".join('<th class="hlab">%d</th>' % c for c in range(1, columns + 1))
    return ('<table class="heat"><tbody>%s<tr><th class="hlab"></th>%s</tr></tbody></table>%s'
            % ("".join(body), xl, ('<p class="cap">%s</p>' % ref(cap)) if cap else ""))


def tabs(tid, items):
    """CSS-only tabs: radio inputs + sibling panels (no JavaScript)."""
    inp, lab, pan = [], [], []
    for i, (name, body) in enumerate(items, 1):
        inp.append('<input type="radio" name="%s" id="%s%d"%s>' % (tid, tid, i, " checked" if i == 1 else ""))
        lab.append('<label for="%s%d">%s</label>' % (tid, i, ref(name)))
        pan.append('<div class="tpanel">%s</div>' % body)
    return ('<div class="tabs n%d">%s<div class="tlab">%s</div><div class="tbody">%s</div></div>'
            % (len(items), "".join(inp), "".join(lab), "".join(pan)))


def filters(items, right=""):
    f = ['<div class="filters">']
    for lab, kind, val in items:
        if kind == "search":
            f.append('<span class="filt"><i>%s</i><input class="in" value="%s"></span>' % (E(lab), E(val)))
        elif kind == "sel":
            opts = "".join('<option%s>%s</option>' % (" selected" if i == 0 else "", E(o))
                           for i, o in enumerate(val))
            f.append('<span class="filt"><i>%s</i><select class="in" disabled>%s</select></span>' % (E(lab), opts))
        elif kind == "date":
            f.append('<span class="filt"><i>%s</i><input class="in" type="date" value="%s" disabled></span>'
                     % (E(lab), E(val)))
        elif kind == "chk":
            ck = "".join('<label class="ck"><input type="checkbox" %s>%s</label>'
                         % (" checked" if on else "", E(o)) for o, on in val)
            f.append('<span class="filt"><i>%s</i>%s</span>' % (E(lab), ck))
    return "".join(f) + '<span class="fright">%s</span></div>' % right


def pager(cur, total, note=""):
    btns = "".join('<a class="pb%s" id="pg-%d" href="#pg-%d">%d</a>'
                   % (" cur" if i == cur else "", i, i, i) for i in range(1, total + 1))
    return ('<div class="pager"><span class="pinfo">%s</span><span class="pbtns">'
            '<a class="pb" id="pg-prev" href="#pg-prev">&#9666;</a>%s'
            '<a class="pb" id="pg-next" href="#pg-next">&#9656;</a></span></div>'
            % (E(note), btns))


def skeleton(rows=4, cols=5):
    head = "".join("<i></i>" for _ in range(cols))
    body = "".join('<div class="sk-row">%s</div>' % head for _ in range(rows))
    return ('<div class="skeleton" role="status" aria-label="loading"><div class="sk-row sk-head">%s</div>%s</div>'
            % (head, body))


def empty(title, body, action=""):
    return ('<div class="empty"><span class="eicon">&#9638;</span><b>%s</b><p>%s</p>%s</div>'
            % (E(title), ref(body), '<span class="eact">%s</span>' % E(action) if action else ""))


def bullets(items, cls="rules", head=None):
    return '<div class="%s">%s<ul>%s</ul></div>' % (
        cls, ('<h4>%s</h4>' % E(head)) if head else "", "".join("<li>%s</li>" % ref(i) for i in items))


def tree(nodes, cap=""):
    """nodes: (depth, code, label, meta, tone)"""
    out = ['<ul class="tree">']
    for d, code, lab, meta, tone in nodes:
        out.append('<li class="%s d%d"><span class="tc"><b>%s</b> %s</span><span class="tm">%s</span></li>'
                   % (tone or "", d, E(code), E(lab), ref(meta)))
    return "".join(out) + "</ul>" + (('<p class="cap">%s</p>' % ref(cap)) if cap else "")


def srcstrip(frame):
    """Data-sources strip: each source table -> schema counts + sibling pages sharing it."""
    out = ['<div class="srcs-strip"><span class="ssl">data sources</span>']
    for t in frame["srcs"]:
        sib = [x for x in TABLE_PAGES.get(t, []) if x != frame["id"]]
        links = "".join('<a href="%s">%s</a>' % (E(PAGE_OF[x]), x) for x in sib) or "<i>only frame</i>"
        out.append('<div class="src-card" id="t-%s"><span class="srcname">%s</span>'
                   '<em>%d cols · %d FK</em><span class="sibs">%s</span></div>'
                   % (E(t), E(t), TNUM[t], TFK[t], links))
    return "".join(out) + "</div>"


# ---------------------------------------------------------------- chrome
SCOPE = ("NBO-221", "Riverside Tower — Mixed Use", "P5 Construction", "GC · Project Manager", "2026-11-20")

HEAD = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>%s</title>\n<link rel="stylesheet" href="%sassets/site.css">\n'
        '<link rel="stylesheet" href="%sassets/print.css" media="print">\n</head>\n')


def rail(frame=None):
    cur = frame["id"] if frame else None
    out = ['<nav class="rail" aria-label="phase rail"><div class="rail-top">'
           '<a class="home" href="../index.html">&#9666; Hub / sitemap</a>'
           '<span class="railproj"><b>%s</b> %s</span></div>' % (SCOPE[0], E(SCOPE[1]))]
    for pk in PHASE_ORDER:
        fr = [f for f in FRAMES if f["phase_key"] == pk]
        openp = " open" if (frame and frame["phase_key"] == pk) else ""
        out.append('<div class="rgrp%s"><span class="rgl"><i class="rdot %s"></i>%s<em>%dT</em></span><ul>'
                   % (openp, pk, E(PHASE_LABEL[pk]), len(PHASE_TABLES[pk])))
        for f in fr:
            out.append('<li><a class="%s" href="%s"><u>%s</u><span>%s</span></a></li>'
                       % ("on" if f["id"] == cur else "", E(f["file"]), E(f["id"]), E(f["title"])))
        out.append("</ul></div>")
    out.append('<div class="rail-foot"><span>Frame pack v1.2 · 25 frames</span>'
               "<span>schema: 45 tables · 320 cols · 84 FK</span></div></nav>")
    return "".join(out)


def topbar(base="../"):
    return ('<header class="topbar"><div class="tb-l"><span class="brand">MERIDIAN<em>CS</em></span>'
            '<span class="scope"><b>%s</b><span>%s</span></span>'
            '<span class="phasecur">%s<span class="caret"></span></span>'
            '<span class="role">%s<span class="caret"></span></span></div>'
            '<div class="tb-r"><span class="qsearch"><u>&#9906;</u>rfi 418'
            "<em>&#9656; 23 hits across 7 tables</em></span>"
            '<span class="asof">data as of <b>%s</b></span>'
            '<span class="ro-badge">read-write</span>'
            '<a class="tb-home" href="%sindex.html">Hub</a></div></header>'
            % (SCOPE[0], E(SCOPE[1]), E(SCOPE[2]), E(SCOPE[3]), E(SCOPE[4]), E(base)))


def breadcrumb(frame):
    return ('<p class="crumbs"><a href="../index.html">Hub</a> <i>&#8250;</i> '
            '<a href="../index.html#%s">%s</a> <i>&#8250;</i> '
            '<b>frame %s</b> <i>&#8250;</i> <span>%s</span></p>'
            % (E(frame["phase_key"]), E(frame["phase"]), E(frame["id"]), E(frame["title"])))


def prevnext(idx):
    p = FRAMES[idx - 1] if idx > 0 else None
    n = FRAMES[idx + 1] if idx + 1 < len(FRAMES) else None
    left = ('<a href="%s"><span>&#9666; previous</span><b>%s · %s</b></a>'
            % (E(p["file"]), E(p["id"]), E(p["title"]))) if p else '<span class="pn-end">&#9666; start of pack</span>'
    right = ('<a href="%s"><span>next &#9656;</span><b>%s · %s</b></a>'
             % (E(n["file"]), E(n["id"]), E(n["title"]))) if n else '<span class="pn-end">end of pack &#9656;</span>'
    return '<div class="prevnext">%s%s</div>' % (left, right)


def rules_panel(frame):
    keep = {k: v for k, v in frame["specs"] if k.startswith(("Primary actions", "Validation", "Roles"))}
    out = ['<details class="spec" open><summary>Frame specification '
           '(from the wireframe pack)</summary><div class="specgrid">']
    for k, items in keep.items():
        out.append("<div><h4>%s</h4><ul>%s</ul></div>"
                   % (E(k), "".join("<li>%s</li>" % ref(i) for i in items)))
    return "".join(out) + "</div></details>"


def page_footer(frame):
    tabs = " · ".join("%s (%d cols)" % (t, TNUM[t]) for t in frame["srcs"])
    return ('<footer class="pgfoot"><div class="pf-row"><span class="prov"><b>Provenance.</b> '
            "Wireframe frame <b>%s</b> — “%s”, group <b>%s</b>. Data-source tables: %s. "
            "Every field name on this page was validated against the parsed schema "
            "(45 tables · 320 columns · 84 FKs) for those tables.</span></div>"
            '<div class="pf-row pf-tabs">%s</div>'
            '<div class="pf-row pf-fine"><span>Static visual demo — no JavaScript, no live queries, '
            "values are illustrative</span><a href=\"../index.html\">Return to hub</a>"
            '<a href="../index.html#provenance">Provenance note</a>'
            "<span>built by gen_site.py</span></div></footer>"
            % (E(frame["id"]), E(frame["title"]), E(frame["phase"]), E(tabs),
               "".join('<a class="ftab" href="%s">%s · %d cols%s</a>'
                       % (E(PAGE_OF[sib[0]]) if (sib := [x for x in TABLE_PAGES[t]
                                                         if x != frame["id"]]) else "../index.html",
                          E(t), TNUM[t], " · also on " + ", ".join(sib) if sib else " · only here")
                       for t in frame["srcs"])))


def clamp_an(text, frame):
    """Only the numbers the source frame actually annotated stay as callouts; regions this
    build adds get a neutral + marker instead of an invented annotation number."""
    allowed = set(frame["anns"])

    def sub(m):
        n = int(m.group(1))
        if n in allowed:
            return m.group(0)
        return ('<span class="an anx" title="region composed for this build — not numbered in '
                'frame %s">+</span>' % E(frame["id"]))
    return re.sub(r'<span class="an" title="wireframe annotation (\d+)">\d+</span>', sub, text)


def page(idx, frame, body, subtitle):
    parts = [HEAD % (E("%s · %s — Meridian CS visual demo" % (frame["id"], frame["title"])), "../", "../"),
             '<body class="pg %s">' % E(frame["phase_key"]), topbar(), '<div class="wrap">', rail(frame),
             '<main class="main">', breadcrumb(frame),
             '<h1>%s<span class="fid">frame %s</span></h1>' % (E(frame["title"]), E(frame["id"])),
             '<p class="sub">%s</p>' % ref(subtitle),
             '<p class="lede"><b>Purpose.</b> %s</p>' % ref(frame["lede"]),
             srcstrip(frame), clamp_an(body, frame), rules_panel(frame), prevnext(idx),
             page_footer(frame),
             "</main></div></body></html>"]
    return "\n".join(parts)


# ------------------------------------------------- region / section interpreter
def section(s):
    """Render one declarative region. Keys: an, label, note, pills, full + kind payload."""
    k = s["k"]
    if k == "raw":
        body = s["html"]
    elif k == "kpi":
        body = kpis(s["items"])
    elif k == "table":
        body = grid(s["cols"], s["rows"], s.get("cls", ""), s.get("foot"), s.get("hint"))
    elif k == "fields":
        body = fields(s["t"], s["names"], s["values"], s.get("states"), s.get("fcols", 2))
    elif k == "chips":
        body = colchips(s["t"], s.get("names"), s.get("caption"))
    elif k == "chipset":
        body = '<div class="chips">%s</div>' % "".join(chip(t, kd, tp) for t, kd, tp in s["items"])
    elif k == "bars":
        body = bars(s["items"], s.get("cap"))
    elif k == "donut":
        body = donut(s["segments"], s.get("cap"))
    elif k == "gantt":
        body = gantt(s["tasks"], s["months"], s.get("cap"))
    elif k == "kanban":
        body = kanban(s["columns"])
    elif k == "stepper":
        body = stepper(s["steps"], s["cur"])
    elif k == "heat":
        body = heat(s["rows"], s["cols"], s["cells"], s.get("cap"))
    elif k == "tabs":
        body = tabs(s["tid"], s["items"])
    elif k == "filters":
        body = filters(s["items"], s.get("right", ""))
    elif k == "pager":
        body = pager(s["cur"], s["total"], s.get("note", ""))
    elif k == "skeleton":
        body = skeleton(s.get("rows", 4), s.get("cols", 5))
    elif k == "empty":
        body = empty(s["title"], s["body"], s.get("action", ""))
    elif k == "tree":
        body = tree(s["nodes"], s.get("cap"))
    elif k == "spark":
        body = '<div class="sparkrow">%s</div>' % "".join(
            '<div class="sparkcard"><h5>%s</h5>%s<span class="spc">%s</span></div>'
            % (E(l), sparkline(v, cls=cls), ref(cap)) for l, v, cap, cls in s["items"])
    elif k == "gauge":
        body = '<div class="gaugerow">%s</div>' % "".join(
            gauge(p, b, sm, t) for p, b, sm, t in s["items"])
    elif k == "banner":
        body = '<div class="banner %s"><b>%s</b><p>%s</p></div>' % (
            s.get("tone", "warn"), E(s["title"]), ref(s["body"]))
    elif k == "kv":
        body = '<dl class="kv">%s</dl>' % "".join(
            "<div><dt>%s</dt><dd>%s</dd></div>" % (ref(a), ref(b)) for a, b in s["items"])
    elif k == "gauge":
        body = '<div class="gaugerow">%s</div>' % "".join(
            '<div class="gauge %s"><span class="ring" style="background:conic-gradient(var(--g-%s) '
            '%s%%,#e3e6eb %s%%)"><b>%s</b><i>%s</i></span></div>'
            % (tone, "bad" if tone == "bad" else ("warn" if tone == "warn" else "ok"),
               pct, 100 - pct, big, small)
            for pct, big, small, tone in s["items"])
    else:
        raise AssertionError("unknown section kind: " + k)
    head = ""
    if s.get("label"):
        head = ('<div class="reg-h"><h3>%s</h3>%s</div>'
                % (ref(s["label"]), "".join(pill(p[0], p[1]) for p in s.get("pills", []))))
    note = ('<p class="rnote">%s</p>' % ref(s["note"])) if s.get("note") else ""
    return '<section class="reg %s%s">%s%s%s</section>' % (
        k, " full" if s.get("full") else "", an(s.get("an")), head, body + note)


def regions(items, layout="stack"):
    cls = {"stack": "rg-stack", "2": "rg-2", "3": "rg-3", "21": "rg-21", "12": "rg-12"}[layout]
    return '<div class="%s">%s</div>' % (cls, "".join(section(x) for x in items))


# ------------------------------------------------------------- per-frame config
CFG["01"] = {
    "type": "shell", "sub": "Persistent chrome · every page in this demo inherits this shell",
    "kpis": [("45", "tables in the parsed schema", "n"), ("7", "phase groups on the rail", "n"),
             ("25", "frames in the wireframe pack", "n"), ("84", "foreign keys resolved", "n"),
             ("2026-11-20", "data currency", "n")],
    "regions": [
        {"k": "tree", "an": 1, "label": "Left rail · phase navigation (7 groups / 45 tables)",
         "cap": "rail entries are navigation only — they carry no write affordances",
         "nodes": [(0, "0" + str(i + 1), PHASE_LABEL[p],
                    "%d tables · %d frames" % (len(PHASE_TABLES[p]),
                                               len([x for x in FRAMES if x["phase_key"] == p])),
                    "now" if i == 3 else "") for i, p in enumerate(PHASE_ORDER)]},
        {"k": "kv", "label": "Top bar · scope, phase, role, data currency", "items": [
            ("Active scope", "NBO-221 · Riverside Tower — Mixed Use · 40 storeys · GFA 118,000 m²"),
            ("Phase chip", "P5 Construction — current_phase on project"),
            ("Role badge", "GC · Project Manager — write on P5, read on SDG layer and carbon credit layer"),
            ("Data as of", "2026-11-20 06:00 UTC — every panel carries its own snapshot time"),
            ("Audit toggle", "read-only view for the registry auditor role strips every write control")]},
        {"k": "table", "an": 2, "label": "Global search · “rfi 418” → 23 hits across 7 tables",
         "hint": "search resolves a project name, a WBS code, an asset serial or a registry reference",
         "cols": [("^", "group"), ("^", "record"), ("^", "matched column"), ("^", "raised"),
                  ("^", "due"), ("^", "state")],
         "rows": [["P5 Construction", "RFI 418", "record id · curtain wall anchor detail", "2026-11-17 09:12",
                   "2026-11-21", (pill("open", "warn"),)],
                  ["P5 Construction", "RFI 417", "linked activity ACT-1108", "2026-11-16 14:03", "2026-11-20",
                   (pill("answered", "ok"),)],
                  ["D12 Design & Funding", "RFI 402", "linked element EL-214", "2026-10-30 11:44", "2026-11-06",
                   (pill("closed", "n"),)],
                  ["P5 Construction", "Submittal 91", "record id · air handler", "2026-11-15 08:20", "2026-11-19",
                   (pill("overdue 1d", "bad"),)],
                  ["Core spine", "WBS E10", "code match", "—", "—", (pill("hit", "n"),)],
                  ["Carbon credit layer", "CC-NBO-021401", "credit serial range", "—", "—", (pill("hit", "n"),)],
                  ["P67 Handover & Operations", "asset SN-88-31", "asset serial", "—", "—", (pill("hit", "n"),)]]},
        {"k": "chipset", "label": "Scope switcher — projects available to this user", "items": [
            ("NBO-221 Riverside Tower", "pk", "current scope"), ("NBO-222 SDG Hub North", "", "P67"),
            ("NBO-218 Harbour Logistics Park", "", "P34"), ("NBO-230 Northbank Data Hall 2", "", "P34"),
            ("NBO-233 University Science Block C", "", "D12"), ("+13 more", "", "")]},
    ],
    "sidebar": [
        {"k": "chipset", "label": "Tables in the core spine", "items": [
            ("project", "pk", "9 cols"), ("site", "fk", "→ project"), ("wbs", "fk", "self-referencing"),
            ("spatial_zone_room", "fk", "→ project"), ("stakeholder", "pk", "4 cols")]},
        {"k": "banner", "tone": "info", "title": "state · project-unselected",
         "body": "with no scope chosen the rail dims, every query returns 0 rows and the register "
                 "(frame 02) is the landing panel"},
        {"k": "empty", "title": "state · session-expired",
         "body": "re-authenticate to continue — 23 cached panels are kept for the resumed session",
         "action": "Sign in again"},
        {"k": "skeleton", "rows": 3, "cols": 6, "label": "state · rail loading"},
    ],
}

CFG["02"] = {
    "type": "register", "sub": "Portfolio root · every downstream frame resolves through project_id",
    "kpis": [("18", "Active projects", "n"), ("$1.24bn", "Sum approved_budget", "n"),
             ("2.1M m²", "Sum gfa_sqm", "n"), ("4", "At risk (critical path slip)", "bad"),
             ("312,400 tCO₂e", "Credits retired YTD", "ok")],
    "filters": [("Search", "search", "Riverside"), ("current_phase", "sel", ["All", "core", "D12", "P34", "P5", "P67"]),
                ("Region", "sel", ["All regions", "EMEA", "APAC", "LATAM"]),
                ("Status", "chk", [("approved", True), ("at risk", True), ("archived", False)]),
                ("Start from", "date", "2025-01-01")],
    "cols": [("project", "project_id"), ("project", "name"), ("project", "rom_budget"),
             ("project", "approved_budget"), ("project", "gfa_sqm"), ("project", "target_start_date"),
             ("project", "target_end_date"), ("project", "current_phase"),
             ("project", "certificate_of_occupancy_date"), ("^", "Δ vs ROM")],
    "rows": [
        ["NBO-221", "Riverside Tower", "$420.0m", "$401.0m", "118,000", "2025-02-17", "2027-09-30", "P5", "—",
         (pill("+2.4%", "warn"),)],
        ["NBO-222", "SDG Hub North", "$132.0m", "$129.4m", "41,500", "2024-11-04", "2026-12-18", "P67",
         "2026-10-02", (pill("-1.9%", "ok"),)],
        ["NBO-218", "Harbour Logistics Park", "$88.5m", "$84.2m", "62,300", "2025-06-02", "2027-03-31", "P34",
         "—", (pill("-4.8%", "ok"),)],
        ["NBO-230", "Northbank Data Hall 2", "$210.0m", "$198.6m", "18,900", "2026-01-19", "2028-05-30", "P34",
         "—", (pill("-5.4%", "ok"),)],
        ["NBO-204", "Civic Library Retrofit", "$46.8m", "$45.1m", "12,400", "2025-03-11", "2026-11-27", "P67",
         "2026-11-06", (pill("-3.6%", "ok"),)],
        ["NBO-233", "University Science Block C", "$164.0m", "$171.3m", "58,700", "2026-04-06", "2028-09-14",
         "D12", "—", (pill("+4.4% — over 15% gate", "bad"),)],
        ["NBO-226", "Airport Cargo Apron 4", "$74.2m", "$71.9m", "88,100", "2025-09-15", "2027-02-26", "P5",
         "—", (pill("-3.1%", "ok"),)],
        ["NBO-240", "Coastal Desalination B", "$95.0m", "—", "9,600", "2027-01-11", "2029-06-30", "core",
         "—", (pill("ROM only", "n"),)],
        ["NBO-215", "Stadium Roof Renewal", "$58.4m", "$56.2m", "21,050", "2024-08-19", "2026-07-31", "P67",
         "2026-07-24", (pill("-3.8%", "ok"),)],
        ["NBO-241", "Green Bond Pilot 5", "$39.6m", "$38.9m", "14,300", "2025-11-03", "2027-06-11", "P5",
         "—", (pill("-1.8%", "ok"),)]],
    "foot": ["Σ", "10 of 18 shown", "$1.42bn", "$1.24bn", "2,104,900", "2024-08", "2029-06", "9 CO issued", "", ""],
    "drawer": {
        "k": "raw", "label": "Row detail drawer — NBO-221 (opens via :target, pure CSS)",
        "html": ('<div class="drawer-host"><a class="drawer-open" href="#row-221">&#9656; open detail '
                 "drawer for NBO-221</a>"
                 '<span id="row-221-close" class="drawer-stop"></span>'
                 '<div class="drawer" id="row-221"><header><span>nested records — site · wbs · '
                 'stakeholder · carbon_project</span><a class="drawer-x" href="#row-221-close">'
                 '&#10005; close</a>'
                 "</header><div class=\"drawer-grid\">"
                 "<div><h4>site</h4><p>parcel PAR-NBO-221 · zoning C-4 · FAR 4.8 · EIA status approved · "
                 "water table 2.6 m</p></div>"
                 "<div><h4>wbs</h4><p>312 nodes · root code A · deepest level 5 · 2 self-references</p></div>"
                 "<div><h4>stakeholder</h4><p>11 organisations · 4 with open rfi rows</p></div>"
                 "<div><h4>carbon_project</h4><p>CP-NBO-01 · registry status verified · 48,200 tCO₂e "
                 "issued</p></div>"
                 "</div></div></div>")},
    "states": [
        {"k": "empty", "title": "filtered-no-results",
         "body": "no project matches region = LATAM + status = archived — 0 of 18 rows", "action": "Clear filters"},
        {"k": "skeleton", "rows": 5, "cols": 10,
         "label": "loading skeleton — structure-accurate: same column count as the resolved grid"}],
}

CFG["03"] = {
    "type": "workspace", "sub": "Single-project landing · read-through aggregations over 10 source tables",
    "stepper": {"k": "stepper", "an": 1, "cur": 3, "full": True,
                "label": "Phase stepper · project.current_phase",
                "steps": list(PHASE_LABEL.values()),
                "note": "current = P5 Construction · the gate into P67 needs every P34 permit granted and "
                        "all NCR rows closed (frame 15)"},
    "tiles": [
        {"k": "kpi", "label": "Budget tile — project + financial_metric", "items": [
            ("$420m", "rom_budget", "n"), ("$401m", "approved_budget", "n"),
            ("$377m", "Committed", "n"), ("$409m", "Forecast at completion", "warn")]},
        {"k": "kpi", "label": "Schedule tile — schedule_activity", "items": [
            ("2027-09", "planned_end (max)", "n"), ("2027-11", "Forecast", "warn"),
            ("-6 d", "total_float_days on critical", "bad"), ("0.94", "SPI", "warn")]},
        {"k": "kpi", "label": "SDG + carbon tile — project_sdg_target / issuance", "items": [
            ("9/14", "targets on track", "ok"), ("48,200 t", "credits issued (tCO₂e)", "n"),
            ("12,500 t", "credits retired (tCO₂e)", "n")]}],
    "regions": [
        {"k": "table", "an": 2, "label": "Cross-table inbox — records needing action",
         "hint": "rows resolve into rfi · submittal · ncr · defect",
         "cols": [("^", "type"), ("^", "ref"), ("^", "subject"), ("^", "owner / link"),
                  ("rfi", "due_date"), ("^", "state"), ("^", "SLA")],
         "rows": [["RFI", "rfi 418", "Curtain wall anchor detail", "SH-002 · EL-214", "2026-11-21",
                   (pill("open", "warn"),), "due in 2 d"],
                  ["Submittal", "submittal 91", "HVAC air handler AHU-3", "SH-022 · EL-318", "2026-11-19",
                   (pill("awaiting review", "bad"),), "over 1 d"],
                  ["NCR", "ncr 12", "Concrete core break below f′c", "wbs E10 · R3-120 Core", "2026-11-24",
                   (pill("unresolved", "bad"),), "blocker"],
                  ["Defect", "defect 7", "Retention release gate", "AST-0031 AHU-3", "2026-12-02",
                   (pill("open", "warn"),), "sla_deadline +12 d"],
                  ["Payment", "app PA-14", "November application uncertified", "CTR-03", "2026-11-28",
                   (pill("draft", "n"),), "cert due 5 d"],
                  ["Permit", "permit PRM-03", "Frame permit expiry", "wbs F3", "2026-12-14",
                   (pill("applied", "warn"),), "expiry 24 d"],
                  ["Punch", "punch PUN-212", "Scoring on glazing", "R3-118", "2026-11-30",
                   (pill("open", "warn"),), "handover blocker"]]},
        {"k": "tree", "an": 3, "label": "WBS roll-up — wbs → boq_item → cost",
         "cap": "cost rolls up via wbs_id and element_id, never onto the rate",
         "nodes": [(0, "A", "Riverside Tower", "$409.0m · 1,204 boq lines", "now"),
                   (1, "E", "Substructure", "$61.4m", ""),
                   (2, "E1", "Foundations", "$24.9m", ""),
                   (3, "E10", "Piling", "$4.1m · 62 %", "ok"),
                   (3, "E11", "Grade beams", "$2.8m · 88 %", "ok"),
                   (2, "E2", "Basal slab", "$18.2m · 41 %", ""),
                   (1, "F", "Superstructure", "$148.6m", "now"),
                   (2, "F3", "Frame", "$38.6m · 26 %", "now"),
                   (1, "G", "Building services", "$74.2m", ""),
                   (1, "H", "Fit-out", "$39.1m", "")]},
    ],
    "aside": [
        {"k": "bars", "label": "Budget consumption", "cap": "derived from approved_budget vs committed",
         "items": [("Approved", 100, "n", "$401.0m"), ("Committed", 94, "a", "$377.0m"),
                   ("Earned value", 61, "ok", "$244.6m"), ("Forecast", 102, "warn", "$409.0m")]},
        {"k": "chipset", "label": "Phase tabs open the rest of the pack", "items": [
            ("06 design economics", "", "D12"), ("08 BOQ & contingency", "", "P34"),
            ("09 schedule & critical path", "", "P34"), ("13 daily progress", "", "P5"),
            ("14 RFI & submittal", "", "P5"), ("17 payments", "", "P5"),
            ("18 handover", "", "P67"), ("21 SDG matrix", "", "SDG"), ("22 credit ledger", "", "CC")]},
        {"k": "banner", "tone": "bad", "title": "blocking banner · covenant headroom 6.4%",
         "body": "raised by the frame 06 rule (headroom < 10%) — funding re-approval is required before "
                 "the next change order routes to the Owner"},
        {"k": "skeleton", "rows": 2, "cols": 4,
         "label": "state · partial aggregation failure — tiles degrade to a skeleton, not a wrong number"}],
}

CFG["04"] = {
    "type": "spine", "sub": "Scope, location and site — the three spines everything else keys off",
    "regions": [
        {"k": "tree", "an": 1, "label": "WBS tree — self-referencing parent_wbs_id",
         "cap": "5 cols · 2 FK (project_id → project, parent_wbs_id → wbs) · 312 nodes, virtualised above 500",
         "nodes": [(0, "E", "Substructure", "wbs_code · Uniclass S30", "now"),
                   (1, "E1", "Foundations", "3,204 m³", ""),
                   (2, "E10", "Piling", "620 bored piles", "ok"),
                   (2, "E11", "Grade beams", "1,140 m", ""),
                   (1, "E2", "Basal slab", "1,240 m³", "now"),
                   (1, "E3", "Basement walls", "880 m³", ""),
                   (0, "F", "Superstructure", "40 storeys", ""),
                   (1, "F3", "Frame", "$38.6m", ""),
                   (0, "G", "Building services", "—", ""),
                   (0, "H", "Fit-out", "—", "")]},
        {"k": "fields", "label": "Selected node — editable fields (wbs)", "t": "wbs", "fcols": 2,
         "names": ["wbs_id", "project_id", "parent_wbs_id", "wbs_code", "description"],
         "values": {"wbs_id": "8f2a…4c11", "project_id": "NBO-221", "parent_wbs_id": "E1 Foundations",
                    "wbs_code": "E10", "description": "Bored piles, 900 mm dia, CFA rig"},
         "states": {"wbs_id": "ro", "project_id": "select", "description": "area"},
         "note": "unsaved-changes guard on · re-parenting E10 under E10 raises the cycle error shown below"},
        {"k": "table", "an": 2, "label": "Spatial zones & rooms — location spine",
         "cols": [("spatial_zone_room", "room_id"), ("spatial_zone_room", "project_id"),
                  ("spatial_zone_room", "level_floor"), ("spatial_zone_room", "room_number"),
                  ("spatial_zone_room", "net_area"), ("spatial_zone_room", "gross_area"),
                  ("spatial_zone_room", "occupancy_load"), ("spatial_zone_room", "acoustic_rating"),
                  ("spatial_zone_room", "fire_rating")],
         "rows": [["R-0118", "NBO-221", 3, "R3-118", "42.6", "51.3", "14", "Rw 52 dB", "EI 60"],
                  ["R-0119", "NBO-221", 3, "R3-119", "38.1", "45.0", "12", "Rw 48 dB", "EI 60"],
                  ["R-0120", "NBO-221", 3, "R3-120 Core", "96.4", "118.2", "60", "—", "EI 120"],
                  ["R-0121", "NBO-221", 4, "R4-118", "42.6", "51.3", "14", "Rw 52 dB", "EI 60"],
                  ["R-0210", "NBO-221", 2, "Plant Room P2", "121.0", "140.5", "6", "Rw 60 dB", "EI 120"],
                  ["R-0305", "NBO-221", 0, "Lobby G-001", "310.4", "356.0", "240", "—", "Open plan"],
                  ["R-0306", "NBO-221", 0, "Retail U-004", "88.9", "104.2", "45", "Rw 48 dB", "EI 60"],
                  ["R-0410", "NBO-221", 7, "R7-210 Meeting", "64.2", "78.6", "22", "Rw 55 dB", "EI 60"]],
         "note": "room_number must be unique per level_floor · acoustic_rating and fire_rating are the "
                 "architect's, not the contractor's"},
        {"k": "fields", "an": 3, "label": "Site & environmental status", "t": "site", "fcols": 3,
         "names": ["site_id", "project_id", "parcel_id", "coordinates", "far", "zoning_code",
                   "soil_bearing_capacity", "water_table_depth", "eia_status"],
         "values": {"site_id": "c41b…9d02", "project_id": "NBO-221", "parcel_id": "PAR-NBO-221",
                    "coordinates": "POINT(-0.1021 51.5007)", "far": "4.8", "zoning_code": "C-4",
                    "soil_bearing_capacity": "240", "water_table_depth": "2.6", "eia_status": "approved"},
         "states": {"site_id": "ro", "coordinates": "ro", "eia_status": "select"},
         "note": "far 4.8 against the C-4 envelope of 5.0 → within limit · eia_status gates the "
                 "carbon_project baseline dates (frame 22)"},
        {"k": "chips", "t": "spatial_zone_room", "label": "spatial_zone_room columns"},
        {"k": "chips", "t": "site", "label": "site columns"},
    ],
    "aside": [
        {"k": "chips", "t": "wbs", "label": "wbs columns"},
        {"k": "empty", "title": "state · orphan node",
         "body": "wbs_code H9 has no parent_wbs_id — it cannot be costed in frame 08 until it is "
                 "re-parented", "action": "Re-parent node"},
        {"k": "banner", "tone": "bad", "title": "rejected · cycle through parent_wbs_id",
         "body": "moving E1 Foundations under E10 Piling would close a loop — the write was refused "
                 "before the graph was touched"},
        {"k": "kv", "label": "Write roles on this frame", "items": [
            ("Architect", "edits wbs and room ratings (RW)"),
            ("GC", "read-only on all three spines"),
            ("Environmental consultant", "edits eia_status only")]}],
}

CFG["05"] = {
    "type": "matrix", "sub": "Actor spine referenced by 84 foreign keys · role × phase access",
    "register": {"k": "table", "label": "Stakeholder register",
                 "cols": [("stakeholder", "stakeholder_id"), ("stakeholder", "organization_name"),
                          ("stakeholder", "role"), ("^", "trade scope (bid_package)"), ("^", "contracts"),
                          ("^", "open items"), ("stakeholder", "contact_info"), ("^", "state")],
                 "rows": [["SH-001", "Northbank Developments", "Owner", "—", "1", "0",
                           "pm@northbank.example", (pill("active", "ok"),)],
                          ["SH-002", "Atelier Kwan Architects", "Architect", "design lead", "1", "3",
                           "studio@akwan.example", (pill("active", "ok"),)],
                          ["SH-004", "Meridian GC", "General Contractor", "enabling works", "1", "6",
                           "contracts@meridian.example", (pill("active", "ok"),)],
                          ["SH-007", "Aurora Facades", "Subcontractor", "curtain wall supply & install",
                           "BP-07", "2", "ops@aurorafacades.example", (pill("active", "ok"),)],
                          ["SH-011", "Kestrel Structures", "Subcontractor", "frame & cores", "BP-03", "4",
                           "delivery@kestrel.example", (pill("unverified org", "warn"),)],
                          ["SH-014", "GridPower Ltd", "Subcontractor", "MV switchgear", "BP-12", "1",
                           "hv@gridpower.example", (pill("active", "ok"),)],
                          ["SH-022", "VertiCo Lifts", "Subcontractor", "elevators", "BP-09", "2",
                           "service@vertico.example", (pill("credential expired", "bad"),)],
                          ["SH-030", "Aster VVB", "Verifier", "issuance audit", "—", "0",
                           "audit@astervvb.example", (pill("read-only", "n"),)],
                          ["SH-041", "Borough Building Control", "Authority", "municipal_inspection",
                           "—", "1", "bc@borough.example", (pill("active", "ok"),)],
                          ["SH-044", "Legacy Sub Ltd", "Subcontractor", "dry lining", "BP-18", "0",
                           "—", (pill("deactivate blocked", "bad"),)]],
                 "note": "SH-044 has no open items today, but the register still refuses deactivation "
                         "while an rfi or submittal row points at the stakeholder_id"},
    "matrix": {"k": "table", "label": "Role × phase permission matrix", "cls": "matrix",
               "cols": [("^", "role")] + [("^", PHASE_LABEL[p]) for p in PHASE_ORDER],
               "rows": [[r[0]] + [(pill(x[0], x[1]),) for x in r[1:]] for r in [
                   ["Owner", ("RW", "ok"), ("RW", "ok"), ("RW", "ok"), ("RW", "ok"), ("RW", "ok"),
                    ("RW", "ok"), ("RW", "ok")],
                   ["Architect", ("RW", "ok"), ("RW", "ok"), ("R", "n"), ("R", "n"), ("R", "n"),
                    ("RW", "ok"), ("RW", "ok")],
                   ["GC", ("R", "n"), ("R", "n"), ("RW", "ok"), ("RW", "ok"), ("RW", "ok"), ("R", "n"),
                    ("R", "n")],
                   ["Subcontractor", ("—", "n"), ("—", "n"), ("R", "n"), ("RW", "ok"), ("R", "n"),
                    ("—", "n"), ("—", "n")],
                   ["Verifier (VVB)", ("—", "n"), ("—", "n"), ("—", "n"), ("R", "n"), ("R", "n"),
                    ("R", "n"), ("R", "n")],
                   ["Registry auditor", ("—", "n"), ("—", "n"), ("—", "n"), ("—", "n"), ("—", "n"),
                    ("R", "n"), ("R", "n")]]],
               "note": "external verifier rows are read-only to all internal roles — the matrix is the "
                       "only place a role is granted, never inherited from the contract"},
    "refs": {"k": "chips", "t": "stakeholder", "label": "stakeholder columns",
             "caption": "4 columns in the parsed schema — org detail that a design brief might split into "
                        "an org table lives here or on contract"},
    "state": {"k": "chipset", "an": 2, "label": "Incoming references on the selected row", "items": [
        ("rfi.stakeholder_id", "fk", "3 open"), ("submittal.stakeholder_id", "fk", "1 open"),
        ("contract.stakeholder_id", "fk", "2 signed"), ("bid_package.trade_scope", "", "awarded BP-07"),
        ("stakeholder.role", "pk", "enum"), ("stakeholder.organization_name", "", "unique"),
        ("stakeholder.contact_info", "", "1 of 4 empty")]},
}

CFG["06"] = {
    "type": "economics", "sub": "Baseline vs revised economics and the capital stack",
    "metrics": {"k": "table", "an": 1, "label": "Metric comparison — baseline vs revised, per wbs",
                "cols": [("financial_metric", "metric_id"), ("financial_metric", "project_id"),
                         ("financial_metric", "version"), ("^", "scenario (wbs)"),
                         ("financial_metric", "roi"), ("financial_metric", "npv"),
                         ("financial_metric", "irr"), ("financial_metric", "cap_rate"),
                         ("financial_metric", "calculated_at"), ("^", "Δ base → revised")],
                "rows": [["FM-2201", "NBO-221", "baseline", "E-Full scheme", "18.4%", "$96.4m", "11.2%",
                          "5.75%", "2026-08-14 09:20", (pill("immutable", "n"),)],
                         ["FM-2231", "NBO-221", "revised", "E-Full scheme", "21.1%", "$112.8m", "10.8%",
                          "5.60%", "2026-11-02 17:05", (pill("+2.7% ROI", "ok"),)],
                         ["FM-2232", "NBO-221", "revised", "Hybrid façade", "19.6%", "$104.1m", "10.4%",
                          "5.90%", "2026-11-02 17:05", (pill("-1.5% ROI", "warn"),)],
                         ["FM-2233", "NBO-221", "revised", "PH1 only", "17.2%", "$88.0m", "12.4%",
                          "6.10%", "2026-10-11 11:32", (pill("+1.2% IRR", "ok"),)],
                         ["FM-2210", "NBO-222", "baseline", "E-Full scheme", "14.8%", "$41.2m", "9.6%",
                          "6.40%", "2026-07-30 08:00", (pill("immutable", "n"),)],
                         ["FM-2240", "NBO-222", "revised", "Timber option", "15.9%", "$45.6m", "9.1%",
                          "6.25%", "2026-11-04 14:12", (pill("+1.1% ROI", "ok"),)],
                         ["FM-2241", "NBO-233", "baseline", "Precast grid", "12.4%", "$52.8m", "8.2%",
                          "7.10%", "2026-06-02 10:45", (pill("stale > 30 d", "warn"),)],
                         ["FM-2242", "NBO-233", "revised", "In-situ option", "13.1%", "$55.0m", "8.6%",
                          "7.25%", "2026-11-18 16:20", (pill("+0.7% ROI", "ok"),)]],
                "note": "the baseline row is append-only — a revision writes a new dated row rather than "
                        "mutating FM-2201"},
    "funding": {"k": "table", "an": 2, "label": "Capital stack — funding_source",
                "cols": [("funding_source", "funding_id"), ("funding_source", "project_id"),
                         ("funding_source", "stakeholder_id"), ("funding_source", "source_type"),
                         ("funding_source", "committed_amount"), ("^", "share"), ("^", "drawn to date")],
                "rows": [["FS-01", "NBO-221", "SH-001 Northbank", "equity", "$136.0m", "34%", "$92.4m"],
                         ["FS-02", "NBO-221", "SH-050 Alder Bank", "senior debt", "$164.5m", "41%", "$71.0m"],
                         ["FS-03", "NBO-221", "SH-051 Green Bond Fund", "green bond", "$72.3m", "18%", "$18.6m"],
                         ["FS-04", "NBO-221", "SH-052 Low-Carbon Grant", "grant", "$28.2m", "7%", "$4.0m"],
                         ["FS-05", "NBO-222", "SH-001 Northbank", "equity", "$48.0m", "45%", "$44.1m"],
                         ["FS-06", "NBO-222", "SH-051 Green Bond Fund", "green bond", "$58.4m", "55%",
                          "$58.4m"]],
                "hint": "source_type is an enum with the four values shown · committed_amount is the "
                        "denominator for the drawdown chart"},
    "donut": {"k": "donut", "label": "Stack composition — committed_amount share",
              "segments": [(64, "#2f5f8f", "senior debt"), (26, "#3d7a70", "equity"),
                           (7, "#c0792f", "green bond"), (3, "#8994a6", "grant")],
              "caption": "green-bond tranches must link to a carbon_project or the covenant check fails"},
    "drawdown": {"k": "raw", "an": 3, "label": "Drawdown schedule vs approved_budget — planned vs drawn",
                 "html": ('<div class="draw"><div class="draw-legend"><span><i class="pl"></i>planned</span>'
                          '<span><i class="dr"></i>drawn</span><span>ceiling — approved_budget $401.0m</span>'
                          "</div>"
                          '<div class="draw-rows">'
                          '<div class="drow"><em>25 Q2</em><i class="pl" style="height:18%"></i>'
                          '<i class="dr" style="height:16%"></i></div>'
                          '<div class="drow"><em>25 Q3</em><i class="pl" style="height:26%"></i>'
                          '<i class="dr" style="height:24%"></i></div>'
                          '<div class="drow"><em>25 Q4</em><i class="pl" style="height:34%"></i>'
                          '<i class="dr" style="height:31%"></i></div>'
                          '<div class="drow"><em>26 Q1</em><i class="pl" style="height:48%"></i>'
                          '<i class="dr" style="height:44%"></i></div>'
                          '<div class="drow"><em>26 Q2</em><i class="pl" style="height:59%"></i>'
                          '<i class="dr" style="height:57%"></i></div>'
                          '<div class="drow"><em>26 Q3</em><i class="pl" style="height:66%"></i>'
                          '<i class="dr" style="height:64%"></i></div>'
                          '<div class="drow"><em>26 Q4</em><i class="pl" style="height:78%"></i>'
                          '<i class="dr" style="height:61%"></i></div>'
                          '<div class="drow"><em>27 Q1</em><i class="pl" style="height:86%"></i></div>'
                          '<div class="drow"><em>27 Q2</em><i class="pl" style="height:93%"></i></div>'
                          '<div class="drow"><em>27 Q3</em><i class="pl" style="height:98%"></i></div>'
                          "</div>"
                          '<p class="cap">headroom at 26 Q4 = 6.4% of approved_budget → below the 10% '
                          "covenant floor, which is what raises the blocking banner in frame 03</p></div>")},
}

STRUCT_T = "structural_element"
MEP_T = "mep_system"
struct_cols = [(STRUCT_T, n) for n in
               ["element_id", "concrete_grade", "rebar_tonnage", "steel_weight", "wind_load",
                "seismic_zone", "foundation_depth"]]
struct_rows = [["EL-214", "C40/50", "42.8", "—", "0.95 kN/m2", "Zone 1", "18.4"],
               ["EL-231", "C40/50", "18.2", "126.4", "0.95 kN/m2", "Zone 1", "18.4"],
               ["EL-090", "C50/60", "31.6", "—", "1.10 kN/m2", "Zone 1", "—"],
               ["EL-240", "C40/50", "88.4", "—", "0.95 kN/m2", "Zone 1", "21.0"],
               ["EL-771", "—", "—", "18.9", "1.35 kN/m2", "Zone 1", "—"],
               ["EL-802", "C30/37", "12.4", "—", "0.95 kN/m2", "Zone 1", "1.2"]]
mep_cols = [(MEP_T, n) for n in
            ["element_id", "system_type", "cooling_heating_load", "kva_demand", "lux_level",
             "flow_rate_lps", "slope"]]
mep_rows = [["EL-318", "HVAC", "148 kW", "62", "—", "1.2", "1:20"],
            ["EL-330", "HVAC", "96 kW", "41", "—", "0.8", "1:25"],
            ["EL-402", "electrical", "—", "420", "—", "—", "—"],
            ["EL-511", "plumbing", "—", "—", "—", "18.4", "1:80"],
            ["EL-512", "fire", "—", "—", "—", "240.0", "1:100"],
            ["EL-620", "lighting", "—", "18", "320 lux", "—", "—"]]

CFG["07"] = {
    "type": "bim", "sub": "IFC element tree · structural / MEP subtype tabs · design control",
    "regions": [
        {"k": "tree", "an": 1, "label": "Element tree from the imported IFC",
         "cap": "7 cols · 3 FK — bim_element is the unified parent, element_id doubles as the subtype PK",
         "nodes": [(0, "L3", "Storey Level 3", "IfcBuildingStorey · 118 elements", "now"),
                   (1, "C-118", "Column C-118", "structural · 600×900 · EL-214", ""),
                   (1, "AHU-3", "Air handling unit AHU-3", "mep · supply 1,800 cfm · EL-318", ""),
                   (2, "D-33", "Supply duct D-33", "mep · 600×400 galvanised", ""),
                   (2, "D-34", "Return duct D-34", "mep — 2 open clashes", "bad"),
                   (1, "B-31", "Beam B-31", "structural · UB 457 · R6 superseded", ""),
                   (0, "L4", "Storey Level 4", "sync in progress 61 %", "warn"),
                   (1, "CW-4A", "Curtain wall panel 4A", "structural · unitised · EL-771", ""),
                   (0, "ROOF", "Plant deck", "element deleted upstream — quarantined", "bad"),
                   (1, "CT-1", "Cooling tower CT-1", "mep · no wbs_id — cannot be costed", "bad")]},
        {"k": "fields", "label": "Shared header — bim_element attributes", "t": "bim_element",
         "fcols": 3, "names": ["element_id", "project_id", "room_id", "wbs_id", "ifc_guid", "discipline",
                               "lod_level"],
         "values": {"element_id": "EL-214", "project_id": "NBO-221", "room_id": "R3-120 Core",
                    "wbs_id": "", "ifc_guid": "3vQrYbTk9S1xYkFQJE4ZnN", "discipline": "structural",
                    "lod_level": "LOD 350"},
         "states": {"ifc_guid": "ro", "wbs_id": "empty", "discipline": "select", "lod_level": "select",
                    "room_id": "select"},
         "note": "the empty wbs_id is a validation failure, not a blank field — 78 elements sit in this "
                 "state and cannot be costed in frame 08"},
    ],
    "tabs": {"k": "tabs", "tid": "sub07", "label": "Subtype grid — one tab per child table",
             "items": [
                 ("structural_element",
                  '<p class="tabintro">inherits element_id from bim_element — no second project_id, '
                  "scope resolves through the parent</p>"
                  + colchips("structural_element")
                  + grid(struct_cols, struct_rows)),
                 ("mep_system",
                  '<p class="tabintro">same parent row, different columns — the tab changes the grid, '
                  "not the schema</p>"
                  + colchips("mep_system")
                  + grid(mep_cols, mep_rows))]},
    "control": {"k": "table", "an": 2, "label": "Design control — revision, clash count, approval",
                "cols": [("design_control", "control_id"), ("design_control", "element_id"),
                         ("design_control", "revision_number"), ("design_control", "clash_count"),
                         ("design_control", "status"), ("design_control", "approved_by"),
                         ("^", "blocks award (frame 11)")],
                "rows": [["DC-881", "EL-214 Column C-118", "R7", "41", (pill("pending", "warn"),), "—",
                          (pill("yes — BP-03 held", "bad"),)],
                         ["DC-882", "EL-318 AHU-3", "R7", "0", (pill("approved", "ok"),), "SH-002",
                          (pill("no", "n"),)],
                         ["DC-883", "EL-330 Duct D-33", "R6", "0", (pill("approved", "ok"),), "SH-002",
                          (pill("no", "n"),)],
                         ["DC-884", "EL-090 Beam B-31", "R7", "12", (pill("superseded", "n"),), "—",
                          (pill("no", "n"),)],
                         ["DC-885", "EL-771 CW panel 4A", "R8", "3", (pill("rejected", "bad"),), "SH-001",
                          (pill("yes — BP-07 held", "bad"),)],
                         ["DC-886", "EL-240 Basal slab", "R5", "0", (pill("approved", "ok"),), "SH-002",
                          (pill("no", "n"),)],
                         ["DC-887", "EL-620 CT-1", "R9", "7", (pill("pending", "warn"),), "—",
                          (pill("no", "n"),)]]},
    "kpis": [("41", "clash_count open", "bad"), ("212", "clashes resolved", "ok"),
             ("350", "median lod_level", "n"), ("78", "elements without wbs_id", "warn"),
             ("3.1 GB", "IFC payload at last sync", "n")],
}

CFG["08"] = {
    "type": "boq", "sub": "Rate build-up on boq_item, rolled up through contingency and change orders",
    "kpis": [("$311.4m", "Base cost", "n"), ("$14.2m", "Risk allowance", "warn"),
             ("$6.9m", "Contingency used", "warn"), ("$409.0m", "Forecast", "bad"),
             ("1,204", "boq lines", "n"), ("8", "lines without a rate", "bad")],
    "filters": [("Line / description", "search", "EL-2"), ("wbs", "sel", ["All", "E", "F", "G", "H"]),
                ("element_id", "chk", [("bound", True), ("missing", True)]),
                ("Rate set", "sel", ["2026 Q3 rateset", "2026 Q4 rateset", "legacy 2025"])],
    "cols": [("boq_item", "boq_id"), ("boq_item", "wbs_id"), ("boq_item", "element_id"),
             ("boq_item", "unit_of_measure"), ("boq_item", "estimated_qty"),
             ("boq_item", "unit_material_rate"), ("boq_item", "unit_labor_rate"),
             ("boq_item", "productivity_norm"), ("^", "line value"), ("^", "state")],
    "rows": [["EL-214", "E2", "EL-214", "m³", "1,240", "88.00", "24.50", "0.55", "$139,420",
              (pill("rated", "ok"),)],
             ["EL-215", "E10", "—", "m", "620", "142.00", "38.00", "0.80", "$111,600",
              (pill("no element_id", "bad"),)],
             ["EL-231", "E11", "EL-231", "m³", "318", "196.00", "52.00", "0.65", "$78,996",
              (pill("rated", "ok"),)],
             ["EL-244", "F3", "EL-090", "t", "412", "1,240.00", "180.00", "1.20", "$585,040",
              (pill("rated", "ok"),)],
             ["EL-250", "F3", "EL-771", "m²", "8,740", "64.50", "28.00", "2.40", "$810,830",
              (pill("rate review", "warn"),)],
             ["EL-263", "G1", "EL-318", "no", "14", "3,850.00", "620.00", "0.30", "$62,580",
              (pill("rated", "ok"),)],
             ["EL-271", "H2", "—", "m²", "18,400", "41.00", "19.50", "3.10", "$1,113,200",
              (pill("rated", "ok"),)],
             ["EL-284", "E3", "EL-284", "m³", "902", "—", "—", "—", "$155,144",
              (pill("missing rate — cannot compute", "bad"),)],
             ["EL-296", "G2", "EL-296", "kg", "24,600", "3.40", "0.90", "8.60", "$105,780",
              (pill("rated", "ok"),)],
             ["EL-307", "F5", "EL-307", "m²", "5,120", "22.80", "11.40", "1.90", "$175,104",
              (pill("rated", "ok"),)]],
    "cont": {"k": "table", "label": "Contingency drawdown — design / construction / VE reserve",
             "cols": [("contingency", "contingency_id"), ("contingency", "wbs_id"),
                      ("contingency", "type"), ("contingency", "allocated_amount"),
                      ("contingency", "remaining_amount"), ("^", "consumed"),
                      ("change_order", "change_order_id")],
             "rows": [["CN-01", "E1", "design", "$2.10m", "$0.60m", "71.4%", "CO-31"],
                      ["CN-02", "E2", "construction", "$6.40m", "$4.15m", "35.2%", "CO-27"],
                      ["CN-03", "F3", "construction", "$5.20m", "$3.90m", "25.0%", "—"],
                      ["CN-04", "G1", "VE reserve", "$2.80m", "$2.80m", "0.0%", "CO-19 rejected"],
                      ["CN-05", "H2", "design", "$1.40m", "$0.22m", "84.3%", "CO-33"],
                      ["CN-06", "G2", "VE reserve", "$1.10m", "$1.10m", "0.0%", "CO-30 pending"]],
             "note": "a transfer into base cost must reference the change_order that consumed it — CN-06 "
                     "cannot be drawn until CO-30 is approved"},
    "cos": {"k": "table", "label": "change_order rows affecting this roll-up",
            "cols": [("change_order", "change_order_id"), ("change_order", "contract_id"),
                     ("change_order", "wbs_id"), ("change_order", "approved_variation_value"),
                     ("change_order", "description")],
            "rows": [["CO-31", "CTR-03", "E10", "+$1.90m", "Ground conditions — dewatering duration ×3"],
                     ["CO-27", "CTR-03", "E20", "-$0.42m", "Basal slab pour joints re-sequenced"],
                     ["CO-33", "CTR-07", "H2", "+$1.18m", "Fit-out specification upgrade"],
                     ["CO-30", "CTR-09", "G2", "+$0.56m", "Switchgear rating — awaiting owner"],
                     ["CO-34", "CTR-07", "F3", "-$200.0k", "Delete redundant roof plant"],
                     ["CO-35", "CTR-18", "H1", "+$840.0k", "Overboard rescue boat davits"]]},
    "editor": {"k": "fields", "label": "Rate editor — selected line EL-284", "t": "boq_item",
               "fcols": 3,
               "names": ["boq_id", "project_id", "wbs_id", "element_id", "unit_of_measure",
                         "estimated_qty", "unit_material_rate", "unit_labor_rate", "productivity_norm"],
               "values": {"boq_id": "EL-284", "project_id": "NBO-221", "wbs_id": "E3",
                          "element_id": "EL-284", "unit_of_measure": "m³", "estimated_qty": "902",
                          "unit_material_rate": "", "unit_labor_rate": "", "productivity_norm": ""},
               "states": {"boq_id": "ro", "unit_material_rate": "empty", "unit_labor_rate": "empty",
                          "productivity_norm": "empty", "wbs_id": "select"},
               "note": "without productivity_norm the duration in frame 09 cannot be computed — the line "
                       "is excluded from the schedule build"},
    "pager": {"k": "pager", "cur": 3, "total": 8, "note": "lines 21–30 of 1,204 · 8 pages"},
    "kpi_an": 2,
}

CFG["09"] = {
    "type": "gantt", "sub": "schedule_activity over the activity_dependency graph · float · critical path",
    "months": ["Q1 26", "Q2 26", "Q3 26", "Q4 26", "Q1 27", "Q2 27", "Q3 27"],
    "tasks": [("E10 Piling", 0, 14, True, 62, "-6 d"), ("E20 Basal slab", 12, 30, True, 41, "-4 d"),
              ("F30 Frame L1-12", 28, 46, False, 26, "9 d"), ("F31 Frame L13-24", 44, 62, False, 8, "14 d"),
              ("G1 MEP risers", 52, 74, False, 12, "6 d"), ("G2 MV switchgear", 60, 70, True, 4, "-2 d"),
              ("H1 Envelope", 66, 84, False, 0, "11 d"), ("H2 Fit-out L1-6", 78, 96, True, 0, "-1 d")],
    "ledger": {"k": "table", "label": "Activity ledger — schedule_activity",
               "cols": [("schedule_activity", "activity_id"), ("schedule_activity", "wbs_id"),
                        ("schedule_activity", "room_id"), ("schedule_activity", "planned_start"),
                        ("schedule_activity", "planned_end"), ("schedule_activity", "actual_start"),
                        ("schedule_activity", "actual_end"), ("schedule_activity", "duration_days"),
                        ("schedule_activity", "total_float_days"), ("schedule_activity", "is_critical_path")],
               "rows": [["ACT-1102", "E10", "—", "2026-02-04", "2026-03-12", "2026-02-06", "2026-03-20",
                         "38", "-6", (pill("critical", "bad"),)],
                        ["ACT-1108", "E20", "—", "2026-03-15", "2026-06-30", "2026-03-22", "—",
                         "107", "-4", (pill("critical", "bad"),)],
                        ["ACT-1204", "F3", "R3-120 Core", "2026-06-14", "2026-11-02", "2026-06-20", "—",
                         "141", "9", (pill("float 9 d", "n"),)],
                        ["ACT-1211", "G1", "R-0210", "2026-09-01", "2027-01-18", "—", "—",
                         "139", "6", (pill("planned", "n"),)],
                        ["ACT-1218", "G2", "R-0210", "2026-10-12", "2026-12-06", "—", "—",
                         "55", "-2", (pill("critical", "bad"),)],
                        ["ACT-1305", "H2", "R3-118", "2027-01-04", "2027-05-21", "—", "—",
                         "137", "-1", (pill("critical", "bad"),)],
                        ["ACT-1310", "H1", "R4-118", "2026-12-01", "2027-03-15", "—", "—",
                         "104", "11", (pill("not started", "warn"),)],
                        ["ACT-1320", "E3", "—", "2026-04-20", "2026-05-30", "2026-04-22", "2026-06-04",
                         "40", "3", (pill("complete", "ok"),)]],
               "note": "planned dates are immutable once baselined — ACT-1211 sits on baseline B3 and a "
                       "change writes a new baseline row"},
    "deps": {"k": "table", "an": 2, "label": "Dependency bridge — activity_dependency",
             "cols": [("activity_dependency", "dependency_id"), ("activity_dependency", "predecessor_id"),
                      ("activity_dependency", "successor_id"), ("activity_dependency", "dependency_type"),
                      ("activity_dependency", "lag_days"), ("^", "effect")],
             "rows": [["DP-401", "ACT-1102", "ACT-1108", "FS", "3", "drives the basal slab start"],
                      ["DP-402", "ACT-1108", "ACT-1204", "FS", "14", "cure time before frame start"],
                      ["DP-403", "ACT-1204", "ACT-1211", "SS", "30", "riser pre-install overlaps"],
                      ["DP-404", "ACT-1218", "ACT-1305", "FF", "-5", "power-on before fit-out finish"],
                      ["DP-405", "ACT-1310", "ACT-1305", "FS", "10", "dry-in gate"],
                      ["DP-406", "ACT-1211", "ACT-1204", "FS", "-140",
                       (pill("rejected — cycle in graph", "bad"),)],
                      ["DP-407", "ACT-1320", "ACT-1204", "FS", "0", "wall top-out link"]],
             "note": "float and critical path are recomputed from this graph, never stored by hand"},
    "weather": {"k": "table", "label": "Idle-weather cross-check — no stored link column",
                "hint": "matched on log_date only — both dates must fall inside the activity window for an "
                        "extension-of-time claim",
                "cols": [("site_weather_log", "log_date"), ("site_weather_log", "wind_kmh"),
                         ("site_weather_log", "rainfall_mm"), ("daily_progress", "headcount"),
                         ("daily_progress", "percent_complete"), ("^", "EOT eligibility")],
                "rows": [["2026-11-18", "62", "6.2", "0", "no change",
                          (pill("eligible — stand-down", "warn"),)],
                         ["2026-11-17", "48", "0.0", "38", "60.5 → 62.0", (pill("productive", "ok"),)],
                         ["2026-11-16", "71", "12.4", "0", "no change", (pill("eligible", "warn"),)],
                         ["2026-11-13", "66", "9.8", "0", "no change", (pill("eligible", "warn"),)],
                         ["2026-11-12", "39", "0.4", "34", "55.0 → 57.5", (pill("productive", "ok"),)],
                         ["2026-05-08", "58", "22.6", "0", "no change",
                          (pill("outside window — refused", "bad"),)]]},
}

CFG["10"] = {
    "type": "risk", "sub": "Statutory permissions and the scored risk register",
    "perm": {"k": "table", "an": 1, "label": "Permit board — status, fee, expiry",
             "cols": [("permit", "permit_id"), ("permit", "wbs_id"), ("permit", "status"),
                      ("permit", "fee_amount"), ("permit", "expiry_date"), ("^", "days to expiry"),
                      ("^", "gate")],
             "rows": [["PRM-01", "E1", (pill("granted", "ok"),), "$8,400", "2027-01-12", "55",
                      (pill("cleared", "ok"),)],
                      ["PRM-02", "E2", (pill("granted", "ok"),), "$12,150", "2027-04-02", "135",
                       (pill("cleared", "ok"),)],
                      ["PRM-03", "F3", (pill("applied", "warn"),), "$6,900", "2026-12-14", "24",
                       (pill("expiry < 30 d — banner", "bad"),)],
                      ["PRM-04", "E1", (pill("applied", "warn"),), "$3,200", "2026-12-20", "30",
                       (pill("dewatering", "n"),)],
                      ["PRM-05", "G", (pill("under review", "n"),), "$18,750", "2027-08-30", "283",
                       (pill("—", "n"),)],
                      ["PRM-06", "H", (pill("refused", "bad"),), "$1,450", "—", "—",
                       (pill("resubmit required", "bad"),)],
                      ["PRM-07", "E3", (pill("granted", "ok"),), "$4,300", "2027-02-28", "102",
                       (pill("cleared", "ok"),)]],
             "note": "an expiring permit inside 30 days raises a cross-frame banner — PRM-03 is the live "
                     "one and it blocks the F3 award in frame 11"},
    "heat": {"k": "heat", "an": 2, "rows": 5, "cols": 5,
             "label": "Risk heat map — probability_score × impact_score",
             "cells": {(4, 4): "R-14", (5, 5): "R-07", (3, 5): "R-02", (5, 3): "R-04", (2, 4): "R-11",
                       (4, 2): "R-05", (3, 3): "R-09"},
             "cap": "both axes are ordinal 1–5, not percentages · exposure = probability × impact"},
    "risk": {"k": "table", "label": "Risk ledger with mitigation log",
             "cols": [("risk_register", "risk_id"), ("risk_register", "wbs_id"),
                      ("risk_register", "probability_score"), ("risk_register", "impact_score"),
                      ("^", "exposure"), ("risk_register", "mitigation_log"), ("^", "owner")],
             "rows": [["R-07", "E1", "5", "5", "25", "Dewatering permit extended, drawdown telemetry added",
                       "SH-004"],
                      ["R-14", "F3", "4", 5, "20", "Labour for L13-24 — named crew clause signed", "SH-004"],
                      ["R-02", "G2", "3", "5", "15", "MV switchgear lead time — second vendor prequalified",
                       "SH-014"],
                      ["R-04", "E2", "4", "3", "12", "Thermal mat on basal slab approved, cure monitored",
                       "SH-004"],
                      ["R-05", "H1", "5", "2", "10", "Glazing scaffold interface — weekly walk", "SH-007"],
                      ["R-09", "F3", "2", "5", "10", "Rebar congestion resolved in BIM, RFI-394 closed",
                       "SH-011"],
                      ["R-11", "F4", "2", "4", "8", "Tower crane out of service 2027-03-15 — barge option "
                       "priced", "SH-011"],
                      ["R-18", "—", "5", "1", "5", "closed: site-wide power disruption drill", "—"]],
             "note": "R-18 is closed but its linked activity ACT-1204 is still open — the state "
                     "'risk closed but linked activity open' is raised on the row"},
    "site": {"k": "chips", "t": "site", "label": "site columns the risk register leans on",
             "caption": "groundwater and bearing capacity feed the construction method statement"},
    "banner": {"k": "banner", "tone": "bad", "title": "expiry banner",
               "body": "1 permit expires in 30 days and 1 is refused — both block activities on the "
                       "critical path shown in frame 09"},
}

CFG["11"] = {
    "type": "procurement", "sub": "bid_package scoring, contract award, bond and insurance expiry",
    "bids": {"k": "table", "an": 1, "label": "Bid comparison grid — one row per package",
             "cols": [("bid_package", "bid_package_id"), ("bid_package", "trade_scope"),
                      ("bid_package", "prequal_score"), ("bid_package", "bid_variance_pct"),
                      ("^", "recommendation"), ("^", "state")],
             "rows": [["BP-03", "Structural frame & cores", "88.4", "+1.8%",
                       (pill("award SH-011", "ok"),), (pill("signed", "ok"),)],
                      ["BP-06", "Basement & enabling works", "79.6", "-4.1%",
                       (pill("award SH-004", "ok"),), (pill("signed", "ok"),)],
                      ["BP-07", "Curtain wall supply & install", "82.5", "+3.1%",
                       (pill("award SH-007", "ok"),), (pill("negotiated", "warn"),)],
                      ["BP-09", "Elevators", "74.0", "-8.4%", (pill("award SH-022", "warn"),),
                       (pill("draft", "n"),)],
                      ["BP-12", "MV switchgear", "91.2", "+12.0%",
                       (pill("written justification required", "bad"),), (pill("packages open", "bad"),)],
                      ["BP-15", "Dry lining & interiors", "68.9", "-11.6%",
                       (pill("rebid recommended", "bad"),), (pill("packages open", "bad"),)],
                      ["BP-18", "Fit-out packages L1-6", "81.0", "+0.4%",
                       (pill("award SH-044", "warn"),), (pill("award under appeal", "warn"),)],
                      ["BP-21", "Landscaping & public realm", "76.2", "+5.5%", (pill("hold", "n"),),
                       (pill("prequal expired", "n"),)]],
             "note": "bid_variance_pct beyond ±10% blocks the award until a written justification is "
                     "attached — BP-12 and BP-15 are held on that rule"},
    "award": {"k": "fields", "an": 2, "label": "Award panel — contract", "t": "contract", "fcols": 2,
              "names": ["contract_id", "project_id", "bid_package_id", "stakeholder_id", "award_value",
                        "retention_pct", "insurance_expiry", "bond_number"],
              "values": {"contract_id": "CTR-07", "project_id": "NBO-221", "bid_package_id": "BP-07",
                         "stakeholder_id": "SH-007", "award_value": "14,860,000", "retention_pct": "5.0",
                         "insurance_expiry": "2027-03-31", "bond_number": "PB-NBO-07-A"},
              "states": {"contract_id": "ro", "award_value": "invalid", "stakeholder_id": "select",
                         "insurance_expiry": "date", "retention_pct": ""},
              "note": "award_value is shown in its error state: it exceeds the approved headroom for "
                      "BP-07, so certification is refused before the row is written"},
    "bonds": {"k": "table", "an": 3, "label": "Bond & insurance expiry — contract columns",
              "cols": [("contract", "contract_id"), ("contract", "bond_number"),
                       ("contract", "insurance_expiry"), ("contract", "stakeholder_id"),
                       ("^", "days to expiry"), ("^", "consequence")],
              "rows": [["CTR-03", "PB-NBO-03-B", "2027-06-30", "SH-011 Kestrel Structures", "222",
                        (pill("ok", "ok"),)],
                       ["CTR-07", "PB-NBO-07-A", "2027-03-31", "SH-007 Aurora Facades", "131",
                        (pill("ok", "ok"),)],
                       ["CTR-09", "PB-NBO-09-C", "2026-12-14", "SH-022 VertiCo Lifts", "24",
                        (pill("renew ≪ 30 d — blocks next payment cert", "bad"),)],
                       ["CTR-12", "PB-NBO-12-A", "2027-01-08", "SH-014 GridPower Ltd", "49",
                        (pill("watch", "warn"),)],
                       ["CTR-18", "— not on file —", "2026-11-30", "SH-044 Legacy Sub Ltd", "10",
                        (pill("suspended — no bond_number", "bad"),)]]},
    "flow": {"k": "chipset", "an": 4, "label": "Award state machine", "items": [
        ("1 · draft", "", "contract row created from the award panel"),
        ("2 · negotiated", "", "variance justification attached"),
        ("3 · signed", "", "bond + insurance registered"),
        ("4 · issued to site", "pk", "POs may now reference the contract (frame 12)")],
        "note": "bonds and insurance are columns on contract — there is no performance_bond or "
                "insurance_policy table in this schema"},
}

CFG["12"] = {
    "type": "supply", "sub": "purchase_order register and supply_shipment track / trace",
    "pos": {"k": "table", "an": 1, "label": "PO register",
            "cols": [("purchase_order", "po_id"), ("purchase_order", "contract_id"),
                     ("purchase_order", "boq_id"), ("purchase_order", "unit_cost"),
                     ("purchase_order", "lead_time_days"), ("^", "line value"), ("^", "state")],
            "rows": [["PO-3341", "CTR-07 · BP-07", "EL-250", "$412,500", "96", "$14.70m",
                      (pill("placed", "ok"),)],
                     ["PO-3342", "CTR-09 · BP-09", "EL-263", "$388,000", "134", "$5.43m",
                      (pill("placed", "ok"),)],
                     ["PO-3350", "CTR-12 · BP-12", "EL-296", "$29,400", "112", "$2.86m",
                      (pill("partial delivery", "warn"),)],
                     ["PO-3355", "CTR-03 · BP-03", "EL-244", "$1,840", "42", "$4.62m",
                      (pill("received", "ok"),)],
                     ["PO-3361", "CTR-07 · BP-07", "EL-214", "$3,120", "88", "$3.90m",
                      (pill("draft", "n"),)],
                     ["PO-3370", "CTR-18 · BP-18", "EL-271", "$960", "35", "$1.18m",
                      (pill("blocked — contract not signed", "bad"),)]],
            "hint": "a PO may only reference a line under a signed contract, and boq_id must exist on "
                    "that award"},
    "miles": {"k": "chipset", "an": 2, "label": "Track & trace milestones for SHP-88", "items": [
        ("1 · fabrication 68 %", "", "supply_shipment.fabrication_pct"),
        ("2 · ETD 2026-11-28", "", "supply_shipment.etd"),
        ("3 · ETA 2026-12-19", "warn", "supply_shipment.eta"),
        ("4 · customs cleared — pending", "pk",
         "customs_cleared_at must be set before delivery against an on-site activity")]},
    "trace": {"k": "table", "an": 2, "label": "Shipment track & trace",
              "cols": [("supply_shipment", "shipment_id"), ("supply_shipment", "po_id"),
                       ("supply_shipment", "fabrication_pct"), ("supply_shipment", "etd"),
                       ("supply_shipment", "eta"), ("supply_shipment", "customs_cleared_at"),
                       ("^", "risk")],
              "rows": [["SHP-88", "PO-3341", "68", "2026-11-28", "2026-12-19", "(pending)",
                        (pill("on plan", "ok"),)],
                       ["SHP-89", "PO-3342", "94", "2026-11-24", "2026-12-12", "2026-12-16",
                        (pill("clear", "ok"),)],
                       ["SHP-90", "PO-3350", "55", "2026-12-06", "2027-01-22", "—",
                        (pill("ETA slipped 12 d", "warn"),)],
                       ["SHP-91", "PO-3350", "30", "2027-01-14", "2027-02-28", "held at port",
                        (pill("customs held", "bad"),)],
                       ["SHP-92", "PO-3355", "100", "2026-10-30", "2026-11-16", "2026-11-19",
                        (pill("delivered", "ok"),)],
                       ["SHP-93", "PO-3361", "12", "2027-01-30", "2027-03-04", "—",
                        (pill("no bookings", "n"),)]],
              "note": "lead_time_days 96 against the planned start 2026-11-20 — the late arrival lands on "
                      "the -6 d float of ACT-1102 in frame 09"},
    "mat": {"k": "fields", "an": 3, "label": "Material attributes — boq_item stands in for a catalogue",
            "t": "boq_item", "fcols": 2,
            "names": ["boq_id", "unit_of_measure", "estimated_qty", "unit_material_rate",
                      "productivity_norm"],
            "values": {"boq_id": "EL-214", "unit_of_measure": "m³", "estimated_qty": "1,240",
                       "unit_material_rate": "88.00", "productivity_norm": "0.55"},
            "states": {"boq_id": "ro"},
            "note": "per-unit embodied carbon is NOT a column in this schema — carbon provenance is "
                    "carried by the credit ledger (frame 22) and the site logs (frame 16)"},
    "states": [{"k": "empty", "title": "no shipments booked",
                "body": "PO-3361 is placed but has no supply_shipment row — book a vessel slot or void "
                        "the line", "action": "Book shipment"},
               {"k": "banner", "tone": "bad", "title": "ETA slipped · customs held",
                "body": "SHP-91 has been held since 2027-02-04 and two activities lose their only feeder"}],
}

CFG["13"] = {
    "type": "progress", "sub": "daily_progress field log feeding the earned-value read-out",
    "form": {"k": "fields", "an": 1, "label": "Field log form — daily_progress", "t": "daily_progress",
             "fcols": 3,
             "names": ["progress_id", "activity_id", "boq_id", "log_date", "headcount", "man_hours",
                       "equipment_hours", "percent_complete", "earned_value_ev", "actual_cost_ac"],
             "values": {"progress_id": "auto · 9d31…", "activity_id": "ACT-1204 F30 L4 frame",
                        "boq_id": "EL-244", "log_date": "2026-11-19", "headcount": "38",
                        "man_hours": "412", "equipment_hours": "96", "percent_complete": "62.0",
                        "earned_value_ev": "1180000", "actual_cost_ac": "1120000"},
             "states": {"progress_id": "ro", "log_date": "date", "man_hours": "invalid",
                        "percent_complete": "warn", "activity_id": "select", "boq_id": "select"},
             "note": "man_hours is flagged, not blocked: 412 against headcount 38 × an 8-hour shift = 304, "
                     "and beyond 2× the shift model raises a data-quality warning"},
    "log": {"k": "table", "label": "Log rows — one per activity per log_date",
            "cols": [("daily_progress", "log_date"), ("daily_progress", "activity_id"),
                     ("daily_progress", "headcount"), ("daily_progress", "man_hours"),
                     ("daily_progress", "equipment_hours"), ("daily_progress", "percent_complete"),
                     ("daily_progress", "earned_value_ev"), ("daily_progress", "actual_cost_ac")],
            "rows": [["2026-11-19", "ACT-1204 F30 L4 frame", "38", "412", "96", "62.0", "$1.18m", "$1.12m"],
                     ["2026-11-19", "ACT-1211 G1 MEP risers", "11", "98", "6", "41.0", "$0.31m", "$0.34m"],
                     ["2026-11-18", "ACT-1204 F30 L4 frame", "36", "288", "92", "60.5", "$1.11m", "$1.06m"],
                     ["2026-11-18", "ACT-1108 E20 basal slab", "22", "176", "24", "41.0", "$0.62m", "$0.71m"],
                     ["2026-11-17", "ACT-1204 F30 L4 frame", "40", "320", "98", "59.0", "$1.06m", "$1.02m"],
                     ["2026-11-17", "ACT-1218 G2 switchgear", "6", "48", "2", "4.0", "$0.09m", "$0.14m"],
                     ["2026-11-16", "ACT-1204 F30 L4 frame", "34", "272", "88", "57.5", "$1.04m", "$0.99m"],
                     ["2026-11-16", "— activity_id null —", "3", "24", "0", "—", "$0.00m", "$0.06m"],
                     ["2026-11-15", "ACT-1310 H1 envelope", "18", "144", "12", "3.0", "$0.05m", "$0.11m"],
                     ["2026-11-14", "ACT-1108 E20 basal slab", "26", "208", "30", "38.0", "$0.58m", "$0.63m"]],
            "hint": "row 8 cannot post to EV because activity_id is null — QC hold-point (frame 15) "
                    "separately gates the basal slab percentage"},
    "split": {"k": "table", "an": 2, "label": "Trade split — derived (no labour table in schema)",
              "cols": [("^", "trade_scope · bid_package"), ("^", "organization_name · stakeholder"),
                       ("^", "man_hours"), ("^", "share"), ("^", "provenance")],
              "rows": [["Structural frame & cores", "Kestrel Structures", "196", "39%",
                        (pill("derived", "n"),)],
                       ["Curtain wall supply & install", "Aurora Facades", "128", "26%",
                        (pill("derived", "n"),)],
                       ["MV switchgear", "GridPower Ltd", "54", "11%", (pill("derived", "n"),)],
                       ["Elevators", "VertiCo Lifts", "42", "8%", (pill("derived", "n"),)],
                       ["Basement & enabling works", "Meridian GC", "68", "13%", (pill("derived", "n"),)],
                       ["Unassigned", "—", "24", "5%", (pill("needs contract link", "warn"),)]],
              "foot": ["Σ", "5 organisations", "412", "100%", "contract → stakeholder"],
              "note": "daily_progress_labor does not exist here: the split walks daily_progress → "
                      "schedule_activity → contract → stakeholder and is labelled derived"},
    "curve": {"k": "raw", "an": 3, "full": True,
              "label": "S-curve — cumulative earned_value_ev vs actual_cost_ac vs planned value",
              "html": ('<div class="scurve"><div class="sc-grid"></div>'
                       '<svg viewBox="0 0 300 90" preserveAspectRatio="none" class="sc-svg" '
                       'aria-hidden="true">'
                       '<polyline points="0,86 30,80 60,70 90,58 120,46 150,36 180,28 210,20 240,14 '
                       '270,10 300,7" fill="none" stroke="var(--accent)" stroke-width="2"/>'
                       '<polyline points="0,88 30,83 60,74 90,63 120,52 150,43 180,35 210,28 240,23 '
                       '270,19 300,16" fill="none" stroke="#8994a6" stroke-width="2" stroke-dasharray="4 3"/>'
                       '<polyline points="0,87 30,82 60,75 90,66 120,58 150,50 180,43 210,37 240,32 '
                       '270,28 300,25" fill="none" stroke="#c0792f" stroke-width="2"/></svg>'
                       '<ul class="sc-key"><li><i class="k-a"></i>earned_value_ev cumulative</li>'
                       '<li><i class="k-b"></i>actual_cost_ac cumulative</li>'
                       "<li><i class=\"k-c\"></i>planned value (baseline)</li></ul>"
                       '<div class="sc-read"><span>SPI <b>0.94</b></span><span>CPI <b>0.97</b></span>'
                       "<span>Variance <b>-$9.4m</b></span><span>as of <b>2026-11-19</b></span></div></div>"),
              "note": "a static polyline over the same series — no script and no live redraw"},
    "kpis": [("$244.6m", "cumulative earned_value_ev", "n"), ("$252.1m", "cumulative actual_cost_ac", "warn"),
             ("0.94", "SPI", "warn"), ("0.97", "CPI", "warn"), ("$184.6m", "remaining to forecast", "n")],
}

CFG["14"] = {
    "type": "kanbanflow", "sub": "rfi and submittal boards on one clock (submitted_at → due_date → closed_at)",
    "board": {"k": "kanban", "an": 1, "full": True, "label": "Kanban with SLA ageing",
              "note": "days open = now − due_date · closed on closed_at · the overdue column recolours "
                      "under the SLA breach rule",
              "columns": [
                  ("draft", "c1", [
                      ("RFI-422 · anchor detail", "rfi 422", "due 2026-11-26 · not yet submitted", "n")]),
                  ("submitted", "c2", [
                      ("RFI-420 · slab penetration", "rfi 420", "submitted_at 2026-11-18 · EL-244", "n"),
                      ("SUB-092 · rebar cage", "submittal 92", "submitted 2026-11-17 · ACT-1108", "n"),
                      ("RFI-419 · core set-out", "rfi 419", "submitted 2026-11-16 · R3-120 Core", "n")]),
                  ("awaiting response", "c3", [
                      ("RFI-418 · curtain wall anchor", "rfi 418", "OVERDUE 1 d · due_date 2026-11-19",
                       "bad"),
                      ("SUB-091 · AHU-3 air handler", "submittal 91", "open 4 d · due 2026-11-23", "warn"),
                      ("SUB-090 · weld procedure", "submittal 90",
                       "8 d · cost_schedule_impact_flag = true", "bad")]),
                  ("answered", "c4", [
                      ("RFI-415 · duct clash", "rfi 415", "code B · resubmit with revised model", "warn"),
                      ("RFI-412 · waterproofing lap", "rfi 412", "code A · no change", "n")]),
                  ("closed", "c5", [
                      ("SUB-088 · CW mock-up", "submittal 88", "closed_at 2026-11-12 · SH-002", "ok"),
                      ("RFI-402 · pile cap depth", "rfi 402", "closed_at 2026-11-04 · code A", "ok"),
                      ("RFI-399 · lift pit dewatering", "rfi 399", "closed_at 2026-10-29 · archive", "ok")]),
                  ("archived", "c6", [])]},
    "chain": {"k": "table", "an": 2, "label": "Review chain — derived (no submittal_review table)",
              "cols": [("^", "step"), ("^", "channel"), ("rfi", "stakeholder_id"), ("^", "state"),
                       ("^", "days with reviewer"), ("^", "gate")],
              "rows": [["1 · site engineer", "rfi 418", "SH-011", (pill("code A", "ok"),), "1",
                       (pill("signed", "ok"),)],
                      ["2 · architect", "rfi 418", "SH-002", (pill("pending", "warn"),), "2",
                       (pill("blocks step 3", "n"),)],
                      ["3 · owner rep", "rfi 418", "—", "locked until step 2", "0",
                       (pill("not started", "n"),)],
                      ["1 · supplier", "submittal 91", "SH-022", (pill("resubmit", "bad"),), "4",
                       (pill("re-review", "warn"),)],
                      ["2 · engineer", "submittal 91", "SH-011", (pill("pending", "warn"),), "1",
                       (pill("closed_at null", "bad"),)],
                      ["3 · facilities lead", "submittal 91", "SH-004", (pill("queued", "n"),), "0",
                       (pill("waiting on 2", "n"),)],
                      ["1 · CQE", "submittal 90", "SH-011", (pill("code B", "warn"),), "3",
                       (pill("resubmit due 11-24", "warn"),)]],
              "note": "a submittal cannot be closed while closed_at is null on any open review step"},
    "flags": {"k": "table", "an": 3, "label": "Impact flag queue",
              "cols": [("^", "record"), ("rfi", "cost_schedule_impact_flag"),
                       ("submittal", "cost_schedule_impact_flag"), ("^", "spawned consequence"),
                       ("^", "countersign")],
              "rows": [["RFI-418", (pill("true", "bad"),), (pill("false", "n"),),
                        "change_order candidate (frame 17) + critical-path review task", "required — PM"],
                      ["SUB-090", (pill("false", "n"),), (pill("true", "bad"),),
                        "+$142k rework allowance · 3 d float consumed", "required — PM + Owner"],
                      ["RFI-420", (pill("false", "n"),), (pill("false", "n"),), "no commercial impact",
                       "—"],
                      ["SUB-092", (pill("—", "n"),), (pill("false", "n"),), "technical only", "—"],
                      ["RFI-415", (pill("false", "n"),), (pill("true", "warn"),),
                       "code B answer reopens the clock, 2 d added", "required — PM"],
                      ["SUB-088", (pill("false", "n"),), (pill("false", "n"),), "closed clean", "—"]],
              "note": "answers raised with cost_schedule_impact_flag need a PM countersign before the "
                      "record can close"},
    "raise": {"k": "fields", "label": "Raise RFI — field states against rfi", "t": "rfi",
              "fcols": 3,
              "names": ["rfi_id", "project_id", "element_id", "activity_id", "stakeholder_id",
                        "submitted_at", "due_date", "closed_at", "cost_schedule_impact_flag"],
              "values": {"rfi_id": "auto · 423", "project_id": "NBO-221", "element_id": "EL-214",
                         "activity_id": "ACT-1204", "stakeholder_id": "SH-002",
                         "submitted_at": "2026-11-20 08:15", "due_date": "2026-11-27", "closed_at": "",
                         "cost_schedule_impact_flag": "false"},
              "states": {"rfi_id": "ro", "closed_at": "empty", "cost_schedule_impact_flag": "bool",
                         "stakeholder_id": "select", "due_date": "date"}},
    "empty": {"k": "empty", "title": "board empty",
              "body": "no records match trade = landscaping for this project — the archived column stays "
                      "read-only", "action": "Reset filters"},
}

CFG["15"] = {
    "type": "quality", "sub": "quality_test results drive the ncr state machine",
    "tests": {"k": "table", "an": 1, "label": "Test result grid — measured_value vs pass_fail",
              "cols": [("quality_test", "test_id"), ("quality_test", "wbs_id"),
                       ("quality_test", "room_id"), ("quality_test", "element_id"),
                       ("quality_test", "test_type"), ("quality_test", "measured_value"),
                       ("quality_test", "pass_fail"), ("^", "consequence")],
              "rows": [["QT-1108", "F3", "R3-118", "EL-090", "concrete_cube_fck", "38.4",
                        (pill("pass", "ok"),), (pill("counts toward % complete", "ok"),)],
                       ["QT-1109", "E10", "R3-120 Core", "EL-214", "concrete_cube_fck", "31.0",
                        (pill("fail", "bad"),), (pill("→ NCR-12 · hold on next pour", "bad"),)],
                       ["QT-1110", "F3", "—", "EL-231", "weld_ut", "0", (pill("pass", "ok"),),
                        (pill("released", "ok"),)],
                       ["QT-1111", "E20", "—", "—", "slump", "118", (pill("pass", "ok"),),
                        (pill("released", "ok"),)],
                       ["QT-1112", "E20", "R-0210", "EL-240", "compaction_ratio", "96.4",
                        (pill("pass", "ok"),), (pill("released", "ok"),)],
                       ["QT-1113", "G1", "R-0210", "EL-318", "duct_leakage_class", "1.32",
                        (pill("fail", "bad"),), (pill("→ NCR-14 · retest pending", "warn"),)],
                       ["QT-1114", "H1", "R4-118", "EL-771", "pull_out_test", "4.9",
                        (pill("pass", "ok"),), (pill("released", "ok"),)],
                       ["QT-1115", "F3", "R3-119", "EL-090", "cover_meter", "42", (pill("pass", "ok"),),
                        (pill("counts toward % complete", "ok"),)]],
              "hint": "the design target (for example f′c) is not a column on quality_test in this "
                      "schema — the comparator comes from the specification reference"},
    "ncr": {"k": "table", "label": "NCR register — ncr rows with the status machine",
            "cols": [("ncr", "ncr_id"), ("ncr", "wbs_id"), ("ncr", "room_id"), ("ncr", "element_id"),
                     ("ncr", "ncr_status"), ("ncr", "raised_date"), ("ncr", "closed_date"),
                     ("ncr", "description")],
            "rows": [["NCR-12", "E10", "R3-120 Core", "EL-214", (pill("retest / repair", "warn"),),
                      "2026-11-12", "—", "Core break below f′c at pour 44 — engineer disposition"],
                     ["NCR-14", "G1", "R-0210", "EL-318", (pill("disposition pending", "warn"),),
                      "2026-11-18", "—", "Duct leakage above the class limit"],
                     ["NCR-11", "F3", "R3-118", "EL-090", (pill("closed (verified)", "ok"),),
                      "2026-10-28", "2026-11-06", "Cover shortfall — rework verified by QT-1115"],
                     ["NCR-10", "E11", "—", "—", (pill("closed (verified)", "ok"),),
                      "2026-10-14", "2026-10-30", "Grade beam kick — accept as is, architect signed"],
                     ["NCR-09", "H1", "R7-210", "EL-771", (pill("open", "bad"),),
                      "2026-09-30", "—", "Anchor pattern deviation, 6 panels — overdue 51 d"],
                     ["NCR-07", "E2", "—", "EL-240", (pill("closed (verified)", "ok"),),
                      "2026-08-19", "2026-09-02", "Cold joint treatment"]],
            "note": "disposition types (repair, replace, accept-as-is, rework) and separateness severity "
                    "are workflow-service fields — there is no ncr_severity or disposition_type table "
                    "in this schema"},
    "stepper": {"k": "stepper", "an": 3, "full": True, "label": "NCR state stepper — ncr_status", "cur": 2,
                "steps": ["open", "disposition pending", "retest / repair", "closed (verified)"],
                "note": "NCR-12 sits on step 3: retest QT-1116 booked for 2026-11-24 · close needs "
                        "closed_date plus the linked retest row"},
    "bridge": {"k": "chips", "an": 2, "t": "quality_test", "label": "quality_test keys",
               "caption": "wbs_id / room_id / element_id are how a result rolls into the O&M file in "
                          "frame 18"},
    "ncrchips": {"k": "chips", "t": "ncr", "label": "ncr columns"},
    "hold": {"k": "banner", "tone": "bad", "title": "hold-point gating frame 13",
             "body": "percent_complete on ACT-1108 cannot tick while NCR-12 is unresolved — a failed "
                     "pass_fail must spawn exactly one open NCR before the next tick"},
    "empty": {"k": "empty", "title": "no tests this week",
              "body": "the lab has not returned a result since 2026-11-14 for wbs E3 — the register is "
                      "showing the previous week", "action": "Open test plan"},
}

CFG["16"] = {
    "type": "hse", "sub": "one daily hse_record, weather stand-down evidence, drone captures by URL",
    "kpis": [("0.42", "ltifr · last 28 days", "warn"), ("97.1%", "ppe_compliance_pct", "ok"),
             ("182", "toolbox_attendance", "n"), ("34.2 t", "waste_tonnage", "n"),
             ("81,500 kgCO₂e", "carbon_kg_co2e · plant & logistics", "n"), ("3", "near misses open", "bad")],
    "kpi_an": 1,
    "ledger": {"k": "table", "an": 2, "label": "HSE ledger",
               "cols": [("hse_record", "hse_id"), ("hse_record", "project_id"),
                        ("hse_record", "log_date"), ("hse_record", "ltifr"),
                        ("hse_record", "ppe_compliance_pct"), ("hse_record", "toolbox_attendance"),
                        ("hse_record", "waste_tonnage"), ("hse_record", "carbon_kg_co2e"),
                        ("^", "incidents")],
               "rows": [["HSE-1104", "NBO-221", "2026-11-19", "0.42", "97.1", "182", "34.2", "81,500", "0"],
                        ["HSE-1103", "NBO-221", "2026-11-18", "0.42", "95.8", "174", "28.7", "76,200",
                         "1 near miss"],
                        ["HSE-1102", "NBO-221", "2026-11-17", "0.44", "96.4", "188", "41.0", "88,400", "0"],
                        ["HSE-1101", "NBO-221", "2026-11-16", "0.44", "98.0", "166", "22.4", "61,900",
                         "0 · stand-down"],
                        ["HSE-1100", "NBO-221", "2026-11-15", "0.46", "94.2", "192", "38.9", "92,100",
                         "1 first aid"],
                        ["HSE-1099", "NBO-221", "2026-11-14", "0.46", "97.6", "201", "44.6", "97,800", "0"],
                        ["HSE-1098", "NBO-221", "2026-11-13", "0.49", "93.1", "158", "19.8", "52,300",
                         "2 near misses"],
                        ["HSE-1097", "NBO-221", "2026-11-12", "0.49", "96.9", "146", "26.1", "58,700", "0"]],
               "hint": "ltifr is per 200,000 man-hours, computed against man_hours from frame 13 — never "
                       "typed into this row"},
    "sparks": {"k": "spark", "an": 3, "label": "Trends — CSS sparklines over the same rows",
               "items": [("LTIFR rolling 12 months", [1.18, 1.04, 0.96, 0.88, 0.81, 0.74, 0.69, 0.61,
                                                      0.58, 0.51, 0.46, 0.42],
                          "0.42 now · target ≤ 0.35", ""),
                         ("Waste diverted %", [58, 61, 64, 66, 71, 74, 76, 78, 79, 80, 81, 81],
                          "diverted 81 % · BREEAM target 80 %", "alt"),
                         ("kgCO₂e per productive day", [70, 74, 69, 81, 77, 88, 92, 86, 82, 79, 76, 82],
                          "operational only — embedded carbon is ledger-side (frame 22)", "")]},
    "weather": {"k": "table", "an": 4,
                "label": "Weather log — stand-down rule on wind_kmh / rainfall_mm",
                "cols": [("site_weather_log", "weather_id"), ("site_weather_log", "project_id"),
                         ("site_weather_log", "log_date"), ("site_weather_log", "temp_c"),
                         ("site_weather_log", "wind_kmh"), ("site_weather_log", "rainfall_mm"),
                         ("site_weather_log", "drone_capture_url"), ("^", "rule")],
                "rows": [["WX-1119", "NBO-221", "2026-11-19", "21.4", "44", "—",
                          "/drone/L4-20261119.tif", (pill("lift allowed", "ok"),)],
                         ["WX-1118", "NBO-221", "2026-11-18", "19.8", "62", "6.2", "(no flight — wind)",
                          (pill("stand-down > 60 km/h", "bad"),)],
                         ["WX-1117", "NBO-221", "2026-11-17", "18.2", "31", "0.0",
                          "/drone/L3-20261117.tif", (pill("normal", "ok"),)],
                         ["WX-1116", "NBO-221", "2026-11-16", "16.9", "68", "12.4", "—",
                          (pill("stand-down", "bad"),)],
                         ["WX-1115", "NBO-221", "2026-11-15", "20.1", "38", "0.4",
                          "/drone/L4-20261115.tif", (pill("normal", "ok"),)],
                         ["WX-1114", "NBO-221", "2026-11-14", "22.6", "26", "0.0",
                          "/drone/roof-20261114.tif", (pill("normal", "ok"),)],
                         ["WX-1113", "NBO-221", "2026-11-13", "17.4", "71", "18.6", "—",
                          (pill("stand-down + EOT", "bad"),)],
                         ["WX-1112", "NBO-221", "2026-11-12", "19.2", "49", "2.2", "(deferred)",
                          (pill("caution 40–60", "warn"),)]]},
    "empty": {"k": "empty", "title": "no log today",
              "body": "the 2026-11-20 hse_record row is missing — the nag fires at 15:00 local · weather "
                      "feed last packet 09:41", "action": "Open daily log"},
}

CFG["17"] = {
    "type": "payments", "sub": "payment_application waterfall, retention pot and the change_order gate",
    "apps": {"k": "table", "an": 1, "label": "Payment applications",
             "cols": [("payment_application", "app_id"), ("payment_application", "contract_id"),
                      ("payment_application", "wbs_id"), ("payment_application", "claimed_amount"),
                      ("payment_application", "certified_amount"), ("payment_application", "retention_held"),
                      ("^", "net due"), ("^", "state")],
             "rows": [["PA-14", "CTR-03", "E2", "$6.42m", "$6.05m", "$0.61m", "$5.44m",
                       (pill("draft", "n"),)],
                      ["PA-13", "CTR-03", "E2", "$5.88m", "$5.71m", "$0.57m", "$5.14m",
                       (pill("certified", "ok"),)],
                      ["PA-12", "CTR-03", "F3", "$4.96m", "$4.61m", "$0.46m", "$4.15m",
                       (pill("paid", "ok"),)],
                      ["PA-09", "CTR-07", "H1", "$3.24m", "$3.24m", "$0.32m", "$2.92m",
                       (pill("paid", "ok"),)],
                      ["PA-10", "CTR-07", "H1", "$2.88m", "$2.12m", "$0.21m", "$1.91m",
                       (pill("queried — 3 lines", "warn"),)],
                      ["PA-04", "CTR-09", "G1", "$1.42m", "—", "—", "—",
                       (pill("suspended — insurance lapse", "bad"),)],
                      ["PA-06", "CTR-12", "G2", "$0.94m", "$0.88m", "$0.09m", "$0.79m",
                       (pill("certified", "ok"),)],
                      ["PA-07", "CTR-18", "H2", "$0.66m", "$0.30m", "$0.03m", "$0.27m",
                       (pill("payless notice issued", "bad"),)]]},
    "waterfall": {"k": "bars", "an": 2, "label": "Claim → certify → less retention → net (PA-14)",
                  "items": [("claimed_amount", 100, "n", "$6.42m"), ("certified_amount", 94, "a", "$6.05m"),
                            ("retention_held", 10, "warn", "$0.61m"), ("net due", 85, "ok", "$5.44m")],
                  "cap": "certified_amount never exceeds claimed_amount · each delta needs a reason line"},
    "ret": {"k": "raw", "an": 3, "label": "Retention pot — contract.retention_pct",
            "html": ('<div class="retpot"><div class="pot"><span class="ring"><b>$4.2m</b>'
                     "<i>held</i></span><ul><li>CTR-03 · 5.0% · $2.14m</li>"
                     "<li>CTR-07 · 5.0% · $1.26m</li><li>CTR-09 · 6.0% · $0.52m</li>"
                     "<li>CTR-12 · 5.0% · $0.28m</li></ul></div>"
                     '<div class="stage"><h5>Release stage — partial</h5>'
                     '<ol class="stepper"><li class="done"><span class="dot">&#10003;</span>'
                     "<span class=\"sl\">substantial completion</span></li>"
                     '<li class="now"><span class="dot">2</span><span class="sl">50 % released at '
                     'completion certificate</span></li>'
                     '<li class="todo"><span class="dot">3</span><span class="sl">balance at DLP end'
                     '</span></li><li class="todo"><span class="dot">4</span>'
                     "<span class=\"sl\">retention release gate (frame 19)</span></li></ol></div></div>"),
            "note": "release is a frame 19 gate — the pot cannot empty while defect rows stay open"},
    "co": {"k": "table", "an": 4, "label": "Change orders — value impact on the forecast",
           "cols": [("change_order", "change_order_id"), ("change_order", "contract_id"),
                    ("change_order", "wbs_id"), ("change_order", "approved_variation_value"),
                    ("change_order", "description"), ("^", "funding route")],
           "rows": [["CO-34", "CTR-07", "F3", "-$120k", "Delete redundant roof plant",
                     (pill("credit", "ok"),)],
                    ["CO-12", "CTR-03", "F3", "-$200k", "Omit 4th stair flight", (pill("credit", "ok"),)],
                    ["CO-31", "CTR-03", "E1", "+$1.90m", "Dewatering duration × 3",
                     (pill("construction contingency", "warn"),)],
                    ["CO-27", "CTR-03", "E2", "-$0.42m", "Pour joints re-sequenced", (pill("credit", "ok"),)],
                    ["CO-33", "CTR-07", "H2", "+$1.18m", "Fit-out spec upgrade",
                     (pill("design contingency", "warn"),)],
                    ["CO-30", "CTR-09", "G2", "+$0.56m", "Switchgear rating",
                     (pill("awaiting owner", "bad"),)],
                    ["CO-35", "CTR-18", "H1", "+$840k", "Overboard rescue boat davits",
                     (pill("above owner threshold", "bad"),)]]},
    "costeps": {"k": "chipset", "an": 3, "label": "Change order approval stepper", "items": [
        ("1 · raised", "", "field change record"), ("2 · priced", "", "QS rate build-up"),
        ("3 · PM approved", "", "below delegation limit"),
        ("4 · owner approved", "pk", "over threshold → contingency or funding re-approval")]},
    "der": {"k": "table", "an": 5, "label": "Derived payment grid — there is no payment_term table",
            "cols": [("^", "milestone"), ("^", "due rule"), ("^", "amount"), ("^", "source"),
                     ("^", "state")],
            "rows": [["Site mobilisation", "signed + 15 d", "$4.0m", "contract", (pill("paid", "ok"),)],
                     ["Monthly cycle", "certification + day 28", "PA net", "payment_application",
                      (pill("due 2026-11-28", "warn"),)],
                     ["Retention tranche 1", "substantial completion", "50 % held", "frame 19 gate",
                      (pill("blocked — open defects", "bad"),)],
                     ["Plant bond release", "customs cleared", "$0.6m", "supply_shipment",
                      (pill("pending", "n"),)],
                     ["Green bond drawdown", "issuance milestone", "$2.4m", "funding_source",
                      (pill("covenant check ok", "ok"),)],
                     ["Final account", "change orders + claims settled", "$11.6m", "change_order",
                      (pill("forecast only", "n"),)]],
            "note": "the schedule is derived from contract terms and shown as a placeholder — no rows "
                    "are written from this panel"},
}

CFG["18"] = {
    "type": "handover", "sub": "asset register, commissioning clearance, punch and the statutory gate",
    "assets": {"k": "table", "an": 1, "label": "Asset register — every operating bim_element becomes a row",
               "cols": [("asset", "asset_id"), ("asset", "asset_tag_qr"), ("asset", "serial_number"),
                        ("asset", "manufacturer"), ("asset", "room_id"), ("asset", "warranty_start"),
                        ("asset", "warranty_end"), ("asset", "lifecycle_replacement_cost"),
                        ("^", "commissioning"), ("^", "punch")],
               "rows": [["AST-0031", "QR-EL-0031", "SN-88-31", "VertiCo", "Lift lobby L3", "2026-10-01",
                         "2029-06-30", "$486,000", (pill("5 / 6 tests pass", "warn"),),
                         (pill("2 open", "bad"),)],
                        ["AST-0044", "QR-ME-0118", "SN-40-18", "AirSym", "R-0210", "2026-09-14",
                         "2028-11-30", "$128,400", (pill("complete", "ok"),), (pill("—", "n"),)],
                        ["AST-0045", "QR-ME-0119", "SN-40-22", "AirSym", "R3-120 Core", "2026-09-14",
                         "2028-11-30", "$96,200", (pill("complete", "ok"),), (pill("1 open", "warn"),)],
                        ["AST-0052", "QR-EL-0210", "SN-12-90", "GridPower", "Substation B2", "2026-08-02",
                         "2031-08-02", "$1,140,000", (pill("awaiting retest", "warn"),), (pill("—", "n"),)],
                        ["AST-0058", "QR-PF-0007", "SN-77-14", "Flowite", "R-0210", "2026-10-20",
                         "2029-10-20", "$42,800", (pill("complete", "ok"),), (pill("—", "n"),)],
                        ["AST-0061", "QR-FC-0305", "SN-31-05", "Nikkiso", "Lobby G-001", "2026-11-02",
                         "2030-06-30", "$64,500", (pill("not started", "n"),), (pill("—", "n"),)],
                        ["AST-0067", "QR-ME-0450", "SN-41-88", "AirSym", "R7-210 Meeting", "2026-11-08",
                         "2028-11-08", "$18,900", (pill("retest booked", "warn"),), (pill("3 open", "bad"),)],
                        ["AST-0070", "QR-WS-0011", "SN-90-04", "Hydroline", "Roof", "2026-11-12",
                         "2031-11-12", "$22,400", (pill("complete", "ok"),), (pill("—", "n"),)]]},
    "comm": {"k": "table", "an": 3, "label": "Commissioning results — design_target vs measured_reading",
             "cols": [("commissioning_test", "comm_id"), ("commissioning_test", "asset_id"),
                      ("commissioning_test", "test_parameter"), ("commissioning_test", "design_target"),
                      ("commissioning_test", "measured_reading"),
                      ("commissioning_test", "passed_boolean")],
             "rows": [["CM-8801", "AST-0044 AHU-3", "supply airflow (cfm)", "1,800", "1,721",
                       (pill("pass", "ok"),)],
                      ["CM-8802", "AST-0044 AHU-3", "fan power (kW)", "7.5", "7.1", (pill("pass", "ok"),)],
                      ["CM-8803", "AST-0058 CHW loop", "test pressure (kPa)", "1,000", "1,000 held",
                       (pill("pass", "ok"),)],
                      ["CM-8804", "AST-0045 AHU-4", "noise (dB(A))", "48", "52", (pill("fail", "bad"),)],
                      ["CM-8805", "AST-0052 MV cable", "insulation (MΩ)", "100", "84",
                       (pill("fail → retest", "bad"),)],
                      ["CM-8806", "AST-0031 Elevator 3", "levelling accuracy (mm)", "10", "6",
                       (pill("pass", "ok"),)],
                      ["CM-8807", "AST-0031 Elevator 3", "door cycles to failure", "50,000", "1,500 run",
                       (pill("pass", "ok"),)],
                      ["CM-8808", "AST-0067 FCU-21", "delivering temperature (°C)", "13.5 ± 1.0", "15.1",
                       (pill("fail", "bad"),)]],
             "note": "an asset cannot close commissioning while a linked punch_item row is open — "
                     "AST-0031 is held by two snags"},
    "punch": {"k": "table", "an": 2, "label": "Snags by room — punch_item",
              "cols": [("punch_item", "punch_id"), ("punch_item", "room_id"), ("punch_item", "asset_id"),
                       ("punch_item", "description"), ("punch_item", "raised_date"),
                       ("punch_item", "resolved_date"), ("^", "age")],
              "rows": [["PUN-212", "R3-118", "—", "Scoring on glazing panel 4A", "2026-11-02", "—", "18 d"],
                       ["PUN-213", "R3-118", "AST-0067", "Diffuser balance report missing", "2026-10-28",
                        "2026-11-15", "closed"],
                       ["PUN-214", "Lift lobby L3", "AST-0031", "Car interior scuff", "2026-11-10", "—",
                        "10 d"],
                       ["PUN-215", "Lift lobby L3", "AST-0031", "Leveling re-check after CM-8806",
                        "2026-11-12", "—", "8 d"],
                       ["PUN-216", "R-0210", "—", "Access panel label set", "2026-11-14", "2026-11-18",
                        "closed"],
                       ["PUN-217", "R7-210 Meeting", "AST-0067", "Condensate trap slope", "2026-11-16",
                        "—", "4 d"],
                       ["PUN-218", "R7-210 Meeting", "AST-0067", "Grille finish mark", "2026-11-16", "—",
                        "4 d"],
                       ["PUN-219", "R7-210 Meeting", "AST-0067", "Control wiring dress", "2026-11-17",
                        "—", "3 d"],
                       ["PUN-220", "Lobby G-001", "AST-0061", "Escalation audio level", "2026-11-18", "—",
                        "2 d"]]},
    "gate": {"k": "table", "an": 4, "label": "Statutory gate — municipal_inspection",
             "cols": [("municipal_inspection", "inspection_id"),
                      ("municipal_inspection", "project_id"), ("municipal_inspection", "room_id"),
                      ("municipal_inspection", "asset_id"),
                      ("municipal_inspection", "inspection_date"),
                      ("municipal_inspection", "pass_fail"), ("^", "effect on the COO")],
             "rows": [["INS-401", "NBO-221", "Lobby G-001", "—", "2026-10-18", (pill("pass", "ok"),),
                       "means of escape signed"],
                      ["INS-402", "NBO-221", "R3-118", "—", "2026-10-26", (pill("pass", "ok"),),
                       "fire compartment L3 signed"],
                      ["INS-403", "NBO-221", "R-0210", "AST-0052", "2026-11-06", (pill("fail", "bad"),),
                       "electrical install certificate withheld"],
                      ["INS-404", "NBO-221", "Lift lobby L3", "AST-0031", "2026-11-19",
                       (pill("pending", "warn"),), "statutory lift exam booked 2026-12-01"],
                      ["INS-405", "NBO-221", "Roof", "AST-0070", "2026-11-20", (pill("pass", "ok"),),
                       "rainwater discharge signed"],
                      ["INS-406", "NBO-221", "R7-210 Meeting", "AST-0067", "2026-12-04",
                       (pill("scheduled", "n"),), "final room-scale inspection"]]},
    "checklist": {"k": "bars", "label": "Handover checklist — 84 % complete",
                  "items": [("Assets registered", 92, "ok", "310 / 337"),
                            ("Commissioning closed", 78, "a", "263 / 337"),
                            ("Punch cleared", 64, "warn", "182 / 284"),
                            ("Statutory inspections", 67, "warn", "4 / 6"),
                            ("O&M file assembled", 71, "a", "quality_test + asset evidence")],
                  "cap": "the certificate stays on project · the gate below is the only writer"},
    "fields": {"k": "fields", "an": 5, "label": "Book inspection — field states (municipal_inspection)",
               "t": "municipal_inspection", "fcols": 3,
               "names": ["inspection_id", "project_id", "room_id", "asset_id", "inspection_date",
                         "pass_fail"],
               "values": {"inspection_id": "auto · INS-407", "project_id": "NBO-221",
                          "room_id": "R3-118", "asset_id": "AST-0067", "inspection_date": "2026-12-04",
                          "pass_fail": "false"},
               "states": {"inspection_id": "ro", "pass_fail": "bool", "asset_id": "select",
                          "room_id": "select"},
               "note": "the boolean here is what unlocks project.certificate_of_occupancy_date — that "
                       "column lives on project (frame 02), not in this form"},
}

CFG["19"] = {
    "type": "defects", "sub": "defect SLA clock and the explicit retention release gate",
    "defects": {"k": "table", "an": 1, "label": "Defect SLA tracker",
                "cols": [("defect", "defect_id"), ("defect", "asset_id"), ("defect", "contract_id"),
                         ("defect", "reported_at"), ("defect", "sla_deadline"), ("defect", "resolved_at"),
                         ("defect", "retention_release_approved"), ("^", "state")],
                "rows": [["DEF-01", "AST-0044 AHU-3", "CTR-07", "2026-10-30 08:12", "2026-11-13 08:12",
                          "—", (pill("false", "bad"),), (pill("SLA breached 7 d", "bad"),)],
                         ["DEF-02", "AST-0067 FCU-21", "CTR-07", "2026-11-04 14:02", "2026-11-18 14:02",
                          "2026-11-15", (pill("false", "warn"),), (pill("retest awaiting", "warn"),)],
                         ["DEF-03", "AST-0031 Elevator 3", "CTR-09", "2026-11-06 09:40", "2026-12-04 09:40",
                          "—", (pill("false", "n"),), (pill("open · 14 d", "n"),)],
                         ["DEF-04", "AST-0052 switchgear", "CTR-12", "2026-11-08 11:05",
                          "2026-11-22 11:05", "—", (pill("false", "warn"),), (pill("dispute raised", "warn"),)],
                         ["DEF-05", "AST-0045 AHU-4", "CTR-07", "2026-11-10 07:20", "2026-12-08 07:20",
                          "—", (pill("false", "n"),), (pill("open · 12 d", "n"),)],
                         ["DEF-06", "AST-0058 CHW pump", "CTR-03", "2026-09-22 16:40", "2026-10-06 16:40",
                          "2026-10-02", (pill("true", "ok"),), (pill("closed", "ok"),)],
                         ["DEF-07", "AST-0061 escalator", "CTR-18", "2026-11-16 10:10",
                          "2026-11-30 10:10", "—", (pill("false", "n"),), (pill("open · 4 d", "n"),)],
                         ["DEF-08", "AST-0070 rainwater valve", "CTR-03", "2026-11-18 13:25",
                          "2026-12-16 13:25", "—", (pill("false", "n"),), (pill("open · 2 d", "n"),)]]},
    "gate": {"k": "kv", "an": 2, "label": "Retention release gate",
             "items": [("defect.retention_release_approved", "server-set boolean — shown below as "
                        "locked / false"),
                       ("Open defects", "7 — the gate cannot arm while the count is non-zero"),
                       ("SLA breached", "1 — DEF-01, 7 days past sla_deadline"),
                       ("Inspection sign-off", "4 of 6 passed (frame 18) — INS-403 still failed"),
                       ("Retention held", "$4.2m across 4 contracts (frame 17)"),
                       ("Gate state", "BLOCKED — 7 open defects")],
             "note": "every work_order against an asset under DLP is flagged to the responsible "
                     "subcontractor through the contract link"},
    "pm": {"k": "table", "an": 3, "label": "Preventive plan — maintenance_schedule",
           "cols": [("maintenance_schedule", "schedule_id"), ("maintenance_schedule", "asset_id"),
                    ("maintenance_schedule", "task_description"),
                    ("maintenance_schedule", "frequency_days"),
                    ("maintenance_schedule", "next_due_date"), ("^", "state")],
           "rows": [["MS-011", "AST-0044 AHU-3", "filter change & belt check", "120", "2027-01-14",
                     (pill("scheduled", "ok"),)],
                    ["MS-012", "AST-0031 Elevator 3", "statutory exam", "182", "2026-12-01",
                     (pill("due soon", "warn"),)],
                    ["MS-013", "AST-0045 AHU-4", "coil clean & condensate trap", "180", "2027-01-08",
                     (pill("scheduled", "ok"),)],
                    ["MS-014", "AST-0052 switchgear", "thermographic survey", "365", "2027-06-30",
                     (pill("planned", "n"),)],
                    ["MS-015", "AST-0058 CHW pump", "seal & vibration check", "90", "2026-12-20",
                     (pill("due soon", "warn"),)],
                    ["MS-016", "AST-0061 escalator", "chain tension & brake test", "90", "2027-02-16",
                     (pill("planned", "n"),)],
                    ["MS-017", "AST-0070 roof valve", "backflow prevention test", "365", "2027-05-02",
                     (pill("planned", "n"),)]]},
    "wo": {"k": "table", "an": 4, "label": "Reactive record — work_order vs plan",
           "cols": [("work_order", "work_order_id"), ("work_order", "asset_id"),
                    ("work_order", "opened_at"), ("work_order", "closed_at"),
                    ("work_order", "downtime_hours"), ("work_order", "repair_cost"), ("^", "planned?")],
           "rows": [["WO-77", "AST-0044 AHU-3 fan", "2026-11-17 06:40", "2026-11-18 09:00", "14.5",
                     "$3,900", (pill("reactive — under DLP", "bad"),)],
                    ["WO-78", "AST-0067 FCU-21", "2026-11-16 11:20", "2026-11-17 08:10", "9.0", "$1,240",
                     (pill("reactive", "warn"),)],
                    ["WO-79", "AST-0052 MV cable", "2026-11-09 07:05", "2026-11-09 15:35", "7.5",
                     "$2,860", (pill("retest prep", "n"),)],
                    ["WO-74", "AST-0058 CHW pump", "2026-10-01 08:00", "2026-10-01 12:30", "4.5", "$680",
                     (pill("planned PM", "ok"),)],
                    ["WO-75", "AST-0031 Elevator 3", "2026-10-14 09:15", "2026-10-14 11:00", "1.75",
                     "$420", (pill("planned PM", "ok"),)],
                    ["WO-76", "AST-0045 AHU-4", "2026-10-22 13:40", "2026-10-23 10:20", "18.0", "$5,120",
                     (pill("reactive", "warn"),)],
                    ["WO-80", "AST-0061 escalator", "2026-11-19 22:05", "—", "open", "—",
                     (pill("awaiting parts", "warn"),)]]},
    "fields": {"k": "fields", "an": 5, "label": "Defect capture — field states (defect)", "t": "defect",
               "fcols": 3,
               "names": ["defect_id", "asset_id", "contract_id", "reported_at", "sla_deadline",
                         "resolved_at", "retention_release_approved"],
               "values": {"defect_id": "auto · DEF-09", "asset_id": "AST-0067 (QR scan)",
                          "contract_id": "CTR-07 (derived)", "reported_at": "2026-11-20 07:55",
                          "sla_deadline": "2026-12-04 07:55", "resolved_at": "",
                          "retention_release_approved": "false"},
               "states": {"defect_id": "ro", "resolved_at": "empty",
                          "retention_release_approved": "locked", "contract_id": "select"},
               "               note": "the boolean renders locked: it is server-set only, and sla_deadline derives from "
                       "the severity class chosen at logging"},
}

CFG["20"] = {
    "type": "telemetry", "sub": "facility_telemetry pivotted onto the handover asset register",
    "kpis": [("18,420", "kWh metered today", "n"), ("14.4", "grid CO₂e factor per kWh ×10³", "warn"),
            ("21.6 °C", "mean supply air temp", "ok"), ("3", "assets below threshold", "bad"),
            ("14:32:10", "latest timestamp (derived max)", "n")],
    "pivot": {"k": "table", "an": 1, "label": "Time-series pivot — metric_name across, metric_value in "
              "each cell",
              "hint": "the pivot is built at read time from narrow rows: one row per asset per timestamp "
                      "per metric_name",
              "cols": [("asset", "asset_id"), ("facility_telemetry", "metric_name"),
                       ("^", "12:00"), ("^", "12:15"), ("^", "12:30"), ("^", "7-day sparkline"),
                       ("^", "24 h Δ")],
              "rows": [["AST-0044 AHU-3", "supply_air_temp_c", "13.8", "13.9", "14.2",
                        (sparkline([13.4, 13.6, 13.9, 14.1, 13.8, 14.0, 14.2]),), "+0.4"],
                       ["AST-0058 CHW loop", "pump_kw", "18.1", "17.9", "18.3",
                        (sparkline([17.2, 18.0, 17.6, 18.4, 17.9, 18.1, 18.3], cls="alt"),), "+0.2"],
                       ["AST-0031 Elevator 3", "door_cycles", "418", "419", "421",
                        (sparkline([380, 396, 402, 410, 408, 416, 421]),), "+3"],
                       ["AST-0052 MV board", "apparent_power_kva", "412", "418", "426",
                        (sparkline([388, 396, 404, 410, 415, 418, 426], cls="warn"),), "+8"],
                       ["AST-0045 AHU-4", "filter_dp_pa", "118", "121", "126",
                        (sparkline([104, 108, 111, 115, 118, 121, 126], cls="warn"),), "+5"],
                       ["AST-0070 roof tank", "level_pct", "62", "62", "61",
                        (sparkline([66, 65, 64, 63, 62, 62, 61]),), "-1"],
                       ["AST-0067 FCU-21", "supply_air_temp_c", "15.1", "15.4", "15.9",
                        (sparkline([14.8, 15.0, 15.2, 15.4, 15.6, 15.7, 15.9], cls="bad"),), "+0.8"],
                       ["AST-0061 escalator", "motor_kw", "4.2", "4.1", "4.4",
                        (sparkline([3.9, 4.0, 4.2, 4.1, 4.3, 4.2, 4.4]),), "+0.3"]],
              "note": "FCU-21 breaches its 14.5 °C band — the alert threshold is ops-owned, the row is "
                      "never written back"},
    "ctx": {"k": "fields", "an": 2, "label": "Asset context — the meter stand-in is the asset row",
            "t": "asset", "fcols": 3,
            "names": ["asset_id", "asset_tag_qr", "manufacturer", "room_id", "warranty_end",
                      "lifecycle_replacement_cost"],
            "values": {"asset_id": "AST-0067", "asset_tag_qr": "QR-ME-0450", "manufacturer": "AirSym",
                       "room_id": "R7-210 Meeting", "warranty_end": "2028-11-08",
                       "lifecycle_replacement_cost": "18,900"},
            "states": {"asset_id": "ro", "asset_tag_qr": "ro", "room_id": "select"},
            "note": "no dedicated meter or IoT table exists in this schema — the asset row is what a "
                    "telemetry_id points at"},
    "grid": {"k": "spark", "an": 3, "label": "Derived slices — metered energy and the grid factor",
             "items": [("Hourly kWh × metered rooms", [42, 38, 44, 51, 66, 72, 68, 61, 58, 63, 71, 74],
                        "pivoted from metric_name = metered_kwh", ""),
                       ("grid_co2_intensity × 10³", [16.2, 15.8, 15.1, 14.9, 15.4, 14.4, 13.9, 14.2, 14.6,
                                                     14.4], "ties to SDG target 7.3.1 (frame 21)", "warn"),
                       ("daylight autonomy, R7 floors", [71, 74, 78, 82, 86, 84, 80, 76, 72, 70],
                        "daylight design values sit on the commissioned asset rows", "alt")],
             "note": "gap → outage inference is an external log in this build; it is labelled derived and "
                     "never written back as truth"},
    "gaps": {"k": "table", "an": 4, "label": "Derived outage windows — telemetry gaps by timestamp",
             "cols": [("^", "gap start"), ("^", "gap end"), ("^", "duration (min, derived)"),
                      ("asset", "asset_id"), ("^", "feed")],
             "rows": [["2026-11-16 03:12", "2026-11-16 04:02", "50", "AST-0044 … AST-0047",
                       (pill("gateway reboot", "warn"),)],
                      ["2026-11-09 22:40", "2026-11-09 22:47", "7", "floor 3 lighting loop",
                       (pill("packet loss", "n"),)],
                      ["2026-11-19 11:02", "2026-11-19 11:03", "1", "AST-0067",
                       (pill("quarantined — orphan", "bad"),)],
                      ["2026-11-04 06:15", "2026-11-04 06:15", "0.5", "AST-0052", (pill("clock skew", "n"),)],
                      ["2026-10-28 19:40", "2026-10-28 20:22", "42", "AST-0061",
                       (pill("escalator stopped", "bad"),)],
                      ["2026-10-21 00:00", "2026-10-21 02:30", "150", "site-wide BMS head",
                       (pill("planned maintenance", "n"),)]]},
    "empty": {"k": "empty", "title": "feed stale · no assets commissioned yet",
              "body": "the last telemetry row for this asset is 2026-11-19 11:03 — the pivot cannot build "
                      "a window, and orphan rows without asset_id quarantine on ingest",
              "action": "Open ingest log"},
}

CFG["21"] = {
    "type": "sdg", "sub": "un_sdg_indicator dictionary · project targets · evidence links",
    "kpis": [("9/17", "goals touched", "n"), ("9/14", "targets met", "ok"), ("3", "in review", "warn"),
             ("2", "off track", "bad"), ("41", "indicator rows bound", "n")],
    "matrix": {"k": "raw", "an": 1, "full": True, "label": "17-goal coverage matrix — goal_number × "
               "target_code",
               "html": ('<div class="sdg-grid">'
                        + "".join(
                            '<div class="sdg-goal s%s" title="%s"><b>%d</b><span>%s</span></div>'
                            % (st, ttl, g, ttl) for g, ttl, st in [
                                (1, "No poverty", "off"), (2, "Zero hunger", "off"),
                                (3, "Good health & well-being", "part"),
                                (4, "Quality education", "off"), (5, "Gender equality", "off"),
                                (6, "Clean water & sanitation", "on"), (7, "Affordable & clean energy", "on"),
                                (8, "Decent work & growth", "part"), (9, "Industry, innovation", "on"),
                                (10, "Reduced inequalities", "off"), (11, "Sustainable cities", "on"),
                                (12, "Responsible consumption", "part"), (13, "Climate action", "on"),
                                (14, "Life below water", "off"), (15, "Life on land", "part"),
                                (16, "Peace, justice", "on"), (17, "Partnerships", "on")])
                        + '</div><p class="cap">dictionary is global (un_sdg_indicator) — coverage is '
                          "computed from the indicator_code values this project actually binds</p>"),
               "note": ""},
    "dict": {"k": "table", "an": 2, "label": "Indicator dictionary rows",
             "cols": [("un_sdg_indicator", "indicator_code"), ("un_sdg_indicator", "goal_number"),
                      ("un_sdg_indicator", "goal_title"), ("un_sdg_indicator", "target_code"),
                      ("un_sdg_indicator", "unit_of_measure"),
                      ("un_sdg_indicator", "indicator_description")],
             "rows": [["6.4.1", "6", "Clean water & sanitation", "6.4", "m³",
                       "water withdrawal per occupant per year"],
                      ["7.3.1", "7", "Affordable & clean energy", "7.3", "kWh/m²",
                       "energy intensity of the operational asset"],
                      ["9.4.1", "9", "Industry, innovation and infrastructure", "9.4", "kgCO₂e/t",
                       "emissions per unit of added value"],
                      ["11.6.1", "11", "Sustainable cities and communities", "11.6", "%",
                       "share of construction waste diverted"],
                      ["12.5.1", "12", "Responsible consumption and production", "12.5", "%",
                       "rebound / reuse rate of demolition material"],
                      ["13.1.2", "13", "Climate action", "13.1", "events",
                       "weather stand-down and disruption events"],
                      ["15.1.1", "15", "Life on land", "15.1", "ha", "biodit value of the site footprint"],
                      ["17.17.1", "17", "Partnerships for the goals", "17.17", "count",
                       "data-sharing agreements signed"]]},
    "targets": {"k": "table", "an": 3, "label": "Target vs actual — project_sdg_target",
                "cols": [("project_sdg_target", "sdg_target_id"),
                         ("project_sdg_target", "indicator_code"), ("project_sdg_target", "wbs_id"),
                         ("project_sdg_target", "baseline_benchmark"), ("project_sdg_target", "target_value"),
                         ("project_sdg_target", "actual_value"),
                         ("project_sdg_target", "compliance_status"),
                         ("project_sdg_target", "last_evaluated_at"), ("^", "roll-up")],
                "rows": [["ST-01", "7.3.1", "whole project", "212", "165", "171", (pill("on track", "ok"),),
                          "2026-11-01", (pill("9/14 met", "n"),)],
                         ["ST-02", "6.4.1", "L1 retail", "1.9", "1.4", "1.9", (pill("off track", "bad"),),
                          "2026-10-15", (pill("re-bound after refurbishment", "n"),)],
                         ["ST-03", "11.6.1", "H1", "42", "80", "81", (pill("met", "ok"),), "2026-11-12",
                          (pill("evidence: 14 rows", "n"),)],
                         ["ST-04", "12.5.1", "E1", "35", "65", "71", (pill("met", "ok"),), "2026-11-12",
                          (pill("met", "ok"),)],
                         ["ST-05", "13.1.2", "site-wide", "3", "2", "4", (pill("in review", "warn"),),
                          "2026-10-20", (pill("weather feed outage counted", "n"),)],
                         ["ST-06", "9.4.1", "F3", "240", "205", "198", (pill("met", "ok"),), "2026-11-18",
                          (pill("linked to CC bridge", "n"),)],
                         ["ST-07", "15.1.1", "landscape", "1.2", "1.2", "1.2", (pill("met", "ok"),),
                          "2026-09-30", (pill("annual review lock", "n"),)],
                         ["ST-08", "17.17.1", "—", "4", "4", "3", (pill("in review", "warn"),),
                          "2026-11-05", (pill("agreement unsigned", "n"),)]]},
    "evidence": {"k": "table", "an": 4, "label": "Evidence drill-through — source_table / source_record_id",
                 "hint": "source_record_id values that no longer resolve mark compliance_status stale, "
                         "not failed",
                 "cols": [("sdg_evidence_link", "evidence_id"), ("sdg_evidence_link", "sdg_target_id"),
                          ("sdg_evidence_link", "source_table"),
                          ("sdg_evidence_link", "source_record_id"),
                          ("sdg_evidence_link", "contribution_value"),
                          ("sdg_evidence_link", "recorded_at"), ("^", "validator")],
                 "rows": [["EV-901", "ST-06 · 9.4.1", "quality_test", "7b3e…c012", "1,120", "2026-11-01",
                           (pill("resolves", "ok"),)],
                          ["EV-902", "ST-05 · 13.1.2", "site_weather_log", "9a1c…44d0", "4 events",
                           "2026-10-20", (pill("resolves", "ok"),)],
                          ["EV-903", "ST-01 · 7.3.1", "facility_telemetry", "55f2…1e19", "480",
                           "2026-11-18", (pill("resolves", "ok"),)],
                          ["EV-904", "ST-03 · 11.6.1", "punch_item", "c1d8…77aa", "18 rows", "2026-11-12",
                           (pill("resolves", "ok"),)],
                          ["EV-905", "ST-02 · 6.4.1", "daily_progress", "1f0b…9002", "12,600",
                           "2026-08-04", (pill("source record deleted → stale", "bad"),)],
                          ["EV-906", "ST-06 · 9.4.1", "boq_item", "e44a…12bb", "148.6 t of rebar mass",
                           "2026-11-18", (pill("resolves", "ok"),)]]},
    "states": [{"k": "empty", "title": "first run · no targets",
                "body": "un_sdg_indicator holds 8 rows for this project but no project_sdg_target has "
                        "bound an actual_value yet", "action": "Bind indicator to target"},
               {"k": "banner", "tone": "warn", "title": "value sanity check refused",
                "body": "an actual_value of 1.9 against baseline_benchmark 0.15 sits outside [0.5×, 10×] "
                        "— the row is rejected until a human re-confirms the unit"}],
}

CFG["22"] = {
    "type": "carbon", "sub": "registry card, MRV issuance, double-entry transactions, SDG bridge",
    "card": {"k": "fields", "an": 1, "label": "Registry card — carbon_project", "t": "carbon_project",
             "fcols": 3,
             "names": ["carbon_project_id", "project_id", "wbs_id", "methodology", "standard_body",
                       "registry_id", "baseline_start", "baseline_end", "crediting_start",
                       "crediting_end", "status"],
             "values": {"carbon_project_id": "CP-NBO-01", "project_id": "NBO-221",
                        "wbs_id": "F3 Superstructure", "methodology": "AMS-I.C grid-displacement v2.1",
                        "standard_body": "VCS", "registry_id": "VCS-2214-NBO",
                        "baseline_start": "2025-02-17", "baseline_end": "2026-02-16",
                        "crediting_start": "2025-02-17", "crediting_end": "2030-02-16",
                        "status": "verified"},
             "states": {"carbon_project_id": "ro", "registry_id": "ro", "project_id": "select",
                        "status": "select", "wbs_id": "select"},
             "note": "baseline dates are gated by the site EIA status (frame 04) — the card cannot "
                     "reach verified while the EIA is pending"},
    "flow": {"k": "chipset", "an": 2, "label": "Lifecycle — derived from status + issuance rows", "items": [
        ("1 · registered", "ok", "2025-03-04"), ("2 · baseline set", "ok", "2025-06-30"),
        ("3 · monitoring", "ok", "quarterly"), ("4 · verified", "pk", "VVB statement 2026-10-22"),
        ("5 · issuing", "warn", "registry settlement pending")],
        "note": "the five stages are the design flow; this schema only stores status, so the stepper "
                "is derived from issuance rows and their dates"},
    "issuance": {"k": "table", "an": 3, "label": "Issuance ledger — carbon_credit_issuance",
                 "cols": [("carbon_credit_issuance", "issuance_id"),
                          ("carbon_credit_issuance", "carbon_project_id"),
                          ("carbon_credit_issuance", "vintage_year"),
                          ("carbon_credit_issuance", "verification_period_start"),
                          ("carbon_credit_issuance", "verification_period_end"),
                          ("carbon_credit_issuance", "tco2e_verified"),
                          ("carbon_credit_issuance", "serial_number_range"),
                          ("carbon_credit_issuance", "vvb_name")],
                 "rows": [["IS-2025-1", "CP-NBO-01", "2025", "2025-02-17", "2025-12-31", "21,400",
                           "CC-NBO-000001–021400", "Aster VVB"],
                          ["IS-2026-1", "CP-NBO-01", "2026", "2026-01-01", "2026-06-30", "26,800",
                           "CC-NBO-021401–048200", "Aster VVB"],
                          ["IS-2026-2", "CP-NBO-02", "2026", "2026-07-01", "2026-12-31", "8,600",
                           "CC-NBO-048201–056800", "Aster VVB"],
                          ["IS-222-1", "CP-NBO-222", "2025", "2025-01-01", "2025-12-31", "14,800",
                           "CC-NBO222-000001–014800", "Terramar VVB"],
                          ["IS-222-2", "CP-NBO-222", "2026", "2026-01-01", "2026-09-30", "9,400",
                           "CC-NBO222-014801–024200", "Terramar VVB"],
                          ["IS-218-1", "CP-NBO-218", "2026", "2026-03-01", "2026-10-31", "3,200",
                           "CC-NBO218-000001–003200", (pill("verification pending", "warn"),)]]},
    "tx": {"k": "table", "an": 4, "label": "Transaction register — carbon_credit_transaction",
           "hint": "types are the ledger codes: P issue · S sell · T transfer · R retire. Σ quantity per "
                   "serial range may never exceed tco2e_verified",
           "cols": [("carbon_credit_transaction", "transaction_id"),
                    ("carbon_credit_transaction", "issuance_id"),
                    ("carbon_credit_transaction", "transaction_type"),
                    ("carbon_credit_transaction", "counterparty"),
                    ("carbon_credit_transaction", "quantity_tco2e"),
                    ("carbon_credit_transaction", "price_per_tco2e"),
                    ("carbon_credit_transaction", "transaction_date"),
                    ("carbon_credit_transaction", "retirement_beneficiary"),
                    ("carbon_credit_transaction", "registry_reference")],
           "rows": [["T-001", "IS-2025-1", (pill("P · issue", "n"),), "registry → owner", "21,400", "—",
                     "2026-01-14", "—", "RR-88021"],
                    ["T-018", "IS-2026-1", (pill("S · sell", "a"),), "NorthBank Trading", "6,000",
                     "$31.40", "2026-08-06", "—", "RR-88077"],
                    ["T-022", "IS-2026-1", (pill("T · transfer", "n"),), "Meridian GC", "3,500", "—",
                     "2026-09-12", "—", "RR-88115"],
                    ["T-030", "IS-2026-1", (pill("R · retire", "ok"),), "annual report FY26", "12,500",
                     "—", "2026-10-02", "SDG Hub North disclosure", "RR-88140"],
                    ["T-031", "IS-222-1", (pill("R · retire", "ok"),), "offset buyer", "12,200", "—",
                     "2026-05-27", "Northbank Scope 3 report", "RR-88144"],
                    ["T-035", "IS-218-1", (pill("P · issue", "warn"),), "registry → owner", "3,200", "—",
                     "2026-11-15", "—", "RR-88190"],
                    ["T-037", "IS-2026-1", (pill("S · sell", "bad"),), "Meridian GC", "3,100", "$29.80",
                     "2026-11-18", "—", "RR-88203 — exceeds remaining balance"]]},
    "bridge": {"k": "table", "an": 5, "label": "Bridge & dual intensity — carbon_credit_sdg_link",
               "hint": "intensity is shown two ways because the brief's material-catalogue mass pathway "
                       "is not modelled in this schema",
               "cols": [("carbon_credit_sdg_link", "link_id"),
                        ("carbon_credit_sdg_link", "issuance_id"),
                        ("carbon_credit_sdg_link", "sdg_target_id"),
                        ("project_sdg_target", "indicator_code"),
                        ("carbon_credit_sdg_link", "contribution_tco2e"),
                        ("^", "intensity · performance basis"), ("^", "intensity · mass basis (bounded)")],
               "rows": [["LK-04", "IS-2026-1", "ST-06 · 9.4.1", "9.4.1", "9,200",
                         "tCO₂e ÷ metered kWh (frame 20)",
                         "tCO₂e ÷ (rebar_tonnage + steel_weight) from structural_element"],
                        ["LK-05", "IS-2026-1", "ST-01 · 7.3.1", "7.3.1", "6,400",
                         "tCO₂e ÷ metered kWh (frame 20)",
                         "tCO₂e ÷ boq_item quantities for the services package"],
                        ["LK-07", "IS-222-1", "ST-03 · 11.6.1", "11.6.1", "2,100",
                         "tCO₂e ÷ diverted tonnage", "tCO₂e ÷ reused structural mass"]]},
    "bal": {"k": "bars", "label": "Ledger balance — issued vs transacted",
            "items": [("tco2e_verified issued", 100, "n", "56,800 t"),
                      ("retired (irreversible)", 44, "ok", "24,700 t"),
                      ("sold", 16, "a", "9,100 t"), ("transferred", 6, "warn", "3,500 t"),
                      ("attempted over-issue T-037", 5, "bad", "3,100 t — refused by the validator")],
            "cap": "serials: CC-NBO-000001–056800 issued · 000001–024700 retired"},
    "kpis": [("56,800 t", "Credits issued", "n"), ("24,700 t", "retired", "ok"),
             ("32,100 t", "In portfolio", "warn"), ("$31.40", "last trade price", "n"),
             ("11", "transactions this vintage", "n")],
}

CFG["23"] = {
    "type": "inspector", "sub": "Generated from the parsed schema at build time — no hand-listed FKs",
    "kpis": [("45", "tables in schema.json", "n"), ("84", "foreign keys total", "n"),
             ("9", "columns on the subject table", "n"), ("2", "incoming references", "ok"),
             ("1", "outgoing reference", "n")],
}

CFG["24"] = {
    "type": "mobile", "sub": "Offline-first capture on four P5 forms, syncing into the same tables",
    "kpis": [("3", "drafts on device", "n"), ("11", "photos queued", "warn"),
             ("08:42", "last full sync", "n"), ("offline", "mode", "bad"),
             ("41%", "device storage free", "warn")],
    "sheets": {"k": "tabs", "tid": "mob24", "an": 1,
               "label": "Sheet picker — the four highest-volume P5 forms",
               "items": [
                   ("daily progress",
                    fields("daily_progress", ["activity_id", "log_date", "headcount", "man_hours",
                                             "equipment_hours", "percent_complete"],
                           {"activity_id": "ACT-1204 F30 L4 frame", "log_date": "2026-11-20",
                            "headcount": "34", "man_hours": "272", "equipment_hours": "88",
                            "percent_complete": "64.0"},
                           {"activity_id": "select", "log_date": "date", "percent_complete": "warn"}, 2)
                    + '<p class="mobnote">draft 2 of 3 · saved locally, not yet posted to '
                      "daily_progress</p>"),
                   ("quality test",
                    fields("quality_test", ["test_id", "test_type", "measured_value", "pass_fail",
                                           "room_id", "element_id"],
                           {"test_id": "auto · QT-1116", "test_type": "concrete_cube_fck",
                            "measured_value": "33.8", "pass_fail": "false", "room_id": "R3-120 Core",
                            "element_id": "EL-214"},
                           {"test_id": "ro", "test_type": "select", "pass_fail": "bool"}, 2)
                    + '<p class="mobnote">a failing value pre-opens the NCR draft (frame 15)</p>'),
                   ("hse / weather",
                    fields("hse_record", ["log_date", "ltifr", "ppe_compliance_pct",
                                         "toolbox_attendance", "waste_tonnage", "carbon_kg_co2e"],
                           {"log_date": "2026-11-20", "ltifr": "0.42", "ppe_compliance_pct": "96.8",
                            "toolbox_attendance": "176", "waste_tonnage": "28.4",
                            "carbon_kg_co2e": "74,300"},
                           {"log_date": "date", "ltifr": "ro"}, 2)
                    + '<p class="mobnote">the stand-down quick-flag writes site_weather_log and a '
                      "non-productive code on the same log_date (frame 16)</p>"),
                   ("RFI with photo",
                    fields("rfi", ["rfi_id", "element_id", "activity_id", "stakeholder_id", "due_date",
                                  "cost_schedule_impact_flag"],
                           {"rfi_id": "auto · 424", "element_id": "EL-771",
                            "activity_id": "ACT-1310 H1 envelope", "stakeholder_id": "SH-002",
                            "due_date": "2026-11-27", "cost_schedule_impact_flag": "false"},
                           {"rfi_id": "ro", "element_id": "select", "due_date": "date",
                            "cost_schedule_impact_flag": "bool"}, 2)
                    + '<p class="mobnote">photo 1 of 4 attached · geo-stamp 51.5007 N 0.1021 W</p>')],
               "note": "each sheet writes the same table as its desktop counterpart in frames 13, 15, "
                       "16 and 14"},
    "queue": {"k": "table", "an": 2, "label": "Queue / sync state",
              "cols": [("^", "item"), ("^", "writes table"), ("^", "queued at"), ("^", "payload"),
                      ("^", "sync"), ("^", "retry")],
              "rows": [["log 11-19", "daily_progress", "18:04", "18 KB", (pill("pending wifi", "n"),), "—"],
                       ["test QT-1109", "quality_test", "18:22", "2.4 MB", (pill("uploading 64%", "warn"),),
                        "attempt 1"],
                       ["log 11-20 draft", "daily_progress", "07:58", "12 KB", (pill("queued", "n"),), "—"],
                       ["HSE 11-20", "hse_record", "08:10", "9 KB", (pill("synced", "ok"),), "—"],
                       ["RFI-418 photo", "rfi", "08:31", "2.1 MB", (pill("synced", "ok"),), "—"],
                       ["survey fix F3", "schedule_activity", "08:33", "1.1 MB",
                        (pill("server unreachable", "bad"),), "backoff 120 s"],
                       ["toolbox sheet", "hse_record", "08:40", "44 KB", (pill("synced", "ok"),), "—"]],
              "note": "queue order is per record id — a re-submitted draft updates the row, it never "
                      "creates a second one"},
    "conflict": {"k": "table", "an": 3, "label": "Conflict warning — same id edited on desktop",
                 "cols": [("quality_test", "test_id"), ("quality_test", "measured_value"),
                          ("^", "server value"), ("^", "resolution"), ("^", "audit")],
                 "rows": [["QT-1109", "31.0", "31.4", (pill("take server (audit kept)", "warn"),),
                           "SH-011 · 2026-11-19 16:44"],
                          ["QT-1112", "96.4", "96.4", (pill("identical — auto-resolved", "ok"),), "—"],
                          ["QT-1116", "33.8", "—", (pill("local only · upload pending", "n"),), "—"]],
                 "hint": "measured_value is the only contested column on this device today"},
    "attach": {"k": "raw", "an": 4, "label": "Capture bundle — photos attach by URL only",
               "html": ('<div class="bundle">'
                        '<figure class="shot"><img alt="site photo placeholder" '
                        'src="../assets/placeholder-photo.svg">'
                        "<figcaption>IMG_1180 · 2.1 MB · geo + 08:31</figcaption>"
                        '<em class="q ok">synced</em></figure>'
                        '<figure class="shot"><img alt="site photo placeholder" '
                        'src="../assets/placeholder-photo.svg">'
                        "<figcaption>IMG_1181 · 1.8 MB · core pour L4</figcaption>"
                        '<em class="q up">uploading 64%</em></figure>'
                        '<figure class="shot ghost"><span class="plus">+</span>'
                        "<figcaption>above 5 MB is recompressed before queueing; originals stay on the "
                        "device 7 days</figcaption></figure></div>")},
    "mstate": {"k": "empty", "title": "state · storage low / server unreachable",
               "body": "the queue keeps working: 7 items held locally, capture disabled above 5 MB, and "
                       "the retry counter shows attempt 2 of 5", "action": "Retry now"},
    "sync": {"k": "kv", "an": 5, "label": "Sync controls & device state", "items": [
        ("Mode", "offline · airplane — queue only, reads served from cache"),
        ("Queue depth", "7 items · 9.4 MB payload"),
        ("Retry policy", "exponential backoff, next attempt in 120 s (server unreachable)"),
        ("Storage", "41 % free on 128 GB — above the 25 % nag threshold"),
        ("Approver", "supervisors approve centrally; the device shows every draft as unverified until then")]},
}

CFG["25"] = {
    "type": "states", "sub": "five non-ideal states replayed on frames 12 (supply) and 17 (payments)",
    "loading": {"k": "raw", "an": 1, "full": True,
                "label": "Frame 12 · loading (skeleton) — column count matches the resolved view",
                "html": ('<div class="skel-demo"><div class="sk-row sk-head"><i></i><i></i><i></i>'
                         "<i></i><i></i></div>"
                         + ('<div class="sk-row"><i></i><i></i><i></i><i></i><i></i></div>' * 6)
                         + "</div>")},
    "empty": {"k": "empty", "an": 2, "title": "Frame 12 · empty",
              "body": "no purchase orders — raise your first PO from an awarded line. BP-12 stays "
                      "unavailable until the bid-variance justification in frame 11 is saved",
              "action": "Raise PO"},
    "error": {"k": "banner", "tone": "bad", "an": 3, "title": "Frame 12 · error + retry",
              "body": "supply chain feed unreachable — timeout after 10 s · retry 2 of 5 · last good "
                      "data 09:41 · partial rows are hidden rather than shown stale"},
    "readonly": {"k": "raw", "an": 4, "full": True,
                 "label": "Frame 17 · read-only role (subcontractor view)",
                 "html": ('<div class="ro-demo">'
                          '<div class="ro-row"><code class="colx">claimed_amount</code>'
                          "<b>$6.42m</b><span>visible — written by this role</span></div>"
                          '<div class="ro-row lock"><code class="colx">certified_amount</code>'
                          "<b>$6.05m</b><span>locked · PM write only (CSS hatching, no disabled "
                          "logic)</span></div>"
                          '<div class="ro-row"><code class="colx">retention_held</code>'
                          "<b>$0.61m</b><span>visible · read-only</span></div>"
                          '<div class="ro-row hide"><code class="colx">approved_variation_value</code><span class="nb">'
                          "not shown</span><span>other party's countersign lives on change_order</span>"
                          "</div></div>")},
    "stale": {"k": "kv", "an": 5, "label": "Frame 17 · stale data banner policy", "items": [
        ("Snapshot age", "certified_amount last written 2026-11-17 14:02 — 62 h old"),
        ("Threshold", "any read set older than 72 h renders the banner"),
        ("Dismissal", "sticky for 4 h, reappears on the next write to the same contract_id"),
        ("Server rule", "read-only and staleness are enforced server-side; the client only mirrors them"),
        ("Banner copy", "“payment figures are 62 h old — re-certify before approving PA-14”")]},
    "coverage": {"k": "table", "an": 6, "label": "State coverage across the pack", "cls": "matrix",
                 "cols": [("^", "state"), ("^", "frames that must render it")],
                 "rows": [[(pill("loading", "n"),),
                           "02 · 03 · 12 · 17 · 20 — skeletons mirror the resolved column count"],
                          [(pill("empty", "n"),), "02 · 12 · 15 · 16 · 20 · 21 · 24 · 25"],
                          [(pill("error", "bad"),), "06 · 10 · 12 · 13 · 21 · 22 · 24"],
                          [(pill("read-only", "n"),),
                           "01 audit view · 05 matrix · 17 sub view · 20 dashboard · 23 inspector"],
                          [(pill("stale", "warn"),),
                           "03 tiles · 06 metric age · 13 EV recompute · 16 weather feed · 20 telemetry"],
                          [(pill("conflict", "warn"),),
                           "24 sync conflict · 13 amended log after a retest · 15 value overwritten on "
                           "the desktop"],
                          [(pill("blocked / gated", "bad"),),
                           "10 permit expiry · 15 QC hold · 18 COO freeze · 19 retention gate · "
                           "22 over-issue refusal"]]},
}


# ---------------------------------------------------------------- page builders
def main_side(regs, side):
    """Two-column page body: primary regions left, contextual rail right."""
    if not side:
        return regions(regs, "stack")
    return '<div class="mainsplit">%s<aside class="side">%s</aside></div>' % (
        regions(regs, "stack"), "".join(section(x) for x in side))


def pg_shell(f, c):
    return ('<div class="chrome-demo">'
            + regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack")
            + main_side(c["regions"], c["sidebar"]) + "</div>")


def pg_register(f, c):
    regs = [{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")},
            {"k": "filters", "items": c["filters"], "right": '<span class="fcount">10 of 18 rows · '
             "sorted by target_end_date</span>"},
            {"k": "table", "cols": c["cols"], "rows": c["rows"], "foot": c["foot"], "an": 2,
             "label": "Project register — every column of project",
             "hint": "approved_budget may not exceed rom_budget by more than 15% without a logged "
                     "change_order · the Δ column is that check"},
            c["drawer"],
            {"k": "pager", "cur": 1, "total": 2, "note": "18 projects · page 1 of 2"}]
    return main_side(regs, c["states"])


def pg_workspace(f, c):
    return (regions([c["stepper"]], "stack")
            + regions(c["tiles"], "3")
            + main_side(c["regions"], c["aside"]))


def pg_spine(f, c):
    return main_side(c["regions"], c["aside"])


def pg_matrix(f, c):
    regs = [c["register"], {"k": "chipset", "an": 4, "label": "Downstream tables that point at a "
                            "stakeholder row", "items": [
                                ("rfi.stakeholder_id", "fk", "raised / answered by"),
                                ("submittal.stakeholder_id", "fk", "reviewer"),
                                ("contract.stakeholder_id", "fk", "awarded to"),
                                ("bid_package.prequal_score", "", "prequalification cleared")]},
                c["refs"], c["matrix"]]
    side = [c["state"],
            {"k": "banner", "tone": "warn", "title": "state · unverified org",
             "body": "SH-011 has no verified contact — the register keeps the row readable but the "
                     "invite flow stays closed"},
            {"k": "kv", "label": "Access notes", "items": [
                ("Deactivation", "blocked while an rfi or submittal row still points at the org"),
                ("Verifier", "rows are read-only to every internal role"),
                ("Credentials", "API credential to the BIM / IFC feed rotates from this frame")]}]
    return main_side(regs, side)


def pg_economics(f, c):
    regs = [c["metrics"], c["funding"], {"k": "chips", "an": 2, "t": "funding_source",
                                         "label": "funding_source columns"}]
    side = [c["donut"], c["drawdown"],
            {"k": "banner", "tone": "warn", "title": "state · stale metric",
             "body": "FM-2241 was last calculated 2026-06-02 — older than 30 days, so the tile shows a "
                     "recompute prompt instead of a date"},
            {"k": "kv", "label": "Rules with a UI consequence", "items": [
                ("Append-only baseline", "the revised rows carry a new calculated_at, FM-2201 never "
                 "changes"),
                ("Green bond link", "FS-03 and FS-06 must resolve to a carbon_project row (frame 22) or "
                 "the covenant check fails"),
                ("Covenant headroom", "below 10% a blocking banner appears in frame 03")]}]
    return main_side(regs, side)


def pg_bim(f, c):
    return (regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack")
            + regions(c["regions"], "21") + regions([c["tabs"]], "stack")
            + regions([c["control"]], "stack"))


def pg_boq(f, c):
    return (regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack")
            + main_side([{"k": "filters", "items": c["filters"],
                          "right": '<span class="fcount">10 of 1,204 lines</span>'},
                         {"k": "table", "an": 1, "cols": c["cols"], "rows": c["rows"], "cls": "num",
                          "label": "BOQ grid — rate build-up on boq_item",
                          "hint": "line value = estimated_qty × (unit_material_rate + unit_labor_rate × "
                                 "productivity_norm)"},
                         c["editor"], c["cont"], c["cos"], c["pager"]],
                        [{"k": "chips", "t": "contingency", "label": "contingency columns"},
                         {"k": "chips", "t": "boq_item", "label": "boq_item columns"},
                         {"k": "banner", "tone": "bad", "title": "state · rate missing",
                          "body": "EL-284 has no unit_material_rate — excluded from the WBS roll-up until "
                                  "a rate set is applied"},
                         {"k": "skeleton", "rows": 3, "cols": 10, "label": "state · unsaved diff loading"}]))


def pg_gantt(f, c):
    return (regions([{"k": "gantt", "an": 1, "full": True, "tasks": c["tasks"], "months": c["months"],
                      "label": "Gantt — bar width from duration_days, colour from is_critical_path",
                      "note": "the shaded segment inside each bar is percent_complete from frame 13"}],
                     "stack")
            + regions([c["ledger"], c["deps"]], "21")
            + main_side([c["weather"]],
                        [{"k": "chips", "t": "schedule_activity", "label": "schedule_activity columns"},
                         {"k": "chips", "t": "activity_dependency", "label": "activity_dependency "
                          "columns"},
                         {"k": "chipset", "label": "dependency_type values", "items": [
                            ("FS finish → start", "", "default"), ("SS start → start", "", "overlap"),
                            ("FF finish → finish", "", "power-on gate"), ("SF start → finish", "",
                                                                          "unused on this project")]},
                         {"k": "banner", "tone": "bad", "title": "state · loop in dependency graph",
                          "body": "DP-406 was rejected before write: ACT-1211 → ACT-1204 closes a cycle "
                                  "through the bridge table"}]))


def pg_risk(f, c):
    return (main_side([c["banner"], c["perm"], c["risk"]],
                      [c["heat"], c["site"],
                       {"k": "table", "label": "Exposure roll-up by wbs", "cls": "num",
                        "cols": [("^", "wbs_id"), ("^", "risks"), ("^", "Σ exposure"), ("^", "band")],
                        "rows": [["E1", "3", "42", (pill("high", "bad"),)],
                                 ["F3", "2", "30", (pill("medium", "warn"),)],
                                 ["G2", "1", "15", (pill("medium", "warn"),)],
                                 ["E2", "1", "12", (pill("medium", "warn"),)],
                                 ["H1", "1", "10", (pill("low", "n"),)]]}])
            + regions([{"k": "chips", "t": "permit", "label": "permit columns"},
                       {"k": "chips", "t": "risk_register", "label": "risk_register columns"}], "2"))


def pg_procurement(f, c):
    return main_side([c["bids"], c["award"], c["flow"], c["bonds"]],
                     [{"k": "chips", "t": "bid_package", "label": "bid_package columns"},
                      {"k": "chips", "t": "contract", "label": "contract columns"},
                      {"k": "bars", "label": "Prequalification spread", "items": [
                          ("BP-12", 91, "ok", "91.2"), ("BP-03", 88, "ok", "88.4"),
                          ("BP-07", 83, "a", "82.5"), ("BP-18", 81, "a", "81.0"),
                          ("BP-06", 80, "a", "79.6"), ("BP-21", 76, "warn", "76.2"),
                          ("BP-09", 74, "warn", "74.0"), ("BP-15", 69, "bad", "68.9")],
                       "cap": "prequal_score is the ranking input · below 70 the package goes to rebid"},
                      {"k": "banner", "tone": "warn", "title": "state · award under appeal",
                       "body": "BP-18 stays readable but locked: the void-award action is disabled until "
                               "the appeal closes"}])


def pg_supply(f, c):
    return main_side([c["pos"], c["miles"], c["trace"], c["mat"]], c["states"]
                     + [{"k": "chips", "t": "purchase_order", "label": "purchase_order columns"},
                        {"k": "chips", "t": "supply_shipment", "label": "supply_shipment columns"},
                        {"k": "chipset", "label": "Absence notes carried by the frame", "items": [
                            ("no material_catalogue table", "warn", "material attributes stay on boq_item"),
                            ("no embodied-carbon column", "warn", "ledger-side only (frame 22)")]},
                        {"k": "spark", "label": "Fabrication progress", "items": [
                            ("SHP-88 · PO-3341", [12, 24, 31, 44, 52, 61, 68],
                             "fabrication_pct weekly", ""),
                            ("SHP-90 · PO-3350", [8, 14, 22, 30, 39, 47, 55], "behind plan", "warn")]},
                        {"k": "empty", "title": "no bookings for SHP-93",
                         "body": "supply_shipment has a row but no carrier booking — the panel stays "
                                 "empty rather than showing an invented vessel", "action": "Add booking"}])


def pg_progress(f, c):
    states = [
        {"k": "banner", "tone": "warn", "title": "state · EV recompute queued",
         "body": "log 11-19 posted — earned_value_ev for ACT-1204 is recalculated against the new "
                 "percent_complete, SPI is not refreshed yet"},
        {"k": "skeleton", "rows": 3, "cols": 8, "label": "state · partially synced (8-column skeleton)"},
        {"k": "empty", "title": "state · offline draft",
         "body": "the 11-20 log is still on the device — it posts through the queue in frame 24 and "
                 "cannot appear here until it lands", "action": "Open the queue"},
        {"k": "chipset", "label": "Row locks", "items": [
            ("log older than 7 d", "n", "locked — an amendment needs a reason code"),
            ("QC hold on ACT-1108", "bad", "percent_complete gated by NCR-12")]}]
    return (regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack")
            + regions([c["form"]], "stack") + regions([c["log"]], "stack")
            + regions([c["split"]], "stack") + regions(states, "3")
            + regions([c["curve"]], "stack"))


def pg_kanbanflow(f, c):
    return (regions([c["board"]], "stack")
            + regions([c["chain"], c["flags"]], "2")
            + main_side([c["raise"]],
                        [c["empty"],
                         {"k": "chipset", "label": "Answer codes and what they gate", "items": [
                            ("code A · no change", "ok", "closes the clock"),
                            ("code B · resubmit", "warn", "reopens with a new due_date"),
                            ("code C · blocked", "bad", "counts against SPI float")]}]))


def pg_quality(f, c):
    return (regions([c["stepper"]], "stack")
            + regions([c["tests"], c["ncr"]], "stack")
            + main_side([c["bridge"], c["ncrchips"]],
                        [c["hold"], c["empty"],
                         {"k": "chipset", "label": "Disposition options (workflow service, not a table)",
                          "items": [("repair", "", "retest required"), ("replace", "", "new element_id"),
                                    ("accept-as-is", "warn", "architect signature"),
                                    ("rework", "", "reopen the log")]}]))


def pg_hse(f, c):
    return (regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack")
            + regions([c["ledger"]], "stack") + regions([c["sparks"]], "stack")
            + main_side([c["weather"]],
                        [c["empty"],
                         {"k": "bars", "label": "Stand-down rules applied this month", "items": [
                            ("wind > 60 km/h", 6, "bad", "6 days"), ("rainfall > 10 mm/h", 3, "warn",
                                                                     "3 days"),
                            ("lightning within 8 km", 2, "warn", "2 days"),
                            ("manual stand-down", 1, "n", "1 day")],
                          "cap": "each stand-down auto-suggests a non-productive code on the same "
                                 "log_date in frame 13"},
                         {"k": "chips", "t": "hse_record", "label": "hse_record columns"},
                         {"k": "chips", "t": "site_weather_log", "label": "site_weather_log columns"}]))


def pg_payments(f, c):
    states = [
        {"k": "banner", "tone": "bad", "title": "state · certification queried",
         "body": "PA-10 — 3 lines queried against claimed_amount, so net due falls to $1.91m until "
                 "each reason line is answered"},
        {"k": "empty", "title": "state · application in draft",
         "body": "PA-14 has never been certified: certified_amount is empty rather than zero, and "
                 "retention_held cannot be derived yet", "action": "Route for certification"},
        {"k": "skeleton", "rows": 3, "cols": 8, "label": "state · payless notice recalculating"},
        {"k": "chipset", "label": "Awaiting owner", "items": [
            ("CO-30", "warn", "+$0.56m · switchgear rating"),
            ("CO-35", "bad", "+$840k · above the delegation threshold")]}]
    return (regions([c["apps"], c["waterfall"]], "21")
            + regions([c["ret"]], "stack")
            + regions([c["co"], c["costeps"]], "stack")
            + main_side([c["der"]], states +
                        [{"k": "chips", "t": "payment_application", "label": "payment_application "
                          "columns"},
                         {"k": "chips", "t": "change_order", "label": "change_order columns"},
                         {"k": "kv", "label": "Thresholds", "items": [
                            ("PM certification limit", "$250,000 per application"),
                            ("Owner approval", "any change_order above $500,000 or any draw on "
                             "funding re-approval"),
                            ("Insurance gate", "a lapse suspends certification — PA-04 is held for "
                             "exactly that")]}])
            + regions([{"k": "filters",
                        "items": [("Contract", "sel", ["All", "CTR-03", "CTR-07", "CTR-09", "CTR-12",
                                                       "CTR-18"]),
                                  ("Period", "sel", ["Nov 2026", "Oct 2026", "Q4 2026"]),
                                  ("State", "chk", [("draft", True), ("certified", True),
                                                    ("suspended", False)])],
                        "right": '<span class="fcount">8 applications · $26.4m claimed</span>'},
                       {"k": "pager", "cur": 1, "total": 4, "note": "applications 1–8 of 31"}], "stack"))


def pg_handover(f, c):
    return (regions([c["checklist"]], "stack")
            + regions([c["assets"]], "stack")
            + regions([c["comm"], c["punch"]], "21")
            + main_side([c["gate"], c["fields"]],
                        [{"k": "chips", "t": "asset", "label": "asset columns — the element and room "
                          "bridges are columns here, not a bridge table"},
                         {"k": "chipset", "label": "Gate status", "items": [
                            ("project.certificate_of_occupancy_date", "pk", "still null — gated"),
                            ("municipal_inspection rows", "warn", "4 passed · 1 failed · 1 scheduled"),
                            ("open punch items", "bad", "182 of 284 cleared")]},
                         {"k": "banner", "tone": "bad", "title": "state · snag storm",
                          "body": "bulk-open on R7-210: three punch_item rows arrived within an hour and "
                                  "now hold AST-0067 out of commissioning"},
                         {"k": "empty", "title": "COO issued · read-only freeze",
                          "body": "shown for NBO-222 — once certificate_of_occupancy_date is set the "
                                  "whole handover panel becomes read-only", "action": "View archived"}])
            + regions([{"k": "chips", "t": "commissioning_test", "label": "commissioning_test columns"},
                       {"k": "chips", "t": "punch_item", "label": "punch_item columns"},
                       {"k": "chips", "t": "municipal_inspection", "label": "municipal_inspection "
                        "columns"}], "3"))


def pg_defects(f, c):
    return (main_side([c["defects"]],
                      [{"k": "gauge", "label": "DLP clock", "cur": 8, "items": [(64, "74 d", "of 117 d "
                        "elapsed", "a")]},
                       {"k": "bars", "label": "Defects by contract", "items": [
                           ("CTR-07 · Aurora Facades", 86, "bad", "3 open"),
                           ("CTR-18 · Legacy Sub", 71, "warn", "2 open"),
                           ("CTR-09 · VertiCo", 50, "warn", "1 open"),
                           ("CTR-12 · GridPower", 43, "warn", "1 open")],
                        "cap": "every work_order here is flagged to the responsible subcontractor"},
                       {"k": "banner", "tone": "bad", "title": "gate · BLOCKED",
                        "body": "retention_release_approved stays false: 7 open defects and one failed "
                                "inspection"},
                       {"k": "empty", "title": "state · all clear (gate armed)",
                        "body": "shown for NBO-215 — zero open defects, DLP expired, release awaiting "
                                "the Owner's signature", "action": "Arm the gate"}])
            + regions([c["gate"], c["fields"]], "2")
            + regions([c["pm"]], "stack")
            + regions([c["wo"]], "stack"))


def pg_telemetry(f, c):
    return (regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack")
            + regions([c["pivot"]], "stack")
            + regions([c["grid"]], "stack")
            + main_side([c["gaps"], c["ctx"]],
                        [c["empty"],
                         {"k": "chipset", "label": "Alert thresholds (ops-owned, not stored in schema)",
                          "items": [("supply_air_temp_c > 14.5", "warn", "2 assets"),
                                    ("filter_dp_pa > 150", "bad", "AST-0045 at 126"),
                                    ("apparent_power_kva > 460", "n", "watch"),
                                    ("gap > 5 min on any asset_id", "warn", "3 today")]},
                         {"k": "chips", "t": "facility_telemetry", "label": "facility_telemetry columns"},
                         {"k": "bars", "label": "Load profile — derived from the pivot", "items": [
                            ("06:00", 28, "n", "186 kW"), ("09:00", 62, "a", "412 kW"),
                            ("12:30", 74, "warn", "486 kW"), ("18:00", 51, "a", "336 kW"),
                            ("23:00", 17, "n", "112 kW")], "cap": "peak measured load against the declared design demand"}])
            + regions([{"k": "chips", "t": "asset", "label": "asset columns (context, from frame 18)"},
                       {"k": "chips", "t": "spatial_zone_room", "label": "spatial_zone_room columns "
                        "(roll-up target)"}], "2"))


def pg_sdg(f, c):
    return (regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack")
            + regions([c["matrix"]], "stack")
            + regions([c["targets"]], "stack")
            + main_side([c["dict"], c["evidence"]], c["states"]
                        + [{"k": "chips", "t": "project_sdg_target", "label": "project_sdg_target "
                            "columns"},
                           {"k": "chips", "t": "sdg_evidence_link", "label": "sdg_evidence_link columns"},
                           {"k": "bars", "label": "Compliance roll-up by goal", "items": [
                               ("7 · energy", 84, "a", "171 of 165 target"),
                               ("6 · water", 58, "bad", "1.9 vs 1.4"),
                               ("11 · waste", 95, "ok", "81 % diverted"),
                               ("12 · materials", 88, "ok", "71 % rebound"),
                               ("13 · resilience", 62, "warn", "4 events"),
                               ("9 · emissions", 79, "a", "198 kgCO₂e/t")]}]))


def pg_carbon(f, c):
    return (regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack")
            + regions([c["card"], c["flow"]], "21")
            + regions([c["issuance"]], "stack")
            + regions([c["tx"], c["bal"]], "21")
            + main_side([c["bridge"]],
                        [{"k": "chips", "t": "carbon_credit_issuance", "label": "carbon_credit_issuance "
                          "columns"},
                         {"k": "chips", "t": "carbon_credit_transaction", "label": "carbon_credit_"
                          "transaction columns"},
                         {"k": "chipset", "label": "Ledger codes", "items": [
                            ("P · issue", "n", "registry → owner"), ("S · sell", "a", "external buyer"),
                            ("T · transfer", "n", "within group"), ("R · retire", "pk",
                                                                    "irreversible, beneficiary written")]},
                         {"k": "banner", "tone": "bad", "title": "state · ledger double-entry mismatch",
                          "body": "T-037 would move 3,100 t against a balance of 2,300 t — the validator "
                                  "refuses the write and flags the issuance row"},
                         {"k": "empty", "title": "state · verification pending",
                          "body": "IS-218-1 has no vvb_name until the VVB statement lands; the row is "
                                  "shown but excluded from the issued total", "action": "Open audit"}])
            + regions([{"k": "chips", "t": "carbon_project", "label": "carbon_project columns"},
                       {"k": "chips", "t": "carbon_credit_sdg_link", "label": "carbon_credit_sdg_link "
                        "columns"}], "2"))


def pg_inspector(f, c):
    subject = f["srcs"][0]
    t = TABLES[subject]
    cols = list(COLS[subject])
    out = [regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack")]
    out.append(regions([{"k": "chips", "an": 1, "t": subject, "full": True,
                         "label": "Columns — %s (%d)" % (subject, len(cols)),
                         "caption": "PK amber · FK teal with the target table · type on hover"}], "stack"))
    out.append(regions([{
        "k": "table", "an": 2,
        "label": "Column metadata as rows — the same list the ERD inspector prints",
        "cols": [("^", "#"), ("^", "column"), ("^", "type"), ("^", "pk"), ("^", "fk target")],
        "rows": [[str(i + 1), (ccode(subject, n),), ctype(subject, n),
                  (pill("PK", "ok") if COLS[subject][n]["pk"] else "—"),
                  (pill("→ %s" % COLS[subject][n]["fk"], "warn") if COLS[subject][n]["fk"] else "—")]
                 for i, n in enumerate(cols)]},
        {"k": "chipset", "an": 3, "label": "Outgoing FKs (where this row points)",
         "items": [("%s → %s" % (n, COLS[subject][n]["fk"]), "fk", "resolve through this column")
                   for n in cols if COLS[subject][n]["fk"]]},
    ], "21"))
    inc = []
    for other in SCHEMA["tables"]:
        for col in other["cols"]:
            if col["fk"] == subject:
                inc.append([("%s.%s" % (other["name"], col["n"]),),
                            (ccode(other["name"], col["n"]),),
                            "many rows of %s can point at one row of %s" % (other["name"], subject)])
    out.append(regions([{
        "k": "table", "an": 4,
        "label": "Incoming FKs (who references this table) — computed scan over all %d tables"
                 % len(SCHEMA["tables"]),
        "hint": "the scan runs over the parsed schema at build time, so it cannot drift from the ERD",
        "cols": [("^", "referencing column"), ("^", "column token"), ("^", "cardinality note")],
        "rows": inc}], "stack"))
    out.append(regions([
        {"k": "banner", "tone": "info", "title": "read-only for all roles",
         "body": "this is documentation, not an editor — no column, FK or reference row here carries a "
                 "write affordance"},
        {"k": "skeleton", "rows": 2, "cols": 5,
         "label": "state · scan not cached (the reference list is computed at build time)"},
        {"k": "empty", "title": "state · leaf table (incoming scan returns 0)",
         "body": "30 of the 45 tables are referenced by nothing, so their inspector would show an empty "
                 "incoming list — for example rfi, contract or payment_application",
         "action": "Pick another table"},
        {"k": "chipset", "label": "Other inspector states from the same scan", "items": [
            ("no outgoing FKs (spine tables)", "n",
             ", ".join(sorted(t for t in TABLES if not any(c["fk"] for c in TABLES[t]["cols"
                                          ])))),
            ("self-reference", "warn", ", ".join(sorted(t for t in TABLES
                                                        if any(c["fk"] == t for c in TABLES[t]["cols"])))),
            ("schema coverage", "ok", "%d of %d tables are declared as a data source by at least one "
             "frame" % (len(TABLE_PAGES), len(SCHEMA["tables"])))]}], "3"))
    sib = [x for x in TABLE_PAGES[subject] if x != f["id"]]
    out.append(regions([{"k": "chipset", "an": 5, "label": "Sibling frames sharing this table",
                         "items": [("frame %s" % x, "", BY_ID[x]["title"]) for x in sib]
                         if sib else [("(leaf table)", "", "no other frame lists this table")]}],
                      "stack"))
    return "".join(out)


def pg_mobile(f, c):
    phone = ('<div class="phone"><div class="pbar"><span>08:42</span>'
             '<span class="pdot off"></span><span>offline &#183; queue only</span>'
             '<span class="pbatt"><i style="width:41%"></i></span></div>'
             + regions([c["sheets"], c["attach"]], "stack")
             + '<div class="phome"></div></div>')
    side = '<div class="mside">%s</div>' % "".join(
        section(x) for x in ([c["queue"], c["conflict"], c["sync"], c["mstate"]]))
    return ('<div class="mobilesplit">%s%s</div>' % (phone, side)
            + regions([{"k": "kpi", "items": c["kpis"], "full": True, "an": c.get("kpi_an")}], "stack"))


def pg_states(f, c):
    order = ["loading", "empty", "error", "readonly", "stale"]
    blocks = [c[k] for k in order]
    return (regions(blocks, "stack")
            + regions([c["coverage"]], "stack")
            + regions([{"k": "kv", "label": "Design-system note", "items": [
                ("Applies to", "all 24 data frames, not only the two shown here"),
                ("Skeleton rule", "same column count as the resolved view — never a generic block"),
                ("Read-only", "enforced server-side; the client mirrors the state"),
                ("Staleness", "a dismissed banner returns on any newer write to the same contract")]}],
                      "stack"))


BUILDERS = {
    "01": pg_shell, "02": pg_register, "03": pg_workspace, "04": pg_spine, "05": pg_matrix,
    "06": pg_economics, "07": pg_bim, "08": pg_boq, "09": pg_gantt, "10": pg_risk,
    "11": pg_procurement, "12": pg_supply, "13": pg_progress, "14": pg_kanbanflow, "15": pg_quality,
    "16": pg_hse, "17": pg_payments, "18": pg_handover, "19": pg_defects, "20": pg_telemetry,
    "21": pg_sdg, "22": pg_carbon, "23": pg_inspector, "24": pg_mobile, "25": pg_states,
}


# ---------------------------------------------------------------- hub (index.html)
HUB_ONE_LINE = {
    "01": "Shell, scope switcher and the rail that carries the seven phase groups.",
    "02": "Project register with the nine project columns and the detail drawer.",
    "03": "Workspace landing: phase stepper, summary tiles, cross-table inbox, WBS roll-up.",
    "04": "The three spines: self-referencing WBS tree, rooms and levels, site data.",
    "05": "Who is modelled and the role × phase permission matrix.",
    "06": "Baseline versus revised economics plus the funding_source capital stack.",
    "07": "IFC element inspector with structural / MEP subtype tabs and design control.",
    "08": "BOQ rate build-up, contingency drawdown and the line-level roll-up.",
    "09": "Gantt over schedule_activity with the activity_dependency bridge.",
    "10": "Permit board, risk heat map and the scored risk ledger.",
    "11": "Bid comparison, the award panel and bond / insurance expiry.",
    "12": "PO register plus fabrication → ETD → ETA → customs track & trace.",
    "13": "Daily field log, trade split and the earned-value S-curve.",
    "14": "RFI and submittal kanban with SLA ageing and the impact flag.",
    "15": "Quality test grid and the four-stage NCR state stepper.",
    "16": "HSE ledger, trend sparklines and the weather stand-down log.",
    "17": "Payment waterfall, retention pot and change-order approvals.",
    "18": "Asset register, commissioning results, punch snags, statutory gate.",
    "19": "Defect SLA clock, PM plan versus reactive work, retention gate.",
    "20": "facility_telemetry pivotted onto assets, gaps and derived load.",
    "21": "SDG dictionary, matrix, targets and the evidence drill-through.",
    "22": "Registry card, issuance ledger, P/S/T/R transactions, SDG bridge.",
    "23": "Record inspector generated from the parsed FK scan.",
    "24": "Offline-first mobile capture, sync queue and conflict state.",
    "25": "Loading, empty, error, read-only and stale replayed on two frames.",
}


def hub_group(pk):
    fr = [f for f in FRAMES if f["phase_key"] == pk]
    cards = []
    for f in fr:
        srcs = " ".join('<li>%s</li>' % E(t) for t in f["srcs"])
        cards.append(
            '<article class="hcard"><a class="hlink" href="pages/%s">'
            '<span class="hnum">%s</span><h3>%s</h3></a>'
            '<p>%s</p><ul class="hsrcs">%s</ul></article>'
            % (E(f["file"]), E(f["id"]), E(f["title"]), E(HUB_ONE_LINE[f["id"]]), srcs))
    return ('<section class="hgroup" id="%s"><header><h2><i class="rdot %s"></i>%s'
            '<em>%d frames · %d tables</em></h2><p class="hgsrcrews">%s</p></header>'
            '<div class="hcards">%s</div></section>'
            % (E(pk), E(pk), E(PHASE_LABEL[pk]), len(fr), len(PHASE_TABLES[pk]),
               " · ".join(tref(t, "pages/") for t in PHASE_TABLES[pk]), "".join(cards)))


def hub():
    frames_by_phase = {pk: len([f for f in FRAMES if f["phase_key"] == pk]) for pk in PHASE_ORDER}
    parts = [HEAD % ("Meridian CS · visual demo hub — 25 wireframe frames", "", "")]
    parts.append('<body class="hub">')
    parts.append(topbar(base=""))
    parts.append('<div class="hubwrap"><main class="hubmain">')
    parts.append('<header class="hubhead"><span class="kicker">Static visual demo · derived from '
                 "the wireframe pack (<code>wireframes.html</code>, 25 frames) and the parsed ERD "
                 "schema</span>"
                 "<h1>Meridian Construction Suite<span class=\"h1sub\">frame-pack walkthrough</span></h1>"
                 "<p class=\"hublede\">Every page below is one wireframe frame rebuilt as product UI: "
                 "same regions, same numbered annotations, same source tables. Nothing here is wired to "
                 "a backend — there is no JavaScript in the build, and all figures are illustrative for "
                 "the NBO-221 Riverside Tower scenario.</p>"
                 '<div class="hubmeta"><span>%d pages + this hub</span><span>%d phase groups</span>'
                 "<span>45 tables · 320 columns · 84 FKs</span><span>HTML + CSS only</span></div>"
                 "</header>" % (len(FRAMES), len(PHASE_ORDER)))
    parts.append(regions([{"k": "kpi", "full": True, "label": "Project overview — the scenario this "
                           "demo walks through", "items": [
                               ("18", "projects in portfolio", "n"),
                               ("$401m", "approved_budget · NBO-221", "n"),
                               ("118,000 m²", "gfa_sqm", "n"),
                               ("0.94", "SPI", "warn"),
                               ("-6 d", "critical-path float", "bad"),
                               ("48 / 56.8 k t", "tCO₂e issued / verified", "ok"),
                               ("9 / 14", "SDG targets met", "warn"),
                               ("$4.2m", "retention held", "warn")]},
                          {"k": "chipset", "label": "Frame groups", "items": [
                              ("%s · %d frames" % (PHASE_LABEL[p], frames_by_phase[p]), p,
                               "%d tables" % len(PHASE_TABLES[p])) for p in PHASE_ORDER]}],
                        "stack"))
    for pk in PHASE_ORDER:
        parts.append(hub_group(pk))
    parts.append('<section class="provn" id="provenance"><h2>Provenance &amp; caveats</h2>'
                 "<div class=\"provn-grid\">"
                 "<div><h3>Where the field names come from</h3><p>Field names on every page are "
                 "validated against <code>/tmp/qwenwork/schema.json</code> — the machine-parsed form of "
                 "the source ERD file. That parse yields <b>45 tables, 320 columns and 84 foreign keys</b> "
                 "across <b>7</b> phase groups (<code>core, d12, p34, p5, p67, sdg, cc</code>). A column "
                 "name may only appear on a page when it belongs to one of that frame's declared "
                 "source tables; the build fails otherwise.</p></div>"
                 "<div><h3>Known mismatch with the source labels</h3><p>The source HTML describes itself "
                 "in its own header as “47 tables · 6 phases”, but the schema array inside that same "
                 "file parses to 45 tables across 7 phase keys. This demo follows the parsed data, not "
                 "the label; the two-frame difference (plus “SDG layer” and “Carbon credit layer” being "
                 "separate keys rather than one phase) is carried through the rail and the hub "
                 "grouping.</p></div>"
                 "<div><h3>Non-functional disclaimer</h3><p>This is a visual-only static site. There are "
                 "no scripts, no handlers, no data fetching and no state: filters, tabs, sort arrows, "
                 "pagers and buttons are rendered as they would look, and the CSS-only interactions "
                 "(hover, <code>:target</code>, radio tabs) exist to show states, not to implement "
                 "behaviour. Values are plausible construction-project numbers, not real ones.</p></div>"
                 "<div><h3>What was simplified</h3><p>Charts that a wireframe drew as placeholders "
                 "(S-curve, drawdown line, LTIFR trend, CO₂ grid-intensity) are drawn as static CSS / "
                 "inline-SVG shapes over the same series. Panels the wireframe marked “derived, no "
                 "table” are kept visibly labelled as derived.</p></div></div></section>")
    parts.append('<section class="sitemap"><h2>Full frame index</h2><div class="tw">'
                 '<table class="grid"><thead><tr>'
                 "<th>#</th><th>page</th><th>phase group</th><th>source tables</th>"
                 "<th>file</th></tr></thead><tbody>")
    for f in FRAMES:
        parts.append('<tr><td>%s</td><td><a href="pages/%s">%s</a></td><td>%s</td><td>%s</td>'
                     "<td><code>pages/%s</code></td></tr>"
                     % (E(f["id"]), E(f["file"]), E(f["title"]), E(PHASE_LABEL[f["phase_key"]]),
                        " · ".join(tref(t, "pages/") for t in f["srcs"]), E(f["file"])))
    parts.append("</tbody></table></div></section>")
    parts.append('<footer class="pgfoot"><div class="pf-row"><span class="prov"><b>Meridian CS · '
                 "visual demo hub.</b> 25 wireframe frames → 25 pages + this hub · assets/site.css "
                 "(single stylesheet, breakpoints 1100px / 640px) + assets/print.css.</span></div>"
                 '<div class="pf-row pf-fine"><span>static / non-functional</span>'
                 '<a href="#provenance">Provenance note</a><span>built by gen_site.py</span>'
                 "</div></footer>")
    parts.append("</main></div></body></html>")
    return "\n".join(parts)


# ---------------------------------------------------------------- stylesheet
CSS_A = """
/* Meridian CS visual demo — single stylesheet. Dark slate + white, one accent, no JS. */
:root{
  --slate-0:#12171f; --slate-1:#1b2230; --slate-2:#232c3c; --slate-3:#33405a;
  --ink:#141a23; --ink-2:#414d61; --ink-3:#6b7789; --line:#dfe3ea; --line-2:#eceff4;
  --paper:#ffffff; --paper-2:#f6f7f9; --paper-3:#eef1f5;
  --accent:#2f6f66; --accent-soft:#e4efec;
  --ok:#3d7a4c; --ok-soft:#e6f0e8; --warn:#c0792f; --warn-soft:#f8efe2;
  --bad:#a8474a; --bad-soft:#f7e9e9; --info:#41628f; --info-soft:#e9eef6;
  --g-a:#2f6f66; --g-ok:#3d7a4c; --g-warn:#c0792f; --g-bad:#a8474a;
  --mono:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,monospace;
  --sans:"Inter","Segoe UI",system-ui,-apple-system,Helvetica,Arial,sans-serif;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper-2);color:var(--ink);font:14px/1.5 var(--sans)}
a{color:inherit;text-decoration:none}
h1,h2,h3,h4,h5{margin:0;font-weight:600;letter-spacing:-0.01em}
p{margin:0}
ul,ol{margin:0;padding:0;list-style:none}
code{font:11.5px/1.4 var(--mono)}
/* ---------- top bar */
.topbar{position:sticky;top:0;z-index:40;display:flex;gap:18px;align-items:center;
  justify-content:space-between;padding:0 20px;height:52px;background:var(--slate-1);color:#e7ebf2;
  border-bottom:1px solid var(--slate-3)}
.tb-l,.tb-r{display:flex;align-items:center;gap:14px;min-width:0}
.brand{font-weight:700;letter-spacing:.14em;font-size:12px}
.brand em{color:var(--accent);font-style:normal;margin-left:3px;background:#fff;padding:1px 4px;
  border-radius:3px;font-size:10px;letter-spacing:.08em}
.scope{display:flex;align-items:baseline;gap:7px;padding:4px 9px;border:1px solid var(--slate-3);
  border-radius:6px;font-size:12.5px;max-width:270px}
.scope b{font-family:var(--mono);font-size:11.5px;color:#9fb6c9}
.scope span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.phasecur,.role{font-size:12px;display:flex;align-items:center;gap:6px;color:#cfd8e4;
  white-space:nowrap}
.caret{width:0;height:0;border:4px solid transparent;border-top-color:#7f8ea3;margin-top:3px}
.qsearch{display:flex;align-items:center;gap:8px;background:var(--slate-0);border:1px solid
  var(--slate-3);border-radius:999px;padding:5px 12px;font-family:var(--mono);font-size:11.5px;
  color:#c9d4e2;max-width:330px;white-space:nowrap;overflow:hidden}
.qsearch u{text-decoration:none;color:var(--accent)}
.qsearch em{font-style:normal;color:#7d8ba0;margin-left:6px}
.asof{font-size:11.5px;color:#94a2b6}
.asof b{font-family:var(--mono);color:#dfe6ef;font-weight:500}
.ro-badge{font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;padding:3px 8px;
  border-radius:4px;background:var(--accent);color:#fff}
.tb-home{font-size:12px;color:#cfd8e4;border:1px solid var(--slate-3);padding:5px 10px;
  border-radius:6px}
.tb-home:hover{background:var(--slate-2)}
/* ---------- layout */
.wrap{display:grid;grid-template-columns:246px minmax(0,1fr);gap:22px;max-width:1580px;
  margin:0 auto;padding:22px 20px 60px}
.main{min-width:0}
.rail{position:sticky;top:74px;align-self:start;max-height:calc(100vh - 96px);overflow:auto;
  background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:12px}
.rail-top{padding-bottom:10px;border-bottom:1px solid var(--line-2);margin-bottom:10px}
.rail-top .home{display:inline-block;font-size:12px;color:var(--accent);font-weight:600}
.railproj{display:block;margin-top:6px;font-size:11.5px;color:var(--ink-3)}
.railproj b{font-family:var(--mono);color:var(--ink-2)}
.rgrp{margin-bottom:8px}
.rgl{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:600;color:var(--ink);
  padding:5px 4px;border-radius:5px}
.rgl em{margin-left:auto;font-style:normal;font-family:var(--mono);font-size:10px;color:var(--ink-3)}
.rdot{width:8px;height:8px;border-radius:2px;flex:0 0 auto;background:var(--ink-3)}
.rdot.core{background:#57627a}.rdot.d12{background:#2f6f66}.rdot.p34{background:#68548f}
.rdot.p5{background:#c0792f}.rdot.p67{background:#3d7a4c}.rdot.sdg{background:#1f7a8c}
.rdot.cc{background:#a8474a}
.rgrp ul{display:none;margin:3px 0 0 0;border-left:1px solid var(--line);margin-left:9px}
.rgrp.open ul{display:block}
.rgrp li a{display:flex;gap:7px;align-items:baseline;font-size:12px;padding:4px 6px 4px 9px;
  color:var(--ink-2);border-left:2px solid transparent;margin-left:-1px;border-radius:0 5px 5px 0;
  min-width:0;max-width:100%}
.rgrp li a u{text-decoration:none;font-family:var(--mono);font-size:10.5px;color:var(--ink-3);
  flex:0 0 auto}
.rgrp li a span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rgrp li a:hover{background:var(--paper-3);color:var(--ink)}
.rgrp li a.on{background:var(--accent-soft);border-left-color:var(--accent);color:#1f4f48;
  font-weight:600}
.rail-foot{margin-top:12px;padding-top:10px;border-top:1px solid var(--line-2);font-size:11px;
  color:var(--ink-3);display:flex;flex-wrap:wrap;gap:4px 10px}
.rail-foot span{flex:1 1 100%}
"""
CSS_B = """
/* ---------- page head */
.crumbs{font-size:12px;color:var(--ink-3);margin-bottom:10px}
.crumbs a:hover{color:var(--accent);text-decoration:underline}
.crumbs i{font-style:normal;color:#b6bfcc;padding:0 3px}
.crumbs b{color:var(--ink-2);font-weight:600}
h1{font-size:23px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.fid{font:500 11px var(--mono);background:var(--slate-1);color:#dbe2ec;padding:3px 8px;
  border-radius:5px;letter-spacing:.04em}
.sub{color:var(--ink-2);font-size:13.5px;margin-top:4px}
.lede{margin-top:10px;font-size:13.5px;color:var(--ink-2);max-width:80ch;background:var(--paper);
  border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:8px;padding:11px 14px}
.lede b{color:var(--ink)}
.lede a,.cap a,.rnote a,.tblnote a,.rules a,li a,.spec a,p a{color:var(--accent);
  border-bottom:1px solid rgba(47,111,102,.28)}
.lede a:hover,.spec a:hover{background:var(--accent-soft);border-bottom-color:var(--accent)}
/* ---------- data source strip */
.srcs-strip{display:flex;flex-wrap:wrap;gap:8px;align-items:stretch;margin:14px 0 18px;
  padding:11px 12px;background:var(--paper);border:1px solid var(--line);border-radius:9px}
.ssl{font:600 10px/1 var(--sans);letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3);
  align-self:center;padding-right:4px}
.src-card{display:flex;flex-direction:column;gap:2px;padding:6px 9px;border:1px solid var(--line);
  border-radius:7px;background:var(--paper-2);min-width:150px}
.srcname{font:600 12px var(--mono);color:var(--ink)}
.srcname:hover{color:var(--accent);text-decoration:underline}
.src-card em{font-style:normal;font-size:10.5px;color:var(--ink-3);font-family:var(--mono)}
.sibs{font-size:10.5px;color:var(--ink-3);display:flex;gap:5px;flex-wrap:wrap}
.sibs a{font-family:var(--mono);color:var(--info);border-bottom:1px dotted rgba(65,98,143,.4)}
.sibs a:hover{background:var(--info-soft)}
.sibs i{font-style:normal;color:#98a3b4}
/* ---------- regions */
.rg-stack{display:flex;flex-direction:column;gap:14px;margin-bottom:14px}
.rg-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-bottom:14px}
.rg-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:14px}
.rg-21{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:14px;margin-bottom:14px}
.rg-12{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);gap:14px;margin-bottom:14px}
.mainsplit{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:16px;align-items:start}
.side{display:flex;flex-direction:column;gap:14px;position:sticky;top:74px}
.reg{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:14px 15px 15px;
  position:relative}
.reg:hover{border-color:#cfd6e0}
.reg-h{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:10px}
.reg-h h3{font-size:13.5px;color:var(--ink)}
.reg-h .pill{margin-left:auto}
.an.anx{background:transparent;color:var(--ink-3);border:1px dashed #b9c2cf;box-shadow:none;
  font-weight:600}
.an{position:absolute;top:10px;right:12px;width:19px;height:19px;border-radius:50%;
  background:var(--slate-1);color:#fff;font:600 10.5px/19px var(--mono);text-align:center;
  box-shadow:0 0 0 3px rgba(27,34,48,.06)}
.rnote{margin-top:9px;font-size:11.5px;color:var(--ink-3);border-top:1px dashed var(--line);
  padding-top:8px}
.cap{margin-top:8px;font-size:11.5px;color:var(--ink-3)}
.tblnote{margin-top:8px;font-size:11.5px;color:var(--ink-3)}
.tabintro{font-size:12px;color:var(--ink-2);margin-bottom:9px}
/* ---------- kpi */
.kpi-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:10px}
.kpi{background:var(--paper);border:1px solid var(--line);border-radius:9px;padding:11px 12px;
  display:flex;flex-direction:column;gap:3px;position:relative;overflow:hidden}
.kpi::after{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--ink-3)}
.kpi.ok::after{background:var(--ok)}.kpi.warn::after{background:var(--warn)}
.kpi.bad::after{background:var(--bad)}.kpi.n::after{background:var(--accent)}
.kv{font:600 19px/1.2 var(--mono);letter-spacing:-.02em;color:var(--ink);
  font-variant-numeric:tabular-nums}
.kpi.warn .kv{color:var(--warn)}.kpi.bad .kv{color:var(--bad)}.kpi.ok .kv{color:var(--ok)}
.kl{font-size:11px;color:var(--ink-3);letter-spacing:.01em}
"""

CSS_C = """
/* ---------- tables */
.reg-h{padding-right:34px}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:8px;
  background-color:var(--paper);
  background-image:linear-gradient(90deg,var(--paper) 22px,rgba(255,255,255,0)),
    linear-gradient(270deg,var(--paper) 22px,rgba(255,255,255,0)),
    radial-gradient(farthest-side at 0 50%,rgba(20,26,35,.16),transparent),
    radial-gradient(farthest-side at 100% 50%,rgba(20,26,35,.16),transparent);
  background-position:0 0,100% 0,0 0,100% 0;background-repeat:no-repeat;background-size:26px 100%,
    26px 100%,12px 100%,12px 100%;background-attachment:local,local,scroll,scroll;
  padding:0 2px}
.tw:hover{border-color:#cfd6e0}
table.grid{width:100%;border-collapse:separate;border-spacing:0;font-size:12.5px;min-width:520px}
table.grid thead th{background:var(--paper-3);text-align:left;font:600 11px var(--mono);
  color:var(--ink-2);padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
table.grid th.col{color:var(--ink)}
table.grid th.col.pk{background:#fbf4e6;color:#7a5a17}
table.grid th.col.fk{color:#245e72}
.fkdot{font-style:normal;color:#5b8fa6;margin-left:4px}
table.grid th.syn{color:var(--ink-3);font-weight:500;font-style:italic}
table.grid tbody td{padding:8px 10px;border-bottom:1px solid var(--line-2);vertical-align:middle;
  color:var(--ink);white-space:nowrap}
table.grid tbody tr:nth-child(even) td{background:#fbfcfd}
table.grid tbody tr:hover td{background:var(--accent-soft)}
table.grid tbody tr:last-child td{border-bottom:0}
table.grid tfoot td{padding:8px 10px;background:var(--slate-1);color:#e5eaf1;font-size:11.5px;
  font-family:var(--mono);white-space:nowrap}
table.grid.num tbody td{font-family:var(--mono);font-variant-numeric:tabular-nums}
table.matrix td{text-align:center}
table.matrix tbody td:first-child{font-weight:600;text-align:left;white-space:normal}
/* ---------- pills / chips */
.pill{display:inline-block;font-size:10.5px;line-height:1;padding:4px 7px;border-radius:999px;
  background:var(--paper-3);color:var(--ink-2);border:1px solid var(--line);white-space:nowrap}
.pill.ok{background:var(--ok-soft);color:#2c5c37;border-color:#c9dfd0}
.pill.warn{background:var(--warn-soft);color:#8a5620;border-color:#ecd9c0}
.pill.bad{background:var(--bad-soft);color:#8b3a3d;border-color:#e8cccc}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{display:inline-flex;align-items:center;gap:5px;font:11px var(--mono);padding:4px 8px;
  border-radius:5px;border:1px solid var(--line);background:var(--paper-2);color:var(--ink-2);
  max-width:100%}
.chip.pk{background:#fbf4e6;border-color:#e8d9b8;color:#7a5a17}
.chip.fk{background:#e9f2f6;border-color:#c8dde6;color:#245e72}
.chip.warn{background:var(--warn-soft);border-color:#ecd9c0;color:#8a5620}
.chip.bad{background:var(--bad-soft);border-color:#e8cccc;color:#8b3a3d}
.chip.ok{background:var(--ok-soft);border-color:#c9dfd0;color:#2c5c37}
.tgt{font-style:normal;color:#7d8b99;font-size:10px}
.chipcap{font-size:11.5px;color:var(--ink-3);flex:1 1 100%;margin-bottom:2px}
/* ---------- form fields */
.fields{display:grid;gap:10px}
.fields.f1{grid-template-columns:minmax(0,1fr)}
.fields.f2{grid-template-columns:repeat(2,minmax(0,1fr))}
.fields.f3{grid-template-columns:repeat(3,minmax(0,1fr))}
.fld{display:flex;flex-direction:column;gap:3px;background:var(--paper-2);border:1px solid
  var(--line);border-radius:7px;padding:7px 9px;min-width:0}
.fname{display:flex;align-items:center;gap:6px}
.fld code{color:var(--ink);font-weight:600}
.fld.pk{background:#fdf8ee;border-color:#eadcbc}
.fld.fk{background:#f2f8fa;border-color:#cfe2e9}
.fld.ro{border-style:dashed}
.fld .fmeta{font:10px var(--mono);color:var(--ink-3)}
.in{width:100%;border:1px solid var(--line);border-radius:5px;background:var(--paper);
  padding:6px 8px;font:12px var(--mono);color:var(--ink);min-width:0}
.in:used,.in.ro,.in[readonly],.in:disabled{
  background:repeating-linear-gradient(135deg,#f4f6f8,#f4f6f8 6px,#eef1f5 6px,#eef1f5 12px);
  color:var(--ink-2);border-style:dashed}
.in.invalid{border-color:var(--bad);background:var(--bad-soft);color:#8b3a3d;border-style:solid}
.in.warn{border-color:var(--warn);background:var(--warn-soft);border-style:solid}
.in.empty{border-style:dashed;border-color:var(--bad);color:#b0777a;background:var(--paper)}
.in:focus{outline:2px solid rgba(47,111,102,.3)}
textarea.in{resize:none;font:12px var(--sans)}
select.in{appearance:none;background-image:linear-gradient(45deg,transparent 50%,#8b96a6 50%),
  linear-gradient(135deg,#8b96a6 50%,transparent 50%);background-position:calc(100% - 14px) 12px,
  calc(100% - 9px) 12px;background-size:5px 5px;background-repeat:no-repeat;padding-right:26px}
.sw{display:inline-flex;align-items:center}
.sw input{position:absolute;opacity:0;width:0;height:0}
.sw span{width:34px;height:18px;border-radius:999px;background:#cfd6e0;position:relative;
  display:inline-block}
.sw span::after{content:"";position:absolute;top:2px;left:2px;width:14px;height:14px;
  border-radius:50%;background:#fff}
.sw input:checked + span{background:var(--accent)}
.sw input:checked + span::after{left:18px}
.swl{font:11px var(--mono);color:var(--ink-2);margin-left:6px}
/* ---------- bars / spark / gauge / donut */
.bars{display:flex;flex-direction:column;gap:8px}
.brow{display:grid;grid-template-columns:minmax(70px,1.2fr) minmax(46px,3fr) minmax(0,auto);
  gap:9px;align-items:center;font-size:11.5px}
.bl{color:var(--ink-2);font-family:var(--mono);font-size:11px;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.btrack{height:10px;background:var(--paper-3);border-radius:5px;overflow:hidden}
.bfill{display:block;height:100%;background:var(--accent);border-radius:5px}
.bfill.n{background:#8994a6}
.bfill.ok{background:var(--ok)}
.bfill.warn{background:var(--warn)}
.bfill.bad{background:var(--bad)}
.br{font-family:var(--mono);color:var(--ink);font-variant-numeric:tabular-nums;
  white-space:normal;overflow-wrap:anywhere;max-width:150px;text-align:right}
.sparkrow{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.sparkcard{border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--paper-2)}
.sparkcard h5{font-size:11.5px;color:var(--ink-2);margin-bottom:8px;font-weight:600}
.spark{display:flex;align-items:flex-end;gap:2px;height:56px}
.spark i{flex:1 1 auto;background:linear-gradient(180deg,var(--accent),#4b8f85);
  border-radius:1px 1px 0 0;min-width:3px}
.spark.alt i{background:linear-gradient(180deg,#41628f,#6f8fb8)}
.spark.warn i{background:linear-gradient(180deg,var(--warn),#d9a465)}
.spark.bad i{background:linear-gradient(180deg,var(--bad),#c47b7e)}
.spc{display:block;font-size:10.5px;color:var(--ink-3);margin-top:6px}
.gaugerow{display:flex;gap:14px;flex-wrap:wrap}
.gauge .ring{width:104px;height:104px;border-radius:50%;display:grid;place-items:center;
  position:relative;text-align:center}
.gauge .ring::after{content:"";position:absolute;inset:11px;background:var(--paper);
  border-radius:50%}
.gauge b,.gauge i{position:relative;z-index:1;display:block}
.gauge b{font:600 17px var(--mono);color:var(--ink)}
.gauge i{font-style:normal;font-size:10px;color:var(--ink-3);padding:0 8px}
.donutwrap{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.donut{width:118px;height:118px;border-radius:50%;display:grid;place-items:center;flex:0 0 auto}
.donut span{width:76px;height:76px;border-radius:50%;background:var(--paper);display:grid;
  place-items:center;text-align:center;line-height:1.25}
.donut span b{font:600 15px var(--mono)}
.donut span i{font-style:normal;font-size:10px;color:var(--ink-3)}
.dlegend{font-size:11.5px;color:var(--ink-2);display:flex;flex-direction:column;gap:4px}
.dlegend i{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px}
.dlegend b{font-family:var(--mono);font-weight:600}
"""

CSS_D = """
/* ---------- gantt */
.gantt{border:1px solid var(--line);border-radius:8px;padding:12px 14px 8px;
  background:var(--paper-2);overflow-x:auto}
.gantt::after,.kanban::after{content:"\2194  horizontal scroll";display:block;text-align:right;
  font:9.5px var(--mono);color:#9aa5b3;margin-top:6px}
.ghead,.grow{display:grid;grid-template-columns:136px minmax(240px,1fr) 74px;gap:12px;
  align-items:center}
.ghead{font:600 10px var(--mono);color:var(--ink-3);text-transform:uppercase;letter-spacing:.06em}
.ghead .monthgrid{display:grid;grid-template-columns:repeat(7,1fr);height:16px;border-radius:4px;
  overflow:hidden;background:var(--paper-3)}
.ghead .monthgrid i{border-right:1px solid var(--line);display:grid;place-items:center;
  font-style:normal;color:var(--ink-3);font-size:9.5px}
.grow{padding:4px 0}
.gl{font:11.5px var(--mono);color:var(--ink-2);white-space:nowrap;overflow:hidden;
  text-overflow:ellipsis}
.gl.crit{color:var(--bad);font-weight:600}
.gtrack{position:relative;height:20px;background:linear-gradient(90deg,var(--paper-3),var(--paper-3))
  padding:0;border-radius:4px;
  background-image:repeating-linear-gradient(90deg,#e3e8ef 0 1px,transparent 1px calc(100%/7))}
.gbar{position:absolute;top:3px;height:14px;border-radius:3px;background:#9aa6b6;overflow:hidden;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.45)}
.gbar.crit{background:var(--bad)}
.gprog{display:block;height:100%;background:rgba(255,255,255,.55)}
.gr{font:11px var(--mono);color:var(--ink-2);text-align:right;white-space:nowrap;
  border-left:1px solid var(--line);padding-left:10px}
.ghead .gr{border-left-color:transparent}
/* ---------- kanban */
.kanban{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:10px;
  overflow-x:auto}
.kcol{background:var(--paper-2);border:1px solid var(--line);border-radius:8px;padding:9px;
  display:flex;flex-direction:column;gap:8px;min-width:160px}
.kcol header{display:flex;align-items:center;gap:8px;font:600 11px var(--sans);
  text-transform:uppercase;letter-spacing:.05em;color:var(--ink-2);padding-bottom:6px;
  border-bottom:2px solid var(--line)}
.kcol header em{margin-left:auto;font-style:normal;font-family:var(--mono);font-size:10.5px;
  color:var(--ink-3)}
.kcol.c3 header{border-color:var(--bad)}
.kcol.c4 header{border-color:var(--warn)}
.kcol.c5 header{border-color:var(--ok)}
.kcard{background:var(--paper);border:1px solid var(--line);border-radius:7px;padding:8px 9px;
  display:flex;flex-direction:column;gap:3px;border-left:3px solid var(--ink-3)}
.kcard b{font-size:12px;font-weight:600}
.kcard code{color:var(--ink-3);font-size:10.5px}
.kcard p{font-size:11px;color:var(--ink-3)}
.kcard.ok{border-left-color:var(--ok)}
.kcard.warn{border-left-color:var(--warn)}
.kcard.bad{border-left-color:var(--bad);background:var(--bad-soft)}
.kcard:hover{transform:translateY(-1px);box-shadow:0 4px 10px rgba(20,26,35,.07)}
.kempty{font-size:11px;color:#a4aebc;border:1px dashed var(--line);border-radius:6px;
  padding:14px 8px;text-align:center}
/* ---------- stepper */
.stepper{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.stepper li{display:flex;align-items:center;gap:7px;background:var(--paper-2);border:1px solid
  var(--line);border-radius:999px;padding:5px 11px 5px 6px;font-size:11.5px;color:var(--ink-2)}
.stepper .dot{width:19px;height:19px;border-radius:50%;background:var(--paper-3);display:grid;
  place-items:center;font:600 10.5px var(--mono);color:var(--ink-3)}
.stepper li.done .dot{background:var(--ok);color:#fff}
.stepper li.done{border-color:#c9dfd0;background:var(--ok-soft);color:#2c5c37}
.stepper li.now{border-color:var(--accent);background:var(--accent-soft);color:#245b53;
  font-weight:600}
.stepper li.now .dot{background:var(--accent);color:#fff}
.stepper li + li::before{content:"";width:0}
.stepper li.todo{opacity:.85}
/* ---------- heat */
table.heat{border-collapse:collapse;width:100%;max-width:330px}
table.heat td{border:1px solid var(--line);height:34px;text-align:center;font-family:var(--mono)}
table.heat .hlab{border:0;font:10px var(--mono);color:var(--ink-3);width:22px;text-align:center}
table.heat td.h0{background:#e9efe9}table.heat td.h1{background:#dfe9df}
table.heat td.h2{background:#f0e8cf}table.heat td.h3{background:#ecd9c3}
table.heat td.h4{background:#e7cbc9}
table.heat td i{font-style:normal;font-size:10.5px;background:rgba(255,255,255,.72);
  border-radius:4px;padding:2px 5px;color:var(--ink)}
/* ---------- css tabs */
.tabs{border:1px solid var(--line);border-radius:8px;background:var(--paper-2)}
.tabs > input{position:absolute;opacity:0;pointer-events:none}
.tlab{display:flex;gap:2px;padding:6px 6px 0;flex-wrap:wrap;border-bottom:1px solid var(--line)}
.tlab label{font:600 11.5px var(--mono);padding:7px 12px;border-radius:6px 6px 0 0;color:var(--ink-3);
  background:var(--paper-3);border:1px solid var(--line);border-bottom:0;cursor:pointer}
.tlab label:hover{color:var(--ink);background:#e7ebf1}
.tpanel{display:none;padding:12px}
.tabs > input:nth-of-type(1):checked ~ .tlab label:nth-child(1),
.tabs > input:nth-of-type(2):checked ~ .tlab label:nth-child(2),
.tabs > input:nth-of-type(3):checked ~ .tlab label:nth-child(3),
.tabs > input:nth-of-type(4):checked ~ .tlab label:nth-child(4){background:var(--paper);
  color:var(--ink);border-top:2px solid var(--accent)}
.tabs > input:nth-of-type(1):checked ~ .tbody .tpanel:nth-of-type(1){display:block}
.tabs > input:nth-of-type(2):checked ~ .tbody .tpanel:nth-of-type(2){display:block}
.tabs > input:nth-of-type(3):checked ~ .tbody .tpanel:nth-of-type(3){display:block}
.tabs > input:nth-of-type(4):checked ~ .tbody .tpanel:nth-of-type(4){display:block}
/* ---------- filters / pager */
.filters{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;background:var(--paper);
  border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.filt{display:flex;flex-direction:column;gap:3px;min-width:120px}
.filt i{font-style:normal;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
  color:var(--ink-3)}
.filt .in{width:auto;min-width:110px}
.ck{display:inline-flex;align-items:center;gap:4px;font-size:11.5px;color:var(--ink-2);
  margin-right:7px;white-space:nowrap}
.fright{margin-left:auto;font-size:11.5px;color:var(--ink-3);font-family:var(--mono)}
.pager{display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:space-between}
.pinfo{font:11.5px var(--mono);color:var(--ink-3)}
.pbtns{display:flex;gap:4px}
.pb{min-width:26px;height:26px;display:grid;place-items:center;border:1px solid var(--line);
  border-radius:5px;font:11px var(--mono);background:var(--paper);color:var(--ink-2)}
.pb:hover{border-color:var(--accent);color:var(--accent)}
.pb.cur{background:var(--slate-1);color:#fff;border-color:var(--slate-1)}
/* ---------- states */
.skeleton{border:1px solid var(--line);border-radius:8px;padding:12px;background:var(--paper-2)}
.sk-row{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:8px}
.sk-row i{display:block;height:11px;border-radius:4px;
  background:linear-gradient(90deg,#e9edf2 25%,#f3f5f8 37%,#e9edf2 63%)}
.sk-row.sk-head i{height:13px;background:#e2e7ee}
.skel-demo .sk-row{grid-template-columns:repeat(5,1fr)}
.empty{border:1px dashed #cbd3de;border-radius:8px;padding:18px 14px;text-align:center;
  background:var(--paper-2);display:flex;flex-direction:column;gap:6px;align-items:center}
.eicon{font-size:20px;color:#b7c1cd;line-height:1}
.empty b{font-size:12.5px;color:var(--ink)}
.empty p{font-size:11.5px;color:var(--ink-3);max-width:52ch}
.eact{margin-top:4px;font-size:11.5px;background:var(--accent);color:#fff;padding:5px 11px;
  border-radius:6px}
.banner{border-radius:8px;padding:10px 12px;border:1px solid;background:var(--warn-soft);
  border-color:#ecd9c0}
.banner b{display:block;font-size:12px;margin-bottom:3px;color:#8a5620}
.banner p{font-size:11.5px;color:#7a5b32}
.banner.bad{background:var(--bad-soft);border-color:#e8cccc}
.banner.bad b{color:#8b3a3d}.banner.bad p{color:#7f4749}
.banner.info{background:var(--info-soft);border-color:#cfdcea}
.banner.info b{color:#31506f}.banner.info p{color:#4c5f77}
"""

CSS_E = """
/* ---------- tree / kv / spec */
.tree{border-left:1px solid var(--line);margin-left:6px}
.tree li{display:flex;gap:8px;align-items:baseline;padding:3px 0 3px 14px;position:relative}
.tree li::before{content:"";position:absolute;left:0;top:14px;width:10px;height:1px;
  background:var(--line)}
.tree li.d1{margin-left:8px}.tree li.d2{margin-left:18px}.tree li.d3{margin-left:28px}
.tree .tc{font-size:12.5px;color:var(--ink-2);white-space:nowrap}
.tree .tc b{font:600 11.5px var(--mono);color:var(--ink);background:var(--paper-3);padding:1px 5px;
  border-radius:4px;margin-right:4px}
.tree .tm{font-size:11px;color:var(--ink-3);margin-left:auto;font-family:var(--mono);
  white-space:nowrap}
.tree li.now .tc b{background:var(--accent-soft);color:#245b53}
.tree li.ok .tc b{background:var(--ok-soft);color:#2c5c37}
.tree li.warn .tc b{background:var(--warn-soft);color:#8a5620}
.tree li.bad .tc b{background:var(--bad-soft);color:#8b3a3d}
dl.kv{display:flex;flex-direction:column;gap:7px}
dl.kv > div{display:grid;grid-template-columns:minmax(96px,.85fr) minmax(0,1.6fr);gap:10px;
  border-bottom:1px dashed var(--line);padding-bottom:6px}
dl.kv dt{font:600 11.5px var(--mono);color:var(--ink-2)}
dl.kv dd{font-size:12px;color:var(--ink-3);margin:0}
.spec{margin:16px 0;background:var(--paper);border:1px solid var(--line);border-radius:10px}
.spec summary{cursor:pointer;padding:11px 14px;font-size:12.5px;font-weight:600;color:var(--ink);
  list-style:none;display:flex;align-items:center;gap:8px}
.spec summary::before{content:"+";font-family:var(--mono);color:var(--accent);font-size:14px}
.spec[open] summary::before{content:"−"}
.spec summary:hover{background:var(--paper-2)}
.specgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;
  padding:0 14px 14px;border-top:1px solid var(--line-2)}
.specgrid h4{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--ink-3);
  margin:12px 0 6px}
.specgrid ul{display:flex;flex-direction:column;gap:6px}
.specgrid li{font-size:12px;color:var(--ink-2);padding-left:12px;position:relative}
.specgrid li::before{content:"▪";position:absolute;left:0;color:var(--accent);font-size:9px;
  top:3px}
.specgrid code{background:var(--paper-3);padding:1px 4px;border-radius:3px;color:var(--ink)}
.rules ul li{font-size:12px;color:var(--ink-2)}
/* ---------- prevnext + footer */
.prevnext{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:18px 0 14px}
.prevnext a,.pn-end{display:flex;flex-direction:column;gap:3px;background:var(--paper);
  border:1px solid var(--line);border-radius:9px;padding:10px 13px;font-size:12px;color:var(--ink-3)}
.prevnext a:last-child,.pn-end:last-child{text-align:right;align-items:flex-end}
.prevnext a:hover{border-color:var(--accent);color:var(--accent)}
.prevnext b{font-size:12.5px;color:var(--ink);font-weight:600}
.pn-end{color:#a7b1be;background:var(--paper-2);border-style:dashed}
.pgfoot{background:var(--slate-1);color:#c8d2e0;border-radius:10px;padding:14px 16px;
  display:flex;flex-direction:column;gap:10px}
.prov{font-size:11.5px;color:#9fb0c6;line-height:1.55}
.prov b{color:#e8edf4}
.pf-tabs{display:flex;flex-wrap:wrap;gap:6px}
.ftab{font:11px var(--mono);background:var(--slate-2);border:1px solid var(--slate-3);
  border-radius:5px;padding:4px 8px;color:#c3cede}
.ftab:hover{background:var(--accent);color:#fff}
.pf-fine{display:flex;flex-wrap:wrap;gap:14px;font-size:11px;color:#8b9bb0;
  border-top:1px solid var(--slate-3);padding-top:9px}
.pf-fine a:hover{color:#e8edf4;text-decoration:underline}
/* ---------- drawer (:target, pure CSS) */
.drawer-host{display:flex;flex-direction:column;gap:8px}
.drawer-open{align-self:flex-start;font:11.5px var(--mono);color:var(--accent);
  border:1px solid var(--accent);border-radius:6px;padding:5px 9px;background:var(--accent-soft)}
.drawer{display:none;border:1px solid var(--line);border-radius:8px;background:var(--paper-2);
  padding:10px 12px}
.drawer:target{display:block;box-shadow:0 8px 24px rgba(20,26,35,.10)}
.drawer-host:has(.drawer:target) .drawer-open{display:none}
.drawer header{display:flex;align-items:center;gap:10px;font-size:11.5px;color:var(--ink-2);
  border-bottom:1px solid var(--line);padding-bottom:7px;margin-bottom:9px;font-weight:600}
.drawer-x{margin-left:auto;font-size:11px;color:var(--ink-3);border:1px solid var(--line);
  border-radius:4px;padding:2px 7px}
.drawer-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
.drawer-grid h4{font:600 11px var(--mono);color:var(--accent);margin-bottom:3px}
.drawer-grid p{font-size:11.5px;color:var(--ink-2)}
.colx{background:var(--paper-3);border-radius:3px;padding:1px 4px;color:var(--ink-2)}
/* ---------- chart stand-ins */
.scurve{position:relative;border:1px solid var(--line);border-radius:8px;background:var(--paper-2);
  padding:12px 12px 8px}
.sc-grid{position:absolute;inset:12px 12px 34px;
  background-image:repeating-linear-gradient(0deg,#e6eaf0 0 1px,transparent 1px 25%)}
.sc-svg{display:block;width:100%;height:130px;position:relative}
.sc-key{display:flex;gap:16px;flex-wrap:wrap;font-size:11px;color:var(--ink-3);margin-top:6px}
.sc-key i{display:inline-block;width:14px;height:2px;vertical-align:middle;margin-right:5px}
.sc-key .k-a{background:var(--accent)}.sc-key .k-b{background:#8994a6}
.sc-key .k-c{background:#c0792f}
.sc-read{display:flex;gap:18px;flex-wrap:wrap;margin-top:8px;font-size:11.5px;color:var(--ink-2)}
.sc-read b{font-family:var(--mono);color:var(--ink)}
.draw{border:1px solid var(--line);border-radius:8px;padding:12px;background:var(--paper-2)}
.draw-legend{display:flex;gap:14px;font-size:11px;color:var(--ink-3);margin-bottom:8px;
  flex-wrap:wrap}
.draw-legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.draw-legend .pl{background:#9fb0c6}.draw-legend .dr{background:var(--accent)}
.draw-rows{display:flex;align-items:flex-end;gap:8px;height:130px}
.drow{flex:1 1 0;display:flex;flex-direction:column;justify-content:flex-end;gap:2px;
  align-items:center;height:100%;position:relative}
.drow i{display:block;width:44%;border-radius:2px 2px 0 0}
.drow .pl{background:#c3cfdc;align-self:flex-end}
.drow .dr{background:var(--accent);align-self:flex-end}
.drow em{position:absolute;bottom:-16px;font-style:normal;font:9.5px var(--mono);
  color:var(--ink-3);white-space:nowrap}
.draw{padding-bottom:30px}
.retpot{display:grid;grid-template-columns:auto minmax(0,1fr);gap:18px;align-items:center}
.retpot .ring{width:104px;height:104px;border-radius:50%;display:grid;place-items:center;
  background:conic-gradient(var(--warn) 0 62%, #e3e6eb 62% 100%);position:relative}
.retpot .ring::after{content:"";position:absolute;inset:12px;background:var(--paper);
  border-radius:50%}
.retpot .ring b,.retpot .ring i{position:relative;z-index:1;display:block;text-align:center}
.retpot .ring b{font:600 16px var(--mono)}.retpot .ring i{font:10px var(--sans);color:var(--ink-3);
  font-style:normal}
.retpot ul{font-size:11.5px;color:var(--ink-2);display:flex;flex-direction:column;gap:4px;
  font-family:var(--mono)}
.retpot .stage h5{font-size:11.5px;color:var(--ink-2);margin-bottom:8px}
/* ---------- read-only gallery + mobile */
.ro-demo{display:flex;flex-direction:column;gap:7px}
.ro-row{display:grid;grid-template-columns:200px 110px minmax(0,1fr);gap:10px;align-items:center;
  border:1px solid var(--line);border-radius:7px;padding:8px 10px;background:var(--paper-2);
  font-size:11.5px;color:var(--ink-3)}
.ro-row b{font-family:var(--mono);color:var(--ink);font-variant-numeric:tabular-nums}
.ro-row.lock{border-color:var(--accent);color:var(--accent);font-weight:600}
.ro-row.lock b{color:#3a4658;background:repeating-linear-gradient(135deg,#eef1f5,#eef1f5 5px,
  #e3e8ef 5px,#e3e8ef 10px);padding:2px 6px;border-radius:4px}
.ro-row.hide{opacity:.62;background:repeating-linear-gradient(135deg,#f6f7f9,#f6f7f9 6px,#eef1f5 6px,
  #eef1f5 12px)}
.ro-row .nb{font:11px var(--mono);color:#8b3a3d}
.bundle{display:grid;grid-template-columns:repeat(auto-fit,minmax(126px,1fr));gap:10px}
.bundle figure{margin:0;border:1px solid var(--line);border-radius:8px;overflow:hidden;
  background:var(--paper-2);position:relative}
.bundle img{display:block;width:100%;height:78px;object-fit:cover}
.bundle .shot span,.bundle .plus{display:grid;place-items:center;height:78px;font-size:22px;
  color:#aab4c2;background:var(--paper-3)}
.bundle figcaption{font-size:10.5px;color:var(--ink-3);padding:6px 8px;line-height:1.4}
.bundle .q{position:absolute;top:6px;right:6px;font-style:normal;font:9.5px var(--mono);
  padding:2px 6px;border-radius:999px;background:#fff;border:1px solid var(--line);color:var(--ink-2)}
.bundle .q.ok{background:var(--ok-soft);color:#2c5c37;border-color:#c9dfd0}
.bundle .q.up{background:var(--warn-soft);color:#8a5620;border-color:#ecd9c0}
.bundle .q.queued{background:var(--paper-3)}
.bundle figure.ghost{border-style:dashed}
.mobilesplit{display:grid;grid-template-columns:340px minmax(0,1fr);gap:16px;align-items:start;
  margin-bottom:14px}
.phone{background:var(--slate-0);border-radius:22px;padding:10px;box-shadow:0 10px 26px
  rgba(20,26,35,.18)}
.pbar{display:flex;align-items:center;gap:9px;color:#c8d2e0;font:10.5px var(--mono);
  padding:2px 6px 8px}
.pdot{width:8px;height:8px;border-radius:50%;background:var(--bad);display:inline-block}
.pbatt{flex:1 1 auto;height:8px;border:1px solid var(--slate-3);border-radius:3px;
  position:relative;max-width:56px}
.pbatt i{display:block;height:100%;width:41%;background:var(--warn)}
.phone .reg{border-radius:12px}
.phome{height:16px}
.mobnote{font-size:11px;color:var(--ink-3);margin-top:8px}
.mside{display:flex;flex-direction:column;gap:14px}
/* ---------- sdg matrix */
.sdg-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(84px,1fr));gap:6px}
.sdg-goal{border-radius:6px;padding:8px;color:#fff;min-height:62px;display:flex;
  flex-direction:column;gap:2px;font-size:10px;line-height:1.25}
.sdg-goal b{font:600 13px var(--mono)}
.sdg-goal.on{background:#2f7a4c}
.sdg-goal.part{background:#c0792f}
.sdg-goal.off{background:#c9d0da;color:#4d5766}
"""

def css():
    return CSS_A + CSS_B + CSS_C + CSS_D + CSS_E + CSS_F


PLACEHOLDER_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 134" role="img">'
                   '<rect width="240" height="134" fill="#dfe5ec"/>'
                   '<path d="M0 104 L58 62 L96 92 L140 44 L190 96 L240 58 L240 134 L0 134Z" '
                   'fill="#c3ccd9"/>'
                   '<circle cx="196" cy="30" r="13" fill="#e7e0c9"/>'
                   '<rect x="14" y="112" width="88" height="4" rx="2" fill="#a9b4c4"/>'
                   '<rect x="108" y="112" width="46" height="4" rx="2" fill="#bdc7d5"/></svg>')


# ---------------------------------------------------------------- write + verify
def write_all():
    os.makedirs(PAGES, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    written = []
    for i, f in enumerate(FRAMES):
        c = CFG[f["id"]]
        body = BUILDERS[f["id"]](f, c)
        path = os.path.join(PAGES, f["file"])
        open(path, "w", encoding="utf-8").write(page(i, f, body, c["sub"]))
        written.append(path)
    idx = os.path.join(SITE, "index.html")
    open(idx, "w", encoding="utf-8").write(hub())
    written.append(idx)
    open(os.path.join(ASSETS, "site.css"), "w", encoding="utf-8").write(css())
    open(os.path.join(ASSETS, "print.css"), "w", encoding="utf-8").write(PRINT_CSS)
    open(os.path.join(ASSETS, "placeholder-photo.svg"), "w", encoding="utf-8").write(PLACEHOLDER_SVG)
    return written


def check_files(paths):
    """Static assertions over the emitted files: no JS, every link resolves, every
    field name belongs to the page's source tables."""
    from bs4 import BeautifulSoup
    broken, checked, ids_seen = [], 0, 0
    js_hits, unknown_cols, unknown_tbl = [], [], []
    for p in paths + [os.path.join(ASSETS, "site.css"), os.path.join(ASSETS, "print.css")]:
        raw = open(p, encoding="utf-8").read()
        if p.endswith(".html"):
            for pat in (r"<script", r"\son[a-z]+\s*=", r"javascript:"):
                if re.search(pat, raw, re.I):
                    js_hits.append((os.path.basename(p), pat))
            soup = BeautifulSoup(raw, "html.parser")
            base = os.path.dirname(p)
            frame = None
            if "/pages/" in p.replace(os.sep, "/"):
                frame = BY_ID[os.path.basename(p)[:2]]
            allowed = set()
            if frame:
                for t in frame["srcs"]:
                    allowed |= set(COLS[t])
                    allowed.add(t)
            for a in soup.find_all(["a", "link", "img"]):
                href = a.get("href") or a.get("src")
                if not href or href.startswith(("http://", "https://", "mailto:")):
                    continue
                checked += 1
                if href.startswith("#"):
                    ids_seen += 1
                    target = href[1:]
                    if target and not soup.find(id=target):
                        broken.append((os.path.basename(p), href, "missing anchor id"))
                    continue
                tgt_path = os.path.normpath(os.path.join(base, href.split("#")[0]))
                if not os.path.isfile(tgt_path):
                    broken.append((os.path.basename(p), href, "no such file"))
            if frame:
                src_ok = frame["srctok"]
                for th in soup.select("th.col"):
                    nm, tb = th.get("data-c"), th.get("data-t")
                    if nm not in allowed or tb not in [x for x in frame["srcs"]]:
                        unknown_cols.append((frame["id"], th.get_text(strip=True)))
                for el in soup.select("[data-c]"):
                    nm, tb = el.get("data-c"), el.get("data-t")
                    if tb not in TABLES or nm not in COLS.get(tb, {}):
                        unknown_cols.append((frame["id"], "%s.%s (not in schema)" % (tb, nm)))
                    elif tb not in frame["srcs"] and nm not in src_ok:
                        unknown_cols.append((frame["id"], "%s.%s (not this frame's table)" % (tb, nm)))
                for code in soup.select("code.colx"):
                    nm = code.get_text(strip=True)
                    if nm not in allowed and nm not in src_ok:
                        unknown_cols.append((frame["id"], nm + " (illustrative)"))
                for t in frame["srcs"]:
                    if t not in TABLES:
                        unknown_tbl.append((frame["id"], t))
                for tok in set(re.findall(r"\b[a-z][a-z0-9]*_[a-z0-9_]*\b", soup.get_text(" "))):
                    if tok in ALL_COL_NAMES and tok not in allowed and tok not in src_ok:
                        unknown_cols.append((frame["id"], tok + " (prose)"))
    return broken, checked, ids_seen, js_hits, unknown_cols, unknown_tbl


ALL_COL_NAMES = set()
for _t in SCHEMA["tables"]:
    for _c in _t["cols"]:
        ALL_COL_NAMES.add(_c["n"])


def check_annotations():
    """Re-read the emitted pages: every annotation number the frame declared must appear,
    and no annotation number the frame did not declare may survive clamping."""
    from bs4 import BeautifulSoup
    missing, invented = [], []
    for f in FRAMES:
        soup = BeautifulSoup(open(os.path.join(PAGES, f["file"]), encoding="utf-8").read(),
                             "html.parser")
        got = sorted({int(x.get_text(strip=True)) for x in soup.select(".an")
                      if x.get_text(strip=True).isdigit()})
        for n in f["anns"]:
            if n not in got:
                missing.append((f["id"], n))
        for n in got:
            if n not in f["anns"]:
                invented.append((f["id"], n))
    return missing, invented


def main():
    paths = write_all()
    print("frames parsed from wireframes.html: %d" % len(FRAMES))
    print("html files written: %d pages + hub = %d" % (len(FRAMES) - 0, len(FRAMES) + 1))
    broken, checked, ids_seen, js_hits, unknown_cols, unknown_tbl = check_files(paths)
    print("links checked: %d (incl. %d same-file anchors) | broken: %d"
          % (checked, ids_seen, len(broken)))
    for b in broken[:25]:
        print("   BROKEN", b)
    print("js constructs found: %d %s" % (len(js_hits), js_hits[:5]))
    print("unknown column identifiers: %d" % len(unknown_cols))
    for u in unknown_cols[:25]:
        print("   UNKNOWN", u)
    print("unknown source tables: %d %s" % (len(unknown_tbl), unknown_tbl[:5]))
    missing, invented = check_annotations()
    print("annotation numbers declared by the frames: %d | not rendered: %d %s | invented: %d %s"
          % (sum(len(f["anns"]) for f in FRAMES), len(missing), missing[:12], len(invented),
             invented[:6]))
    total = sum(os.path.getsize(p) for p in paths)
    print("bytes of html emitted: %d" % total)
    return 0 if (not broken and not js_hits and not unknown_cols and not unknown_tbl) else 1





CSS_F = """
/* ---------- hub */
.hub .topbar{position:sticky}
.hubwrap{max-width:1580px;margin:0 auto;padding:24px 20px 60px}
.hubmain{min-width:0}
.hubhead{background:var(--slate-1);color:#e9edf3;border-radius:12px;padding:22px 24px;
  margin-bottom:16px}
.kicker{display:inline-block;font:11px var(--mono);letter-spacing:.02em;color:#9fb6c9;
  border:1px solid var(--slate-3);border-radius:999px;padding:4px 11px;background:var(--slate-0)}
.hubhead h1{font-size:28px;margin:12px 0 0;display:flex;gap:12px;align-items:baseline;
  flex-wrap:wrap;color:#fff}
.h1sub{font-size:13px;font-weight:400;color:#9fb0c6}
.hublede{margin-top:9px;font-size:13.5px;color:#c2cddc;max-width:88ch;line-height:1.6}
.hublede code,.provn code,.specgrid code{font:11.5px var(--mono);background:rgba(255,255,255,.08);
  padding:1px 5px;border-radius:4px}
.hubmeta{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.hubmeta span{font:11px var(--mono);background:var(--slate-2);border:1px solid var(--slate-3);
  border-radius:6px;padding:5px 10px;color:#cbd6e4}
.hub .kpi-strip{background:var(--paper);border:1px solid var(--line);border-radius:10px;
  padding:14px;margin:14px 0}
.hub .kpi{background:var(--paper-2)}
.hub .chips{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:14px;
  margin-bottom:26px}
.hgroup{margin-bottom:26px}
.hgroup > header{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;
  border-bottom:1px solid var(--line);padding-bottom:8px;margin-bottom:12px}
.hgroup h2{font-size:16px;display:flex;align-items:center;gap:9px}
.hgroup h2 em{font:11px var(--mono);font-style:normal;color:var(--ink-3)}
.hgsrcrews{font-size:11px;color:var(--ink-3);font-family:var(--mono);margin-left:auto;
  line-height:1.9}
.tblref code{color:var(--info);border-bottom:1px dotted rgba(65,98,143,.4)}
.tblref:hover code{background:var(--info-soft);color:#2b4a75}
.hcards{display:grid;grid-template-columns:repeat(auto-fill,minmax(268px,1fr));gap:12px}
.hcard{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:13px 14px;
  display:flex;flex-direction:column;gap:7px;transition:box-shadow .12s,border-color .12s}
.hcard:hover{border-color:var(--accent);box-shadow:0 6px 18px rgba(20,26,35,.08)}
.hlink{display:flex;gap:9px;align-items:baseline}
.hlink:hover h3{color:var(--accent)}
.hcard h3{font-size:13.5px}
.hnum{font:600 11px var(--mono);background:var(--slate-1);color:#fff;border-radius:5px;
  padding:2px 6px}
.hcard p{font-size:11.5px;color:var(--ink-3)}
.hsrcs{display:flex;flex-wrap:wrap;gap:4px;margin-top:auto}
.hsrcs li{font:10.5px var(--mono);background:var(--paper-3);border:1px solid var(--line);
  border-radius:4px;padding:2px 5px;color:var(--ink-2)}
.provn{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:18px;
  margin:30px 0}
.provn h2{font-size:16px;margin-bottom:12px}
.provn-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.provn h3{font-size:12px;color:var(--accent);margin-bottom:6px}
.provn p{font-size:12px;color:var(--ink-2);line-height:1.6}
.sitemap{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:18px}
.sitemap h2{font-size:16px;margin-bottom:12px}
.sitemap table.grid{min-width:640px}
.main > *,.hubmain > *,.mainsplit > *,.side > *,.rg-2 > *,.rg-3 > *,.rg-21 > *,.rg-12 > *{min-width:0}
.sitemap td a{color:var(--accent)}
.sitemap td a:hover{text-decoration:underline}
/* ---------- responsive */
@media (max-width:1100px){
  .wrap{grid-template-columns:214px minmax(0,1fr);gap:16px}
  .mainsplit{grid-template-columns:minmax(0,1fr)}
  .side{position:static;flex-direction:row;flex-wrap:wrap}
  .side > .reg{flex:1 1 260px}
  .rg-3{grid-template-columns:repeat(2,minmax(0,1fr))}
  .rg-21,.rg-12{grid-template-columns:minmax(0,1fr)}
  .fields.f3{grid-template-columns:repeat(2,minmax(0,1fr))}
  .mobilesplit{grid-template-columns:minmax(0,1fr)}
  .phone{max-width:360px}
  .tb-r .qsearch{display:none}
}
@media (max-width:640px){
  .topbar{height:52px;flex-direction:row;align-items:center;gap:10px;padding:0 12px;
    overflow-x:auto}
  .tb-l{flex-wrap:nowrap;gap:9px;flex:0 0 auto}
  .tb-r{flex:0 0 auto;gap:9px}
  .scope span,.phasecur,.role,.asof{display:none}
  .qsearch{max-width:172px;font-size:11px;padding:4px 9px}
  .wrap{display:block;padding:14px 12px 40px}
  .rail{position:static;max-height:none;margin-bottom:12px;padding:8px 9px;display:flex;
    align-items:center;gap:10px;overflow-x:auto;white-space:nowrap}
  .rail-top{display:flex;flex-direction:column;gap:1px;border:0;padding:0;margin:0;flex:0 0 auto}
  .railproj{margin-top:2px;font-size:10.5px}
  .rgrp{display:flex;align-items:center;gap:6px;margin:0;flex:0 0 auto}
  .rgrp ul{display:none !important}
  .rgrp.open ul{display:flex !important;gap:4px;border-left:0;margin:0;flex-wrap:nowrap}
  .rgrp.open li{flex:0 0 auto}
  .rgl{padding:0;white-space:nowrap}
  .rgrp.open li a{border-left:0;border:1px solid var(--line);border-radius:999px;padding:4px 9px;
    max-width:100%}
  .rgrp li a span{white-space:nowrap}
  .rgrp.open li a.on{border-color:var(--accent)}
  .rail-top{display:flex;justify-content:space-between;align-items:center;gap:8px}
  .rail-foot{display:none}
  .rg-2,.rg-3,.rg-21,.rg-12{grid-template-columns:minmax(0,1fr)}
  .fields.f2,.fields.f3{grid-template-columns:minmax(0,1fr)}
  .kpi-strip{grid-template-columns:repeat(2,minmax(0,1fr))}
  .hubhead{padding:16px}.hubhead h1{font-size:22px}
  .hcards{grid-template-columns:minmax(0,1fr)}
  .hgsrcrews{margin-left:0}
  .prevnext{grid-template-columns:minmax(0,1fr)}
  .main{display:flex;flex-direction:column}
  .main > .crumbs,.main > h1,.main > .sub,.main > .lede{order:1}
  .main > div:not(.srcs-strip):not(.prevnext):not(.mobilesplit){order:2}
  .main > .mobilesplit{order:2}
  .main > .srcs-strip{order:3}
  .main > details.spec{order:4}
  .main > .prevnext{order:5}
  .main > .pgfoot{order:6}
  .srcs-strip{flex-wrap:nowrap;overflow-x:auto;padding:8px;gap:7px}
  .ssl::after{content:" \2194  scroll";color:var(--accent)}
  .src-card{flex:0 0 auto;min-width:160px;padding:5px 8px}
  h1{font-size:19px;gap:8px}
  .sub{font-size:12.5px}
  .crumbs{font-size:11px;margin-bottom:7px}
  .lede{font-size:12.5px;padding:9px 11px;margin-top:8px}
  .reg{padding:12px 12px 13px}
  .ro-row{grid-template-columns:minmax(0,1fr);gap:4px}
  .retpot{grid-template-columns:minmax(0,1fr)}
  .filters{gap:8px}.fright{margin-left:0;width:100%}
  .ghead,.grow{grid-template-columns:96px minmax(170px,1fr) 56px}
  table.grid{font-size:11.5px}
  .tree li{flex-wrap:wrap}
  .tree .tm{margin-left:0;flex:1 1 100%;white-space:normal;overflow-wrap:anywhere}
  .kpi-strip{gap:8px}
}
"""

PRINT_CSS = """
/* print.css - the demo is meant to be printed as a frame pack */
@page{size:A4 landscape;margin:12mm}
body{background:#fff}
.topbar,.rail,.prevnext,.srcs-strip,.filters,.pager{display:none !important}
.wrap,.hubwrap{display:block;padding:0;max-width:none}
.reg{break-inside:avoid;page-break-inside:avoid;border:1px solid #ccd2da}
.rg-2,.rg-3,.rg-21,.rg-12,.mainsplit{display:block}
.side{position:static}
h1{font-size:17pt}
a{color:#000}
.tw{overflow:visible}
table.grid{min-width:0;font-size:9pt}
"""



if __name__ == "__main__":
    raise SystemExit(main())















