/* Measured layout pass.
 *
 * The master pinned every sticker, polaroid and margin note at a hand-typed
 * mm offset. Those offsets were art-directed against a set of images that
 * never shipped; against the restored library they land on top of the words.
 *
 * Rather than re-art-direct the pages, this pass keeps each piece as close to
 * where the author put it as possible and only slides it to the NEAREST spot
 * where it clears all text. Occupancy is rasterised on a 2mm grid and
 * candidates are searched outward from the original position, biased to move a
 * piece down the page rather than sideways, which is how a scrapbook reads.
 * Size is reduced only when no clear position exists at full scale.
 *
 * Geometry note: a piece's visible box is its bounding box AFTER its rotation
 * (and any translate). Placement therefore solves for the bounding box, then
 * converts back to the `left`/`top` the element actually needs, so reapplying
 * the transform lands it exactly where it was solved for.
 */
import { chromium } from 'playwright-core';
import path from 'node:path';
import fs from 'node:fs';

const ROOT = process.argv[2];
const OUT  = process.argv[3];
const PX_MM = 96 / 25.4;

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1240, height: 1754 } });
await page.goto('file://' + path.resolve(ROOT, 'index.html'), { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.evaluate(async () => {
  await Promise.all([...document.images].map(i => i.complete ? 0 :
    new Promise(r => { i.addEventListener('load', r); i.addEventListener('error', r); })));
});
await page.waitForTimeout(400);

const plan = await page.evaluate((PX_MM) => {
  const CELL  = 2 * PX_MM;
  const GAP   = 2.4 * PX_MM;
  const BLEED = 5 * PX_MM;
  const out = { rules: [], notes: [] };

  document.querySelectorAll('.page').forEach((pg, pi) => {
    const sheet = pg.querySelector('.sheet');
    const S  = sheet.getBoundingClientRect();
    const cs0 = getComputedStyle(sheet);
    // absolutely positioned children resolve against the PADDING box
    const OX = S.left + parseFloat(cs0.borderLeftWidth);
    const OY = S.top  + parseFloat(cs0.borderTopWidth);
    const PW = S.width  - parseFloat(cs0.borderLeftWidth) - parseFloat(cs0.borderRightWidth);
    const PH = S.height - parseFloat(cs0.borderTopWidth)  - parseFloat(cs0.borderBottomWidth);
    const rel = r => ({ x: r.left - OX, y: r.top - OY, w: r.width, h: r.height });

    const isMovable = el =>
      (el.matches('img.st') || el.matches('.pola')) &&
      !el.closest('.hdr') &&
      parseFloat(getComputedStyle(el).opacity) > 0.25;

    // ---- obstacles ------------------------------------------------------
    // Painted from the client rects of the TEXT NODES themselves, not from
    // their containers. A paragraph that wraps a <b> is still a paragraph, and
    // container-based detection kept skipping exactly those — which is how a
    // margin note ended up sitting on a line of the conclusion.
    const obstacles = [];
    const textOnly = [];
    const skip = el => el.closest('.pola') || el.matches('.keylbl') ||
                       el.closest('.keylbl') || isMovable(el);
    const walker = document.createTreeWalker(sheet, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (!n.nodeValue.trim()) continue;
      const host = n.parentElement;
      if (!host || skip(host)) continue;
      const rng = document.createRange();
      rng.selectNodeContents(n);
      for (const r of rng.getClientRects()) {
        if (r.width < 1 || r.height < 1) continue;
        const rr = rel(r);
        obstacles.push(rr); textOnly.push(rr);
      }
    }
    // fixed furniture that carries no text of its own
    sheet.querySelectorAll('.bunt, .hdr, .ftr, svg, .note, .pola').forEach(el => {
      if (isMovable(el)) return;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      const rr = rel(r);
      obstacles.push(rr);
      if (el.matches('.note, .hdr, .ftr')) textOnly.push(rr);
    });

    const GW = Math.ceil(PW / CELL), GH = Math.ceil(PH / CELL);
    const grid = new Uint8Array(GW * GH);
    const textGrid = new Uint8Array(GW * GH);   // words only
    const paint = (b, pad) => {
      const x0 = Math.max(0, Math.floor((b.x - pad) / CELL));
      const x1 = Math.min(GW - 1, Math.ceil((b.x + b.w + pad) / CELL));
      const y0 = Math.max(0, Math.floor((b.y - pad) / CELL));
      const y1 = Math.min(GH - 1, Math.ceil((b.y + b.h + pad) / CELL));
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) grid[y * GW + x] = 1;
    };
    obstacles.forEach(o => paint(o, GAP * 0.5));
    const paintText = (b, pad) => {
      const x0 = Math.max(0, Math.floor((b.x - pad) / CELL));
      const x1 = Math.min(GW - 1, Math.ceil((b.x + b.w + pad) / CELL));
      const y0 = Math.max(0, Math.floor((b.y - pad) / CELL));
      const y1 = Math.min(GH - 1, Math.ceil((b.y + b.h + pad) / CELL));
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) textGrid[y * GW + x] = 1;
    };
    textOnly.forEach(o => paintText(o, GAP * 0.5));

    const free = (b) => {
      if (b.x < -BLEED || b.y < 0) return false;
      if (b.x + b.w > PW + BLEED) return false;
      if (b.y + b.h > PH) return false;
      const x0 = Math.max(0, Math.floor(b.x / CELL));
      const x1 = Math.min(GW - 1, Math.ceil((b.x + b.w) / CELL));
      const y0 = Math.max(0, Math.floor(b.y / CELL));
      const y1 = Math.min(GH - 1, Math.ceil((b.y + b.h) / CELL));
      for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++)
        if (grid[y * GW + x]) return false;
      return true;
    };

    const mkCand = (dxMax, dyUp, dyDn, upBias) => {
      const c = [];
      for (let dy = -dyUp; dy <= dyDn; dy += 2)
        for (let dx = -dxMax; dx <= dxMax; dx += 2)
          c.push([dx, dy, Math.abs(dy) * (dy < 0 ? upBias : 1) + Math.abs(dx) * 1.25]);
      c.sort((a, b) => a[2] - b[2]);
      return c;
    };
    const CAND   = mkCand(70, 60, 150, 1.9);
    const CAND_L = mkCand(105, 85, 190, 1.35);

    // measure each piece twice: with its transform, and without, so we know
    // exactly how far the transform displaces its bounding box
    const measure = el => {
      const prev = el.style.transform;
      const withT = rel(el.getBoundingClientRect());
      el.style.transform = 'none';
      const noT = rel(el.getBoundingClientRect());
      el.style.transform = prev;
      return { withT, noT, dx: withT.x - noT.x, dy: withT.y - noT.y };
    };

    const movables = [...sheet.querySelectorAll('[data-fx]')].filter(isMovable);
    const moved = new Map();

    movables.forEach(el => {
      const m = measure(el);
      const r0 = m.withT;
      let best = null;
      for (const scale of [1, .94, .88, .82, .76, .70, .64, .58]) {
        const w = r0.w * scale, h = r0.h * scale;
        const bx = r0.x + (r0.w - w) / 2, by = r0.y + (r0.h - h) / 2;
        for (const [dx, dy] of CAND) {
          const cand = { x: bx + dx * PX_MM, y: by + dy * PX_MM, w, h };
          if (free(cand)) { best = { cand, scale }; break; }
        }
        if (best) break;
      }
      if (!best) { out.notes.push(`p${pi + 1} fx${el.dataset.fx}: no clear position`); return; }
      paint(best.cand, GAP * 0.45);
      moved.set(el.dataset.fx, { from: r0, to: best.cand });

      // convert the solved bounding box back into the element's own left/top
      const left = best.cand.x - m.dx * best.scale;
      const top  = best.cand.y - m.dy * best.scale;
      const decl = [
        `top:${(top / PX_MM).toFixed(2)}mm`, `bottom:auto`,
        `left:${(left / PX_MM).toFixed(2)}mm`, `right:auto`,
      ];
      if (best.scale !== 1) {
        const bw = (el.matches('img') ? el.clientWidth : el.offsetWidth) * best.scale;
        decl.push(`width:${(bw / PX_MM).toFixed(2)}mm`);
        if (el.matches('img')) decl.push('height:auto');
      }
      out.rules.push(`[data-fx="${el.dataset.fx}"]{` +
        decl.map(d => d + ' !important').join(';') + `}`);
    });

    // ---- margin notes follow the piece they annotate --------------------
    sheet.querySelectorAll('.keylbl[data-fx]').forEach(lb => {
      const m = measure(lb);
      const r0 = m.withT;
      let near = null, bestD = 1e9;
      moved.forEach(p => {
        const d = Math.hypot(p.from.x + p.from.w / 2 - (r0.x + r0.w / 2),
                             p.from.y + p.from.h / 2 - (r0.y + r0.h / 2));
        if (d < bestD) { bestD = d; near = p; }
      });
      const start = { ...r0 };
      if (near && bestD < 95 * PX_MM) {
        start.x += near.to.x - near.from.x;
        start.y += near.to.y - near.from.y;
      }
      let put = null;
      for (const [dx, dy] of CAND_L) {
        const c = { x: start.x + dx * PX_MM, y: start.y + dy * PX_MM, w: r0.w, h: r0.h };
        if (free(c)) { put = c; break; }
      }
      if (!put) {
        // last resort: open paper has run out, so let the note rest on a
        // sticker. It still may not touch a word.
        const freeOfText = (b) => {
          if (b.x < 0 || b.y < 0 || b.x + b.w > PW || b.y + b.h > PH) return false;
          const x0 = Math.max(0, Math.floor(b.x / CELL));
          const x1 = Math.min(GW - 1, Math.ceil((b.x + b.w) / CELL));
          const y0 = Math.max(0, Math.floor(b.y / CELL));
          const y1 = Math.min(GH - 1, Math.ceil((b.y + b.h) / CELL));
          for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++)
            if (textGrid[y * GW + x]) return false;
          return true;
        };
        for (const [dx, dy] of CAND_L) {
          const c = { x: start.x + dx * PX_MM, y: start.y + dy * PX_MM, w: r0.w, h: r0.h };
          if (freeOfText(c)) { put = c; break; }
        }
        if (put) out.notes.push(`p${pi + 1} label fx${lb.dataset.fx}: resting on imagery`);
      }
      if (!put) { out.notes.push(`p${pi + 1} label fx${lb.dataset.fx}: NO POSITION`); return; }
      paint(put, GAP * 0.3);
      out.rules.push(`[data-fx="${lb.dataset.fx}"]{` + [
        `top:${((put.y - m.dy) / PX_MM).toFixed(2)}mm`, `bottom:auto`,
        `left:${((put.x - m.dx) / PX_MM).toFixed(2)}mm`, `right:auto`,
      ].map(d => d + ' !important').join(';') + `}`);
    });
  });
  return out;
}, PX_MM);

fs.writeFileSync(OUT,
  "/* GENERATED by tools/layout.mjs — measured placement corrections.\n" +
  "   Every pasted piece keeps the author's position unless it landed on text;\n" +
  "   then it slides to the nearest clear spot. Do not hand-edit. */\n" +
  plan.rules.join("\n") + "\n");
console.log(`layout rules: ${plan.rules.length}`);
plan.notes.forEach(n => console.log("  ! " + n));
await browser.close();
