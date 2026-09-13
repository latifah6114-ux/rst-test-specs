/* Strict verification: no text may be covered, clipped, or pushed off-sheet. */
import { chromium } from 'playwright-core';
import path from 'node:path';

const ROOT = process.argv[2];
const PX_MM = 96 / 25.4;
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1240, height: 1754 } });
await page.goto('file://' + path.resolve(ROOT, 'index.html'), { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.evaluate(async () => {
  await Promise.all([...document.images].map(i => i.complete ? 0 :
    new Promise(r => { i.addEventListener('load', r); i.addEventListener('error', r); })));
});
await page.waitForTimeout(500);

const report = await page.evaluate((PX_MM) => {
  const issues = [];
  const overlap = (a, b, tol = 2) =>
    a.left < b.right - tol && b.left < a.right - tol &&
    a.top < b.bottom - tol && b.top < a.bottom - tol;

  document.querySelectorAll('.page').forEach((pg, pi) => {
    const n = pi + 1;
    const sheet = pg.querySelector('.sheet');
    const S = sheet.getBoundingClientRect();
    const cs = getComputedStyle(sheet);
    const inner = {
      left: S.left + parseFloat(cs.borderLeftWidth),
      right: S.right - parseFloat(cs.borderRightWidth),
      top: S.top + parseFloat(cs.borderTopWidth),
      bottom: S.bottom - parseFloat(cs.borderBottomWidth),
    };

    // every line of text on the page
    const lines = [];
    const w = document.createTreeWalker(sheet, NodeFilter.SHOW_TEXT);
    for (let t = w.nextNode(); t; t = w.nextNode()) {
      if (!t.nodeValue.trim()) continue;
      // a margin note carries its own opaque tag and paints above the
      // stickers, so it is not "covered" when one sits beneath it
      if (t.parentElement && t.parentElement.closest('.keylbl')) continue;
      const r = document.createRange(); r.selectNodeContents(t);
      for (const cr of r.getClientRects())
        if (cr.width > 1 && cr.height > 1)
          lines.push({ rect: cr, text: t.nodeValue.trim().slice(0, 42),
                       host: t.parentElement });
    }

    // 1. text escaping the sheet (the master clipped silently via overflow:hidden)
    lines.forEach(L => {
      if (L.rect.bottom > inner.bottom + 1 || L.rect.top < inner.top - 1 ||
          L.rect.right > inner.right + 1 || L.rect.left < inner.left - 1)
        issues.push(`p${n} TEXT OUTSIDE SHEET: "${L.text}"`);
    });

    // 2. imagery sitting on words
    const pieces = [...sheet.querySelectorAll('img.st, .pola, .keylbl')]
      .filter(e => !e.closest('.hdr'))
      .filter(e => parseFloat(getComputedStyle(e).opacity) > 0.25);
    pieces.forEach(p => {
      const pr = p.getBoundingClientRect();
      lines.forEach(L => {
        if (p.contains(L.host)) return;
        if (overlap(pr, L.rect, 3))
          issues.push(`p${n} ${p.className || p.tagName} COVERS TEXT: "${L.text}"`);
      });
    });

    // 3. imagery escaping the sheet
    pieces.forEach(p => {
      const r = p.getBoundingClientRect();
      if (r.bottom > inner.bottom + 1 || r.top < inner.top - 1 ||
          r.right > inner.right + 1 || r.left < inner.left - 1)
        issues.push(`p${n} PIECE OUTSIDE SHEET: ${p.dataset.fx} ${p.className}`);
    });

    // 4. pieces colliding with each other
    for (let i = 0; i < pieces.length; i++)
      for (let j = i + 1; j < pieces.length; j++) {
        const a = pieces[i].getBoundingClientRect(), b = pieces[j].getBoundingClientRect();
        // a note deliberately resting on a sticker is allowed
        const noteOnPiece = pieces[i].matches('.keylbl') !== pieces[j].matches('.keylbl');
        if (!noteOnPiece && overlap(a, b, 4))
          issues.push(`p${n} PIECES OVERLAP: ${pieces[i].dataset.fx} / ${pieces[j].dataset.fx}`);
      }
  });

  // 5. missing assets
  document.querySelectorAll('img').forEach(i => {
    if (i.naturalWidth === 0) issues.push(`MISSING ASSET: ${i.getAttribute('src')}`);
  });
  return issues;
}, PX_MM);

if (!report.length) console.log("VERIFY: clean — no covered text, no clipping, no collisions.");
else { console.log(`VERIFY: ${report.length} issue(s)`); report.forEach(r => console.log("  " + r)); }
await browser.close();
