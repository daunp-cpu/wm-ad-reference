// 복각 요청 받기: POST {items:[{id,...}]} → Blob jobs/<시각>.json 저장(맥 작업기가 3분마다 가져가 처리)
// GET → 대기 중·처리 중 요청 목록(페이지 상태 표시용)
import { put, list, get, del } from '@vercel/blob';
import crypto from 'crypto';
// 검색창 실시간 수집(2026-11-11): 검색어 → Blob ls/<키>.json (맥 작업기가 메타 광고 라이브러리에서 긁어 올림)
const lsKey = q => crypto.createHash('sha1').update(String(q).trim().toLowerCase()).digest('hex').slice(0, 16);
let LSC = new Map();
// 별표(2026-11-11): Blob stars.json = {레퍼런스id: {by, at, meta}} — 팀장님이 찍으면 다들 보고 복각
let STC = { at: 0, b: null };
// 2026-11-11 고침: 처음엔 stars.json 한 파일을 통째로 덮어썼는데, 덮어쓴 직후 옛 내용이 읽히는 때가 있어 별표가 몇 초 뒤 사라지고
// 다음 사람이 찍으면 옛 내용 위에 저장돼 앞사람 별표가 지워졌음(화영 신고) → 별표 하나 = Blob star/<id>.json 파일 하나(덮어쓰기 없음)
let STJ = new Map();
async function starsGet() {
  const out = {}; const bl = (await list({ prefix: 'star/', token: T, limit: 1000 })).blobs;
  await Promise.all(bl.map(async b => { const ck = b.pathname + '|' + b.uploadedAt; let v = STJ.get(ck);
    if (!v) { try { const r = await get(b.pathname, { access: 'private', token: T }); v = JSON.parse(await new Response(r.stream).text()); STJ.set(ck, v) } catch (e) { return } }
    out[b.pathname.slice(5, -5)] = v }));
  if (STJ.size > 2000) STJ = new Map([...STJ].slice(-500));
  return out;
}
async function lsGet(k) { try { const r = await get(`ls/${k}.json`, { access: 'private', token: T }); if (r) return JSON.parse(await new Response(r.stream).text()) } catch (e) {} return null }
const WHO = ['화영', '다운', '도현', '근형', '형태'];
let CACHE = { at: 0, body: null, ttl: 5000 };
let ZC = { at: 0, body: null };
let JOBC = new Map();   // 요청 파일 내용(한 번 올라가면 안 바뀜) — 목록 볼 때마다 파일마다 get 하던 것 줄이기(2026-10-21)
const BRAND_OK = ['SOOO', 'FnL', '칸디데'];   // 2026-11-10 브랜드(업체) — data/brands.json 키와 같게
const brandOf = b => BRAND_OK.includes(b) ? b : 'SOOO';
const pickAssets = body => (Array.isArray(body.assets) ? body.assets : []).slice(0, 10).filter(x => x && /^[a-z0-9]{8,32}$/.test(x.up || '') && +x.n >= 1 && +x.n <= 80 && /^(jpg|jpeg|png|webp|gif|heic|mp4|mov|m4v|webm|pdf|txt|md|doc|docx|rtf|pptx)$/.test(String(x.ext || '').toLowerCase()))
  .map(x => ({ up: x.up, n: +x.n, ext: String(x.ext).toLowerCase(), kind: ['video', 'image', 'doc', 'audio'].includes(x.kind) ? x.kind : 'image', name: String(x.name || '').slice(0, 60) }));   // '쓸 에셋' 목록 검사   // 진행 상황 답 5초 재사용(Blob 호출 수 줄이기 — 무료 한도 초과로 정지됐던 원인)   // 이름 필수(누가 만들었는지)
const T = process.env.BLOB_READ_WRITE_TOKEN;
export default async function handler(req, res) {
  try {
    if (req.method === 'POST') {
      CACHE.at = 0;
      const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
      const ts = new Date().toISOString().replace(/[:.]/g, '-');
      const okKey = /^\d{4}-\d{2}-\d{2}$/.test(body.date || '') && /^\d{3}$/.test(body.no || '');
      if (body.type === 'star') {   // 별표 찍기/빼기
        const id = String(body.id || ''); if (!/^\d{1,25}$/.test(id)) return res.status(400).json({ ok: false, msg: '레퍼런스 id 오류' });
        if (!WHO.includes(body.by)) return res.status(400).json({ ok: false, msg: '이름을 골라주세요' });
        if (body.on) {
          const m = body.meta && typeof body.meta === 'object' ? body.meta : {}; const str = (v, n) => typeof v === 'string' ? v.slice(0, n) : '';
          const v = { by: body.by, at: Date.now(), meta: { page: str(m.page, 80), t: str(m.t, 600), dur: str(m.dur, 10), days: typeof m.days === 'number' || typeof m.days === 'string' ? m.days : '', poster: str(m.poster, 1500), imgs: (Array.isArray(m.imgs) ? m.imgs : []).slice(-2).map(x => str(x, 1500)), video: str(m.video, 1500), img: str(m.img, 300) } };
          await put(`star/${id}.json`, JSON.stringify(v), { access: 'private', token: T, addRandomSuffix: false, allowOverwrite: true, contentType: 'application/json' });
        } else { try { await del(`star/${id}.json`, { token: T }) } catch (e) {} }
        const S = await starsGet(); if (body.on) S[id] = S[id] || { by: body.by, at: Date.now() }; else delete S[id];   // 방금 쓴 건 목록 반영이 늦어도 확실히
        STC = { at: Date.now(), b: { ok: true, stars: S } }; return res.status(200).json(STC.b);
      }
      if (body.type === 'slacksync') {   // 소재공유방 새로고침 버튼(2026-11-12): 하루 1번 자동 + 필요할 때 누르면 맥 작업기가 슬랙 새 글을 가져옴
        if (!WHO.includes(body.by)) return res.status(400).json({ ok: false, msg: '이름을 골라주세요' });
        if (global.__SSY && Date.now() - global.__SSY < 3 * 60e3) return res.status(200).json({ ok: true, cached: true });
        global.__SSY = Date.now();
        await put(`jobs/${ts}.json`, JSON.stringify({ type: 'slacksync', by: body.by, requested: new Date().toISOString() }), { access: 'private', token: T, addRandomSuffix: false, allowOverwrite: true, contentType: 'application/json' });
        return res.status(200).json({ ok: true, job: ts });
      }
      if (body.type === 'libsearch') {   // 검색어로 메타 광고 라이브러리 '지금 집행 중' 광고 바로 수집
        const q = String(body.q || '').trim().slice(0, 40); if (q.length < 1) return res.status(400).json({ ok: false, msg: '검색어를 넣어주세요' });
        const terms = [q, ...(Array.isArray(body.terms) ? body.terms : [])].map(x => String(x || '').trim().slice(0, 40)).filter((x, i, a) => x && a.indexOf(x) === i).slice(0, 8);
        const k = lsKey(q), cur = await lsGet(k);
        const fresh = cur && ((cur.state === 'done' && Date.now() - cur.at < 30 * 60e3) || ((cur.state === 'pending' || cur.state === 'running') && Date.now() - (cur.req || cur.at) < 8 * 60e3));
        if (fresh && !body.force) return res.status(200).json({ ok: true, key: k, cached: true });
        await put(`ls/${k}.json`, JSON.stringify({ state: 'pending', q, terms, req: Date.now(), at: Date.now() }), { access: 'private', token: T, addRandomSuffix: false, allowOverwrite: true, contentType: 'application/json' });
        await put(`jobs/${ts}.json`, JSON.stringify({ type: 'libsearch', requested: new Date().toISOString(), q, terms, key: k }), { access: 'private', token: T, addRandomSuffix: false, allowOverwrite: true, contentType: 'application/json' });
        LSC.delete(k); return res.status(200).json({ ok: true, key: k, job: ts });
      }
      if (body.type === 'setup' || body.type === 'status') {   // 세팅하기 / ON·OFF
        if (!okKey) return res.status(400).json({ ok: false, msg: '잘못된 요청' });
        const pick = ['by', 'date', 'no', 'on', 'account', 'campaign_id', 'adset_id', 'new_campaign', 'copy_campaign', 'new_adset', 'copy_adset', 'budget'];
        const job = { type: body.type, requested: new Date().toISOString() }; pick.forEach(k => { if (body[k] !== undefined && body[k] !== '') job[k] = body[k] });
        if (body.type === 'setup' && !WHO.includes(body.by)) return res.status(400).json({ ok: false, msg: '담당자를 골라주세요' });
        if (body.type === 'setup') {   // 확인 창에서 고친 값(이름·링크·제목·설명·본문·AI 기능·버전)
          const lim = { ad_name: 200, link: 1000, title: 255, desc: 255, body: 3000 };
          Object.entries(lim).forEach(([k, n]) => { if (typeof body[k] === 'string' && body[k].trim()) job[k] = body[k].trim().slice(0, n) });
          if (job.link && !/^https:\/\/sooo\.kr\//.test(job.link)) return res.status(400).json({ ok: false, msg: '링크는 https://sooo.kr/ 로 시작해야 해요' });
          if (+body.version >= 1) job.version = +body.version;
          if (/^\d{5,20}$/.test(body.page_id || '')) job.page_id = body.page_id;
          if (body.ig_id === '' || /^\d{5,20}$/.test(body.ig_id || '')) job.ig_id = body.ig_id;
          if (body.features && typeof body.features === 'object') { job.features = {}; Object.entries(body.features).forEach(([k, v]) => { if (/^[a-z_]{2,60}$/.test(k)) job.features[k] = !!v }) }
        }
        if (body.type === 'setup' && !job.adset_id && !job.new_adset) return res.status(400).json({ ok: false, msg: '세트를 골라주세요' });
        await put(`jobs/${ts}.json`, JSON.stringify(job), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
        return res.status(200).json({ ok: true, job: ts });
      }
      if (body.type === 'chunk') {   // 레퍼런스 직접 추가: 파일 조각(약 2.5MB씩, base64)
        if (!/^[a-z0-9]{8,32}$/.test(body.up || '') || !(+body.i >= 0 && +body.i < 80) || typeof body.data !== 'string' || body.data.length > 3600000) return res.status(400).json({ ok: false, msg: '잘못된 조각' });
        await put(`uploads/${body.up}/${String(+body.i).padStart(3, '0')}`, Buffer.from(body.data, 'base64'), { access: 'private', token: T, addRandomSuffix: false, allowOverwrite: true, contentType: 'application/octet-stream' });
        return res.status(200).json({ ok: true });
      }
      if (body.type === 'addref') {   // 조각 다 올린 뒤 → 맥 작업기가 합쳐서 레퍼런스 카드로
        const kind = body.kind === 'video' ? 'video' : 'image', ext = String(body.ext || '').toLowerCase();
        if (!/^[a-z0-9]{8,32}$/.test(body.up || '') || !(+body.n >= 1 && +body.n <= 80) || !/^(jpg|jpeg|png|webp|gif|mp4|mov|m4v|webm)$/.test(ext)) return res.status(400).json({ ok: false, msg: '잘못된 요청' });
        if (!WHO.includes(body.by)) return res.status(400).json({ ok: false, msg: '이름을 골라주세요' });
        const job = { type: 'addref', requested: new Date().toISOString(), by: body.by, up: body.up, n: +body.n, kind, ext,
          name: String(body.name || '').trim().slice(0, 60), ...(body.go ? { bokgak: { brand: brandOf(body.brand), landing: /^https:\/\/[^\s"'<>]{4,1000}$/.test(body.landing || '') ? body.landing : '', command: String(body.command || '').trim().slice(0, 2000) } } : {}), assets: pickAssets(body), asset_note: String(body.asset_note || '').trim().slice(0, 500), memo: String(body.memo || '').trim().slice(0, 1000), src: /^https?:\/\//.test(body.src || '') ? String(body.src).slice(0, 500) : '' };
        await put(`jobs/${ts}.json`, JSON.stringify(job), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
        return res.status(200).json({ ok: true, job: ts });
      }
      if (body.type === 'delref') {   // 직접 추가한 레퍼런스 삭제
        if (!/^\d{8,20}$/.test(String(body.id || ''))) return res.status(400).json({ ok: false, msg: '잘못된 요청' });
        await put(`jobs/${ts}.json`, JSON.stringify({ type: 'delref', requested: new Date().toISOString(), id: String(body.id), by: WHO.includes(body.by) ? body.by : '' }), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
        return res.status(200).json({ ok: true, job: ts });
      }
      if (body.type === 'delete') {   // 검수 페이지에서 소재 삭제(목록에서 숨김, 파일은 남김)
        if (!okKey && !(/^[0-9A-Za-z_-]{6,40}$/.test(body.fjob || '') && /^\d{1,25}$/.test(body.fref || ''))) return res.status(400).json({ ok: false, msg: '잘못된 요청' });
        await put(`jobs/${ts}.json`, JSON.stringify({ type: 'delete', requested: new Date().toISOString(), date: body.date, no: body.no, fjob: body.fjob || '', fref: body.fref || '', by: WHO.includes(body.by) ? body.by : '' }), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
        return res.status(200).json({ ok: true, job: ts });
      }
      if (body.type === 'retry') {   // 실패 카드 '다시 복각하기'(그때 설정 그대로)
        if (!(/^[0-9A-Za-z_-]{6,40}$/.test(body.fjob || '') && /^\d{1,25}$/.test(body.fref || ''))) return res.status(400).json({ ok: false, msg: '잘못된 요청' });
        await put(`jobs/${ts}.json`, JSON.stringify({ type: 'retry', requested: new Date().toISOString(), fjob: body.fjob, fref: body.fref, by: WHO.includes(body.by) ? body.by : '' }), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
        return res.status(200).json({ ok: true, job: ts });
      }
      if (body.type === 'cancel') {   // 제작 취소: 시작 전이면 요청 삭제, 진행 중이면 멈춤 표시(작업기가 다음 소재부터 건너뜀)
        if (!/^[0-9TZ-]{20,40}$/.test(body.job || '')) return res.status(400).json({ ok: false, msg: '잘못된 요청' });
        try { await del(`jobs/${body.job}.json`, { token: T }) } catch (e) {}
        await put(`cancel/${body.job}`, '1', { access: 'private', token: T, addRandomSuffix: false, allowOverwrite: true, contentType: 'text/plain' });
        return res.status(200).json({ ok: true });
      }
      if (body.type === 'select') {   // 대표 버전 바꾸기(생성 없음)
        if (!/^\d{4}-\d{2}-\d{2}$/.test(body.date || '') || !/^\d{3}$/.test(body.no || '') || !(+body.version >= 1)) return res.status(400).json({ ok: false, msg: '잘못된 요청' });
        await put(`jobs/${ts}.json`, JSON.stringify({ type: 'select', requested: new Date().toISOString(), date: body.date, no: body.no, version: +body.version }), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
        return res.status(200).json({ ok: true, job: ts });
      }
      if (body.type === 'revise') {   // 검수 페이지 피드백 → 수정 요청
        const fb = String(body.feedback || '').trim().slice(0, 1000);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(body.date || '') || !/^\d{3}$/.test(body.no || '') || !fb) return res.status(400).json({ ok: false, msg: '피드백을 적어주세요' });
        await put(`jobs/${ts}.json`, JSON.stringify({ type: 'revise', requested: new Date().toISOString(), date: body.date, no: body.no, feedback: fb, base: +body.base || 0, ...(pickAssets(body).length ? { assets: pickAssets(body) } : {}) }), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
        return res.status(200).json({ ok: true, job: ts });
      }
      if (body.type === 'zcre_quote') {   // ZCRE 생성 탭: 견적 요청(무료). 생성은 견적을 보고 '승인'해야만
        const model = String(body.model || ''), prompt = String(body.prompt || '').trim().slice(0, 4000);
        if (!WHO.includes(body.by)) return res.status(400).json({ ok: false, msg: '담당자를 골라주세요' });
        if (!/^[a-z0-9][a-z0-9.\-]{1,127}$/.test(model)) return res.status(400).json({ ok: false, msg: '모델을 골라주세요' });
        const assets = (Array.isArray(body.assets) ? body.assets : []).slice(0, 5).filter(x => x && /^[a-z0-9]{8,32}$/.test(x.up || '') && +x.n >= 1 && +x.n <= 80 && /^(jpg|jpeg|png|webp|mp4|mov|m4v|webm|mp3|wav|ogg|m4a)$/.test(String(x.ext || '').toLowerCase()))
          .map(x => ({ up: x.up, n: +x.n, ext: String(x.ext).toLowerCase(), name: String(x.name || '').slice(0, 60) }));
        const refs = (Array.isArray(body.refs) ? body.refs : []).map(String).filter(x => /^\d{1,25}$/.test(x)).slice(0, 5);
        if (!prompt && !assets.length && !refs.length) return res.status(400).json({ ok: false, msg: '프롬프트나 참조 파일을 넣어주세요' });
        await put(`jobs/${ts}.json`, JSON.stringify({ type: 'zcre_quote', requested: new Date().toISOString(), by: body.by, model, media: ['image', 'video', 'audio'].includes(body.media) ? body.media : '', prompt, opts: String(body.opts || '').trim().slice(0, 500), assets, refs }), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
        ZC.at = 0; return res.status(200).json({ ok: true, job: ts });
      }
      if (body.type === 'zcre_run' || body.type === 'zcre_cancel') {   // 견적 승인하고 생성 / 견적 취소
        if (!/^[0-9TZ-]{20,40}$/.test(body.rid || '')) return res.status(400).json({ ok: false, msg: '잘못된 요청' });
        if (!WHO.includes(body.by)) return res.status(400).json({ ok: false, msg: '담당자를 골라주세요' });   // 2026-11-11: 요청자 비면 받지 않음
        await put(`jobs/${ts}.json`, JSON.stringify({ type: body.type, requested: new Date().toISOString(), rid: body.rid, by: body.by }), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
        ZC.at = 0; return res.status(200).json({ ok: true, job: ts });
      }
      const items = (body.items || []).filter(x => x && /^\d+$/.test(String(x.id))).slice(0, 30);
      const landing = /^https:\/\/[^\s"'<>]{4,1000}$/.test(body.landing || '') ? body.landing : '';   // 복각하기 팝업에서 고른 랜딩
      if (landing) items.forEach(x => { x.landing = landing });
      if (!WHO.includes(body.by)) return res.status(400).json({ ok: false, msg: '이름을 골라주세요' });
      if (!items.length) return res.status(400).json({ ok: false, msg: '선택한 레퍼런스가 없습니다' });
      await put(`jobs/${ts}.json`, JSON.stringify({ requested: new Date().toISOString(), by: body.by, brand: brandOf(body.brand), items, command: String(body.command || '').trim().slice(0, 2000), ...(pickAssets(body).length ? { assets: pickAssets(body), asset_note: String(body.asset_note || '').trim().slice(0, 500) } : {}) }), { access: 'private', token: T, addRandomSuffix: false, contentType: 'application/json' });
      return res.status(200).json({ ok: true, job: ts, count: items.length });
    }
    if (req.query && req.query.stars) {   // 별표 목록(3초 재사용)
      if (!STC.b || Date.now() - STC.at > 3000) STC = { at: Date.now(), b: { ok: true, stars: await starsGet() } };
      res.setHeader('Cache-Control', 'private, max-age=3'); return res.status(200).json(STC.b);
    }
    if (req.query && req.query.ls) {   // 실시간 수집 결과(3초 재사용)
      const k = /^[0-9a-f]{16}$/.test(req.query.ls) ? req.query.ls : lsKey(req.query.ls); const c = LSC.get(k);
      if (c && Date.now() - c.t < 3000) return res.status(200).json(c.b);
      const b = { ok: true, key: k, ls: await lsGet(k) }; LSC.set(k, { t: Date.now(), b }); if (LSC.size > 200) LSC = new Map([...LSC].slice(-50));
      res.setHeader('Cache-Control', 'private, max-age=3'); return res.status(200).json(b);
    }
    if (req.query && req.query.zcre) {   // ZCRE 탭 상태(맥이 Blob zcre.json 에 올림 — 토큰·서명 URL 없음)
      if (!ZC.body || Date.now() - ZC.at > 4000) { let z = null; try { const r = await get('zcre.json', { access: 'private', token: T }); if (r) z = JSON.parse(await new Response(r.stream).text()) } catch (e) {} ZC = { at: Date.now(), body: { ok: true, zcre: z } } }
      res.setHeader('Cache-Control', 'private, max-age=4'); return res.status(200).json(ZC.body);
    }
    if (CACHE.body && Date.now() - CACHE.at < CACHE.ttl) { res.setHeader('Cache-Control', 'private, max-age=5'); return res.status(200).json(CACHE.body) }
    const blobs = (await list({ prefix: 'jobs/', token: T })).blobs.slice(0, 20);
    const jobs = await Promise.all(blobs.map(async b => {
      const o = { job: b.pathname.slice(5, -5), at: b.uploadedAt };
      try { const ck = b.pathname + '|' + b.uploadedAt; let j = JOBC.get(ck); if (!j) { const r = await get(b.pathname, { access: 'private', token: T }); j = JSON.parse(await new Response(r.stream).text()); JOBC.set(ck, j); if (JOBC.size > 300) JOBC = new Map([...JOBC].slice(-100)) }
        o.type = j.type || 'bokgak'; o.by = j.by || ''; if (j.type === 'addref') { o.name = j.name; o.kind = j.kind; o.go = !!j.bokgak } if (j.items) o.items = j.items.map(x => ({ id: String(x.id), page: x.page || '', days: x.days || '' })); if (j.no) { o.date = j.date; o.no = j.no } if (j.type === 'setup') o.adset = j.adset_id || ('new:' + (j.new_adset || '')) } catch (e) {}
      return o;
    }));
    let status = null;
    try { const s = await get('status.json', { access: 'private', token: T }); if (s) status = JSON.parse(await new Response(s.stream).text()); } catch (e) {}
    // 동시에 만드는 요청마다 진행 상태(2026-10-26)
    const statuses = {};
    try { for (const b of (await list({ prefix: 'st/', token: T })).blobs.slice(0, 12)) { try { const s = await get(b.pathname, { access: 'private', token: T }); if (s) statuses[b.pathname.slice(3, -5)] = JSON.parse(await new Response(s.stream).text()); } catch (e) {} } } catch (e) {}
    CACHE = { at: Date.now(), body: { ok: true, pending: jobs, status, statuses }, ttl: (jobs.length || (status && status.state === 'working') || Object.keys(statuses).length) ? 5000 : 15000 };   // 한가할 땐 15초 재사용(새 요청 POST 가 오면 바로 비움)
    res.setHeader('Cache-Control', 'private, max-age=5');
    return res.status(200).json(CACHE.body);
  } catch (e) {
    return res.status(500).json({ ok: false, msg: String(e.message || e) });
  }
}
