"""qa_audit.py — Playwright viewport audit of the static demo (served over http).

For each (page, width): page-level horizontal overflow, elements sticking out past the viewport
that are NOT inside an intentional scroll container, plus screenshots.
ALL=1 audits every page; SHOTS=1 also writes screenshots.
"""
import json, os, urllib.request
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3000"
OUT = os.path.dirname(os.path.abspath(__file__))
SITE_ROOT = os.path.abspath(os.path.join(OUT, "..", "site"))
SAMPLE = ["index.html",
          "pages/09-schedule-dependencies-critical-path.html",
          "pages/14-rfi-submittal-workflow.html",
          "pages/22-carbon-credit-module-project-issuance-ledger-sdg-bridge.html"]
if os.environ.get("ALL") == "1":
    PAGES = ["index.html"] + sorted("pages/" + f for f in os.listdir(os.path.join(SITE_ROOT, "pages"))
                                    if f.endswith(".html"))
    SHOTS = os.environ.get("SHOTS") == "1"
else:
    PAGES, SHOTS = SAMPLE, True
WIDTHS = [(1440, 900), (390, 844)]
# containers that are allowed to hold wider content (documented scroll areas)
SCROLL = (".tw,.gantt,.kanban,.sdg-grid,.draw,.specgrid,.mobilesplit,.rail,.tabs,.retpot,"
          ".bundle,.srcs-strip,.chips,.stepper,.gaugerow,.sparkrow,.donutwrap,.prevnext,"
          ".ro-demo,.tree,.filters,.kcol,.drawer-grid,.pgfoot,.hgroup>header")

JS = """(sel) => {
  const w = window.innerWidth;
  const bad = [];
  document.querySelectorAll('body *').forEach(e => {
    const r = e.getBoundingClientRect();
    if (r.right > w + 1 && !e.closest(sel)) {
      bad.push(e.tagName + '.' + (typeof e.className === 'string' ? e.className.slice(0, 30) : '')
               + ' right=' + Math.round(r.right) + ' w=' + Math.round(r.width));
    }
  });
  return {
    iw: w,
    scrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body.scrollWidth,
    offenders: bad.slice(0, 6),
    offenderCount: bad.length,
    tableBlocks: document.querySelectorAll('.tw').length,
    scrollableOverflow: [...document.querySelectorAll('.tw')].filter(t => t.scrollWidth > t.clientWidth + 1).length
  };
}"""


def main():
    try:
        urllib.request.urlopen(BASE + "/index.html", timeout=4)
    except Exception as e:
        print("server not reachable:", e)
        return 2
    report = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except Exception:
            browser = pw.chromium.launch(
                executable_path="/opt/playwright-browsers/chromium-1209/chrome-linux64/chrome")
        for width, height in WIDTHS:
            ctx = browser.new_context(viewport={"width": width, "height": height})
            page = ctx.new_page()
            for p in PAGES:
                page.goto(BASE + "/" + p, wait_until="load")
                data = page.evaluate(JS, SCROLL)
                name = os.path.basename(p).replace(".html", "")
                shot = ""
                if SHOTS:
                    if width == 1440:
                        page.screenshot(path="%s/%s-1440-top.png" % (OUT, name), full_page=False)
                    shot = os.path.join(OUT, "%s-%d.png" % (name, width))
                    page.screenshot(path=shot, full_page=True)
                data.update(page=p, width=width, screenshot=shot,
                            ok=data["scrollWidth"] <= width + 1 and data["offenderCount"] == 0)
                report.append(data)
                if not data["ok"] or width == 390:
                    print("w=%-5d %-56s scrollWidth=%-5d offenders=%-3d ok=%s %s"
                          % (width, name, data["scrollWidth"], data["offenderCount"], data["ok"],
                             ("| " + " ; ".join(data["offenders"])) if data["offenders"] else ""))
            ctx.close()
        browser.close()
    bad = [r for r in report if not r["ok"]]
    print("checks:", len(report), "| failing:", len(bad))
    json.dump(report, open(os.path.join(OUT, "viewport-report.json"), "w"), indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
