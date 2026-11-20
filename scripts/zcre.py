"""ZCRE 생성 탭 상태 관리(맥 쪽). 상태는 data/zcre/state.json, 페이지는 Blob zcre.json 을 읽음(토큰·서명 URL 은 절대 안 올림).
사용: python3 -I zcre.py new <job> | prep <rid> | quoted <rid> | approve <job> | ran <rid> | cancel <job> | fail <rid> <이유> | push
흐름: 견적 요청(new→prep→Claude 견적→quoted) → 다운이 '승인하고 생성'(approve→Claude 생성→ran) → 결과 site/z/ 로 배포."""
import json, os, sys, shutil, subprocess, datetime, glob
R = '/Users/daun/ad-reference/'; Z = R + 'data/zcre/'; ST = Z + 'state.json'; NODE = '/Users/daun/.local/node/bin/node'
KST = datetime.timezone(datetime.timedelta(hours=9)); NOW = datetime.datetime.now(KST)
os.makedirs(Z + 'jobs', exist_ok=True); os.makedirs(R + 'site/z', exist_ok=True)
MIME = {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'webp': 'image/webp', 'gif': 'image/gif', 'mp4': 'video/mp4', 'mov': 'video/quicktime',
        'm4v': 'video/mp4', 'webm': 'video/webm', 'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'ogg': 'audio/ogg', 'm4a': 'audio/mp4'}


def load():
    return json.load(open(ST)) if os.path.exists(ST) else {'items': [], 'balance': None, 'balance_at': ''}


def save(s): json.dump(s, open(ST + '.tmp', 'w'), ensure_ascii=False, indent=1); os.replace(ST + '.tmp', ST)


def item(s, rid): return next((x for x in s['items'] if x['rid'] == rid), None)


def job(j): return json.load(open(Z + f'jobs/{j}.json'))


def work(rid): w = Z + rid + '/'; os.makedirs(w + 'in', exist_ok=True); os.makedirs(w + 'out', exist_ok=True); return w


def month_used(s):
    m = NOW.strftime('%Y-%m')
    return sum(float(x.get('used') or 0) for x in s['items'] if x.get('state') == 'done' and (x.get('done_at') or '').startswith(m))


def push():
    s = load()
    pub = {'balance': s.get('balance'), 'balance_at': s.get('balance_at', ''), 'month_used': month_used(s), 'at': NOW.strftime('%m-%d %H:%M'),
           'items': [{k: x.get(k) for k in ('rid', 'by', 'model', 'media', 'prompt', 'opts', 'nref', 'state', 'credits', 'used', 'review', 'files', 'err', 'at', 'done_at', 'new_credits')}
                     for x in sorted(s['items'], key=lambda x: x['rid'], reverse=True)[:40]]}
    p = Z + 'public.json'; json.dump(pub, open(p, 'w'), ensure_ascii=False)
    subprocess.run([NODE, R + 'scripts/blob.mjs', 'putjson', 'zcre.json', p], cwd=R)


def ref_image(i):   # 레퍼런스 카드 대표 이미지(복각하기와 같은 곳에서 찾음)
    for q in (R + f'site/m/L{i}.jpg', R + f'site/m/A{i}.jpg', R + f'data/ref_{i}.jpg', R + f'site/m/{i}.jpg'):
        if os.path.exists(q): return q
    for q in glob.glob(R + f'site/m/*{i}*.jpg')[:1]: return q
    return None


cmd = sys.argv[1]; s = load()
if cmd == 'new':   # 견적 요청 접수
    j = job(sys.argv[2]); rid = sys.argv[2]
    if not item(s, rid):
        s['items'].append({'rid': rid, 'by': j.get('by', ''), 'model': j['model'], 'media': j.get('media', ''), 'prompt': j.get('prompt', ''), 'opts': j.get('opts', ''),
                           'refs': j.get('refs', []), 'assets': j.get('assets', []), 'nref': len(j.get('refs', [])) + len(j.get('assets', [])), 'state': 'quoting', 'at': NOW.strftime('%m-%d %H:%M')})
        save(s)
elif cmd == 'prep':   # 참조 파일 준비 + brief.json
    rid = sys.argv[2]; x = item(s, rid); w = work(rid); files = []
    for k, a in enumerate(x.get('assets', []), 1):
        q = w + f"in/F{k}.{a['ext']}"
        if not os.path.exists(q): subprocess.run([NODE, R + 'scripts/blob.mjs', 'fetchup', a['up'], q], cwd=R, capture_output=True)
        if os.path.exists(q): files.append({'path': q, 'role': f"올린 파일 {k} ({a.get('name', '')})"})
    for k, i in enumerate(x.get('refs', []), 1):
        q = ref_image(i)
        if q: shutil.copy(q, w + f'in/R{k}.jpg'); files.append({'path': w + f'in/R{k}.jpg', 'role': f'레퍼런스 카드 {k}(id {i}) 대표 이미지'})
    for f in files:
        ext = f['path'].rsplit('.', 1)[-1].lower(); ct = MIME.get(ext, 'application/octet-stream')
        f.update(filename=os.path.basename(f['path']), content_type=ct, media_type=ct.split('/')[0], size_bytes=os.path.getsize(f['path']))
    json.dump({'rid': rid, 'model_name': x['model'], 'media': x['media'], 'prompt': x['prompt'], 'opts': x['opts'], 'files': files,
               'idempotency_key': 'wm-adref-' + rid, 'work': w}, open(w + 'brief.json', 'w'), ensure_ascii=False, indent=1)
elif cmd == 'quoted':   # Claude 가 쓴 quote.json 반영(quote_token 은 로컬에만)
    rid = sys.argv[2]; x = item(s, rid); q = Z + rid + '/quote.json'
    r = json.load(open(q)) if os.path.exists(q) else {'ok': False, 'reason': '견적 결과가 없어요(Claude 실행 실패)'}
    if r.get('ok'): x.update(state='quoted', credits=r.get('credits'), review=r.get('review', ''), quoted_at=NOW.isoformat())
    else: x.update(state='failed', err=r.get('reason', '견적 실패'))
    if r.get('balance') is not None: s['balance'] = r['balance']; s['balance_at'] = NOW.strftime('%m-%d %H:%M')
    save(s)
elif cmd == 'approve':   # 승인 요청 → 견적 상태인지 확인하고 생성 대기로. 출력: 진행할 rid(없으면 빈 줄)
    j = job(sys.argv[2]); x = item(s, j.get('rid', ''))
    if x and x['state'] in ('quoted', 'price_up'):
        x.update(state='running', approved_by=j.get('by', ''), approved_credits=(x.get('new_credits') or x.get('credits'))); save(s)
        json.dump({'credits_max': x['approved_credits'], 'by': j.get('by', '')}, open(Z + x['rid'] + '/approved.json', 'w'))
        print(x['rid'])
    else: print('')
elif cmd == 'ran':   # 생성 결과 반영 → 결과 파일 site/z/ 로
    rid = sys.argv[2]; x = item(s, rid); w = Z + rid + '/'; q = w + 'result.json'
    r = json.load(open(q)) if os.path.exists(q) else {'ok': False, 'reason': '생성 결과가 없어요(Claude 실행 실패) — ZCRE 기록에서 상태를 확인해야 해요'}
    if r.get('ok'):
        out = []
        for k, f in enumerate(r.get('files', []), 1):
            src = f.get('view_path') or f.get('path')
            if not src or not os.path.exists(src): continue
            ext = src.rsplit('.', 1)[-1].lower(); dst = f'z/{rid}_{k}.{ext}'
            shutil.copy(src, R + 'site/' + dst)
            out.append({'url': dst, 'media': f.get('media') or MIME.get(ext, 'image/').split('/')[0]})
            dl = os.path.expanduser(f'~/Downloads/ZCRE/{rid}_{k}.' + (f.get('path') or src).rsplit('.', 1)[-1])   # 원본은 맥에도 보관
            os.makedirs(os.path.dirname(dl), exist_ok=True)
            if f.get('path') and os.path.exists(f['path']): shutil.copy(f['path'], dl)
        x.update(state='done' if out else 'failed', files=out, used=r.get('credits_used', x.get('approved_credits')), request_id=r.get('request_id', ''),
                 done_at=NOW.isoformat(), err='' if out else '결과 파일을 못 받았어요')
    elif r.get('reason') == 'price_up':
        x.update(state='price_up', new_credits=r.get('credits'), err=f"견적이 {x.get('credits')} → {r.get('credits')} 크레딧으로 올라서 멈췄어요. 다시 승인하면 생성해요")
    else: x.update(state='failed', err=r.get('reason', '생성 실패'), request_id=r.get('request_id', ''))
    if r.get('balance') is not None: s['balance'] = r['balance']; s['balance_at'] = NOW.strftime('%m-%d %H:%M')
    save(s)
elif cmd == 'owner':   # 견적을 만든 사람(견적 토큰은 그 사람 계정 것이라 생성도 그 맥에서)
    x = item(s, sys.argv[2]); print((x or {}).get('by', ''))
elif cmd == 'cancel':
    j = job(sys.argv[2]); x = item(s, j.get('rid', ''))
    if x and x['state'] in ('quoted', 'price_up', 'failed'): x['state'] = 'cancelled'; save(s)
elif cmd == 'fail':
    x = item(s, sys.argv[2])
    if x: x.update(state='failed', err=sys.argv[3]); save(s)
elif cmd == 'balance':   # 잔액만 갱신: zcre.py balance <숫자>
    s['balance'] = float(sys.argv[2]); s['balance_at'] = NOW.strftime('%m-%d %H:%M'); save(s)
if cmd in ('new', 'quoted', 'approve', 'ran', 'cancel', 'fail', 'push', 'balance'): push()
