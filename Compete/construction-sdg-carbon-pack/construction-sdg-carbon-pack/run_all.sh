#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 tools/parse_schema.py
python3 tools/gen_wireframes.py
python3 tools/gen_site.py
python3 tools/verify_site.py
