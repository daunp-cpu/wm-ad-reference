// 검색창 실시간 수집 (2026-11-11 다운 "검색 결과는 최대한 많이, 관련된 거, 집행 중인 거, 실시간으로 다").
// 사용: node scripts/libsearch.mjs <출력.json> <검색어> [비슷한 말...]
// 메타 광고 라이브러리(KR) '게재 중'·노출 많은 순을 검색어마다 동시에(탭 여러 개) 긁고, 새 카드가 안 늘 때까지 스크롤(검색어당 최대 300개).
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire('/Users/daun/.local/node/lib/node_modules/@playwright/mcp/');
const { chromium } = require('playwright');
const [outFile, ...qs] = process.argv.slice(2);
const MAX = 300, MAXSCROLL = 30;
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'] });
const ctx = await browser.newContext({ locale: 'ko-KR', userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36', viewport: { width: 1400, height: 1000 } });
const grab = () => {
  const res = [];
  const els = [...document.querySelectorAll('span,div')].filter(e => e.childElementCount === 0 && /^(라이브러리 ID|Library ID):\s*\d+/.test(e.textContent.trim()));
  for (const e of els) {
    let c = e;
    for (let k = 0; k < 15; k++) { c = c.parentElement; if (!c) break; if (/(광고 상세 정보 보기|요약 세부 사항 보기|See ad details|See summary details)/.test(c.innerText) && c.querySelector('img,video') && c.innerText.length > 80) break; }
    if (!c) continue;
    const t = c.innerText; const vid = c.querySelector('video');
    const imgs = [...c.querySelectorAll('img')].filter(i => i.naturalWidth > 200).map(i => i.src).slice(0, 4);
    const sm = t.match(/(\d{4})\. (\d+)\. (\d+)\.에 게재 시작/);
    res.push({ id: e.textContent.match(/\d+/)[0], start: sm ? `${sm[1]}-${String(sm[2]).padStart(2, '0')}-${String(sm[3]).padStart(2, '0')}` : null,
      multi: +((t.match(/광고 (\d+)개에서/) || [0, 1])[1]), low: /노출수가 적음|Low impression/.test(t), dur: (t.match(/0:00 \/ (\d+:\d+)/) || [])[1] || '',
      video: vid ? (vid.src || '') : '', poster: vid ? vid.poster : '', imgs,
      text: t.split(/광고 상세 정보 보기|요약 세부 사항 보기|See ad details|See summary details/).pop().slice(0, 600) });
  }
  return res;
};
// 로그인 없이는 한 번에 30개까지만 보임 → 같은 검색어를 각도(전체·이미지만·영상만·정확히 일치·최신순)로 나눠 각각 30개씩 모음
const ANGLES = [['keyword_unordered', 'all', 'total_impressions'], ['keyword_unordered', 'image', 'total_impressions'], ['keyword_unordered', 'video', 'total_impressions'],
];   // 정확히 일치·최신순은 새 광고 0개라 뺌(11/11 실측)
async function one([q, [st, mt, so]]) {
  const page = await ctx.newPage();
  const url = 'https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=KR&q=' + encodeURIComponent(q) + `&search_type=${st}&media_type=${mt}` + (so === 'total_impressions' ? '&sort_data[mode]=total_impressions&sort_data[direction]=desc' : '');
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(5000);
    let last = -1, same = 0;
    for (let i = 0; i < MAXSCROLL; i++) {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await page.mouse.wheel(0, 4000); await page.waitForTimeout(2000);
      const n = await page.evaluate(() => document.body.innerText.split(/라이브러리 ID|Library ID/).length - 1);
      if (n >= MAX) break;
      if (n === last) { if (++same >= 4) break; await page.waitForTimeout(1500) } else same = 0;
      last = n;
    }
    const cards = await page.evaluate(grab);
    cards.forEach((c, i) => { c.q = q; c.rank = i + 1; c.ang = st[8] + mt[0] + so[0] });
    console.log(q, st, mt, so, cards.length); return cards.slice(0, MAX);
  } catch (e) { console.log(q, 'ERR', e.message.slice(0, 120)); return [] }
  finally { await page.close() }
}
const tasks = qs.flatMap(q => ANGLES.map(a => [q, a]));
const all = []; let ti = 0;   // 탭 8개씩 동시에
await Promise.all(Array.from({ length: 8 }, async () => { while (ti < tasks.length) { const t = tasks[ti++]; all.push(...(await one(t)).map(c => ({ ...c, _o: tasks.indexOf(t) }))) } }));
all.sort((a, b) => a._o - b._o || a.rank - b.rank);
await browser.close();
const today = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
const seen = new Map(), dupText = new Set();
for (const c of all) {   // 같은 광고(id)·같은 문구 중복 제거, 첫 검색어 결과가 앞
  if (seen.has(c.id)) continue;
  const k = c.text.replace(/\s+/g, ' ').slice(0, 80); if (dupText.has(k)) continue; dupText.add(k);
  c.days = c.start ? Math.round((Date.parse(today) - Date.parse(c.start)) / 864e5) : null;
  c.page = (c.text.split(/\n/).map(x => x.trim()).find(x => x && x !== '광고') || '').replace(/\s*페이지는 .*함께합니다$/, '').slice(0, 40);
  seen.set(c.id, c);
}
// 메타 한국어 검색은 느슨해서 무관한 광고가 섞임 → 문구에 검색어(비슷한 말 포함)가 실제로 있는 광고를 앞으로, 그 안에선 오래 집행된 순
const terms = qs.map(x => x.toLowerCase());
const main = terms[0].replace(/\s+/g, '');
const ads = [...seen.values()].map(c => { const tx = c.text.toLowerCase(); return { ...c, hit: terms.some(t => tx.includes(t)), main: tx.replace(/\s+/g, '').includes(main) } })
  .sort((a, b) => (b.main - a.main) || (b.hit - a.hit) || ((b.days || 0) - (a.days || 0)));   // 검색어 그대로 → 비슷한 말 → 나머지, 그 안에선 오래 집행된 순
ads.forEach(c => { delete c._o });
fs.writeFileSync(outFile, JSON.stringify({ state: 'done', q: qs[0], qs, at: Date.now(), n: ads.length, hit: ads.filter(c => c.hit).length, ads }));
console.log('합계', ads.length);
