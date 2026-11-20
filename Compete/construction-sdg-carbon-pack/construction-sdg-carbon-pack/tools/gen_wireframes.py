"""Generate wireframes.html: detailed screen frames derived from the parsed ERD schema."""
# ---- pack path shim: all paths resolve relative to this pack ----
import os
import pathlib as _pathlib
ROOT = _pathlib.Path(__file__).resolve().parents[1]
TMP = ROOT / "work"
TMP.mkdir(parents=True, exist_ok=True)
# -------------------------------------------------------------------
import json, html as H, re

S = json.load(open(os.fspath(TMP / "schema.json")))
T = {t["name"]: t for t in S["tables"]}
PHASE = {"core": "Core spine", "d12": "D12 Design & Funding", "p34": "P34 Procurement & Planning",
         "p5": "P5 Construction", "p67": "P67 Handover & Operations",
         "sdg": "SDG layer", "cc": "Carbon credit layer"}
OUTP = os.fspath(ROOT) + "/output/wireframes.html"

CSS = """
:root{--ink:#1a1d21;--mut:#6b7280;--line:#c2c8d0;--bg:#f4f5f7;--pan:#fff;--dash:#9aa3ad;--acc:#2f5d8a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.5 ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace}
header.top{padding:26px 32px;background:var(--pan);border-bottom:3px solid var(--ink)}
h1{margin:0 0 6px;font-size:24px;letter-spacing:-.4px}h2{margin:34px 32px 4px;font-size:17px}
.sub{color:var(--mut);font-size:12.5px;max-width:74ch}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin:14px 32px 0}
.legend span{border:1px solid var(--line);background:var(--pan);padding:3px 9px;font-size:11.5px;border-radius:12px}
.frame{margin:26px 32px;background:var(--pan);border:1.5px solid var(--ink);border-radius:6px;overflow:hidden;
page-break-inside:avoid;box-shadow:3px 3px 0 rgba(26,29,33,.09)}
.fh{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;padding:10px 14px;
border-bottom:1.5px solid var(--ink);background:#eceef1}
.fid{font-weight:700;background:var(--ink);color:#fff;padding:2px 8px;border-radius:4px;font-size:12px}
.ft{font-weight:700;font-size:15.5px}.fp{font-size:11px;color:var(--mut);border:1px dashed var(--dash);padding:1px 7px;border-radius:9px}
.fb{padding:14px;display:grid;gap:12px}
.row{display:grid;gap:12px}.c2{grid-template-columns:1fr 1fr}.c3{grid-template-columns:1fr 1fr 1fr}
.c21{grid-template-columns:2fr 1fr}.c12{grid-template-columns:1fr 2fr}
.reg{border:1.4px dashed var(--dash);border-radius:5px;padding:10px;background:var(--pan);min-height:64px;position:relative}
.rl{font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:-4px 0 8px;font-weight:700}
.an{position:absolute;top:-9px;right:-9px;width:20px;height:20px;border-radius:50%;background:var(--acc);
color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;border:1.5px solid var(--pan)}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.chip{border:1px solid var(--line);border-radius:4px;padding:2px 6px;font-size:11px;background:#fafbfc;white-space:nowrap}
.chip.pk{border-color:#a9791c;background:#fdf4e3;font-weight:700}
.chip.fk{border-color:#2b7a72;background:#e8f6f4}
.chip.fk::after{content:"\\2192 "\\2009 attr}
.fld{border:1px solid var(--line);border-radius:4px;padding:5px 7px;font-size:11.5px;background:#fff}
.flds{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:6px}
.fld b{display:block;font-size:10px;color:var(--mut);font-weight:700;letter-spacing:.04em;text-transform:uppercase}
.fld i{font-style:normal;color:#9aa3ad;font-size:10px}
table.w{width:100%;border-collapse:collapse;font-size:11px}
table.w th{background:#eceef1;border:1px solid var(--line);padding:5px;text-align:left;font-weight:700;white-space:nowrap}
table.w td{border:1px solid var(--line);padding:5px;color:#767e88;background:#fff}
.bar,.ph{border:1px solid var(--dash);border-radius:3px;background:repeating-linear-gradient(45deg,#f2f3f5,#f2f3f5 6px,#e9ebee 6px,#e9ebee 12px)}
.kpi{border:1px solid var(--line);border-radius:4px;padding:7px;text-align:center;background:#fafbfc}
.kpi b{display:block;font-size:15px}.kpi span{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));gap:8px}
.note{font-size:11.5px;color:#43484f}
.spec{border-top:1.4px dashed var(--dash);margin-top:12px;padding-top:10px;display:grid;
grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;font-size:11.5px}
.spec h4{margin:0 0 3px;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--mut)}
.spec ul{margin:0;padding-left:16px}.spec li{margin:1px 0}
.srcs{display:flex;flex-wrap:wrap;gap:5px}
.src{font-size:10.5px;border:1px solid var(--ink);border-radius:3px;padding:1px 6px;background:#fff}
.src em{font-style:normal;color:var(--mut)}
.cols{display:grid;grid-template-columns:repeat(auto-fill,minmax(88px,1fr));gap:6px}
.kan{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}
.kan>div{border:1px solid var(--line);border-radius:4px;padding:6px;background:#fafbfc;font-size:10.5px}
.heat{display:grid;grid-template-columns:repeat(5,1fr);gap:4px}
.heat i{display:block;height:22px;border-radius:3px;border:1px solid var(--line)}
.gantt{display:grid;gap:3px}.gantt>div{display:grid;grid-template-columns:74px 1fr;gap:6px;align-items:center;font-size:10px}
.gantt b{font-weight:400;color:var(--mut);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gantt .bar{height:14px}
.tree{font-size:11px;line-height:1.75;color:var(--mut)}
.tree u{text-decoration:none;color:var(--ink)}
.m{color:#93a1b1;font-style:normal}
footer{margin:30px 32px;padding-top:12px;border-top:2px solid var(--ink);font-size:11.5px;color:var(--mut)}
code{background:#eceef1;padding:1px 4px;border-radius:3px;font-size:11px}
.idx{margin:10px 32px;border:1px solid var(--line);background:var(--pan);border-radius:6px;overflow:auto}
.idx td{border-top:1px solid var(--line);padding:5px 8px;font-size:11.5px;vertical-align:top}
.idx td:first-child{width:64px;font-weight:700}
@media (max-width:640px){
 .frame,h2,.idx,.legend,footer{margin-left:10px;margin-right:10px}
 header.top{padding:18px 14px}
 .row{grid-template-columns:1fr !important;min-width:0}
 .reg,.kpi,.kan>div{min-width:0;overflow-wrap:anywhere}
 table.w{display:block;overflow-x:auto}
 table.w th{white-space:normal}
 .flds{grid-template-columns:repeat(auto-fill,minmax(130px,1fr))}
 .idx{display:block;overflow-x:auto}
 .idx td{max-width:46vw;overflow-wrap:anywhere}
 .tree,.kan,.gantt{overflow-x:auto}
 .kan{grid-auto-flow:column;grid-template-columns:none;grid-auto-columns:46%}
}
"""


def cols_of(tbl, only=None):
    t = T[tbl]
    return [c for c in t["cols"] if (only is None or c["n"] in only)]


def chips(tbl, only=None, exclude=None):
    """Field chips rendered straight from the schema (PK amber, FK teal + arrow target)."""
    out = []
    for c in cols_of(tbl, only):
        if exclude and c["n"] in exclude:
            continue
        cls = "pk" if c["pk"] else ("fk" if c["fk"] else "")
        lbl = f"{c['n']}" + (f"&#8594;{c['fk']}" if c["fk"] else "")
        out.append(f'<span class="chip {cls}" title="{H.escape(c["ty"])}">{lbl}</span>')
    return f'<div class="chips">{"".join(out)}</div>'


def fields(tbl, only=None, exclude=None):
    out = []
    for c in cols_of(tbl, only):
        tag = "PK" if c["pk"] else ("FK" if c["fk"] else "")
        hint = c["fk"] or ("&#9633; type " + c["ty"])
        out.append(f'<div class="fld"><b>{c["n"]}{" &#183; " + tag if tag else ""}</b>'
                   f'<i>{hint.replace("<", "&lt;")}</i></div>')
    return f'<div class="flds">{"".join(out)}</div>'


def reg(label, inner, an=None):
    a = f'<span class="an">{an}</span>' if an else ""
    rl = f'<div class="rl">{label}</div>' if label else ""
    return f'<div class="reg">{a}{rl}{inner}</div>'


def srcs(tables):
    return ('<div class="srcs">' + "".join(
        f'<span class="src">{t}<em> &middot; {len(T[t]["cols"])} cols &middot; '
        f'{sum(1 for c in T[t]["cols"] if c["fk"])} FK</em></span>' for t in tables) + "</div>")


def frame(fid, title, phase, purpose, regions, tables, actions, rules, roles, states, annot=None):
    prd = PHASE[phase]
    body = "".join(f'<div class="row {cls}">{"".join(items)}</div>' for cls, items in regions)
    sp = ('<div class="spec">'
          + f'<div><h4>Data sources (tables &rarr; this frame)</h4>{srcs(tables)}</div>'
          + f'<div><h4>Primary actions</h4><ul>{"".join(f"<li>{a}</li>" for a in actions)}</ul></div>'
          + f'<div><h4>Validation &amp; business rules</h4><ul>{"".join(f"<li>{r}</li>" for r in rules)}</ul></div>'
          + f'<div><h4>Roles / states</h4><ul><li>{roles}</li><li>{states}</li></ul></div>'
          + "</div>")
    notes = ""
    if annot:
        notes = ('<div class="reg" style="border-style:solid;border-color:var(--line)">'
                 '<div class="rl">Annotations</div><ol class="note" style="margin:0;padding-left:18px">'
                 + "".join(f"<li>{a}</li>" for a in annot) + "</ol></div>")
    return (f'<section class="frame"><div class="fh"><span class="fid">{fid}</span>'
            f'<span class="ft">{title}</span><span class="fp">{prd}</span></div>'
            f'<div class="fb"><div class="note">{purpose}</div>{body}{sp}{notes}</div></section>')

COV, FR = [], []       # COV: tables referenced; FR: rendered frame html
META = []              # (fid, title, phase, tables) for the page index
def use(*t):
    COV.extend(t)


def F(fid, title, phase, purpose, regions, tables, actions, rules, roles, states, annot=None):
    FR.append(frame(fid, title, phase, purpose, regions, tables, actions, rules, roles, states, annot))
    META.append((fid, title, phase, tables))
    return fid


g = lambda *items: ("", items)
g2 = lambda *items: ("c2", items)
g3 = lambda *items: ("c3", items)
g21 = lambda *items: ("c21", items)
g12 = lambda *items: ("c12", items)
KPIS = lambda *p: '<div class="kpis">' + "".join(
    f'<div class="kpi"><b>{v}</b><span>{k}</span></div>' for k, v in p) + "</div>"
PH_ = lambda h, n: '<div class="ph" style="height:%s"></div>' % (h,) if n is None else \
    '<div class="ph" style="height:%s"><span class="m"> %s</span></div>' % (h, n)
TB = lambda heads, rows: ('<table class="w"><tr>' + "".join(f"<th>{h}</th>" for h in heads) + "</tr>"
    + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) + "</table>")
STEP = lambda *s: '<div class="chips">' + "".join(
    f'<span class="chip{" pk" if i == len(s) - 1 else ""}">{i + 1}. {x}</span>' for i, x in enumerate(s)) + "</div>"


# ---------------------------------------------------------------- 01 shell
F(FID1 := "01", "Application shell &amp; global navigation", "core",
  "Persistent chrome for every screen: project scope switcher, phase rail (the seven groups in the ERD), "
  "global search, role badge. The phase rail is the notebook&#8217;s IA, mapped 1:1 to <code>phase</code> values.",
  [g21(reg("Left rail &#183; phase navigation (7 groups / 45 tables)",
           '<div class="tree">' + "".join(
               f'<u>{PHASE[p]}</u> <span class="m">{S["phases"][p]} tables</span><br>'
               for p in ["core", "d12", "p34", "p5", "p67", "sdg", "cc"]) + "</div>", "1"),
        reg("Top bar &#183; scope, phase, role, data currency",
            KPIS(("Project", "NBO-221 Riverside"), ("Phase", "P5 Construction"),
                 ("Role", "GC Project Manager"), ("Data as of", "2026-11-20")))),
   g(reg("Global search &#183; table, WBS code, serial number, registry ref",
         PH_("30px", "query &#8220;rfi 418&#8221; &#9656; 23 hits across 7 tables &#8212; grouped by phase")))],
  ["project", "stakeholder"],
  ["switch project scope", "jump to any phase group", "global record search", "toggle read-only audit view"],
  ["Scope switcher must re-key every child query by <code>project_id</code>; no cross-project bleed.",
   "Phase rail entries are navigation only &#8212; they carry no write affordances."],
  "Owner &#183; Architect &#183; GC &#183; Subcontractor &#183; Verifier (VVB) &#183; Registry auditor",
  "default &#183; project-unselected &#183; session-expired"), use("project", "stakeholder")

# ---------------------------------------------------------------- 02 portfolio
F("02", "Portfolio &#8212; project register", "core",
  f"List view over <code>project</code> ({len(T['project']['cols'])} columns). This is the root of every other frame: "
  "all downstream tables resolve through <code>project_id</code>.",
  [g(reg("KPI strip &#183; aggregated from project + child tables",
         KPIS(("Active projects", "18"), ("Sum approved budget", "$1.24bn"), ("GFA", "2.1M m&#178;"),
              ("At risk (critical path slip)", "4"), ("Credits retired YTD", "312,400 tCO&#8322;e"))), "1"),
    g21(reg("Project table &#8212; every column from <code>project</code>",
             TB([c["n"] for c in T["project"]["cols"]],
                [["&#8226;", "NBO Riverside", "$420m", "$401m", "118,000", "2025-02", "2027-09", "P5", "&#8212;"],
                 ["&#8226;", "SDG Hub North", "$132m", "$129m", "41,500", "2024-11", "2026-12", "P67", "2026-10-02"]]),
             "2"),
     reg("Row detail drawer (opens on click)",
         PH_("150px", "nested: site &#183; wbs &#183; stakeholder &#183; carbon_project")))],
  ["project"],
  ["create project", "duplicate baseline", "export register", "drill into workspace (frame 03)"],
  ["<code>approved_budget</code> may not exceed <code>rom_budget</code> by &gt; 15% without a logged change_order.",
   "<code>current_phase</code> is derived from child records, never typed free-form.",
   "<code>certificate_of_occupancy_date</code> gated by municipal_inspection result (frame 18)."],
  "Owner + GC see all rows; subcontractors see only packages they were awarded.",
  "empty &#183; filtered-no-results &#183; loading skeleton"), use("project")

# ---------------------------------------------------------------- 03 workspace
F("03", "Project workspace hub", "core",
  "Single-project landing page: the phase stepper, budget/schedule/SDG/carbon summary tiles, and the tab set that "
  "opens every other frame in this pack.",
  [g(reg("Phase stepper &#183; project.current_phase",
         STEP(*[PHASE[p] for p in ["core", "d12", "p34", "p5", "p67", "sdg", "cc"]]), "1")),
   g3(reg("Budget tile &#8212; project + financial_metric",
          KPIS(("ROM", "$420m"), ("Approved", "$401m"), ("Committed", "$377m"), (" forecast", "$409m"))),
      reg("Schedule tile &#8212; schedule_activity",
          KPIS(("Planned end", "2027-09"), ("Forecast", "2027-11"), ("Float (critical)", "-6 d"), ("SPI", "0.94"))),
      reg("SDG + carbon tile &#8212; project_sdg_target / issuance",
          KPIS(("SDG targets met", "9/14"), ("Credits issued", "48,200 t"), ("Retired", "12,500 t")))),
   g2(reg("Recent records needing action (cross-table inbox)",
          TB(["type", "ref", "subject", "SLA", "state"],
             [["RFI", "rfi_id 418", "Curtain wall anchor detail", "due in 2d", "open"],
              ["Submittal", "submittal_id 91", "HVAC air handler", "over 1d", "awaiting review"],
              ["NCR", "ncr_id 12", "Concrete core break &lt; f&#8242;c", "blocker", "unresolved"],
              ["Defect", "defect_id 7", "Retention release gate", "sla_deadline +12d", "open"]]),
          "2"),
      reg("WBS roll-up (wbs &#8594; boq_item &#8594; cost)",
          '<div class="tree"><u>E</u> Substructure<br>&nbsp;&nbsp;<u>E1</u> Foundations<br>&nbsp;&nbsp;&nbsp;&nbsp;<u>E10</u> Piling '
          '<span class="m">$4.1m</span><br>&nbsp;&nbsp;<u>E2</u> Basal slab<br><u>F</u> Superstructure<br>'
          '&nbsp;&nbsp;<u>F3</u> Frame <span class="m">$38.6m</span></div>', "3"))],
  ["project", "site", "wbs", "financial_metric", "schedule_activity", "project_sdg_target", "rfi", "submittal", "ncr", "defect"],
  ["open any phase tab", "act on inbox item", "export project fact sheet"],
  ["Tiles are read-through aggregations; the source of truth stays in the child tables listed in the spec."],
  "All roles; write access limited to the phase owner", "loading &#183; partial aggregation failure &#183; archived project"), use(
     "site", "wbs", "financial_metric", "schedule_activity", "project_sdg_target", "rfi", "submittal", "ncr", "defect")

# ---------------------------------------------------------------- 04 core spine
F("04", "Core spine &#8212; WBS, spatial zones, site", "core",
  "Browses the three spines the cost, location and scope data hang off. <code>wbs</code> is self-referencing "
  "(<code>parent_wbs_id &#8594; wbs</code>) so it renders as a tree, not a grid.",
  [g21(reg("WBS tree (self-FK parent_wbs_id)",
           '<div class="tree"><u>E</u> Substructure <span class="m">wbs_code</span><br>'
           '&nbsp;&#9492;<u>E1</u> Foundations<br>&nbsp;&nbsp;&#9492;<u>E10</u> Piling<br>'
           '&nbsp;&#9492;<u>E2</u> Basal slab<br><u>F</u> Superstructure&#8230;</div><br>' + chips("wbs"), "1"),
       reg("Selected node &#8212; editable fields", fields("wbs"))),
   g2(reg("Spatial zones &amp; rooms &#8212; location spine",
          TB([c["n"] for c in cols_of("spatial_zone_room")],
             [["&#8226;", "Z1", "Level 3", "R3-118", "Office", "42.6", "BREEAM Very Good", ""]])
          + "<br>" + chips("spatial_zone_room"), "2"),
      reg("Site &amp; environmental status", fields("site"), "3"))],
  ["wbs", "spatial_zone_room", "site"],
  ["re-parent WBS node (cycles rejected)", "bulk import Uniclass 2015 codes", "set room rating"],
  ["Re-parenting must be rejected if it creates a cycle through <code>parent_wbs_id</code>.",
   "<code>far</code> vs planning envelope validated against <code>zoning_code</code>.",
   "<code>eia_status</code> gates the carbon_project baseline dates (frame 22)."],
  "Architect edits WBS; GC read-only; environmental consultant edits eia_status",
  "tree &gt; 500 nodes (virtualise) &#183; orphan node &#183; unsaved-changes guard"), use("wbs", "spatial_zone_room", "site")

# ---------------------------------------------------------------- 05 stakeholders
F("05", "Stakeholder register &amp; access matrix", "core",
  "The actor spine referenced by 84 foreign keys across the schema; the frame shows who is modelled and which downstream "
  "tables point back at them.",
  [g2(reg("Register", TB([c["n"] for c in cols_of("stakeholder")],
              [["&#8226;", "SH-004", "Meridian GC", "General Contractor", "GC-88", "PM", "active"]])),
      reg("Incoming references (who depends on this row)",
          '<div class="chips">' + "".join(
              f'<span class="chip fk">{t}&#8594;{c["n"]}</span>'
              for t in sorted(COV) if t in T for c in T[t]["cols"] if c["fk"] == "stakeholder") + "</div>", "2"), ),
   g(reg("Role &times; phase permission matrix",
         TB(["role", *[PHASE[p] for p in ["core", "d12", "p34", "p5", "p67", "sdg", "cc"]]],
            [["Owner"] + ["RW"] * 7, ["Architect", "RW", "RW", "R", "R", "R", "RW", "RW"],
             ["GC", "R", "R", "RW", "RW", "RW", "R", "R"],
             ["VVB auditor", "", "", "", "", "", "R", "R"]])), "3")],
  ["stakeholder", "contract", "rfi", "submittal", "bid_package"],
  ["invite org", "assign trade scope", "rotate API credential to BIM/IFC feed"],
  ["A stakeholder with an open rfi or submittal cannot be deactivated &#8212; reassign first.",
   "External verifier (VVB) rows are read-only to all internal roles."],
  "Admin maintains register; others read", "unverified org &#183; credential expired &#183; no contacts"), use(
     "stakeholder", "contract", "bid_package", "submittal")

# ---------------------------------------------------------------- 06 funding
F("06", "Design economics &amp; funding sources", "d12",
  f"Baseline-vs-revised comparison over <code>financial_metric</code> ({len(T['financial_metric']['cols'])} cols) plus the "
  "capital stack from <code>funding_source</code>. This frame is why the ERD keeps baseline and revised side by side.",
  [g2(reg("Metric comparison &#8212; baseline vs revised, per wbs",
          TB([c["n"] for c in cols_of("financial_metric")],
             [["&#8226;", "NPV", "E-Full", "18.4%", "21.1%", "+2.7%", "2026-11-02"],
              ["&#8226;", "IRR", "E-Full", "11.2%", "10.8%", "-0.4%", "2026-11-02"]]),
          "1"),
      reg("Capital stack &#8212; funding_source",
          PH_("150px", "equity 34% &#183; senior debt 41% &#183; green bond 18% &#183; grant 7%")
          + "<br>" + chips("funding_source"), "2")),
   g(reg("Drawdown schedule vs approved_budget",
         PH_("120px", "line chart: planned vs drawn, by quarter"), "3"))],
  ["financial_metric", "funding_source", "project", "wbs"],
  ["save revised scenario (keeps baseline immutable)", "attach covenant document", "recompute against new forecast cost"],
  ["Baseline row is append-only; revisions create a new dated row rather than mutating.",
   "Green-bond tranches must be linked to a carbon_project, otherwise the covenant check fails.",
   "Covenant headroom &lt; 10% surfaces a blocking banner in frame 03."],
  "Client-side CFO + Owner; GC read-only on funding", "no scenario saved &#183; stale metric (&gt; 30d) &#183; FX mismatch warning"), use("financial_metric", "funding_source")

# ---------------------------------------------------------------- 07 BIM inspector
F("07", "BIM / IFC element inspector &amp; design control", "d12",
  "<code>bim_element</code> is the unified parent of <code>structural_element</code> and <code>mep_system</code> "
  "(inheritance in a relational schema), so the frame shows one shared header plus a subtype tab.",
   [g21(reg("Element tree from imported IFC (element_id + project_id)",
            '<div class="tree"><u>Storey L3</u><br>&nbsp;&#9492;<u>Column C-118</u> <span class="m">structural</span><br>'
            '&nbsp;&#9492;<u>AHU-3</u> <span class="m">mep</span><br>&nbsp;&#9492;<u>Duct D-33</u> <span class="m">mep</span></div><br>'
            + chips("bim_element"), "1"),
       reg("Shared attributes + subtype tabs",
           '<div class="chips"><span class="chip pk">structural_element</span><span class="chip pk">mep_system</span></div>'
           + PH_("112px", "subtype field grid loads per tab &#8212; concrete grade / rebar mass vs HVAC capacity / refrigerant"))),
    g2(reg("Design control &#8212; revision, clash detection, LOD, approval",
           TB([c["n"] for c in cols_of("design_control")],
              [["&#8226;", "R7", "clash 41 open", "LOD 350", "pending"],
               ["&#8226;", "R7", "clash 0", "LOD 400", "approved"]]),
           "2"),
       reg("Model health",
           KPIS(("Clashes open", "41"), ("Clashes resolved", "212"), ("LOD", "350"),
                ("Elements without WBS link", "78"))))],
   ["bim_element", "structural_element", "mep_system", "design_control"],
   ["import / re-sync IFC", "run clash set", "approve revision (blocks P34 award until done)", "link element to wbs"],
   ["Awarding a bid_package that contains an element in an unapproved revision is blocked.",
    "<code>structural_element</code> and <code>mep_system</code> share the PK of <code>bim_element</code> via "
    "<code>element_id</code> &#8212; the subtype adds no second project_id; scope resolves through the parent.",
    "78 elements without <code>wbs_id</code> cannot be costed in frame 08."],
   "Architect + BIM manager write; GC read", "sync in progress &#183; import failed (schema version) &#183; element deleted upstream"), use(
      "bim_element", "structural_element", "mep_system", "design_control")

# ---------------------------------------------------------------- 08 BOQ
F("08", "Bill of quantities &amp; contingency", "p34",
  f"Rate build-up across <code>boq_item</code> ({len(T['boq_item']['cols'])} cols). Qty &times; (material + labour) is the "
  "spine every later cost figure rolls up to WBS.",
   [g21(reg("BOQ grid",
            TB([c["n"] for c in cols_of("boq_item")],
               [["&#8226;", "C30/37 concrete", "m&#179;", "1,240", "m", "88.00", "24.50", "0.55", "E20", "EL-214"]]),
            "1"),
       reg("Rate editor", fields("boq_item"))),
    g2(reg("Contingency drawdown &#8212; design / construction / VE reserve",
           TB([c["n"] for c in cols_of("contingency")],
              [["&#8226;", "design", "$2.1m", "$0.6m", "$1.5m"]]) + "<br>" + chips("contingency")),
       reg("Derived (read-only)",
           KPIS(("Base cost", "$311.4m"), ("Risk", "$14.2m"), ("Conting. used", "$6.9m"),
                ("Forecast", "$409.0m")), "2"))],
   ["boq_item", "contingency", "wbs", "change_order"],
   ["add line", "apply rate set", "bind line to wbs &amp; element", "re-roll up to WBS"],
   ["<code>productivity_norm</code> drives labour hours; without it the schedule (frame 09) cannot compute duration.",
    "Cost rolls up via <code>boq_item.wbs_id</code> and <code>boq_item.element_id</code>, never onto the rate &#183; one WBS node may carry many lines.",
    "Contingency transfer into base cost must reference the change_order that consumed it."],
   "Quantity surveyor writes; GC reviews awarded rates", "rate missing &#183; circular unit conversion &#183; unsaved diff"), use(
      "boq_item", "contingency", "change_order")

# ---------------------------------------------------------------- 09 schedule
F("09", "Schedule, dependencies &amp; critical path", "p34",
  "Gantt over <code>schedule_activity</code>; links live in the bridge table <code>activity_dependency</code>, "
  "so an activity can have many predecessors without the parent growing columns.",
  [g(reg("Gantt &#8212; bars coloured by is_critical_path, width by duration_days",
         '<div class="gantt">' + "".join(
             f'<div><b>{a}</b><div class="bar" style="width:{w}%;margin-left:{l}%;'
             f'background:{"#e8b3b3" if crit else "#d4d9df"}"></div></div>'
             for a, w, l, crit in [("E10 Piling", 22, 0, 1), ("E20 Slab", 30, 18, 1),
                                   ("F30 Frame", 34, 44, 0), ("G MEP", 26, 62, 0),
                                   ("H Fit-out", 18, 78, 1)]) + "</div>", "1"), ),
   g2(reg("Activity ledger", TB([c["n"] for c in cols_of("schedule_activity")][:8],
              [["&#8226;", "E10", "2026-02-04", "2026-03-12", "2026-02-06", "2026-03-20", "38", "-6"]])),
      reg("Dependency link editor (bridge table)", fields("activity_dependency"), "2"), )],
  ["schedule_activity", "activity_dependency", "wbs", "spatial_zone_room", "daily_progress", "site_weather_log"],
  ["re-baseline (snapshots planned dates)", "insert FS/SS link", "flag critical path", "punch activity to a room"],
  ["Planned dates are immutable once baselined &#8212; a change writes a new baseline row.",
   "Float and critical path are recomputed from the dependency graph, never stored by hand.",
   "Idle-weather days are matched to <code>site_weather_log.log_date</code> via <code>log_date</code> on daily_progress "
   "&#8212; there is no stored link column; both dates must fall inside the activity window for an extension-of-time claim.",
   "Progress written from frame 13 (daily_progress.percent_complete) drives actual_end."],
  "Planner writes; subs read their own activities", "loop in dependency graph (rejected) &#183; calendar missing &#183; re-baseline in review"), use(
     "schedule_activity", "activity_dependency", "daily_progress", "site_weather_log")

# ---------------------------------------------------------------- 10 permits & risk
F("10", "Permits, approvals &amp; risk register", "p34",
  "Two pre-construction gates side by side: statutory permissions and the scored risk register.",
  [g2(reg("Permit board &#8212; status / expiry",
          TB([c["n"] for c in cols_of("permit")],
             [["&#8226;", "Foundation", "applied", "2026-01-12", "$8.4k", "2027-01-12", "ok"]]), "1"),
      reg("Risk heat map &#8212; probability_score &times; impact_score",
          '<div class="heat">' + "".join(
              f'<i style="background:{b}"></i>' for b in
              ["#d9e4d9", "#cfe0cf", "#e6e0c8", "#e2c9b6", "#dcb0ac"] * 5) + '</div>'
          + f"<br><span class='m'>10 risks on register &#183; {len(T['risk_register']['cols'])} cols each</span>", "2")),
   g(reg("Risk ledger with mitigation log",
         TB([c["n"] for c in cols_of("risk_register")],
            [["&#8226;", "R-07 ground water", "4", "5", "20", "dewatering permit extended, monitored"]])) )],
  ["permit", "risk_register", "wbs", "site", "project"],
  ["register permit &amp; upload decision notice", "score risk", "attach mitigation", "link risk to WBS element"],
  ["An expiring permit inside 30 days raises a cross-frame banner.",
   "<code>probability_score &#215; impact_score</code> drives the exposure figure; both are ordinal, not percent.",
   "Risks linked to <code>site</code> (groundwater, soil bearing) feed the construction method statement."],
  "Client representative owns permits; PM owns risks", "permit refused &#183; expiry imminent &#183; risk closed but linked activity open"), use(
     "permit", "risk_register")

# ---------------------------------------------------------------- 11 procurement awards
F("11", "Procurement &#8212; bid packages &amp; award", "p34",
  "Bid tabulation and award decisions. <code>bid_package</code> carries the evaluation scores; the award writes a "
  "<code>contract</code> row pointing at the winning <code>stakeholder</code>. Bonds and insurance are contract columns "
  "(no separate performance_bond / insurance_policy tables in this schema).",
  [g21(reg("Bid comparison grid &#8212; one row per package",
           TB([c["n"] for c in cols_of("bid_package", only=["bid_package_id", "trade_scope", "prequal_score", "bid_variance_pct"])],
              [["BP-07", "Curtain wall supply &amp; install", "82.5", "+3.1%"],
               ["BP-09", "Elevators", "74.0", "-8.4%"],
               ["BP-12", "MV switchgear", "91.2", "+12.0% &#9888;"]]), "1"),
       reg("Award panel &#8212; contract",
           fields("contract", only=["stakeholder_id", "award_value", "retention_pct"]) + "<br>"
           + STEP("draft", "negotiated", "signed", "issued to site"), "2")),
    g(reg("Bond &amp; insurance expiry strip &#8212; contract.bond_number / contract.insurance_expiry",
          TB(["bond_number", "insurance_expiry", "days to expiry", "flag"],
             [["PB-NBO-07-A", "2027-03-31", "131", "ok"],
              ["PB-NBO-09-C", "2026-12-14", "&#8226; 24", "renew &#8810; 30d &#8212; blocks next payment cert"]]), "3"))],
  ["bid_package", "contract", "stakeholder", "project"],
  ["record bid &amp; prequal score", "award package &#8594; create contract", "register bond / insurance dates", "rebid (void award)"],
  ["<code>bid_variance_pct</code> beyond &#177;10% forces a written justification before award.",
    "Award requires a prequal-cleared <code>stakeholder_id</code>; retention default from <code>contract.retention_pct</code>, not free-typed.",
    "<code>insurance_expiry</code> or bond lapsing suspends <code>payment_application</code> certification (frame 17)."],
  "Procurement manager writes; commercial/QS verifies; Owner approves awards above threshold",
  "packages open &#183; award under appeal &#183; prequal expired"), use("bid_package", "contract")

# ---------------------------------------------------------------- 12 supply chain
F("12", "Supply chain &#8212; purchase orders &amp; track / trace", "p34",
  "Long-lead procurement: <code>purchase_order</code> attaches to the award and BOQ line; <code>supply_shipment</code> "
  "progresses fabrication &#8594; ETD &#8594; ETA &#8594; customs. Material attributes stay on <code>boq_item</code> "
  "(no material_catalogue table in this parsed schema).",
  [g(reg("PO register &#8212; purchase_order",
         TB([c["n"] for c in cols_of("purchase_order")],
            [["&#8226;", "PO-3341", "contract BP-07", "boq EL-214", "$412,500", "96"]]), "1")),
    g21(reg("Shipment track &amp; trace &#8212; keyed on fabrication_pct / etd / eta / customs_cleared_at",
            STEP("fabrication " + "68%", "ETD 2026-11-28", "ETA 2026-12-19", "cleared 2026-12-23")
            + "<br>" + TB([c["n"] for c in cols_of("supply_shipment")],
                          [["&#8226;", "PO-3341", "68", "2026-11-28", "2026-12-19", "(pending)"]])
            + '<br><span class="m">idle risk: lead_time_days 96 vs planned activity start &#8212; late arrival flags frame 09 float</span>', "2"),
        reg("Material attributes &#8212; boq_item (stand-in for a catalogue)",
            fields("boq_item", only=["unit_of_measure", "estimated_qty", "unit_material_rate", "productivity_norm"]), "3"))],
  ["purchase_order", "supply_shipment", "boq_item", "contract"],
  ["raise PO from awarded line", "update fabrication %", "log vessel ETD/ETA", "record customs clearance"],
  ["PO may only reference a line under a signed <code>contract</code>.",
    "<code>customs_cleared_at</code> must be set before the shipment is allowed to deliver against an on-site activity.",
    "Per-unit embodied carbon is NOT a column in this schema &#8212; carbon provenance is carried by the credit ledger "
    "(frame 22) and site logs (frame 16), not by material rows."],
  "Supply chain coordinator writes; site agent confirms receipt; Owner read-only",
  "no shipments booked &#183; customs held &#183; ETA slipped (banner) &#183; partial delivery"), use("purchase_order", "supply_shipment")

# ---------------------------------------------------------------- 13 progress / EV
F("13", "Daily progress &amp; earned value", "p5",
  "The site field log feeding the S-curve: one <code>daily_progress</code> row per activity per <code>log_date</code>; "
  "EV metrics (<code>earned_value_ev</code>, <code>actual_cost_ac</code>) accumulate against "
  "<code>schedule_activity</code>. A dedicated labour-breakdown table (daily_progress_labor) is not in this schema, "
  "so the split is derived via contract &#8594; stakeholder.",
  [g21(reg("Field log form &#8212; daily_progress",
            fields("daily_progress") 
            + "<br>" + TB(["log_date", "activity_id", "headcount", "man_hours", "equipment_hours", "percent_complete", "earned_value_ev", "actual_cost_ac"],
                          [["2026-11-19", "F30 L4 frame", "38", "412", "96", "62.0", "$1.18m", "$1.12m"],
                           ["2026-11-19", "G1 MEP risers", "11", "98", "6", "41.0", "$0.31m", "$0.34m"]]), "1"),
        reg("Sub contractor / trade split &#8212; derived",
            TB(["trade_scope (bid_package)", "organisation (stakeholder)", "man_hours", "share"],
               [["Curtain wall", "Aurora Facades", "128", "26%"],
                ["MV switchgear", "GridPower Ltd", "54", "11%"],
                [" &#8212; derived, no labour table &#8212;", "", "412", "100%"]]), "2")),
    g(reg("S-curve placeholder &#8212; cumulative earned_value_ev vs actual_cost_ac vs planned",
          PH_("150px", "EV / AC / PV curves by log_date &#183; SPI=CPI read-out"), "3"))],
  ["daily_progress", "schedule_activity", "boq_item", "contract", "bid_package", "stakeholder"],
  ["submit daily log", "attach photos", "recompute EV / SPI / CPI", "lock history after 7 days"],
  ["<code>percent_complete</code> cannot regress unless the prior log is amended with a reason code.",
    "A log row without <code>activity_id</code> cannot post to EV; QC hold-point passed (frame 15) is required before % counts on gated works.",
    "<code>man_hours</code> should reconcile with headcount &#215; shift length; beyond 2&#215; raises a data-quality flag."],
  "Site engineer / superintendent submits; PM approves; subs see own trades",
  "offline draft &#183; partially synced &#183; log locked &#183; EV recompute queued"), use("daily_progress", "boq_item")

# ---------------------------------------------------------------- 14 RFI / submittals
F("14", "RFI &amp; submittal workflow", "p5",
  "Two parallel information channels over the same clock: <code>rfi</code> (question out &#8594; answer back) and "
  "<code>submittal</code> (document out &#8594; review chain back). Ageing is computed from submitted_at / due_date / "
  "closed_at; a submittal_review table is not modelled here, so the reviewer chain rides on <code>stakeholder_id</code> "
  "plus status notes.",
  [g(reg("Kanban with SLA ageing &#8212; days open = now &#8722; due_date, closed on closed_at",
         '<div class="kan"><div><b>draft</b><br>RFI-422 anchor detail<br><span class="m">due &#8810;</span></div>'
         '<div><b>answered</b><br>SUB-091 air handler<br><span class="m">open 4d</span></div>'
         '<div><b>awaiting response</b><br>RFI-418 curtain wall<br><span class="m">OVERDUE 1d</span></div>'
         '<div><b>closed</b><br>SUB-088 rebar cage<br><span class="m">closed_at ok</span></div></div>', "1")),
    g2(reg("Review chain panel (derived &#8212; no submittal_review table)",
           TB(["step", "reviewer (stakeholder_id)", "state", "days"],
              [["1 engineer", "SH-011", "code A", "1"],
               ["2 architect", "SH-002", "pending", "2"],
               ["3 owner rep", "&#8212;", "locked until 2", "0"]]), "2"),
       reg("Impact callout flag", fields("rfi", only=["cost_schedule_impact_flag"]) 
           + '<br><span class="note">flag set &#8594; record spawns a change_order candidate (frame 17) and a critical-path review task</span>', "3"))],
  ["rfi", "submittal", "stakeholder", "bim_element", "schedule_activity", "project"],
  ["raise RFI against element/activity", "route to reviewer", "code answer (A/B/C)", "close &#183; archive", "escalate overdue"],
  ["Due clock starts at <code>submitted_at</code>; SLA breach recolours the card and notifies the responsible stakeholder.",
    "A submittal cannot be closed while <code>closed_at</code> is null on any open review step.",
    "<code>cost_schedule_impact_flag</code> answers require PM countersign before closing."],
  "GC raises; design team answers; Owner sees flagged items only",
  "board empty &#183; filter by trade &#183; overdue banner &#183; read-only archive"), use("rfi", "submittal", "bim_element")

# ---------------------------------------------------------------- 15 quality / NCR
F("15", "Quality tests &amp; NCR lifecycle", "p5",
  "Conformance evidence. <code>quality_test</code> stores one measured result against an enumerated <code>test_type</code>; "
  "a failed test raises an <code>ncr</code> whose state machine is <code>ncr_status</code>. The design target itself "
  "(e.g. f&#8242;c) is not a column on quality_test in this schema &#8212; the comparator comes from the spec reference.",
  [g2(reg("Test result grid &#8212; measured_value vs pass_fail",
           TB([c["n"] for c in cols_of("quality_test", only=["test_id", "test_type", "measured_value", "pass_fail"])],
              [["QT-1108", "concrete_cube_fck", "38.4", "&#9745; pass"],
               ["QT-1109", "concrete_cube_fck", "31.0", "&#9746; fail &#8594; NCR-12"],
               ["QT-1110", "weld_ut", "0 indication", "pass"],
               ["QT-1111", "slump", "118", "pass"]]), "1"),
       reg("Test / NCR attributes",
           chips("quality_test", only=["wbs_id", "room_id", "element_id", "test_type"]) + "<br>"
           + chips("ncr", only=["ncr_status", "raised_date", "closed_date"]), "2")),
    g(reg("NCR state stepper &#8212; ncr_status",
          STEP("open", "disposition pending", "retest / repair", "closed (verified)")
          + '<br><span class="m">disposition types (repair, replace, accept-as-is, rework) are an ENUM on the workflow service, not a table in this schema; '
          'separateness severity likewise stays a form field &#8212; ncr_severity / disposition_type tables are absent</span>', "3"))],
  ["quality_test", "ncr", "wbs", "spatial_zone_room", "bim_element"],
  ["log test result", "auto-raise NCR on fail", "assign disposition", "schedule retest", "close with evidence"],
  ["A failed <code>pass_fail</code> must spawn exactly one open NCR before the next <code>percent_complete</code> tick (frame 13).",
    "NCR close requires <code>closed_date</code> plus linked retest row; element bridge to asset handover rides on <code>element_id</code> (frame 18).",
    "Tests are keyed to wbs / room / element so results roll into the O&amp;M file."],
  "CQE raises &amp; closes; lab submits results; architect approves accept-as-is",
  "no tests this week &#183; NCR overdue &#183; retest pending &#183; hold on next pour"), use("quality_test", "ncr")

# ---------------------------------------------------------------- 16 HSE / weather
F("16", "HSE, environment &amp; weather", "p5",
  "Safety and environment share one daily record (<code>hse_record</code>); the site log (<code>site_weather_log</code>) "
  "supplies work-stop evidence. Drone stills attach by URL only.",
  [g(reg("KPI strip &#8212; last 28 days over hse_record",
         KPIS(("LTIFR", "0.42"), ("PPE compliance", "97.1%"), ("Toolbox attendance", "182"),
              ("Waste tonnage", "34.2 t"), ("Carbon (plant &amp; logistics)", "81,500 kgCO&#8322;e"),
              ("Near misses open", "3")), "1")),
    g21(reg("HSE ledger",
            TB([c["n"] for c in cols_of("hse_record")],
               [["&#8226;", "2026-11-19", "0.42", "34.2", "81500", "97.1", "182"]]), "2"),
        reg("Trend placeholders", PH_("120px", "LTIFR rolling 12m") + "<br>" + PH_("90px", "waste diverted vs landfill"), "3")),
   g(reg("Weather log &#8212; stand-down rules on wind_kmh / rainfall_mm; drone_capture_url attached",
         TB([c["n"] for c in cols_of("site_weather_log")],
            [["&#8226;", "2026-11-19", "21.4", "44", "&#8212; ", "/drone/L4-20261119.tif"],
             ["&#8226;", "2026-11-18", "19.8", "62", "6.2", "(no flight &#8212; wind)"]])
         + '<br><span class="m">rule: tower crane stands down at wind_kmh &gt; 60; concrete pour halts on sustained rainfall_mm; idle day links to frame 09 EOT trail</span>', "4"))],
  ["hse_record", "site_weather_log", "project"],
  ["submit daily HSE log", "record incident / near miss", "attach toolbox sheet", "flag stand-down", "pull drone capture"],
  ["LTIFR is per 200,000 man-hours, computed against man_hours from frame 13, not typed.",
    "A weather row marking stand-down auto-suggests a non-productive code on the same-log_date daily_progress rows.",
    "<code>carbon_kg_co2e</code> here is operational (plant/logistics); embedded carbon is ledger-side (frame 22)."],
  "HSE officer writes; GC PM co-signs severe incidents; Owner read-only",
  "no log today (nag) &#183; incident under investigation &#183; weather feed outage"), use("hse_record", "site_weather_log")

# ---------------------------------------------------------------- 17 payments / CO
F("17", "Payments &amp; change orders", "p5",
  "Monthly cost flow: <code>payment_application</code> per contract with the claim/certify/retention waterfall, and "
  "<code>change_order</code> approvals moving <code>approved_variation_value</code> into forecast. A payment_term table "
  "is not in this schema &#8212; the payment schedule below is derived from contract terms, shown as placeholders.",
  [g21(reg("Payment waterfall &#8212; claimed vs certified vs retention",
            TB([c["n"] for c in cols_of("payment_application", only=["app_id", "claimed_amount", "certified_amount", "retention_held"])],
               [["PA-14", "$6.42m", "$6.05m", "$0.61m"],
                ["PA-13", "$5.88m", "$5.71m", "$0.57m"]])
            + "<br>" + PH_("120px", "claim &#8594; certify &#8594; less retention &#8594; net due, by application"), "1"),
        reg("Retention pot &#8212; contract",
            KPIS(("Retention %", "contract.retention_pct"), ("Held", "$4.2m"), ("Release stage", "partial")), "2")),
    g2(reg("Change order approval stepper &#8212; value impact to forecast",
           STEP("raised", "priced", "PM approved", "owner approved") + "<br>"
           + TB([c["n"] for c in cols_of("change_order")],
                [["&#8226;", "CO-31 ground conditions", "wbs E1", "+$1.9m", "dewatering duration x3"]]), "3"),
       reg("Derived payment grid (no payment_term table)",
           TB(["milestone", "due", "amount", "source"],
              [["site mobilisation", "signed +15d", "$4.0m", "contract"],
               ["monthly cycle", "cert + day 28", "PA net", "payment_application"],
               ["retention tranche 1", "substantial completion", "50% held", "frame 19 gate"]]), "4"))],
  ["payment_application", "change_order", "contract", "wbs", "contingency", "stakeholder"],
  ["compile application from EV (frame 13)", "certify / query line", "route CO for approval", "apply contingency draw"],
  ["Certified amount never exceeds claimed; each delta needs a reason line.",
    "An approved CO over threshold must either consume <code>contingency.allocated_amount</code> (with remaining_amount update) or a funding re-approval.",
    "Insurance/bond lapse (frame 11) suspends certification; retention release is a frame 19 gate."],
  "QS compiles; PM certifies below delegation; Owner signs above threshold",
  "application in draft &#183; certification queried &#183; CO awaiting owner &#183; payless notice"), use("payment_application", "change_order")

# ---------------------------------------------------------------- 18 handover
F("18", "Handover &#8212; assets, commissioning, punch &amp; statutory", "p67",
  "The P67 gateway. Every installed <code>bim_element</code> that operates becomes an <code>asset</code> row "
  "(element/room/PO bridges are the asset columns themselves); <code>commissioning_test</code> clears it, "
  "punch items snag it, and <code>municipal_inspection</code> pass gates "
  "<code>project.certificate_of_occupancy_date</code>.",
  [g21(reg("Asset register with commissioning status",
            TB([c["n"] for c in cols_of("asset", only=["asset_id", "asset_tag_qr", "serial_number", "manufacturer", "warranty_end"])],
               [["Elevator 3", "QR-EL-0031", "SN-88-31", "VertiCo", "2029-06"],
                ["AHU-3", "QR-ME-0118", "SN-40-18", "AirSym", "2028-11"]]) + "<br>" + chips("asset"), "1"),
        reg("Snags by room &#8212; punch_item",
            TB(["room_number", "description", "raised_date", "resolved_date"],
               [["R3-118", "scoring on glazing", "2026-11-02", "&#8212; open"],
                ["R3-118", "diffuser balance report", "2026-10-28", "2026-11-15"]]), "2")),
    g2(reg("Commissioning results &#8212; design_target vs measured_reading",
           TB([c["n"] for c in cols_of("commissioning_test")],
              [["&#8226;", "AHU-3", "supply airflow (cfm)", "1,800", "1,721", "&#9745;"],
               ["&#8226;", "CHW loop", "test pressure (kPa)", "1,000", "1,000 held", "&#9745;"],
               ["&#8226;", "MV cable", "insulation (&#937;)", "100", "84", "fail &#8594; retest"]]), "3"),
       reg("Statutory gate", fields("municipal_inspection") 
           + '<br><span class="note">&#9745; all required inspections pass &#8594; enables <code>project.certificate_of_occupancy_date</code>; '
           'any open fail keeps the project in P67</span>', "4"))],
  ["asset", "commissioning_test", "punch_item", "municipal_inspection", "spatial_zone_room", "bim_element", "project", "purchase_order"],
  ["scan QR to open asset", "record commissioning reading", "raise / clear punch", "book inspection", "issue COO when green"],
  ["Asset cannot close commissioning while a linked punch item is open.",
    "municipal_inspection rows key on room and asset; the certificate flag lives only on <code>project</code>.",
    "element &#8594; asset and system &#8594; zone mappings are the asset's own <code>element_id</code> / <code>room_id</code> "
    "columns &#8212; the dedicated bridge tables named in the design brief are absent from this schema."],
  "Commissioning manager writes; facilities lead accepts; authority submits inspections",
  "handover checklist 84% &#183; snag storm (bulk open) &#183; inspection failed &#183; COO issued (read-only freeze)"), use(
      "asset", "commissioning_test", "punch_item", "municipal_inspection")

# ---------------------------------------------------------------- 19 defects / retention
F("19", "Defects liability &amp; retention release gate", "p67",
  "DLP running on <code>defect</code>: reported &#8594; SLA &#8594; resolved, per asset. The retention release is the "
  "explicit boolean <code>retention_release_approved</code> and must not flip while any defect stays open. Preventive "
  "plan (<code>maintenance_schedule</code>) is set against reactive fail work (<code>work_order</code>).",
  [g21(reg("Defect SLA tracker",
            TB([c["n"] for c in cols_of("defect")],
               [["&#8226;", "AHU-3", "2026-10-30 08:12", "2026-11-13 08:12", "&#8212;", "false"],
                ["&#8226;", "R3-118 glazing", "2026-11-04 14:02", "2026-11-18 14:02", "2026-11-15", "false"]])
            + '<br><span class="m">breach if resolved_at &gt; sla_deadline; ageing chips colour at T-3d</span>', "1"),
        reg("Release gate",
            fields("defect", only=["retention_release_approved"]) + "<br>"
            + KPIS(("Open defects", "7"), ("SLA breached", "1"), ("Retention held", "$4.2m"),
                   ("Gate", "BLOCKED &#8212; open defects exist")), "2")),
    g2(reg("Preventive plan &#8212; maintenance_schedule",
           TB([c["n"] for c in cols_of("maintenance_schedule")],
              [["&#8226;", "AHU-3", "filter change &amp; belt check", "120", "2027-01-14"],
               ["&#8226;", "Elevator 3", "statutory exam", "182", "2026-12-01"]]), "3"),
       reg("Reactive record &#8212; work_order vs plan",
           TB([c["n"] for c in cols_of("work_order", only=["work_order_id", "asset_id", "opened_at", "downtime_hours", "repair_cost"])],
              [["WO-77", "AHU-3 fan", "2026-11-17 06:40", "14.5", "$3,900"]])
           + '<br><span class="m">ratio reactive-hours to scheduled preventive per asset drives plan revisions</span>', "4"))],
  ["defect", "maintenance_schedule", "work_order", "asset", "contract"],
  ["log defect from asset QR", "assign &amp; track SLA", "mark resolved with photo", "approve retention release", "rebalance PM plan"],
  ["<code>retention_release_approved</code> is server-set only: it requires zero open defects and inspection sign-off (frame 18).",
    "<code>sla_deadline</code> derives from defect severity class at logging; edits are audited.",
    "Every work_order against an asset under DLP is flagged to the responsible subcontractor (contract link)."],
  "Facilities manager owns gate; subcontractor fixes; Owner releases retention",
  "gate blocked &#183; SLA breach banner &#183; dispute raised &#183; all clear (gate armed)"), use("defect", "maintenance_schedule", "work_order")

# ---------------------------------------------------------------- 20 telemetry
F("20", "Facility telemetry / digital twin", "p67",
  f"Post-handover heartbeat. <code>facility_telemetry</code> is the schema's only sensor-grade table: narrow rows keyed "
  "by <code>metric_name</code>, pivotted at read time onto assets from the frame 18 register. Dedicated meter, IoT, "
  "outage and energy-source tables are not in this parsed schema &#8212; the panels below are the pivot's own slices.",
  [g21(reg("Time-series pivot &#8212; metric_name as column, metric_value as cell",
            TB(["asset &#8594; asset_id", "metric_name", "12:00", "12:15", "12:30", "24h delta"],
               [["AHU-3", "supply_air_temp_c", "13.8", "13.9", "14.2", "+0.4"],
                ["CHW loop", "pump_kw", "18.1", "17.9", "18.3", "+0.2"],
                ["Elevator 3", "door_cycles", "418", "419", "421", "+3"]]), "1"),
        reg("Asset context (meter stand-in)",
            fields("asset", only=["asset_tag_qr", "manufacturer", "warranty_end"]) 
            + '<br><span class="m">utility provider &amp; tariff rate are not schema columns; rate is an external feed joined at display time</span>', "2")),
    g2(reg("Derived outage windows &#8212; telemetry gaps by <code>timestamp</code>",
           TB(["gap start", "gap end", "duration (min, derived)", "affected assets"],
              [["2026-11-16 03:12", "2026-11-16 04:02", "50", "AHU-1..4"],
               ["2026-11-09 22:40", "2026-11-09 22:47", "7", "floor 3 lighting"]]), "3"),
       reg("CO&#8322; grid-intensity chart placeholder",
           PH_("130px", "metric_name = grid_co2_intensity &#215; metered kWh; ties to SDG target (frame 21)"), "4"))],
  ["facility_telemetry", "asset", "spatial_zone_room", "project"],
  ["pivot by asset/room", "set alert thresholds", "export window for audit", "reconcile gaps to outage log feed"],
  ["No metric row may exist without a live <code>asset_id</code>; orphan telemetry quarantines on ingest.",
    "Gap &#8594; outage inference is an external log in this build &#8212; labelled derived, never written back as truth.",
    "CO&#8322; intensity is a value feed joined on timestamp; carbon credits stay ledger-side (frame 22)."],
  "Facilities ops write thresholds only; data plant owns ingest; Owner dashboard read-only",
  "stale feed (&gt;15 min) &#183; no assets commissioned yet &#183; gap quarantine review"), use("facility_telemetry")

# ---------------------------------------------------------------- 21 SDG
F("21", "SDG module &#8212; goal matrix, targets &amp; evidence", "sdg",
  "The UN framework lands as three tables: the indicator dictionary (<code>un_sdg_indicator</code>), this project's "
  "numbers (<code>project_sdg_target</code>, baseline vs target vs actual) and proof (<code>sdg_evidence_link</code>), "
  "whose <code>source_table</code> / <code>source_record_id</code> must point at rows that exist elsewhere in this schema.",
  [g21(reg("17-goal matrix &#8212; goal_number &#215; target_code coverage",
            TB([c["n"] for c in cols_of("un_sdg_indicator", only=["goal_number", "goal_title", "target_code", "indicator_code", "unit_of_measure"])],
               [["6", "Clean water &amp; sanitation", "6.4", "6.4.1", "m&#179;"],
                ["7", "Affordable &amp; clean energy", "7.3", "7.3.1", "kWh/m&#178;"],
                ["11", "Sustainable cities", "11.6", "11.6.1", "%"],
                ["13", "Climate action", "13.1", "13.1.2", "events"],
                ["&#8230;", "17 goals &#183; dictionary is global, not project-scoped", "", "", ""]]), "1"),
        reg("Goal coverage read-out",
            KPIS(("Goals touched", "9/17"), ("Targets met", "9/14"), ("In review", "3"), ("Off-track", "2")), "2")),
    g2(reg("Target vs actual &#8212; project_sdg_target",
           TB([c["n"] for c in cols_of("project_sdg_target", only=["indicator_code", "baseline_benchmark", "target_value", "actual_value", "compliance_status", "last_evaluated_at"])],
              [["7.3.1", "212", "165", "171", "on track", "2026-11-01"],
               ["6.4.1", "1.9", "1.4", "1.9", "off track", "2026-10-15"]]), "3"),
       reg("Evidence drill-through &#8212; source_table / source_record_id",
           TB([c["n"] for c in cols_of("sdg_evidence_link")],
              [["&#8226;", "7.3.1 &#8594;", "hse_record", "uuid&#8230;", "1,120", "2026-11-01"],
               ["&#8226;", "13.1.2 &#8594;", "site_weather_log", "uuid&#8230;", "3 events", "2026-10-20"],
               ["&#8226;", "7.3.1 &#8594;", "facility_telemetry", "bigint&#8230;", "480", "2026-11-18"]])
           + '<br><span class="m">validator: source_table must name a table in this schema and source_record_id must resolve</span>', "4"))],
  ["un_sdg_indicator", "project_sdg_target", "sdg_evidence_link", "project", "wbs"],
  ["bind indicator to target", "enter measurement", "attach evidence record", "run compliance roll-up", "export SDG report"],
  ["Actual outside [0.5&#215;, 10&#215;] baseline rejects until re-confirmed &#8212; unit errors are common.",
    "Evidence rows whose source record is deleted mark the target <code>compliance_status</code> as stale, not failed.",
    "<code>baseline_benchmark</code> is external (UN data) joined by indicator_code; never free-typed."],
  "ESG lead owns targets; data owners attach evidence; verifier read-only",
  "first run (no targets) &#183; evidence broken link &#183; annual review lock"), use("un_sdg_indicator", "sdg_evidence_link")

# ---------------------------------------------------------------- 22 carbon credits
F("22", "Carbon credit module &#8212; project, issuance, ledger &amp; SDG bridge", "cc",
  "Full credit chain: registered <code>carbon_project</code> &#8594; MRV issuance (<code>carbon_credit_issuance</code>, "
  "VVB-verified) &#8594; transactions (<code>carbon_credit_transaction</code>: issue/sell/transfer/retire) &#8594; SDG co-benefit "
  "bridge. Intensity is honestly shown two ways, because the brief's material-catalogue mass pathway is not modelled here.",
  [g21(reg("Registry card &#8212; carbon_project",
            fields("carbon_project", only=["methodology", "standard_body", "registry_id", "crediting_start", "crediting_end", "status"])
            + "<br>" + chips("carbon_project", only=["project_id", "wbs_id"]), "1"),
        reg("Lifecycle",
            STEP("registered", "baseline set", "monitoring", "verified", "issuing") + "<br>"
            + KPIS(("Credits issued", "48,200 t"), ("Retired", "12,500 t"), ("In portfolio", "35,700 t")), "2")),
    g2(reg("Issuance ledger &#8212; carbon_credit_issuance",
           TB([c["n"] for c in cols_of("carbon_credit_issuance", only=["issuance_id", "vintage_year", "verification_period_end", "tco2e_verified", "serial_number_range", "vvb_name"])],
              [["IS-2025-1", "2025", "2025-12-31", "21,400", "CC-NBO-000001&#8211;021400", "Aster VVB"],
               ["IS-2026-1", "2026", "2026-06-30", "26,800", "CC-NBO-021401&#8211;048200", "Aster VVB"]])
           + '<br><span class="m">one verification_report_url per issuance; serial ranges must be contiguous &amp; unique</span>', "3"),
       reg("Transaction register &#8212; carbon_credit_transaction",
           TB([c["n"] for c in cols_of("carbon_credit_transaction", only=["transaction_id", "transaction_type", "counterparty", "quantity_tco2e", "price_per_tco2e", "retirement_beneficiary", "registry_reference"])],
              [["T-001", "P (issue)", "registry &#8594; owner", "21,400", "&#8212;", "&#8212;", "RR-88021"],
               ["T-018", "S (sell)", "NorthBank TR", "6,000", "$31.40", "&#8212;", "RR-88077"],
               ["T-022", "T (transfer)", "Meridian GC", "3,500", "&#8212;", "&#8212;", "RR-88115"],
               ["T-030", "R (retire)", "SDG Hub report", "12,500", "&#8212;", "Annual report FY26", "RR-88140"]]), "4")),
    g(reg("Bridge &amp; dual intensity panel &#8212; carbon_credit_sdg_link",
          TB(["sdg_target &#8594; indicator (via project_sdg_target)", "contribution_tco2e", "intensity &#8212; performance basis", "intensity &#8212; mass basis (bounded)"],
             [["7.3.1", "9,200", "tCO&#8322;e &#247; metered kWh (frame 20)", "tCO&#8322;e &#247; (rebar_tonnage + steel_weight) from structural_element"]])
          + '<br><span class="m">no material_catalogue.embodied_carbon_kgco2e_per_unit or element_asset_bridge exists in this schema: mass-based intensity uses in-scope steel quantities '
          'with an external emission factor; both bases shown side by side, neither is authoritative alone</span>', "5"))],
  ["carbon_project", "carbon_credit_issuance", "carbon_credit_transaction", "carbon_credit_sdg_link", "project_sdg_target", "project", "wbs", "structural_element", "boq_item"],
  ["register project &amp; methodology", "record verified issuance", "execute P/S/T/R transaction", "retire with beneficiary note", "link co-benefit to SDG target", "export registry statement"],
  ["Retirement is irreversible; <code>retirement_beneficiary</code> + <code>registry_reference</code> become part of the permanent record.",
    "Sum of transaction quantities may never exceed <code>tco2e_verified</code> of the linked issuance.",
    "<code>carbon_credit_sdg_link</code> points at a real <code>project_sdg_target</code> row and its contribution must pass the frame 21 evidence validator."],
  "Carbon manager raises; VVB verifies; registry operator settles; Owner approves retirements",
  "draft project &#183; verification pending &#183; ledger double-entry mismatch &#183; retired (immutable)"), use(
      "carbon_project", "carbon_credit_issuance", "carbon_credit_transaction", "carbon_credit_sdg_link")

# ---------------------------------------------------------------- 23 ERD inspector
INSPECT = "carbon_credit_issuance"
_out = [c for c in T[INSPECT]["cols"] if c["fk"]]
_in = [(t, c["n"]) for t in sorted(T) for c in T[t]["cols"] if c["fk"] == INSPECT and t != INSPECT]
_roles = ["one issuance enters the ledger through many transactions", "co-benefit bridge to an SDG target"]
F("23", "Entity / record inspector (mirrors the source ERD Inspector)", "core",
  f"The source schema file ships an inspector that, for one table, lists its columns, its outgoing FK links and every "
  "incoming reference. This frame is that view, live-generated for <code>" + INSPECT + "</code> from the parsed schema.",
  [g21(reg("Columns &#8212; " + INSPECT, chips(INSPECT), "1"),
      reg("Outgoing FKs (where this row points)",
          '<div class="chips">' + "".join(f'<span class="chip fk">{c["n"]}&#8594;{c["fk"]}</span>' for c in _out)
          + "</div><br><span class='m'>one FK &#8212; issuance belongs to exactly one carbon_project</span>", "2")),
    g(reg("Incoming FKs (who references this table) &#8212; computed scan over all 45 tables",
          '<div class="chips">' + "".join(f'<span class="chip fk">{t}.{n}</span>' for t, n in _in)
          + '</div><br>' + TB(["referencing column", "role"],
                             [[f"{t}.{n}", _roles[i] if i < len(_roles) else ""] for i, (t, n) in enumerate(_in)]), "3")),
   ],
  [INSPECT, "carbon_project", "carbon_credit_transaction", "carbon_credit_sdg_link"],
  ["pick any table from the spine", "follow FK out / trace refs in", "jump to owning frame", "copy DDL-ish field list"],
  ["The scan is schema-derived at build time &#8212; no hard-coded reference lists that can drift from the ERD.",
    "Columns render from column metadata: PK amber, FK teal with target table, type on hover."],
  "Read-only for all roles; this is documentation, not an editor",
  "no FKs in (leaf table) &#183; no FKs out (spine table) &#183; self-reference (wbs)"), use(INSPECT)

# ---------------------------------------------------------------- 24 mobile capture
F("24", "Mobile field capture &#8212; offline-first", "p5",
  "The tablet/phone surface for the four highest-volume P5 forms. Writes land in a local queue against the same tables "
  "as the desktop frames: <code>daily_progress</code>, <code>quality_test</code>, <code>hse_record</code>, <code>rfi</code>.",
  [g3(reg("Sheet: daily log (offline)",
          fields("daily_progress", only=["activity_id", "log_date", "headcount", "man_hours", "percent_complete"]), "1"),
      reg("Capture bundle",
          '<div class="ph" style="height:88px"><span class="m"> photo 1/4 &#183; geo-stamped</span></div><br>'
          + TB(["attachment", "size", "state"], [["IMG_1180", "3.1 MB", "queued"]]), "2"),
      reg("Queue / sync state",
          TB(["item", "table", "sync"],
             [["log 11-19", "daily_progress", "pending wifi"],
              ["test QT-1109", "quality_test", "uploading 64%"],
              ["RFI-418 photo", "rfi", "synced"]]), "3")),
    g2(reg("Conflict warning &#8212; same id edited on desktop",
           TB(["record", "local", "server", "resolution"],
              [["QT-1109", "measured 31.0", "measured 31.4", "take server (audit kept)"]])
           + '<br><span class="m">last-writer-wins is refused; merges are explicit and logged</span>', "4"),
       reg("Sync controls &amp; battery state",
           KPIS(("Drafts", "3"), ("Photos queued", "11"), ("Last full sync", "08:42"), ("Mode", "offline")), "5"))],
  ["daily_progress", "quality_test", "hse_record", "rfi", "schedule_activity"],
  ["fill sheet offline", "stamp geo + time", "queue upload", "resolve sync conflict", "print site copy"],
  ["Queue order is per record id; a re-submitted draft updates, never duplicates.",
    "Photos above 5 MB are recompressed before queueing; originals stay on device 7 days.",
    "The HSE stand-down quick-flag (frame 16) must sync before the next day's weather reconciliation."],
  "Site engineer / foreman / safety officer; supervisors approve centrally",
  "airplane mode &#183; 4G partial &#183; storage low &#183; server unreachable (retry backoff)"), use()

# ---------------------------------------------------------------- 25 state gallery
F("25", "Cross-cutting state gallery", "core",
  "The five non-ideal states every data frame must implement, replayed on two representatives: frame 12 (supply chain) "
  "and frame 17 (payments).",
  [g3(reg("Frame 12 &#183; loading (skeleton)",
          PH_("12px", None) + "<br>" + PH_("12px", None) + "<br>" + '<div class="ph" style="height:74px;margin-top:6px"></div>', "1"),
      reg("Frame 12 &#183; empty",
          '<div class="ph" style="height:96px;display:flex;align-items:center;justify-content:center">'
          '<span class="m">no purchase orders &#183; "raise your first PO from an awarded line" &#183; [help]</span></div>', "2"),
      reg("Frame 12 &#183; error + retry",
          '<div class="flds"><div class="fld" style="border-color:#b66"><b>supply chain feed unreachable</b>'
          '<i>timeout after 10s &#183; retry (2) &#183; last good data 09:41</i></div></div>', "3")),
    g2(reg("Frame 17 &#183; read-only role (subcontractor view)",
           '<div class="flds"><div class="fld"><b>certified_amount</b><i>visible, locked &#128274;-style hatching</i></div>'
           '<div class="fld"><b>retention_held</b><i>visible</i></div>'
           '<div class="fld"><b>owner countersign</b><i>hidden &#8212; other party</i></div></div>'
           + '<br><span class="m">no write affordance renders at all; banner states the effective scope</span>', "4"),
       reg("Frame 17 &#183; stale data banner",
           '<div class="note" style="border:1.4px solid #a9791c;background:#fdf4e3;padding:6px;border-radius:4px">'
           '&#9888; costing snapshot is 6 days old &#183; change_order CO-31 approved since &#183; [refresh] [dismiss 24h]</div>', "5"))],
  ["purchase_order", "supply_shipment", "payment_application", "change_order", "contract"],
  ["degrade gracefully on feed loss", "respect role scopes", "age any snapshot > 72h with banner", "retry with backoff"],
  ["Skeletons must be structure-accurate (same column count as the resolved view).",
    "Read-only is enforced server-side; the client just mirrors it.",
    "Dismissed staleness reappears on any newer write to the same contract."],
  "Design-system requirement; applies to all 24 data frames",
  "the gallery itself &#183; plus per-frame states listed in each spec"), use()

# ---------------------------------------------------------------- page assembly
TOT_T = len(S["tables"])
TOT_C = sum(len(t["cols"]) for t in S["tables"])
TOT_FK = sum(1 for t in S["tables"] for c in t["cols"] if c["fk"])
REFD = set(COV) | {t for _, _, _, tl in META for t in tl}
MISSING = sorted(set(T) - REFD)

legend = ('<h2>Phase groups &amp; table counts (parsed schema)</h2><div class="legend">' + "".join(
    f'<span>{PHASE[p]} &middot; {S["phases"][p]}</span>' for p in ["core", "d12", "p34", "p5", "p67", "sdg", "cc"]) +
    f'<span>total {TOT_T} tables</span></div>')

idx = ('<h2>Frame index</h2><table class="idx"><tr><td>frame</td><td>title</td><td>phase group</td><td>source tables</td></tr>' +
       "".join(f'<tr><td>{fid}</td><td>{title}</td><td>{PHASE[ph]}</td>'
               f'<td>{" ".join(f"<code>{t}</code>" for t in tl)}</td></tr>'
               for fid, title, ph, tl in META) + "</table>")

cov_rows = "".join(
    f'<tr><td>{t["name"]}</td><td>{PHASE[t["phase"]]}</td>'
    f'<td>{"covered &#9745;" if t["name"] in REFD else "GAP &#8212; not referenced"}</td></tr>'
    for t in S["tables"])
missing_txt = ("Every one of the 45 parsed tables is referenced by at least one frame (45/45)."
               if not MISSING else "Unreferenced: " + ", ".join(MISSING) +
               " &#8212; deliberately uncovered or awaiting a dedicated frame.")
coverage = (f'<h2>COVERAGE REPORT &#8212; schema tables vs frames</h2>'
            f'<div class="note">{len(REFD & set(T))} / {TOT_T} tables referenced by the 25 frames above. {missing_txt}</div>'
            '<div class="reg" style="border-style:solid;border-color:var(--line);margin:10px 0 0"><div class="rl">Table-by-table</div>'
            f'<table class="w"><tr><th>table</th><th>phase group</th><th>state</th></tr>{cov_rows}</table></div>'
            f'<div class="note" style="margin-top:10px">Parsed totals: <b>{TOT_T} tables / {TOT_C} columns / {TOT_FK} foreign keys</b> '
            f'&#183; 7 phase groups. NB: the source file&#8217;s own header label reads &ldquo;47 tables &#183; 6 phases&rdquo;, '
            f'while parse_schema.py extracts {TOT_T} tables across 7 phase groups from the same file&#8217;s SCHEMA array; '
            'the parsed schema is treated as authoritative for this pack.</div>')

page = ('<!doctype html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Wireframes &#8212; Construction Lifecycle, SDG &amp; Carbon Credit Edition</title>'
        f'<style>{CSS}</style></head><body>'
        '<header class="top"><h1>Wireframes &#8212; Construction Lifecycle, SDG &amp; Carbon Credit Edition</h1>'
        '<div class="sub">Low-fidelity screen frames derived from <code>IDEA_COMP01_SCHEMA.html</code> '
        '(Construction Lifecycle ERD &#8212; SDG &amp; Carbon Credit Edition), parsed to schema.json. '
        'Every field chip, form and sample row traces back to a real table &#183; column &#183; FK in that schema; '
        'each frame&#8217;s provenance is declared in its spec block. Anything the brief named that the schema '
        'does not contain is stated as absent rather than invented.</div>'
        f'{legend}{idx}<h2>Frames</h2>' + "".join(FR) +
        '<h2>Appendix: totals</h2><footer>' + coverage +
        f'<div style="margin-top:12px">Generated {__import__("datetime").date.today().isoformat()} &#183; '
        f'{len(FR)} frames &#183; gen_wireframes.py &#183; source: uploads/IDEA_COMP01_SCHEMA.html</div></footer>'
        '</body></html>')

import os
os.makedirs(os.path.dirname(OUTP), exist_ok=True)
open(OUTP, "w", encoding="utf-8").write(page)
print(f"frames={len(FR)} tables={TOT_T} cols={TOT_C} fks={TOT_FK} covered={len(REFD & set(T))}/{TOT_T} missing={MISSING}")
print(f"wrote {OUTP} ({os.path.getsize(OUTP)} bytes)")
