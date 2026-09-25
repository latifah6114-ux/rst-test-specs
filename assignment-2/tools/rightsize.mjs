/* Report the largest printed width, in mm, that each asset is actually used
   at, so the library can be resampled to exactly what 300dpi needs. */
import { chromium } from 'playwright-core';
import path from 'node:path';
import fs from 'node:fs';
const ROOT = process.argv[2];
const b = await chromium.launch({ executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args:['--no-sandbox']});
const p = await b.newPage({ viewport:{width:1240,height:1754} });
await p.goto('file://' + path.resolve(ROOT,'index.html'), {waitUntil:'load'});
await p.evaluate(()=>document.fonts.ready);
await p.evaluate(async()=>{await Promise.all([...document.images].map(i=>i.complete?0:new Promise(r=>{i.addEventListener('load',r);i.addEventListener('error',r);})));});
await p.waitForTimeout(400);
const used = await p.evaluate(()=>{
  const PX_MM = 96/25.4, out = {};
  document.querySelectorAll('img').forEach(i=>{
    const src = i.getAttribute('src').split('/').pop();
    const r = i.getBoundingClientRect();
    const mm = Math.max(r.width, r.height)/PX_MM;
    out[src] = Math.max(out[src]||0, mm);
  });
  return out;
});
fs.writeFileSync(process.argv[3], JSON.stringify(used,null,1));
console.log(Object.keys(used).length, 'assets measured');
await b.close();
