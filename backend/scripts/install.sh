#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${BUILDCLAW_VENV_DIR:-$ROOT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "missing dependency: $1"
  fi
}

require_cmd "$PYTHON_BIN"
require_cmd git

cd "$ROOT_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e .

if [[ ! -f "$ROOT_DIR/config.yaml" ]]; then
  cp "$ROOT_DIR/config.example.yaml" "$ROOT_DIR/config.yaml"
  echo "Created config.yaml from config.example.yaml"
fi

if [[ ! -f "$ROOT_DIR/.env" && -f "$ROOT_DIR/.env.example" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "Created .env from .env.example"
fi

python "$ROOT_DIR/scripts/doctor.py"

cat <<'EOF'

BuildClaw backend installation completed.

Next steps:
1. Edit backend/config.yaml
2. Edit backend/.env if needed
3. Start with:
   source backend/.venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8080
EOF
