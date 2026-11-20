// 메타 광고 라이브러리(KR)에서 키워드별 '게재 중' 광고를 노출 많은 순으로 긁는다.
// 사용: node scripts/scrape-library.mjs [키워드...]   결과: data/library-raw.json
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire('/Users/daun/.local/node/lib/node_modules/@playwright/mcp/');
const { chromium } = require('playwright');
const cfg = JSON.parse(fs.readFileSync(new URL('../config.json', import.meta.url)));
const queries = process.argv.slice(2).length ? process.argv.slice(2) : cfg.queries.map(q => q.q);
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const ctx = await browser.newContext({ locale: 'ko-KR', userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36', viewport: { width: 1400, height: 1000 } });
const page = await ctx.newPage();
const out = [];
for (const q of queries) {
  const url = 'https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=KR&q=' + encodeURIComponent(q) + '&search_type=keyword_unordered&media_type=all&sort_data[mode]=total_impressions&sort_data[direction]=desc';
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(6000);
    for (let i = 0; i < cfg.scrolls; i++) { await page.mouse.wheel(0, 6000); await page.waitForTimeout(1300); }
    const cards = await page.evaluate(() => {
      const res = [];
      const els = [...document.querySelectorAll('span,div')].filter(e => e.childElementCount === 0 && /^(라이브러리 ID|Library ID):\s*\d+/.test(e.textContent.trim()));
      for (const e of els) {
        let c = e;
        for (let k = 0; k < 15; k++) { c = c.parentElement; if (!c) break; if (/(광고 상세 정보 보기|요약 세부 사항 보기|See ad details|See summary details)/.test(c.innerText) && c.querySelector('img,video') && c.innerText.length > 80) break; }
        if (!c) continue;
        const t = c.innerText; const vid = c.querySelector('video');
        const imgs = [...c.querySelectorAll('img')].filter(i => i.naturalWidth > 200).map(i => i.src).slice(0, 4);
        const sm = t.match(/(\d{4})\. (\d+)\. (\d+)\.에 게재 시작/) || t.match(/Started running on (\w+ \d+, \d{4})/);
        res.push({ id: e.textContent.match(/\d+/)[0], start: sm ? (sm[1].length === 4 && sm[2] ? `${sm[1]}-${String(sm[2]).padStart(2,'0')}-${String(sm[3]).padStart(2,'0')}` : new Date(sm[1]).toISOString().slice(0,10)) : null,
          multi: +((t.match(/광고 (\d+)개에서/) || t.match(/(\d+) ads use this/) || [0, 1])[1]),
          low: /노출수가 적음|Low impression/.test(t), dur: (t.match(/0:00 \/ (\d+:\d+)/) || [])[1] || '',
          video: vid ? (vid.src || '') : '', poster: vid ? vid.poster : '', imgs,
          text: t.split(/광고 상세 정보 보기|요약 세부 사항 보기|See ad details|See summary details/).pop().slice(0, 500) });
      }
      return res;
    });
    cards.forEach((c, i) => { c.q = q; c.rank = i + 1; out.push(c); });
    console.log(q, cards.length);
  } catch (e) { console.log(q, 'ERR', e.message.slice(0, 120)); }
}
await browser.close();
// 11/5: 아침에 인터넷이 아직 안 붙어 0건이면 어제 레퍼런스를 0건으로 덮어써 사이트가 텅 비었음 → 0건이면 저장 안 함
if (out.length === 0) { console.log('수집 0건 — 어제 목록 유지(저장 안 함)'); await browser.close(); process.exit(2); }
fs.writeFileSync(new URL('../data/library-raw.json', import.meta.url), JSON.stringify(out));
