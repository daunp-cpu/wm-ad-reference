// Cloudflare Pages Function. Vercel Blob 자리에 Workers KV(바인딩 JOBS)를 쓴다 — 동작은 api/bokgak.js 와 같다.
// POST: 복각·세팅·수정·추가 요청을 jobs/<시각>.json 으로 적는다(맥 작업기가 3분마다 가져감)
// GET : 대기 중 요청 목록 + 진행 상태
const WHO = ['화영', '다운', '도현', '근형', '형태'];   // 이름 필수(누가 만들었는지)
const J = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { 'Content-Type': 'application/json' } });

export async function onRequest({ request, env }) {
  const KV = env.JOBS;
  // KV 에는 본문과 함께 metadata 로 올린 시각을 남긴다(Blob 의 uploadedAt 대용)
  const putJob = (k, v) => KV.put(k, typeof v === 'string' ? v : JSON.stringify(v), { metadata: { at: new Date().toISOString() } });
  try {
    if (request.method === 'POST') {
      const body = await request.json().catch(() => ({}));
      const ts = new Date().toISOString().replace(/[:.]/g, '-');
      const okKey = /^\d{4}-\d{2}-\d{2}$/.test(body.date || '') && /^\d{3}$/.test(body.no || '');

      if (body.type === 'setup' || body.type === 'status') {   // 세팅하기 / ON·OFF
        if (!okKey) return J({ ok: false, msg: '잘못된 요청' }, 400);
        const pick = ['by', 'date', 'no', 'on', 'campaign_id', 'adset_id', 'new_campaign', 'copy_campaign', 'new_adset', 'copy_adset', 'budget'];
        const job = { type: body.type, requested: new Date().toISOString() };
        pick.forEach(k => { if (body[k] !== undefined && body[k] !== '') job[k] = body[k]; });
        if (body.type === 'setup' && !WHO.includes(body.by)) return J({ ok: false, msg: '담당자를 골라주세요' }, 400);
        if (body.type === 'setup') {   // 확인 창에서 고친 값(이름·링크·제목·설명·본문·AI 기능·버전)
          const lim = { ad_name: 200, link: 1000, title: 255, desc: 255, body: 3000 };
          Object.entries(lim).forEach(([k, n]) => { if (typeof body[k] === 'string' && body[k].trim()) job[k] = body[k].trim().slice(0, n); });
          if (job.link && !/^https:\/\/ofhue\.kr\//.test(job.link)) return J({ ok: false, msg: '링크는 https://ofhue.kr/ 로 시작해야 해요' }, 400);
          if (+body.version >= 1) job.version = +body.version;
          if (/^\d{5,20}$/.test(body.page_id || '')) job.page_id = body.page_id;
          if (body.ig_id === '' || /^\d{5,20}$/.test(body.ig_id || '')) job.ig_id = body.ig_id;
          if (body.features && typeof body.features === 'object') {
            job.features = {};
            Object.entries(body.features).forEach(([k, v]) => { if (/^[a-z_]{2,60}$/.test(k)) job.features[k] = !!v; });
          }
        }
        if (body.type === 'setup' && !job.adset_id && !job.new_adset) return J({ ok: false, msg: '세트를 골라주세요' }, 400);
        await putJob(`jobs/${ts}.json`, job);
        return J({ ok: true, job: ts });
      }

      if (body.type === 'chunk') {   // 레퍼런스 직접 추가: 파일 조각(약 2.5MB씩, base64)
        if (!/^[a-z0-9]{8,32}$/.test(body.up || '') || !(+body.i >= 0 && +body.i < 80) || typeof body.data !== 'string' || body.data.length > 3600000) return J({ ok: false, msg: '잘못된 조각' }, 400);
        // KV 는 base64 그대로 두고 작업기가 디코드한다(바이너리 왕복보다 단순)
        await KV.put(`uploads/${body.up}/${String(+body.i).padStart(3, '0')}`, body.data);
        return J({ ok: true });
      }

      if (body.type === 'addref') {   // 조각 다 올린 뒤 → 맥 작업기가 합쳐서 레퍼런스 카드로
        const kind = body.kind === 'video' ? 'video' : 'image', ext = String(body.ext || '').toLowerCase();
        if (!/^[a-z0-9]{8,32}$/.test(body.up || '') || !(+body.n >= 1 && +body.n <= 80) || !/^(jpg|jpeg|png|webp|gif|mp4|mov|m4v|webm)$/.test(ext)) return J({ ok: false, msg: '잘못된 요청' }, 400);
        if (!WHO.includes(body.by)) return J({ ok: false, msg: '이름을 골라주세요' }, 400);
        await putJob(`jobs/${ts}.json`, {
          type: 'addref', requested: new Date().toISOString(), by: body.by, up: body.up, n: +body.n, kind, ext,
          name: String(body.name || '').trim().slice(0, 60), memo: String(body.memo || '').trim().slice(0, 1000),
          src: /^https?:\/\//.test(body.src || '') ? String(body.src).slice(0, 500) : '',
        });
        return J({ ok: true, job: ts });
      }

      if (body.type === 'delete') {   // 검수 페이지에서 소재 삭제(목록에서 숨김, 파일은 남김)
        if (!okKey) return J({ ok: false, msg: '잘못된 요청' }, 400);
        await putJob(`jobs/${ts}.json`, { type: 'delete', requested: new Date().toISOString(), date: body.date, no: body.no, by: WHO.includes(body.by) ? body.by : '' });
        return J({ ok: true, job: ts });
      }

      if (body.type === 'cancel') {   // 시작 전이면 요청 삭제, 진행 중이면 멈춤 표시
        if (!/^[0-9TZ-]{20,40}$/.test(body.job || '')) return J({ ok: false, msg: '잘못된 요청' }, 400);
        try { await KV.delete(`jobs/${body.job}.json`); } catch (e) {}
        await KV.put(`cancel/${body.job}`, '1');
        return J({ ok: true });
      }

      if (body.type === 'select') {   // 대표 버전 바꾸기(생성 없음)
        if (!/^\d{4}-\d{2}-\d{2}$/.test(body.date || '') || !/^\d{3}$/.test(body.no || '') || !(+body.version >= 1)) return J({ ok: false, msg: '잘못된 요청' }, 400);
        await putJob(`jobs/${ts}.json`, { type: 'select', requested: new Date().toISOString(), date: body.date, no: body.no, version: +body.version });
        return J({ ok: true, job: ts });
      }

      if (body.type === 'revise') {   // 검수 페이지 피드백 → 수정 요청
        const fb = String(body.feedback || '').trim().slice(0, 1000);
        if (!/^\d{4}-\d{2}-\d{2}$/.test(body.date || '') || !/^\d{3}$/.test(body.no || '') || !fb) return J({ ok: false, msg: '피드백을 적어주세요' }, 400);
        await putJob(`jobs/${ts}.json`, { type: 'revise', requested: new Date().toISOString(), date: body.date, no: body.no, feedback: fb, base: +body.base || 0 });
        return J({ ok: true, job: ts });
      }

      // 기본: 복각 요청
      const items = (body.items || []).filter(x => x && /^\d+$/.test(String(x.id))).slice(0, 30);
      const landing = /^https:\/\/[^\s"'<>]{4,1000}$/.test(body.landing || '') ? body.landing : '';   // 복각하기 팝업에서 고른 랜딩
      if (landing) items.forEach(x => { x.landing = landing; });
      if (!WHO.includes(body.by)) return J({ ok: false, msg: '이름을 골라주세요' }, 400);
      if (!items.length) return J({ ok: false, msg: '선택한 레퍼런스가 없습니다' }, 400);
      await putJob(`jobs/${ts}.json`, { requested: new Date().toISOString(), by: body.by, items });
      return J({ ok: true, job: ts, count: items.length });
    }

    // GET — 대기 목록 + 진행 상태
    const listed = await KV.list({ prefix: 'jobs/', limit: 20 });
    const jobs = await Promise.all(listed.keys.map(async k => {
      const out = { job: k.name.slice(5, -5), at: (k.metadata || {}).at || '' };
      try {
        const j = JSON.parse(await KV.get(k.name));
        out.type = j.type || 'bokgak'; out.by = j.by || '';
        if (j.type === 'addref') { out.name = j.name; out.kind = j.kind; }
        if (j.items) out.items = j.items.map(x => ({ id: String(x.id), page: x.page || '', days: x.days || '' }));
        if (j.no) { out.date = j.date; out.no = j.no; }
        if (j.type === 'setup') out.adset = j.adset_id || ('new:' + (j.new_adset || ''));
      } catch (e) {}
      return out;
    }));
    let status = null;
    try { const s = await KV.get('status.json'); if (s) status = JSON.parse(s); } catch (e) {}
    return J({ ok: true, pending: jobs, status });
  } catch (e) {
    return J({ ok: false, msg: String(e.message || e) }, 500);
  }
}
