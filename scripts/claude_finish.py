"""Claude 직접 복각 결과(result.json)를 검수 페이지 기록(review.json)에 반영. 사용: python3 -I claude_finish.py <brief.json> <result.json|없음>
result.json(Claude 가 씀) = {"ok":true, "items":[{"ref_id", "kind":"image|video", "img":절대경로, "mp4":절대경로(영상),
   "soguo","hook1","hook2","headline","sub","format","why","body"(선택),"title"(선택),"landing","landing_title","note","summary"(수정일 때)}], "err":""}"""
import json, os, shutil, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
bk = {}; exec(compile(open(HERE + '/bokgak.py').read().replace('\nmain()\n', '\n'), HERE + '/bokgak.py', 'exec'), bk)
R = bk['R']; KST = datetime.timezone(datetime.timedelta(hours=9)); NOW = datetime.datetime.now(KST); D = NOW.strftime('%Y-%m-%d')
brief = json.load(open(sys.argv[1]))
res = json.load(open(sys.argv[2])) if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else {'ok': False, 'err': 'Claude 가 결과 파일을 남기지 않음(시간 초과 또는 중단)'}
rv = json.load(open(R + 'data/review.json')) if os.path.exists(R + 'data/review.json') else []
BH = 'bh-reference' in R; PAGE = '오브휴' if BH else '뷰티매거진'   # 광고 이름 끝 칸(게시 페이지)
_BR = json.load(open(R + 'data/brands.json')) if os.path.exists(R + 'data/brands.json') else {}   # 2026-11-10 브랜드별 광고 이름 규칙
def _name_of(nn, pl, kt, by):
    bc = _BR.get(brief.get('brand') or 'SOOO', {}); nf = bc.get('name_fmt') if (brief.get('brand') or 'SOOO') != 'SOOO' else None
    v = dict(yymmdd=NOW.strftime('%y%m%d'), yyyymmdd=NOW.strftime('%Y%m%d'), nn=nn, soguo=pl['soguo'], kt=kt, person=bk['FULL'].get(by, '박다운'))
    return nf.format(**v) if nf else f"{v['yymmdd']}_{nn} / {pl['soguo']} / {kt} / {v['person']} / {PAGE}"
def body_of(r):
    if r.get('body'): return r['body']
    if BH: return f"‼️3만원대 전기요 비밀링크 오픈‼️\n{r.get('hook1', '')}\n{r.get('hook2', '')}\n\n{bk['CHECK']}\n\n추워지기 전에 지금 바로 확인해보세요👇"
    return f"[1+1🔥] 탈모샴푸 개당 2만원대!\n{r.get('hook1', '')}\n{r.get('hook2', '')}\n\n{bk['CHECK']}\n\n지금 공식몰에서 1+1로 만나보세요👇"
def plan_of(r):
    return {k: r.get(k, '') for k in ('soguo', 'hook1', 'hook2', 'headline', 'sub', 'format', 'why', 'body', 'title') if r.get(k)} | {'soguo': r.get('soguo') or '복각', 'hook1': r.get('hook1', ''), 'hook2': r.get('hook2', ''), 'headline': r.get('headline', ''), 'sub': r.get('sub', ''), 'by_claude': True, 'note': r.get('note', '')}
def put(src, dst):
    os.makedirs(os.path.dirname(R + 'site/' + dst), exist_ok=True); shutil.copy(src, R + 'site/' + dst); return dst
by = brief.get('by') or '다운'; kt_of = {'video': 'video', 'image': 'image', 'gif': 'GIF'}
if brief['type'] == 'revise':
    rec = next(x for x in rv if x['date'] == brief['date'] and x.get('no') == brief['no'] and x.get('ok'))
    if not rec.get('versions'): rec['versions'] = [{'v': 1, 'img': rec['img'], 'plan': dict(rec.get('plan', {})), 'at': rec.get('made', ''), 'note': '처음 복각', **({'mp4': rec['media']['mp4']} if (rec.get('media') or {}).get('mp4') else {})}]
    if res.get('ok') and res.get('items'):
        r = res['items'][0]; nv = max(v['v'] for v in rec['versions']) + 1; stem = f"review/{rec['date']}/{rec['no']}_v{nv}"
        v = {'v': nv, 'img': put(r['img'], stem + '.jpg'), 'plan': plan_of(r), 'at': NOW.strftime('%m-%d %H:%M'), 'from': brief.get('base_version'),
             'feedback': brief.get('feedback', ''), 'rules': (brief.get('prev_feedback') or []) + [brief.get('feedback', '')], 'note': 'Claude 직접 — ' + (r.get('summary') or r.get('note', '')), 'work': brief.get('work'), 'review': r.get('review') or []}
        if r.get('mp4'): v['mp4'] = put(r['mp4'], stem + '.mp4'); rec['media'] = {**(rec.get('media') or {}), 'mp4': v['mp4']}
        rec['versions'].append(v); rec['cur'] = nv; rec['img'] = v['img']; rec['plan'] = v['plan']; rec['revised'] = NOW.strftime('%H:%M')
        if r.get('body'): rec['body'] = r['body']
        if r.get('landing'): rec['landing'] = r['landing']; rec['landing_title'] = r.get('landing_title') or rec.get('landing_title')
        print('수정 완료', rec['no'], f'v{nv}')
    else:
        rec['revise_err'] = {'at': NOW.strftime('%m-%d %H:%M'), 'msg': (res.get('err') or '')[:200]}; print('수정 실패', res.get('err'))
else:
    if brief.get('retry_of'):
        for x in rv:
            if not x.get('ok') and x.get('job') == brief['retry_of']['fjob'] and str(x.get('ref_id')) == brief['retry_of']['fref']: x['deleted'] = NOW.strftime('%m-%d %H:%M'); x['deleted_by'] = '다시 복각'
    done = {str(r.get('ref_id')): r for r in (res.get('items') or [])} if res.get('ok') else {}
    for ib in brief['items']:
        r = done.get(ib['ref_id'])
        rec = {'date': D, 'made': NOW.strftime('%H:%M'), 'job': brief['job'], 'by': by, 'ref_id': ib['ref_id'], 'ref_page': ib.get('ref_page', ''), 'ref_days': ib.get('ref_days'),
               'ref_kind': ib.get('ref_kind', ''), 'ref_text': (ib.get('ref_text') or '')[:300]}
        if not r or not os.path.exists(r.get('img', '')):
            rec.update(ok=False, err='Claude 직접 복각 실패: ' + ((r or {}).get('err') or res.get('err') or '결과 없음')[:180],
                       retry={'item': ib['item'], 'by': by, 'brand': brief.get('brand') or 'SOOO', 'user': ib.get('assets', []), 'docs': [{k: d[k] for k in ('lab', 'name', 'path')} for d in ib.get('docs', [])], 'note': ib.get('asset_note', '')})
            rv.append(rec); print('실패', ib['ref_id']); continue
        nn = f"{len([x for x in rv if x['date'] == D and x.get('ok')]) + 1:03d}"; kt = 'video' if r.get('mp4') else 'image'
        img = put(r['img'], f'review/{D}/{nn}.jpg'); pl = plan_of(r)
        v1 = {'v': 1, 'img': img, 'plan': dict(pl), 'at': NOW.strftime('%m-%d %H:%M'), 'note': 'Claude 직접 복각 — ' + r.get('note', ''), 'work': brief.get('work'), 'review': r.get('review') or []}
        if r.get('mp4'): v1['mp4'] = put(r['mp4'], f'review/{D}/{nn}.mp4'); rec.update(kind='video', media={'mp4': v1['mp4']})
        lu = r.get('landing') or ib.get('landing') or brief.get('default_landing') or bk['DEFAULT']; ymd = NOW.strftime('%Y%m%d')
        rec.update(no=nn, img=img, ok=True, plan=pl, cur=1, versions=[v1], by_claude=True, brand=brief.get('brand') or 'SOOO',
                   ad_name=_name_of(nn, pl, kt, by),
                   body=body_of(r), landing=lu, landing_title=r.get('landing_title') or '', title=r.get('title') or '',
                   link=bk['with_utm'](lu, ymd, nn, kt, camp=bk['camp_of'](lu, r.get('landing_title') or '')))
        rv.append(rec); print('완료', nn, pl['soguo'])
json.dump(rv, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1)
