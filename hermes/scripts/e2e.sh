#!/usr/bin/env bash
# End-to-end check of the plugin inside a real Hermes; installs from git HEAD, so commit first.
set -euo pipefail

HERMES=${HERMES:-hermes}
HERMES_PYTHON=${HERMES_PYTHON:-python3}
PLUGIN_DIR=$(cd "$(dirname "$0")/.." && pwd)
REPO_ROOT=$(git -C "$PLUGIN_DIR" rev-parse --show-toplevel)
HERMES_HOME=$(mktemp -d)
# Git Bash: native Windows Python needs C:/ paths, and file:// URLs need a leading slash before the drive.
if command -v cygpath >/dev/null; then HERMES_HOME=$(cygpath -m "$HERMES_HOME"); fi
[[ $REPO_ROOT == /* ]] || REPO_ROOT=/$REPO_ROOT
export HERMES_HOME
trap 'rm -rf "$HERMES_HOME"' EXIT

step() { printf '\n== %s\n' "$*"; }

step "validate + doctor"
"$HERMES" plugins validate "$PLUGIN_DIR"
"$HERMES" plugins doctor "$PLUGIN_DIR" --ci

step "install from git (marketplace path)"
# No --yes-deps: tinyfish connect installs non-interactively and must still end up enabled.
# tee so a hang still shows how far the install got.
"$HERMES" plugins install "file://$REPO_ROOT#hermes" --enable </dev/null 2>&1 | tee "$HERMES_HOME/install.log"
install_log=$(<"$HERMES_HOME/install.log")
if grep -qi 'node dependencies' <<<"$install_log"; then
  echo "FAIL: Hermes saw a package.json in the plugin dir" >&2
  exit 1
fi
status=$("$HERMES" plugins list --json | "$HERMES_PYTHON" -c \
  'import json, sys; print(next((p["status"] for p in json.load(sys.stdin) if p["name"] == "tinyfish"), "missing"))')
if [ "$status" != "enabled" ]; then
  echo "FAIL: tinyfish plugin is $status, expected enabled" >&2
  exit 1
fi

if [ -z "${TINYFISH_API_KEY:-}" ]; then
  # CI always has a key; a silent skip there once hid every live check.
  if [ -n "${CI:-}" ]; then
    echo "FAIL: TINYFISH_API_KEY unset in CI" >&2
    exit 1
  fi
  step "TINYFISH_API_KEY unset; skipping live checks"
  exit 0
fi

step "setup + live doctor"
"$HERMES" tinyfish setup --yes
"$HERMES" tinyfish doctor --live

step "search + extract through Hermes' own web tools"
"$HERMES_PYTHON" - <<'PY'
import asyncio
import json

from hermes_cli.plugins import discover_plugins
from tools.web_tools import web_extract_tool, web_search_tool

discover_plugins()
search = json.loads(web_search_tool("TinyFish web agent", limit=2))
assert search["success"] and search["data"]["web"], search
extract = json.loads(asyncio.run(web_extract_tool(["https://example.com"], "markdown")))
page = extract["results"][0]
assert not page.get("error") and "Example Domain" in page["title"], page
print("search + extract OK")
PY
