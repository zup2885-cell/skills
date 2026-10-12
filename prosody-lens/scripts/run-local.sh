#!/bin/sh
set -eu
skill_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
runtime_dir="${PROSODY_LENS_RUNTIME:-$HOME/.codex/skill-runtimes/prosody-lens}"
if [ ! -x "$runtime_dir/bin/python" ]; then
  printf '%s\n' "Prosody runtime missing: $runtime_dir" >&2
  exit 1
fi
PATH="$runtime_dir/bin:$PATH"
export PATH
exec "$runtime_dir/bin/python" "$skill_dir/scripts/prosody_analyze.py" "$@"
