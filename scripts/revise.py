"""검수 페이지 피드백으로 복각 소재 수정 / 대표 버전 바꾸기. 사용: python3 -I revise.py job.json
revise: {date,no,feedback,base}  base = 기준 버전 번호(0이면 지금 대표 버전) → 새 버전 v(N+1) 추가하고 대표로
select: {date,no,version}       → 그 버전을 대표로(생성 없음)"""
import json, os, sys, datetime, base64
HERE = os.path.dirname(os.path.abspath(__file__))
bk = {}; exec(compile(open(HERE + '/bokgak.py').read().replace('\nmain()\n', '\n'), HERE + '/bokgak.py', 'exec'), bk)   # 함수만 가져오기
R, CHECK, gem, img_part, PRODUCT, FACTS = bk['R'], bk['CHECK'], bk['gem'], bk['img_part'], bk['PRODUCT'], bk['FACTS']
BV = bk['BV']
KST = datetime.timezone(datetime.timedelta(hours=9)); NOW = datetime.datetime.now(KST)
job = json.load(open(sys.argv[1])); rv = json.load(open(R + 'data/review.json'))
if job.get('type') == 'delete' and job.get('fref'):   # 실패 기록 지우기(번호 없음 → 요청 번호+레퍼런스로 찾음)
    for x in rv:
        if not x.get('ok') and x.get('job') == job['fjob'] and str(x.get('ref_id')) == str(job['fref']): x['deleted'] = NOW.strftime('%m-%d %H:%M'); x['deleted_by'] = job.get('by', '')
    json.dump(rv, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1); print('실패 기록 삭제', job['fref']); sys.exit(0)
rec = next(x for x in rv if x['date'] == job['date'] and x.get('no') == job['no'] and x.get('ok'))
if job.get('type') == 'delete':   # 목록에서 숨김(파일·메타 광고는 그대로)
    rec['deleted'] = NOW.strftime('%m-%d %H:%M'); rec['deleted_by'] = job.get('by', '')
    json.dump(rv, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1); print('삭제', rec['date'], rec['no']); sys.exit(0)
if not rec.get('versions'): rec['versions'] = [{'v': 1, 'img': rec['img'], 'plan': dict(rec['plan']), 'at': rec.get('made', ''), 'note': '처음 복각'}]; rec['cur'] = 1
def apply(v):   # 대표 버전 → 광고 이름·본문·이미지
    pl = dict(v['plan']); rec['plan'] = pl; rec['img'] = v['img']; rec['cur'] = v['v']
    if v.get('mp4'): rec['media'] = {**(rec.get('media') or {}), 'mp4': v['mp4']}
    kt = {'gif': 'GIF', 'video': 'video'}.get(rec.get('kind'), 'image')
    rec['ad_name'] = f"{rec['ad_name'].split('_')[0]}_{rec['no']} / {pl['soguo']} / {kt} / {({'다운': '박다운', '화영': '김화영', '도현': '박도현', '근형': '박근형', '형태': '유형태', '다솔': '다솔'}).get(rec.get('by'), '박다운')} / 뷰티매거진"
    rec['body'] = pl['body'] if pl.get('body') else f"[1+1🔥] 탈모샴푸 개당 2만원대!\n{pl['hook1']}\n{pl['hook2']}\n\n{CHECK}\n\n지금 공식몰에서 1+1로 만나보세요👇"
if job.get('type') == 'select':
    apply(next(v for v in rec['versions'] if v['v'] == job['version']))
    json.dump(rv, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1); print('대표 버전', job['version']); sys.exit(0)
base = next((v for v in rec['versions'] if v['v'] == job.get('base')), None) or next(v for v in rec['versions'] if v['v'] == rec.get('cur', 1))
pl = dict(base['plan']); cur = R + 'site/' + base['img']
import time as _tm, subprocess as _sp
_T0 = _tm.time(); _EXP = 150 if pl.get('cuts') else 70   # 예상 초(영상·이미지)
def rstep(msg, pct):   # 검수 페이지 진행 카드용(실패해도 무시)
    try: _sp.run(['node', R + 'scripts/blob.mjs', 'status', json.dumps({'state': 'working', 'job': job.get('job', ''), 'cur': f"{rec['date']}_{rec['no']}", 'step': msg, 'pct': pct, 't0': _T0, 'exp': _EXP, 'now': _tm.time()}, ensure_ascii=False)], cwd=R, capture_output=True, timeout=60)
    except Exception: pass
rstep('피드백 읽는 중', 5)
def fb_chain(v):   # 이 버전까지 받은 피드백 전부(처음 → 지금 순서)
    out, seen = [], set()
    while v and v['v'] not in seen:
        seen.add(v['v'])
        if v.get('feedback'): out.append(v['feedback'])
        v = next((x for x in rec['versions'] if x['v'] == v.get('from')), None)
    return out[::-1]
PREV = fb_chain(base)
prev_txt = ('\n★ 이 소재에 이전에 받은 피드백(이번 수정에서도 전부 계속 지킨다, 되돌리지 말 것):\n' + '\n'.join(f'{i}. {f}' for i, f in enumerate(PREV, 1)) + '\n') if PREV else ''
NEWU, NEWD = [], []   # 수정하며 새로 붙인 파일(F1·F2…)
if job.get('assets'):
    bk['fetch_user_assets']({**job, 'asset_note': ''}, 'F'); NEWU = [dict(u) for u in bk['USER']]; NEWD = [dict(d) for d in bk['DOCS']]
BV.USER = [dict(u) for u in (pl.get('_user') or [])] + NEWU; BV.DOCS = NEWD
def ftxt():
    if not (NEWU or NEWD): return ''
    t = '\n★ 다운이 이번 수정에 새로 붙인 파일: ' + ', '.join(f"{u['lab']}({'영상 %.1f초' % u['dur'] if u['kind'] == 'video' else '사진'} {u['name'][:20]})" for u in NEWU)
    t += ' — 사진·영상은 이번 수정에 꼭 반영한다(영상 컷이면 "src":"user","user":"F1" 처럼). 글씨 빽빽한 문서 캡처는 지시서로 읽는다.'
    for d in NEWD: t += f"\n[참고 문서 {d['lab']} {d['name'][:30]} — 지시서, 최우선으로 따름]\n{d['text'][:6000]}"
    return t + '\n'
def fparts():
    return [img_part(u['img']) for u in NEWU] + [{'inline_data': {'mime_type': 'application/pdf', 'data': base64.b64encode(open(d['path'], 'rb').read()).decode()}} for d in NEWD if d['path'].lower().endswith('.pdf') and os.path.getsize(d['path']) < 15_000_000]
if pl.get('cuts'):   # 영상 복각: 컷 계획을 피드백대로 고쳐 다시 편집(만든 Veo 장면은 재사용)
    ask = f"""SOOO 복각 광고 영상을 다운(마케터) 피드백대로 고친다.
{FACTS}
지금 컷 계획(v{base['v']}): {json.dumps(pl, ensure_ascii=False)}
{prev_txt}이번 피드백: {job['feedback']}{ftxt()}
쓸 수 있는 다운 에셋 라벨: {', '.join(u['lab'] for u in BV.USER) or '없음'}
첨부 = 에셋 번호 목록 이미지, 지금 영상 대표 장면, (있으면) 새로 붙인 파일. 같은 형식의 전체 JSON 을 돌려준다(바꿀 것만 바꾸고 나머지는 그대로). "summary" 필드에 무엇을 고쳤는지 한국어 한 줄.
장면 규칙: 레퍼런스와 완전히 똑같은 에셋이 있을 때만 asset, 아니면 gen(레퍼런스 장면을 우리 제품으로 AI 재현, frame_prompt·motion_prompt). 분위기만 비슷한 에셋 짜집기 금지. gen·veo 합계 40초 이하. 자막 스타일(bx·font·color 등)은 피드백이 바꾸라고 할 때만 바꾼다."""
    rstep('수정 계획 세우는 중', 20)
    r = gem('gemini-3.1-pro-preview', [img_part(R + 'data/assets_grid.jpg'), img_part(cur)] + fparts() + [{'text': ask}], {'temperature': 0.3, 'responseMimeType': 'application/json'}, timeout=300)
    np_ = json.loads(r['candidates'][0]['content']['parts'][0]['text']); np_ = np_[0] if isinstance(np_, list) else np_
    summ = np_.pop('summary', ''); np_['_ref'] = pl.get('_ref'); np_['_user'] = BV.USER   # 레퍼런스·에셋 정보 이어 붙이기
    STY = ('bx', 'lines', 'font', 'color', 'stroke', 'stroke_w', 'box', 'bg_alpha', 'align', 'hl')
    for i, c in enumerate(np_.get('cuts', [])):   # 실측한 자막 스타일은 피드백이 바꾸라고 한 게 아니면 그대로
        oc = (pl.get('cuts') or [])[i] if i < len(pl.get('cuts') or []) else {}
        for j, t in enumerate(c.get('texts') or []):
            ot = (oc.get('texts') or [])[j] if j < len(oc.get('texts') or []) else {}
            for k in STY:
                if k not in t and k in ot: t[k] = ot[k]
    if any(t for c in np_.get('cuts', []) for t in (c.get('texts') or []) if not t.get('bx')) and np_.get('_ref'):
        BV.measure_texts(gem, img_part, np_['_ref'], np_, np_['_ref'].rsplit('.', 1)[0] + '_measure')
    nv = max(v['v'] for v in rec['versions']) + 1; mp4 = f"review/{rec['date']}/{rec['no']}_v{nv}.mp4"; img = f"review/{rec['date']}/{rec['no']}_v{nv}.jpg"
    prod = PRODUCT if not rec.get('landing') or bk['is_default'](rec['landing']) else bk['landing_ctx'](rec['landing'])['product']
    _nc = max(1, len(np_.get('cuts', [])))
    def _lg(m, _c=[0]):
        print(m, flush=True); _c[0] += 1; rstep(f'다시 편집 중 — {m}', 40 + int(50 * _c[0] / _nc))
    rstep('다시 편집 시작', 40)
    vs = BV.render(np_, R + 'site/' + mp4, prod, R + f"data/work/{rec['date']}_{rec['no']}_v{nv}", log=_lg); BV.poster(R + 'site/' + mp4, R + 'site/' + img)
    rstep('저장 중', 95)
    rec['versions'].append({'v': nv, 'rules': PREV + [job['feedback']], 'img': img, 'mp4': mp4, 'plan': np_, 'at': NOW.strftime('%m-%d %H:%M'), 'from': base['v'], 'feedback': job['feedback'], 'note': summ, 'veo_sec': vs})
    apply(rec['versions'][-1]); rec['revised'] = NOW.strftime('%H:%M')
    json.dump(rv, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1); print('수정 완료(영상)', rec['no'], f'v{nv}', summ, f'Veo {vs}초'); sys.exit(0)
ask = f"""SOOO 복각 광고 소재를 다운(마케터) 피드백대로 고친다.
{FACTS}
지금 소재(v{base['v']}): 소구점 {pl['soguo']} / 이미지 큰 문구 "{pl['headline']}" / 작은 문구 "{pl['sub']}" / 본문 후킹 "{pl['hook1']}" · "{pl['hook2']}"
{prev_txt}이번 피드백: {job['feedback']}{ftxt()}
첨부 = 지금 이미지{', 그 뒤는 새로 붙인 파일' if (NEWU or NEWD) else ''}. JSON만:
{{"image_change": true 또는 false, "image_instruction":"이미지 편집 지시(영어, 바꿀 것만 구체적으로, 나머지는 그대로 유지하라고)","soguo":"","headline":"","sub":"","hook1":"","hook2":"","summary":"무엇을 고쳤는지 한국어 한 줄"}}
바꿀 필요 없는 필드는 지금 값을 그대로 넣는다."""
rstep('수정 계획 세우는 중', 20)
r = gem('gemini-3.1-pro-preview', [img_part(cur)] + fparts() + [{'text': ask}], {'temperature': 0.3, 'responseMimeType': 'application/json'})
fx = json.loads(r['candidates'][0]['content']['parts'][0]['text'])
fx = fx[0] if isinstance(fx, list) else fx   # 가끔 배열로 돌려줘서 그대로 쓰면 .get 에서 죽는다
if not isinstance(fx, dict): raise SystemExit('수정 계획을 못 읽었습니다(응답 형식 이상)')
for k in ('soguo', 'headline', 'sub', 'hook1', 'hook2'):
    if fx.get(k): pl[k] = fx[k]
nv = max(v['v'] for v in rec['versions']) + 1; img = base['img']
if fx.get('image_change'):
    rstep('이미지 고치는 중', 50)
    p = (fx['image_instruction'] + f"\nKorean text on the image must read exactly: big \"{pl['headline']}\" ; small \"{pl['sub']}\"."
         "\nEdit the first image only as instructed and keep everything else the same. The other images are the real SOOO products: keep their exact shape, color and label. 4:5.")
    if NEWU: p += f"\nThe LAST {len(NEWU)} images are new assets the marketer attached for this revision: use them as instructed in the feedback."
    g = gem('nano-banana-pro-preview', [img_part(cur)] + [img_part(x) for x in PRODUCT] + [img_part(u['img']) for u in NEWU] + [{'text': p}], {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': '4:5'}}, timeout=400)
    b = next((pt.get('inline_data') or pt.get('inlineData') for c in g.get('candidates', []) for pt in c.get('content', {}).get('parts', []) if pt.get('inline_data') or pt.get('inlineData')), None)
    if not b: raise SystemExit('이미지 수정 실패')
    img = f"review/{rec['date']}/{rec['no']}_v{nv}.jpg"; open(R + 'site/' + img, 'wb').write(base64.b64decode(b['data']))
    from PIL import Image
    im = Image.open(R + 'site/' + img).convert('RGB'); im.thumbnail((1080, 1350)); im.save(R + 'site/' + img, quality=90)
rstep('저장 중', 95)
rec['versions'].append({'v': nv, 'rules': PREV + [job['feedback']], 'img': img, 'plan': pl, 'at': NOW.strftime('%m-%d %H:%M'), 'from': base['v'], 'feedback': job['feedback'], 'note': fx.get('summary', '')})
apply(rec['versions'][-1]); rec['revised'] = NOW.strftime('%H:%M')
json.dump(rv, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1); print('수정 완료', rec['no'], f'v{nv}', fx.get('summary'))
