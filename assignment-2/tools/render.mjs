/* Render the final PDF, plus per-page PNGs for visual inspection, and report
   any page whose content overflows its sheet (the original clipped silently). */
import { chromium } from 'playwright-core';
import path from 'node:path';
import fs from 'node:fs';

const root  = process.argv[2];
const pdfTo = process.argv[3];
const shots = process.argv[4] || null;

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--no-sandbox', '--font-render-hinting=none', '--disable-lcd-text'],
});
const page = await browser.newPage({ viewport: { width: 1240, height: 1754 }, deviceScaleFactor: 2 });
await page.goto('file://' + path.resolve(root, 'index.html'), { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.evaluate(async () => {
  await Promise.all([...document.images].map(i => i.complete ? 0 :
    new Promise(r => { i.addEventListener('load', r); i.addEventListener('error', r); })));
});
await page.waitForTimeout(600);

// ---- diagnostics: overflow, missing assets, font resolution --------------
const diag = await page.evaluate(() => {
  const out = { pages: [], missing: [], fonts: {} };
  document.querySelectorAll('.page').forEach((p, i) => {
    const s = p.querySelector('.sheet');
    const kids = [...s.children];
    let low = 0;
    kids.forEach(k => {
      const r = k.getBoundingClientRect(), sr = s.getBoundingClientRect();
      low = Math.max(low, r.bottom - sr.top);
    });
    const cs = getComputedStyle(s);
    const padB = parseFloat(cs.paddingBottom);
    const avail = s.clientHeight - padB;
    out.pages.push({
      n: i + 1,
      lead: [...p.classList].find(c => c.startsWith('lead-')),
      contentPx: Math.round(low),
      availPx: Math.round(s.getBoundingClientRect().height - padB),
      scrollOver: Math.round(s.scrollHeight - s.clientHeight),
    });
  });
  document.querySelectorAll('img').forEach(i => {
    if (i.naturalWidth === 0) out.missing.push(i.getAttribute('src'));
  });
  const probe = (fam, wt) => {
    const d = document.createElement('span');
    d.style.cssText = `font-family:${fam};font-weight:${wt};font-size:80px;position:absolute;visibility:hidden`;
    d.textContent = 'Handwriting 123';
    document.body.appendChild(d);
    const w = d.getBoundingClientRect().width; d.remove(); return Math.round(w);
  };
  out.fonts = { kalam400: probe("'Kalam'", 400), kalam700: probe("'Kalam'", 700),
                caveat700: probe("'Caveat'", 700), cursive: probe('cursive', 400) };
  return out;
});
console.log(JSON.stringify(diag, null, 1));

await page.pdf({ path: pdfTo, format: 'A4', printBackground: true,
                 margin: { top: 0, right: 0, bottom: 0, left: 0 }, preferCSSPageSize: true });

if (shots) {
  fs.mkdirSync(shots, { recursive: true });
  const els = await page.$$('.page');
  for (let i = 0; i < els.length; i++) {
    await els[i].screenshot({ path: path.join(shots, `p${String(i + 1).padStart(2, '0')}.png`) });
  }
}
await browser.close();
