#!/bin/sh
set -e
mkdir -p "${USER_DATA_DIR:-/data/profile}"
exec xvfb-run -a --server-args="-screen 0 1512x900x24 -ac -nolisten tcp" \
  uvicorn app:app --host 0.0.0.0 --port "${PORT:-3000}"
