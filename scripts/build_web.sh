#!/usr/bin/env bash
#
# Build the self-contained WebAssembly demo (pygbag) for GitHub Pages.
#
# Why this is more than "pygbag --build":
# pygbag apps need cross-origin isolation (COOP/COEP) for their filesystem, but
# GitHub Pages does not send those headers, and pygbag loads its Python runtime
# from a *cross-origin* CDN. So we:
#   1) package the app with pygbag,
#   2) mirror the pygbag runtime next to index.html so it is *same-origin*,
#   3) rewrite index.html to point at that local runtime and drop the terminal,
#   4) add coi-serviceworker.js, which supplies the COOP/COEP headers.
#
# Output: build/web  (ready to publish to GitHub Pages).
set -euo pipefail

PYGBAG_VER="0.9.3"
PYVER="cp312"
PYGAME_WHL="pygame_ce-2.5.7-cp312-cp312-wasm32_bi_emscripten.whl"
CDN="https://pygame-web.github.io/cdn"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$ROOT/.webbuild"
DIST="$STAGE/build/web"

# 1. Package only the code that ships (keeps the bundle tiny).
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp "$ROOT/main.py" "$STAGE/"
cp -r "$ROOT/threebody" "$STAGE/"
( cd "$STAGE" && python -m pygbag --build --ume_block 0 \
    --title "The Three-Body Problem" main.py )

# 2. Mirror the pygbag runtime same-origin under build/web/cdn/.
mkdir -p "$DIST/cdn/$PYGBAG_VER/cpython312" "$DIST/cdn/$PYVER"
dl() { curl -sSL --fail -o "$DIST/cdn/$1" "$CDN/$1"; }
dl "$PYGBAG_VER/pythons.js"
dl "$PYGBAG_VER/cpythonrc.py"
dl "$PYGBAG_VER/empty.html"
dl "$PYGBAG_VER/cpython312/main.js"
dl "$PYGBAG_VER/cpython312/main.wasm"
dl "$PYGBAG_VER/cpython312/main.data"
dl "index-$PYGBAG_VER-$PYVER.json"
dl "$PYVER/$PYGAME_WHL"

# 3. Rewrite index.html + the package index to be same-origin, and add the SW.
python - "$DIST/index.html" "$DIST/cdn/index-$PYGBAG_VER-$PYVER.json" <<'PY'
import json
import sys

html, index = sys.argv[1], sys.argv[2]

s = open(html, encoding="utf-8").read()
s = s.replace("https://pygame-web.github.io/cdn/", "cdn/")  # runtime -> same-origin
s = s.replace("vtx,snd,gui", "snd,gui")                      # drop the xterm terminal
s = s.replace(
    '<html lang="en-us">',
    '<html lang="en-us"><script src="coi-serviceworker.min.js"></script>',
    1,
)
open(html, "w", encoding="utf-8").write(s)

data = json.load(open(index))
data["-CDN-"] = "cdn/"   # resolve package wheels same-origin too
json.dump(data, open(index, "w"), indent=4)
PY

# 4. Ship coi-serviceworker (supplies COOP/COEP on GitHub Pages).
cp "$ROOT/web/coi-serviceworker.min.js" "$DIST/"

echo "Web build ready: $DIST"
