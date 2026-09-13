#!/usr/bin/env bash
# Rebuild Assignment 2 from the approved master.
#
#   ./build.sh /path/to/Assignment_2_ORIGINAL_MASTER.html
#
# Stages: assemble -> solve layout -> verify -> export -> right-size -> slim.
# The layout solver measures the real rendered page, so it must run against a
# freshly assembled index.html before the PDF is exported.
set -euo pipefail
cd "$(dirname "$0")"
MASTER="${1:-master/Assignment_2_ORIGINAL_MASTER.html}"
PDF="Assignment 2 - Latifah Almutairi - Leader Shadi.pdf"
NODE_MODULES="${NODE_MODULES:-$PWD/node_modules}"
export NODE_PATH="$NODE_MODULES"

echo "1/5  assembling index.html from the approved master"
: > build/layout.css
python3 tools/build.py "$MASTER" build/fonts.css css/master.css index.html

echo "2/5  solving furniture placement against the rendered page"
node tools/layout.mjs . build/layout.css

echo "3/5  verifying no text is covered, clipped or collided"
node tools/verify.mjs .

echo "4/5  exporting A4 PDF"
node tools/render.mjs . "$PDF"

echo "5/5  slimming (lossless dedupe + 4:4:4 q92 colour recompression)"
python3 tools/slim_pdf.py "$PDF" "$PDF.tmp" && mv "$PDF.tmp" "$PDF"

ls -lh "$PDF"
