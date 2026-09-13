#!/usr/bin/env python3
"""
Slot curation for Assignment 2.

The original `assets/` folder never shipped with the master HTML, so the image
layer is restored from the project's own recovered library. Every choice below
is driven by the author's OWN margin annotation for that slot — the `keylbl`
text sitting beside it — so the narrative reading of each page is preserved
rather than reinvented.

Preference order: assets separated from the composite sheets, because they are
uniform in resolution, already cut out, and therefore read as one system.
"""
import sys, shutil, pathlib, json
from PIL import Image

LIB = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

# slot -> (library asset, why this asset — the author's own cue)
SLOTS = {
 # the recurring mark: header lockup + the faint ghost watermarks
 "img001": ("sheet-37-12", "the recurring jester emblem — used as the mark and the ghost watermark"),

 # PAGE 1 — cover
 "img002": ("sheet-77-14", "the big top: the show the whole story takes place inside"),
 "img003": ("sheet-02-01", "the welcome, arms open"),
 "img004": ("sheet-11-04", "its bright twin, answering across the title"),

 # PAGE 2 — My Goals
 "img005": ("sheet-11-16", "key: material goals — happily replaced"),
 "img006": ("sheet-77-09", "key: aim true"),

 # PAGE 3 — Uprooting
 "img007": ("sheet-87-01", "key: break free · inner peace · walk on"),
 "img008": ("sheet-37-04", "left behind / searched for — the two masks"),

 # PAGE 4 — The Atmosphere I Left
 "img009": ("sheet-37-10", "key: look closer · repeated copies · still standing"),
 "img010": ("sheet-37-10", "key: the copies — same shape, same smile (deliberately the same asset as img009)"),
 "img011": ("sheet-02-10", "first smile of the show — watch it repeat"),

 # PAGE 5 — Trying to Get Myself Back
 "img012": ("sheet-87-03", "key: rest was part of the lab"),
 "img013": ("sheet-87-15", "scattered puzzle pieces"),
 "img014": ("sheet-11-11", "...coming back together"),
 "img015": ("sheet-02-13", "key: read rise"),

 # PAGE 6 — Action Plan
 "img016": ("sheet-37-06", "key: wonder"),
 "img017": ("sheet-77-12", "the lab, its own rules"),
 "img018": ("sheet-02-12", "tools that love the craziness"),
 "img019": ("sheet-11-17", "spaces bigger than the jumps"),

 # PAGE 7 — Connecting Assignment 1 & 2
 "img020": ("sheet-87-20", "key: every piece connects"),
 "img021": ("sheet-37-07", "the map becoming a path"),
 "img022": ("sheet-77-11", "key: the bridge — goals → plan → why"),

 # PAGE 8 — No One Perfect Except God
 "img023": ("sheet-11-19", "key: gentle eyes see further"),
 "img024": ("sheet-37-03", "key: read rise"),

 # PAGE 9 — Conclusion + the Gate
 "img025": ("sheet-37-15", "key: rigidity — the same taste, again"),
 "img026": ("sheet-02-02", "key: a rehearsed smile — the show"),
 "img027": ("sheet-02-04", "the gate — enter if you dare"),
 "img028": ("sheet-77-13", "the doorman"),

 # PAGE 10 — The Story 1/4
 "img029": ("sheet-11-12", "the welcome — wide arms, loud colors"),
 "img030": ("sheet-37-16", "the one who spoke"),
 "img031": ("sheet-77-08", "the painted smile — look closer"),
 "img032": ("sheet-02-11", "and the smile beside it"),

 # PAGE 11 — The Story 2/4
 "img033": ("sheet-37-13", "the tangled, exhausted mind"),
 "img034": ("sheet-11-10", "arrogant in what he memorized"),
 "img035": ("sheet-77-07", "the play — keep them laughing"),
 "img036": ("sheet-11-18", "the puppets in their final live show"),

 # PAGE 12 — The Story 3/4
 "img037": ("sheet-02-16", "studied belittlement"),
 "img038": ("sheet-11-02", "what the eyes see is not what the soul holds"),
 "img039": ("sheet-37-17", "the audience — enjoying the show"),
 "img040": ("sheet-87-08", "the poisoned dagger, same taste"),

 # PAGE 13 — The Story 4/4
 "img041": ("sheet-02-17", "by what scale are they weighed"),
 "img042": ("sheet-37-09", "all of them human"),
 "img043": ("sheet-37-02", "the smile fades — the mask stays"),
 "img044": ("sheet-02-04", "the show goes on... without her"),

 # PAGE 14 — Finale: ROLL WITH FREEDOM
 "img045": ("sheet-37-14", "lightweight, fast"),
 "img046": ("sheet-87-04", "the mask stays with the show"),
 "img047": ("sheet-77-03", "...she walks free"),
 "img048": ("sheet-02-06", "the open field is home"),
 "img049": ("sheet-37-11", "uproot with love, not hate"),
}

report = []
missing = []
for slot, (asset, why) in SLOTS.items():
    src = LIB / f"{asset}.png"
    if not src.exists():
        missing.append((slot, asset)); continue
    dst = OUT / f"{slot}.png"
    shutil.copyfile(src, dst)
    w, h = Image.open(dst).size
    report.append({"slot": slot, "asset": asset, "w": w, "h": h, "cue": why})

print(f"placed {len(report)} / {len(SLOTS)} slots")
if missing:
    print("MISSING:", missing)
(OUT.parent / "slot-map.json").write_text(json.dumps(report, indent=1))
lo = [r for r in report if max(r["w"], r["h"]) < 600]
print("assets under 600px on the long edge:", [r["slot"] for r in lo] or "none")
