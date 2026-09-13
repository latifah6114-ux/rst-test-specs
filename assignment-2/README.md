# Assignment 2 — Leader Shadi · Master Class · Leadership School Program
**Trainee: Latifah Almutairi**

Final, presentation-ready build. 14 pages, A4 portrait.

**→ `Assignment 2 - Latifah Almutairi - Leader Shadi.pdf`**

---

## What this is

The finalisation of the existing Assignment 2. The approved writing, the page
structure, the symbolism and the creative direction are the original work; this
build corrects execution only.

**The approved text is byte-for-byte identical to the master.** The build
carries the master's `<body>` across verbatim and rebuilds only the document
head, so this is verifiable rather than asserted: extracting the text content
from `master/Assignment_2_ORIGINAL_MASTER.html` and from `index.html` yields
the same 22,900 characters.

## What was actually wrong, and what was done

### 1. The fonts never loaded
The master asked for `Caveat` and `Kalam` from a local `fonts/` folder that was
never shipped, so all fourteen pages fell back to a generic system `cursive`.
This was the single largest quality failure — every heading and every line of
body text was rendering in the wrong typeface.

Both faces are now embedded directly in the HTML as base64 woff2. **Static**
instances are used, not Google's variable-font delivery: a variable instance
cannot be subset into a PDF as a real font program, so Chromium silently falls
back to Type3 glyph outlines, which inflates the file and costs text
selectability. The exported PDF now carries `Caveat-SemiBold`, `Caveat-Bold`,
`Kalam-Regular` and `Kalam-Bold` as proper embedded TrueType.

### 2. Two overlays were painting on top of the words
`.sheet::before` (a light wash) and `.sheet::after` (paper tooth) were
positioned above the text in paint order, greying out every page. Both effects
are now folded into the sheet's own background stack, so the paper keeps its
depth and the ink sits at full strength on top of it.

### 3. The running head collided with itself
The mark in the header carried `class="st"`, whose `position:absolute` is
needed by every pasted sticker — so the mark escaped the header and landed on
the header text. It is now returned to flow, and on pages flying the bunting
the head drops clear of it.

### 4. The image layer had to be rebuilt
`assets/img001.png` … `img049.png` — 49 files — were referenced but never
shipped. They were restored from the project's own recovered image library
(three sources, deduplicated to 168 unique artworks plus 5 composite sheets).

Each slot was chosen against **the author's own margin annotation for that
slot**, so the narrative reading is preserved rather than reinvented — the
label reading *"key: aim true"* gets the target and dart; *"Scattered Puzzle
Pieces"* gets the puzzle strip; *"the copies — same shape, same smile"* gets
literally the same asset twice. `slot-map.json` records every choice and the
cue behind it.

### 5. The specialty logo system — separated and rebuilt
Five assets in the library were **composite sheets**: 1300×1040 grids holding
many individual jester, mask and character marks at once, over a baked-in
transparency checkerboard.

Those sheets were segmented into **93 individual, print-ready assets** at a
uniform ~900px, each tight-cropped to its own bounding box with a real alpha
channel. The rest of the library sat on flat black or flat white, which would
have printed as hard rectangles on cream paper.

The cutout pipeline (`tools/extract_assets.py`):
1. classify the backdrop from the border ring;
2. mask it, then keep **only** the part touching the frame edge — so black
   inside a mask, or white inside an eye, survives;
3. feather the matte, then **un-multiply the backdrop back out of the edge
   pixels** — this is the step that removes the dark halo that betrays a cheap
   cutout;
4. tight-crop, resample with Lanczos, finish with a restrained unsharp pass.

No asset's identity, colour or symbolism was altered. Eight slots were
reassigned away from artwork that carried an illustrated colour backdrop or a
straight edge cut from the sheet margin.

### 6. Nothing sits on the words any more
The master pinned every sticker, polaroid and margin note at a hand-typed mm
offset, art-directed against the images that never shipped. Against the
restored library they landed squarely on the text.

`tools/layout.mjs` solves this by measurement rather than by re-art-directing:
occupancy is rasterised on a 2mm grid from the client rects of the **text nodes
themselves**, and each piece is moved to the *nearest* clear position, biased
to slide down the page rather than sideways — which is how a scrapbook reads.
Each piece keeps its size, rotation and side; size is reduced only when no
clear position exists. Margin notes travel with the piece they annotate, and
as a last resort may rest on a sticker — never on a word.

The cover and the finale are compositions rather than layouts, so their pieces
are hand-placed and locked in `build/cover.css`.

### 7. Typography
- Body set in Kalam **400**, not 700. The master set every paragraph bold,
  which in a handwriting face reads as shouting and fatigues over the long
  story pages. Bold is returned to emphasis, where it now means something.
- Reading measure capped at 150mm. Full-width lines ran to ~99 characters;
  they now run to roughly 80.
- Hanging flower bullets: wrapped lines align under the first word instead of
  falling back under the ✿.
- Highlighter marks lost their drop shadow — a marker stroke sits *in* the
  paper, it does not float above it — and the doubled wavy underline was
  thinned from 2.5px to 1.8px.
- The running foot no longer wraps to two lines.
- Never justified; handwriting must not be.

### 8. The ruling now means something
This is the one idea holding the pages together. Each page declares a single
`--lead`, and **both** the text leading and the pitch of the ruled paper are
driven from it — so the handwriting sits *on* the rules, the way real writing
does. A dense page simply declares a finer rule, exactly as a writer reaching
for a tighter-ruled sheet would. That is also what buys the crowded story
pages their room without touching a word.

### 9. Print correctness
- The master set `page-break-after:always` on every page, which emits a blank
  15th page on export. The last page is now exempt.
- `overflow:hidden` on `.page` meant any overset text was silently clipped.
  `tools/verify.mjs` now fails the build on text leaving the sheet.
- Assets are resampled to exactly what their printed size needs at 300 dpi.
- The exported PDF is deduplicated, and colour channels are recompressed as
  **4:4:4** JPEG at q92 — no chroma subsampling, so painted edges stay clean —
  while every alpha mask stays lossless. 25.6 MB → 10.5 MB, measured at a
  maximum pixel difference of 11/255 and RMS under 0.4: visually lossless.

## Verification

`tools/verify.mjs` is a gate, not a report. It fails on: text outside the
sheet, imagery covering text, pieces outside the sheet, pieces colliding, and
missing assets. Current status: **clean**.

## Rebuilding

```bash
./build.sh master/Assignment_2_ORIGINAL_MASTER.html
```

Requires `playwright-core` (`NODE_PATH` must point at it) and Python with
Pillow, numpy, scipy and pikepdf. To regenerate the image library from the
original sources, run `tools/prepare_library.py` then `tools/curate.py`.

## Layout

```
Assignment 2 - Latifah Almutairi - Leader Shadi.pdf   the deliverable
index.html                       final document, fonts embedded
assets/img001…img049.png         the 49 print-ready assets
slot-map.json                    every slot, its asset, and the cue behind it
master/                          the approved master, untouched
build/style.css                  finalisation stylesheet
build/layout.css                 generated — measured placement corrections
build/cover.css                  hand-set art direction, cover and finale
tools/                           the pipeline
```
