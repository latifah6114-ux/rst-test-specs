#!/usr/bin/env python3
"""Turn the built document into an editable master.

Three things stand between the built file and something a person can actually
work in:

  1. the four type faces are base64'd into the file, which bloats it and means
     you scroll past 190 KB of noise to reach the markup;
  2. the solved positions live in a generated override sheet keyed by
     data-fx index, so to nudge a sticker you must first work out which
     number it is;
  3. everything hides under build/.

This writes fonts out as real files, folds every solved position back into the
element's own style attribute where it can be edited in place, and leaves
index.html as the single thing you open.
"""
import re, base64, pathlib, sys

ROOT   = pathlib.Path(sys.argv[1])
SRC    = ROOT / "index.html"
LAYOUT = ROOT / "build" / "layout.css"
COVER  = ROOT / "build" / "cover.css"
FONTS  = ROOT / "fonts"
CSS    = ROOT / "css"
FONTS.mkdir(exist_ok=True); CSS.mkdir(exist_ok=True)

html = SRC.read_text(encoding="utf-8")

# ---- 1. fonts out to real files -----------------------------------------
face = re.compile(
    r"@font-face\{font-family:'([^']+)';font-style:(\w+);font-weight:(\d+);"
    r"font-display:block;src:url\(data:font/woff2;base64,([A-Za-z0-9+/=]+)\) format\('woff2'\)\}")
decls, written = [], 0
for fam, style, wt, b64 in face.findall(html):
    slug = f"{fam.replace(' ','')}-{wt}{'i' if style=='italic' else ''}.woff2"
    (FONTS / slug).write_bytes(base64.b64decode(b64)); written += 1
    decls.append(f"@font-face{{\n  font-family:'{fam}';\n  font-style:{style};\n"
                 f"  font-weight:{wt};\n  font-display:block;\n"
                 f"  src:url('../fonts/{slug}') format('woff2');\n}}")
(CSS / "fonts.css").write_text(
    "/* Caveat & Kalam — the hand of the document.\n"
    "   Static instances, not variable: a variable instance cannot be subset\n"
    "   into a PDF as a real font program and degrades to Type3 outlines. */\n\n"
    + "\n\n".join(decls) + "\n")

# strip the inlined faces and point at the file instead
html = face.sub("", html)
html = re.sub(r"<style>\s*/\* Caveat & Kalam.*?</style>", "", html, flags=re.S)
html = re.sub(r"<style>\s*</style>", "", html)

# ---- 2. solved positions folded back into each element ------------------
# the solver's positions, then the hand-set cover/finale art direction on top
rules = dict(re.findall(r'\[data-fx="(\d+)"\]\{([^}]*)\}', LAYOUT.read_text()))
for fx, decl in re.findall(r'\[data-fx="(\d+)"\]\{([^}]*)\}', COVER.read_text()):
    rules[fx] = rules.get(fx, "") + ";" + decl
folded = 0
def fold(m):
    global folded
    tag, fx = m.group(0), m.group(1)
    if fx not in rules: return tag
    over = {}
    for d in rules[fx].split(";"):
        d = d.replace("!important", "").strip()
        if ":" in d:
            k, v = d.split(":", 1); over[k.strip()] = v.strip()
    sm = re.search(r'style="([^"]*)"', tag)
    base = {}
    if sm:
        for d in sm.group(1).split(";"):
            if ":" in d:
                k, v = d.split(":", 1); base[k.strip()] = v.strip()
    base.update(over)                      # the solved position wins
    base = {k: v for k, v in base.items() if v != "auto"}
    style = ";".join(f"{k}:{v}" for k, v in base.items())
    folded += 1
    tag = re.sub(r'\s*style="[^"]*"', "", tag)
    tag = re.sub(r'\s*data-fx="\d+"', "", tag)
    return tag[:-1].rstrip() + f' style="{style}">'

html = re.sub(r'<(?:img|div)[^>]*data-fx="(\d+)"[^>]*>', fold, html)
html = html.replace('<link rel="stylesheet" href="build/layout.css">\n', "")
html = html.replace('href="build/style.css"', 'href="css/master.css"')
html = html.replace('<link rel="stylesheet" href="build/cover.css">\n', '')
html = html.replace("<head>", '<head>\n<link rel="stylesheet" href="css/fonts.css">', 1)

SRC.write_text(html, encoding="utf-8")
print(f"fonts written : {written} files -> fonts/")
print(f"positions folded into their own elements: {folded}")
print(f"index.html    : {SRC.stat().st_size//1024} KB (was 259 KB)")
