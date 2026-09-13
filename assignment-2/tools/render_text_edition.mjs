/* Export the reading edition, with a real running foot carrying page numbers. */
import { chromium } from 'playwright-core';
import path from 'node:path';
const ROOT = process.argv[2], OUT = process.argv[3];
const b = await chromium.launch({
  executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args:['--no-sandbox']});
const p = await b.newPage({ viewport:{width:1240,height:1754} });
await p.goto('file://'+path.resolve(ROOT,'text-edition.html'), {waitUntil:'load'});
await p.evaluate(()=>document.fonts.ready);
await p.waitForTimeout(400);

const foot = `
<style>
  @font-face{font-family:'FootSerif';src:local('Georgia'),local('Times New Roman');}
  div{ font-family:Georgia,'Times New Roman',serif; font-size:8px; color:#8a8faa;
       width:100%; padding:0 24mm; display:flex; justify-content:space-between;
       letter-spacing:.04em; }
  .l{ font-style:italic; }
</style>
<div>
  <span class="l">Assignment 2 &middot; Latifah Almutairi &middot; Leader Shadi</span>
  <span class="pageNumber"></span>
</div>`;

await p.pdf({ path: OUT, format:'A4', printBackground:true,
  displayHeaderFooter:true, headerTemplate:'<span></span>', footerTemplate:foot,
  margin:{ top:'26mm', right:'0mm', bottom:'18mm', left:'0mm' },
  preferCSSPageSize:false });
await b.close();
console.log('exported', OUT);
