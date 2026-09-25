#!/usr/bin/env python3
"""Assemble the reading edition from the blocks lifted out of the master."""
import json, sys, pathlib, html as H

BLOCKS = json.loads(pathlib.Path(sys.argv[1]).read_text())
FONTS_SERIF = pathlib.Path(sys.argv[2]).read_text()
FONTS_HAND  = pathlib.Path(sys.argv[3]).read_text()
CSS         = pathlib.Path(sys.argv[4]).read_text()
OUT         = pathlib.Path(sys.argv[5])

body, i = [], 0
n = len(BLOCKS)

# ---- title page: everything before the first section heading -------------
first_h1 = next(i for i, b in enumerate(BLOCKS) if b["t"] == "h1")
cover, i = BLOCKS[:first_h1], first_h1

body.append('<section class="cover">')
for b in cover:
    if b["t"] == "eyebrow":  body.append(f'<p class="eyebrow">{b["html"]}</p>')
    elif b["t"] == "display":body.append(f'<h1 class="display">{b["html"]}</h1>')
    elif b["t"] == "ribbon": body.append(f'<span class="ribbon">{b["html"]}</span>')
    else:
        cls = "lede" if b is cover[2] else ""
        body.append(f'<p class="{cls}">{b["html"]}</p>')
body.append('<div class="rule-orn"></div>')
body.append(
  '<p class="imprint"><strong>Latifah Almutairi</strong><br>'
  'Assignment 2 &nbsp;·&nbsp; Leadership School Program<br>'
  'Master Class &nbsp;·&nbsp; Leader Shadi<br>'
  'Saturday, 5 September 2026<br><br>'
  '<em>Reading edition — text only</em></p>')
body.append('</section>')

# ---- the body ------------------------------------------------------------
finale_open = False
while i < n:
    b = BLOCKS[i]; t = b["t"]

    # the closing spread begins at the last eyebrow
    if t == "eyebrow" and not finale_open:
        body.append('<section class="finale">')
        finale_open = True
        body.append(f'<p class="eyebrow">{b["html"]}</p>'); i += 1; continue

    if t == "h1":        body.append(f'<h1>{b["html"]}</h1>')
    elif t == "h2":      body.append(f'<h2>{b["html"]}</h2>')
    elif t == "display": body.append(f'<p class="display">{b["html"]}</p>')
    elif t == "byline":  body.append(f'<span class="byline">{b["html"]}</span>')
    elif t == "sig":     body.append(f'<span class="sig">{b["html"]}</span>')
    elif t == "ribbon":  body.append(f'<span class="ribbon">{b["html"]}</span>')
    elif t == "box-open":  body.append('<div class="box">')
    elif t == "box-close": body.append('</div>')
    elif t == "ul":
        body.append("<ul>" + "".join(f"<li>{x}</li>" for x in b["items"]) + "</ul>")
    elif t == "note":
        body.append(f'<aside class="note"><h3>{b["h"]}</h3><p>{b["p"]}</p></aside>')
    elif t == "p":
        cls = " ".join(c for c, on in
                       (("small", b.get("small")), ("centre", b.get("centre"))) if on)
        body.append(f'<p class="{cls}">{b["html"]}</p>' if cls else f'<p>{b["html"]}</p>')
    i += 1
if finale_open: body.append('</section>')

OUT.write_text(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Assignment 2 — Reading Edition — Latifah Almutairi</title>
<style>
{FONTS_SERIF}
{FONTS_HAND}
</style>
<style>
{CSS}
</style>
</head>
<body>
<main class="sheet">
{chr(10).join(body)}
</main>
</body>
</html>
""", encoding="utf-8")
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)")
