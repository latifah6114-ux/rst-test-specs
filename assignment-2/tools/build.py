#!/usr/bin/env python3
"""Assemble the final Assignment 2 document.

The <body> of the approved master is carried across BYTE-FOR-BYTE. Only the
document head is rebuilt: real embedded fonts in place of the four TTFs that
never shipped, and the finalisation stylesheet in place of the original inline
block. Two mechanical passes then run over the body:

  * each .page is tagged with the vertical-rhythm class it needs
  * a tiny loader marks any asset that fails to load, so an absent file prints
    as silence instead of a broken frame

No text node is touched.
"""
import re, sys, pathlib

MASTER = pathlib.Path(sys.argv[1])
FONTS  = pathlib.Path(sys.argv[2])
CSS    = pathlib.Path(sys.argv[3])
OUT    = pathlib.Path(sys.argv[4])

src = MASTER.read_text(encoding="utf-8")

head_end = src.index("</head>")
body_start = src.index("<body>")
body = src[body_start:]

# ---- vertical rhythm per page -------------------------------------------
# Chosen from each page's real text load: the ruling pitch follows the leading,
# so a dense page simply reaches for a finer-ruled sheet.
LEAD = {
 1:"lead-air",   2:"lead-open",  3:"lead-open",  4:"lead-open",  5:"lead-open",
 6:"lead-close", 7:"lead-tight", 8:"lead-open",  9:"lead-micro", 10:"lead-open",
 11:"lead-close",12:"lead-tight",13:"lead-micro",14:"lead-air",
}
n = 0
def tag(m):
    global n
    n += 1
    return f'<div class="page {LEAD.get(n,"lead-open")}">'
body = re.sub(r'<div class="page">', tag, body)
assert n == 14, f"expected 14 pages, tagged {n}"

# ---- index every piece of pasted furniture so the layout pass can address it
_fx = [0]
def _mark(m):
    _fx[0] += 1
    return m.group(0)[:-1] + f' data-fx="{_fx[0]}">' if m.group(0).endswith(">") else m.group(0)

def _tagfx(tag_re, src):
    def sub(m):
        _fx[0] += 1
        head = m.group(0)
        return head[:-1] + f' data-fx="{_fx[0]}"' + head[-1:]
    return re.sub(tag_re, sub, src)

body = _tagfx(r'<img class="st"[^>]*>', body)
body = _tagfx(r'<div class="pola"[^>]*>', body)
body = _tagfx(r'<div class="keylbl"[^>]*>', body)

LOADER = """
<script>
/* an asset that cannot load must print as silence, never as a broken frame */
document.querySelectorAll('img').forEach(function(i){
  function flag(){ i.setAttribute('data-missing','1'); }
  if (i.complete && i.naturalWidth === 0) flag();
  i.addEventListener('error', flag);
});
</script>
"""
body = body.replace("</body>", LOADER + "</body>")

head = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Assignment_2_Leader_Shadi_Master_Class_Leadership_School_Program</title>

<!-- Caveat & Kalam, subset and embedded. The master called for these two
     faces but shipped no font files, so every page fell back to a generic
     cursive. Embedding them restores the intended hand. -->
<style>
{FONTS.read_text()}
</style>

<style>
{CSS.read_text()}
</style>

<!-- measured layout corrections: keeps every pasted piece where the author
     scattered it, but never on top of a word -->
<link rel="stylesheet" href="build/layout.css">
<link rel="stylesheet" href="build/cover.css">
</head>
"""

OUT.write_text(head + body, encoding="utf-8")
print(f"wrote {OUT}  ({OUT.stat().st_size//1024} KB)  pages tagged: {n}")
