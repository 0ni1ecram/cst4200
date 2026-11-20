#!/bin/bash
# qa_viewport.sh — overflow + screenshot audit for the static demo
set -u
BASE="http://127.0.0.1:3000"
OUT="/workspace/118d5070-a474-4827-861f-0e35765109be/work/output/qa"
PROBE='JSON.stringify((()=>{const w=window.innerWidth;const bad=[];document.querySelectorAll("body *").forEach(e=>{const r=e.getBoundingClientRect();if(r.right>w+1){const sc=e.closest(".tw,.kanban,.gantt,.sdg-grid,.draw,.specgrid");if(!sc)bad.push(e.tagName+"#"+(e.id||"")+"."+(e.className&&e.className.toString?e.className.toString().slice(0,34):"")+" right="+Math.round(r.right))}});return{sw:document.documentElement.scrollWidth,iw:w,over:bad.length,bad:bad.slice(0,6)}})())'
PAGES=("index.html" "pages/09-schedule-dependencies-critical-path.html" "pages/14-rfi-submittal-workflow.html" "pages/22-carbon-credit-module-project-issuance-ledger-sdg-bridge.html")
WIDTHS=(1440 390)
for W in "${WIDTHS[@]}"; do
  case $W in 1440) H=900;; 390) H=844;; esac
  timeout 90 playwright-cli resize "$W" "$H" >/dev/null 2>&1
  for P in "${PAGES[@]}"; do
    NAME=$(basename "$P" .html)
    timeout 120 playwright-cli open "$BASE/$P" >/dev/null 2>&1
    RES=$(timeout 90 playwright-cli eval "$PROBE" 2>&1 | grep -A2 "### Result" | sed -n '3p')
    echo "w=$W page=$NAME $RES"
    timeout 90 playwright-cli screenshot 2>&1 | grep -oE "[^ '\"]+\.png" | tail -1 | while read -r SHOT; do
      [ -f "$SHOT" ] && cp "$SHOT" "$OUT/${NAME}-${W}.png" && echo "   shot -> $OUT/${NAME}-${W}.png"
    done
  done
done
