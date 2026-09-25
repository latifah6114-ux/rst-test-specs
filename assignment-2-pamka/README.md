# Assignment 2 — The Programmable Mind & The Unbroken Reference
**Latifah Almutairi · Imperial Archive · 5 September 2026**

18 pages, A4. `index.html` is the master; the PDF is its export.

## Editable — nothing is flattened
Open `index.html` in any browser. Every word is live text, every image is an
`<img>` you can swap, every position is an mm value in that element's own
`style` attribute. One stylesheet, one font file, five images.

```
index.html      THE MASTER — open this
css/master.css  the whole design system
css/fonts.css   → fonts/CaveatBrush-400.woff2
assets/         the five images
```

## The images (10)
Ten images across the document. The cutouts were lifted off their backgrounds so they sit *on* the paper instead
of arriving as white rectangles — the backdrop is masked only where it touches
the frame edge, then un-multiplied out of the edge pixels so no halo is left.

| file | where | treatment |
|---|---|---|
| `img_clown_hero.png` | P01 cover rail | cut from white |
| `img_jester_purple.png` | P01 cover rail | cut from the transparency checkerboard |
| `img_harlequin_queen.png` | P01 cover rail | chroma-keyed off flat magenta, then despilled |
| `img_notebook_hat.jpg` | P02, beneath the yellow note | kept whole, shown as a taped-in print |
| `img_harlequin_gothic.png` | P03, the naming layer | cut from white |
| `img_harlequin_axis.png` | P10, Wave M | cut from white |
| `img_protocol_notebook.jpg` | P12, the archive | kept whole — it *is* the protocol, WAVE_A→O |
| `img_book_cap.jpg` | P13, the sources | kept whole; printed 58mm because its source is only 640px |
| `img_hair_key.png` | P16, the seal | cut from white; a Craiyon watermark painted out first |
| `img_harlequin_red.png` | P16, the seal | cut from white |

To swap one: drop a new file in `assets/` and change the `src`.

## Two things were fixed while building
1. **The Story was being silently cut in half.** It overflowed its page by
   954px, and `overflow:hidden` on `.inner` hid the loss rather than showing
   it. Split across two pages (P14 + P15) and rebalanced 9/8 paragraphs; the
   seal and end page renumbered accordingly. Page count 17 → 18.
2. **Eight consecutive Wave spreads sat top-heavy**, each with half the page
   empty, which reads as unfinished rather than as breathing room. The two
   cards on each are now optically centred and carry a little more type.

Verified: 18 pages, A4 210×297 mm, no missing assets, no page overflowing,
Caveat Brush embedded from a real font file.

## Filename used for the export
`Almutairi_L_Assignment-2_Programmable-Mind-Unbroken-Reference_2026-09-05.pdf`
— APA-style: author, initial, title, ISO date. The archive-side alternative is
`CIRCUS-NB-HD5-IMPERIAL-A2-Programmable-Mind-Unbroken-Reference-v2.0.pdf`.


## Print resolution
Every image was checked against the size it actually prints at. The book
photograph came in at only 640px on its long edge; at the 96mm it was first
given, that is 180 dpi — visibly soft. There is no larger original, so it is
printed at 58mm instead, which its pixels genuinely support. Upscaling would
have invented detail that is not there.

| image | printed | source | effective |
|---|---|---|---|
| harlequin_red | 34mm | 1377px | 1032 dpi |
| jester_purple | 40mm | 1520px | 969 dpi |
| clown_hero | 40mm | 1473px | 929 dpi |
| harlequin_gothic | 47mm | 1600px | 861 dpi |
| harlequin_queen | 40mm | 1120px | 712 dpi |
| harlequin_axis | 38mm | 858px | 570 dpi |
| notebook_hat | 91mm | 1920px | 536 dpi |
| protocol_notebook | 119mm | 1920px | 411 dpi |
| hair_key | 23mm | 298px | 332 dpi |
| book_cap | 58mm | 640px | 312 dpi |

Nothing prints below 300 dpi. Export is 9.8 MB — well inside the 100 MB
budget, with the artwork carried losslessly rather than recompressed to save
space it did not need to save.
