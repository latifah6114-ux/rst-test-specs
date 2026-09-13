/* Build the reading edition: the writing of Assignment 2, nothing else.
 *
 * The master is a fixed 14-page scrapbook in which the prose sits alongside
 * pasted imagery, margin annotations and per-page running furniture. This pass
 * walks the real rendered DOM and lifts out only the writing, in document
 * order, so nothing depends on parsing the markup by hand.
 *
 * DROPPED, and why:
 *   img / .st / .pola  — the imagery itself
 *   .keylbl, .pola .cap— captions for that imagery; orphaned without it
 *   svg                — the bunting and the journey map are drawings
 *   .hdr / .ftr        — per-page furniture, reinstated as a proper running
 *                        head and foot with real page numbers
 * Every other character the author wrote is carried across untouched.
 */
import { chromium } from 'playwright-core';
import path from 'node:path';
import fs from 'node:fs';

const MASTER = process.argv[2];
const OUT    = process.argv[3];

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--no-sandbox'] });
const page = await browser.newPage();
await page.goto('file://' + path.resolve(MASTER), { waitUntil: 'domcontentloaded' });

const blocks = await page.evaluate(() => {
  const out = [];
  const keepInline = el => {
    // preserve the author's emphasis and marked passages
    const html = el.innerHTML;
    return html
      .replace(/<span class="hk ([a-z])"[^>]*>/g, '<mark class="hk-$1">')
      .replace(/<\/span>/g, '</mark>')
      .replace(/<br\s*\/?>/g, '<br>');
  };

  document.querySelectorAll('.page').forEach((pg, pi) => {
    const sheet = pg.querySelector('.sheet').cloneNode(true);
    sheet.querySelectorAll('img, svg, .st, .pola, .keylbl, .hdr, .ftr').forEach(n => n.remove());

    const walk = (node) => {
      for (const el of node.children) {
        if (!el.textContent || !el.textContent.trim()) continue;

        if (el.matches('h1.t'))  { out.push({ t: 'h1', html: keepInline(el), page: pi + 1 }); continue; }
        if (el.matches('h2.s'))  { out.push({ t: 'h2', html: keepInline(el) }); continue; }
        if (el.matches('p'))     { out.push({ t: 'p', html: keepInline(el),
                                              small: el.classList.contains('small'),
                                              centre: /text-align:\s*center/.test(el.getAttribute('style')||'') }); continue; }
        if (el.matches('ul'))    { out.push({ t: 'ul', items: [...el.querySelectorAll('li')].map(li => li.innerHTML) }); continue; }
        if (el.matches('.note')) {
          out.push({ t: 'note',
                     h: el.querySelector('h3')?.textContent.trim() || '',
                     p: el.querySelector('p')?.innerHTML || '' });
          continue;
        }
        if (el.matches('.goalbox')) { out.push({ t: 'box-open' }); walk(el); out.push({ t: 'box-close' }); continue; }
        if (el.matches('.twocol')) {
          const cols = [...el.children].map(c => { const s = []; 
            const save = out.length; walk(c); cols_push(out, save, s); return s; });
          continue;
        }
        if (el.matches('.ribbon') || el.querySelector(':scope > .ribbon')) {
          const r = el.matches('.ribbon') ? el : el.querySelector(':scope > .ribbon');
          out.push({ t: 'ribbon', html: r.textContent.trim() }); continue;
        }
        if (el.matches('.sig')) { out.push({ t: 'sig', html: el.textContent.trim() }); continue; }

        // a bare div: either a wrapper, or a line of display text
        const blockKids = [...el.children].some(c =>
          getComputedStyle(c).display !== 'inline' && c.textContent.trim());
        if (blockKids) { walk(el); continue; }

        // the sheet is a detached clone, so computed styles are unreliable —
        // read the author's own inline declaration instead
        const style = el.getAttribute('style') || '';
        const fs  = parseFloat((style.match(/font-size:\s*([\d.]+)px/) || [])[1] || '0');
        const fam = (style.match(/font-family:\s*'([^']+)'/) || [])[1] || '';
        const txt = el.textContent.trim();

        // a caption for the journey map, which is a drawing and has been dropped
        if (/^—\s*the map of the journey\s*—$/.test(txt)) continue;

        if (fs >= 40)                       out.push({ t: 'display', html: txt });
        else if (el.classList.contains('small'))
                                            out.push({ t: 'eyebrow', html: txt });
        else if (/Caveat/.test(fam))        out.push({ t: 'byline', html: txt });
        else                                out.push({ t: 'p', html: keepInline(el), centre: true });
      }
    };
    function cols_push(){}
    walk(sheet);
  });
  return out;
});

await browser.close();
fs.writeFileSync(OUT, JSON.stringify(blocks, null, 1));
console.log(`lifted ${blocks.length} blocks`);
console.log(Object.entries(blocks.reduce((a,b)=>(a[b.t]=(a[b.t]||0)+1,a),{}))
  .map(([k,v])=>`${k}:${v}`).join('  '));
