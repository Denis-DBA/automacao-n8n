#!/usr/bin/env bash
set -euo pipefail
command -v python3 >/dev/null || { echo 'Instale Python 3.12+ e Docker com Compose.' >&2; exit 1; }
exec python3 "$(cd -- "$(dirname -- "$0")" && pwd)/setup.py" "$@"
