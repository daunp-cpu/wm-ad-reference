"""Claude 직접 복각 — 요청 1건을 Claude 가 바로 쓸 수 있게 준비(레퍼런스·첨부 에셋 내려받기, 메모·기획안 정리) → brief.json.
사용: python3 -I claude_prep.py <요청.json> <작업폴더>
요청 type: bokgak(복각하기·추가하고 바로 복각) / retry(실패 카드 다시 복각) / revise(수정하기)"""
import json, os, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
bk = {}; exec(compile(open(HERE + '/bokgak.py').read().replace('\nmain()\n', '\n'), HERE + '/bokgak.py', 'exec'), bk)   # 함수만 가져오기
R = bk['R']; BV = bk['BV']
KST = datetime.timezone(datetime.timedelta(hours=9)); NOW = datetime.datetime.now(KST)
job = json.load(open(sys.argv[1])); W = sys.argv[2]; os.makedirs(W, exist_ok=True)
rv = json.load(open(R + 'data/review.json')) if os.path.exists(R + 'data/review.json') else []
SITE = 'BH(오브휴)' if 'bh-reference' in R else 'SOOO'
brief = {'site': SITE, 'root': R, 'job': job.get('job', ''), 'type': job.get('type', 'bokgak'), 'by': job.get('by') or '다운', 'work': W,
         'facts': bk['FACTS'], 'check': bk['CHECK'], 'default_landing': bk['DEFAULT'], 'product_photos': bk['PRODUCT'], 'items': [],
         'command': job.get('command', '')}   # 복각 창 '명령어 입력'
_BR = json.load(open(R + 'data/brands.json')) if os.path.exists(R + 'data/brands.json') else {}   # 2026-11-10 브랜드(SOOO·FnL·칸디데)
def _brand_ctx(b):
    brief['brand'] = b if b in _BR else 'SOOO'; bc = _BR.get(brief['brand'], {})
    brief['brand_info'] = {k: bc.get(k) for k in ('label', 'account', 'page_label', 'shop', 'memos', 'notes') if bc.get(k)}
    if brief['brand'] != 'SOOO':   # SOOO 고정값(샴푸 근거·사진·108 랜딩)이 다른 브랜드에 섞이지 않게
        brief['facts'] = bc.get('facts', ''); brief['check'] = bc.get('check', ''); brief['default_landing'] = bc.get('default_landing', ''); brief['product_photos'] = bc.get('product_photos', [])
        brief['site'] = bc.get('label', brief['brand'])   # (위 command = 다운이 Claude 에게 직접 쓰는 편집 지시, 최우선)
def assets_of(it=None):
    out = [{k: u.get(k) for k in ('lab', 'kind', 'path', 'img', 'name', 'dur')} for u in bk['USER']]
    docs = [{k: d.get(k) for k in ('lab', 'name', 'path', 'text')} for d in bk['DOCS']]
    return out, docs, bk['UNOTE'][0]
def item_brief(it):
    bk['item_assets'](it); ua, docs, note = assets_of()
    cr = json.load(open(R + 'data/custom_refs.json')) if os.path.exists(R + 'data/custom_refs.json') else []
    c = next((x for x in cr if x['id'] == str(it['id'])), {})
    vid = BV.ref_video(it) if it.get('dur') else None
    return {'ref_id': str(it['id']), 'ref_page': it.get('page', ''), 'ref_text': (it.get('t') or '')[:600], 'ref_days': it.get('days'),
            'ref_kind': ('영상 ' + it['dur']) if it.get('dur') else '이미지', 'ref_video': vid, 'ref_image': bk['ref_image'](it),
            'ref_memo': c.get('memo', ''), 'landing': it.get('landing') or brief.get('default_landing') or bk['DEFAULT'], 'assets': ua, 'docs': docs, 'asset_note': note,
            'item': {k: v for k, v in it.items() if k not in ('imgs',)}}

t = brief['type']
_brand_ctx(job.get('brand') or 'SOOO')
if t in ('bokgak', 'retry'):
    if t == 'retry':   # 실패 카드의 '다시 복각하기' — 그때 설정 그대로
        old = next((x for x in rv if not x.get('ok') and x.get('job') == job['fjob'] and str(x.get('ref_id')) == str(job['fref'])), None)
        rt = (old or {}).get('retry') or {}
        it = rt.get('item') or {'id': str(job['fref']), 'page': (old or {}).get('ref_page', '')}
        bk['JOB_USER'][:] = [u for u in rt.get('user', []) if os.path.exists(u.get('img') or u.get('path') or '')]; bk['JOB_NOTE'][0] = rt.get('note', '')
        from refdocs import doc_text
        bk['JOB_DOCS'][:] = [{**d, 'text': doc_text(d['path'])} for d in rt.get('docs', []) if os.path.exists(d['path'])]
        brief['command'] = brief['command'] or rt.get('command', '')
        _brand_ctx(rt.get('brand') or (old or {}).get('brand') or job.get('brand') or 'SOOO')
        brief['by'] = rt.get('by') or (old or {}).get('by') or brief['by']; brief['retry_of'] = {'fjob': job['fjob'], 'fref': str(job['fref'])}
        items = [it]
    else:
        bk['fetch_user_assets'](job)
        bk['JOB_USER'][:] = [dict(u) for u in bk['USER']]; bk['JOB_NOTE'][0] = bk['UNOTE'][0]; bk['JOB_DOCS'][:] = [dict(d) for d in bk['DOCS']]
        items = job.get('items') or []
    for it in items: brief['items'].append(item_brief(it))
elif t == 'revise':
    rec = next(x for x in rv if x['date'] == job['date'] and x.get('no') == job['no'] and x.get('ok'))
    vs = rec.get('versions') or [{'v': 1, 'img': rec['img'], 'plan': rec.get('plan', {}), 'mp4': (rec.get('media') or {}).get('mp4')}]
    base = next((v for v in vs if v['v'] == job.get('base')), None) or next(v for v in vs if v['v'] == rec.get('cur', 1))
    chain, seen, v = [], set(), base
    while v and v['v'] not in seen:
        seen.add(v['v']); chain.append(v.get('feedback')) if v.get('feedback') else None; v = next((x for x in vs if x['v'] == v.get('from')), None)
    newu = []
    if job.get('assets'): bk['fetch_user_assets']({**job, 'asset_note': ''}, 'F'); newu, ndocs, _ = assets_of()
    else: ndocs = []
    _brand_ctx(rec.get('brand') or 'SOOO')
    # 2026-11-11 다운: 수정 요청엔 요청자가 안 와서 전부 '다운'(=다운 계정)으로 돌았다(화영·근형 수정 25건).
    # → 소재 주인(카드의 by)을 요청자로 삼아 그 사람 맥으로 보낸다. 이전 대화도 그 맥에 있다.
    if not job.get('by') and rec.get('by'): brief['by'] = rec['by']
    brief.update(date=rec['date'], no=rec['no'], feedback=job.get('feedback', ''), prev_feedback=chain[::-1],
                 base_version=base['v'], base_img=R + 'site/' + base['img'], base_mp4=(R + 'site/' + base['mp4']) if base.get('mp4') else None,
                 kind=rec.get('kind') or 'image', plan=base.get('plan', {}), body=rec.get('body', ''), landing=rec.get('landing'), landing_title=rec.get('landing_title'),
                 ref=item_brief({'id': rec['ref_id'], 'page': rec.get('ref_page', ''), 'dur': (rec.get('ref_kind') or '').replace('영상 ', '') if (rec.get('ref_kind') or '').startswith('영상') else None, 'landing': rec.get('landing')}),
                 new_assets=newu, new_docs=ndocs)
def prewarm():
    """Claude 가 시작하자마자 쓰는 것들을 미리 만들어 둠(시간 단축): 0.5초 시트·컷 경계·대표 프레임."""
    import subprocess, re
    P = os.path.join(W, 'pre'); os.makedirs(P, exist_ok=True); out = {}
    def sheet(src, name):
        q = f'{P}/{name}_sheet.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', 'fps=2,scale=200:-1,tile=8x8', '-frames:v', '1', q], timeout=180)
        cuts = subprocess.run(['ffmpeg', '-i', src, '-vf', "scale=270:-1,select='gt(scene,0.2)',metadata=print", '-an', '-f', 'null', '-'], capture_output=True, text=True, timeout=300).stderr
        cut = [round(float(x), 2) for x in re.findall(r'pts_time:([0-9.]+)', cuts)]
        return {'sheet': q if os.path.exists(q) else None, 'cuts': cut}
    vids = [(it.get('ref_video'), 'ref') for it in brief.get('items', [])] + [((brief.get('ref') or {}).get('ref_video'), 'ref'), (brief.get('base_mp4'), 'base')]
    for src, name in vids:
        if src and os.path.exists(src) and name not in out:
            try: out[name] = sheet(src, name)
            except Exception as e: out[name] = {'err': str(e)[:100]}
    # 2026-11-04 속도: 레퍼런스·지금 버전 받아쓰기(단어 시각)도 미리 — 맥 GPU, 모델 한 번만 띄움
    srcs = [(s_, n) for s_, n in vids if s_ and os.path.exists(s_)]
    seen = set(); srcs = [(s_, n) for s_, n in srcs if not (n in seen or seen.add(n))]
    if srcs:
        try:
            KIT = '/Users/daun/ad-reference/claude_kit'
            wavs = []
            for s_, n in srcs:
                w = f'{P}/{n}.wav'
                if subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', s_, '-vn', '-ac', '1', '-ar', '16000', w], timeout=120).returncode == 0 and os.path.getsize(w) > 2000: wavs.append((w, n))
            if wavs:
                r = subprocess.run([KIT + '/venv/mlxw/bin/python', '-I', KIT + '/mlxw.py', '--words'] + [w for w, _ in wavs], capture_output=True, text=True, timeout=600).stdout
                parts = r.split('## ') if len(wavs) > 1 else ['', wavs[0][0] + '\n' + r]
                for ptxt in parts[1:]:
                    head, _, body = ptxt.partition('\n'); n = next((n for w, n in wavs if head.strip() == w), None)
                    if n: open(f'{P}/{n}_words.txt', 'w').write(body); out.setdefault(n, {})['words'] = f'{P}/{n}_words.txt'
        except Exception as e: out['asr_err'] = str(e)[:100]
    return out
def google_ok():
    import subprocess
    g = next((x for x in (os.path.expanduser('~/.advideo/bin/gcloud'), os.path.expanduser('~/.local/bin/gcloud')) if os.path.exists(x)), 'gcloud')
    try: return subprocess.run([g, 'auth', 'print-access-token'], capture_output=True, timeout=30).returncode == 0
    except Exception: return False
if t == 'revise':
    bw = next((v.get('work') for v in vs if v['v'] == base['v']), None)
    if bw and os.path.isdir(bw): brief['base_work'] = bw   # 이전 버전 만든 작업 폴더(편집 코드·측정값·재료) — 이어서 고치기
    # 2026-11-04 속도: 이전 작업 폴더의 편집 코드·재료를 미리 복제(APFS 복제라 즉시·용량 0) → Claude 는 바로 고쳐서 렌더
    if bw and os.path.isdir(bw + '/w') and not os.path.exists(W + '/w'):
        import subprocess
        subprocess.run(['cp', '-cR', bw + '/w', W + '/w'])
        if os.path.isdir(W + '/w'): brief['base_copied'] = W + '/w'
if not google_ok():   # 구글 인증 만료면 드라이브·Vertex(Gemini·Veo) 막힘 → Claude 가 헤매지 않게 미리 알림
    brief['warn'] = '구글 인증 만료 — 드라이브 다운로드·Vertex(Gemini·Veo) 안 됨. data/drive_index.json 의 local 파일·로컬 에셋·ZCRE 로 만들고 note 에 적을 것'
    import subprocess; subprocess.run(['osascript', '-e', 'display notification "구글 로그인이 만료됐어요 — Claude 에게 재로그인 요청해주세요" with title "복각 사이트"'])
DI = R + 'data/drive_index.json'
if os.path.exists(DI): brief['drive_index'] = DI
try: brief['pre'] = prewarm()
except Exception as e: brief['pre'] = {'err': str(e)[:100]}
json.dump(brief, open(W + '/brief.json', 'w'), ensure_ascii=False, indent=1)
print(W + '/brief.json')
