#!/usr/bin/env bash
cd "$(dirname "$0")/app" || exit 1
command -v python3 >/dev/null 2>&1 || { echo "python3 not found."; exit 1; }
python3 server.py "${1:-8080}"
