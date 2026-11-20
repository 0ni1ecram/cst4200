# Construction Lifecycle — SDG & Carbon Credit pack

Everything produced in this session, in one folder. Open `index.html` (or `site/index.html`) — no install,
no server, no build step needed to look at it.

> **Status of this material.** The demo site and wireframes are **AI-generated and have not been human
> reviewed**. They are also **visual only**: no JavaScript, no working inputs. Treat them as clickable-looking
> prototypes for layout and data-coverage conversations, not as software.

## Contents

| Path | What it is |
|---|---|
| `index.html` | Redirect into the demo site |
| `site/` | 26-page static demo website (hub + one page per wireframe frame), HTML + CSS only |
| `output/wireframes.html` | The 25 annotated wireframe frames, single file |
| `output/notebooks/` | MNIST work: `mnist_cnn_four_stages.ipynb` (CNN, executed), `mnist_ann_clean.ipynb`, `mnist_ann.ipynb`, `mnist_ann.py`, guide, ablation CSV |
| `output/qa/` | Playwright screenshots of the site at 1440px and 390px |
| `data/IDEA_COMP01_SCHEMA.html` | The source ERD everything was derived from |
| `tools/` | The generators that rebuild `output/wireframes.html` and `site/` from `data/` |
| `work/` | Generated intermediates (`schema.json`, `frames.json`) — safe to delete, tools recreate them |

## Quick start

**Just look at it:** double-click `index.html`.
**Serve it locally** (only needed if you want a URL): `./start.sh` → http://localhost:8000

## Regenerate everything from the schema

```bash
./run_all.sh
```
or step by step — requires only Python 3 (standard library, nothing to install):

```bash
python3 tools/parse_schema.py      # ERD -> work/schema.json  (45 tables / 320 cols / 84 FKs)
python3 tools/gen_wireframes.py    # -> output/wireframes.html
python3 tools/gen_site.py          # -> site/  (reads wireframes.html for frame ids/titles)
python3 tools/verify_site.py       # link, field-name and structure audit; prints "problems: 0"
```

All paths in `tools/` resolve relative to this pack, so it works wherever you put it — verified by running
the folder from a different location with `work/` cleared first.

## Notebooks (separate dependencies)

The MNIST notebooks ship **pre-executed**, with outputs and figures baked in — read them without installing
anything. To re-run them you need `tensorflow-cpu`, `scikit-learn`, `pandas`, `matplotlib`, `jupyter`; expect
~2 min on CPU per notebook and a first-run MNIST download. Verified results: dense ANN 99.39% train / 98.04%
test; CNN 99.59% / 98.74% (test figures are single-seed; the CNN is under-trained by design to fit the CPU
budget — ~99.2% is normal for this architecture fully trained).

## Known limits (not exhaustive, but the ones that matter)

- Site is static: filters, sort arrows, pagers, tabs and checkboxes are **styled states**, not behaviour.
  Tabs and one row drawer use `:target`/radio CSS tricks only.
- Gantt (page 09) draws bars, progress and float but **no dependency arrows**; the link graph lives in
  `activity_dependency`.
- Chart panels (06/13/16/20) are static shapes with no axes, ticks or tooltips.
- SDG matrix colours (21) are authored coverage, not read from `un_sdg_indicator` (8 dictionary rows for
  17 goals).
- Page 25's countersign row cites `approved_variation_value` because `approved_by` is not a column of any
  table that frame declares — it is composition, not data.
- The source ERD labels itself "47 tables · 6 phases"; the parsed data is **45 tables across 7 phase groups**.
  Every artefact here uses the parsed numbers.
- Carbon intensity can be computed mass-based or performance-based; the schema has no material master with
  per-unit embodied carbon, so both bases are shown side by side rather than one being presented as truth.
