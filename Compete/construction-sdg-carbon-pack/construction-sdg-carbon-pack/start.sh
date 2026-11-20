#!/usr/bin/env bash
cd "$(dirname "$0")"
port="${1:-8000}"
echo "serving demo on http://localhost:$port  (Ctrl-C to stop)"
exec python3 -m http.server "$port"
