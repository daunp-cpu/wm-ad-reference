"""레퍼런스 → SOOO 복각 소재 자동 생성. 사용: python3 -I bokgak.py job.json
1) Gemini가 레퍼런스(이미지+문구)를 분석해 SOOO용 복각안(소구점·후킹·이미지 지시) 작성
2) 나노바나나 프로가 레퍼런스 구도 + SOOO 실제 제품 사진으로 4:5 이미지 생성(1건 약 250원)
3) data/review.json 에 날짜별로 기록(광고 이름·본문·링크 초안 포함). 키는 파일에서 읽고 출력하지 않음."""
import base64, json, os, sys, re, hashlib, datetime, urllib.request, urllib.parse, urllib.error, mimetypes, time
R = '/Users/daun/ad-reference/'; KEY = open(os.path.expanduser('~/.config/gemini/key')).read().strip()
KST = datetime.timezone(datetime.timedelta(hours=9)); NOW = datetime.datetime.now(KST); D = NOW.strftime('%Y-%m-%d')
PRODUCT = [R + 'assets/샴푸앰플_흰배경.jpg', R + 'assets/샴푸_로고연출.jpg']
FACTS = """SOOO 스칼프처 샴푸 500ml (탈모 증상 완화 기능성) — 공식몰 1+1 70,000원→49,000원(개당 24,500원, '개당 2만원대').
쓸 수 있는 근거: 1회 사용 두피 온도 -4.5℃(㈜휴먼피부임상시험센터 21명), 피지 86.3% 감소, 각질 80.0% 감소, 정수리 냄새 57.8% 감소, 4주 탈락 모발 72.4% 감소,
스위스 로잔공대 출신 화학박사 개발, 국립낙동강생물자원관 기술이전 특허 성분(콩제비꽃 추출물), 해양심층수. 제품색: 뮤트 브라운핑크 펌프병 + 투명 라벤더 앰플, 브랜드 톤 연보라.
금지: 올리브영 1위·누적 10만 개(다른 제품 실적), '머리가 난다/자란다/발모/치료' 같은 의약품 표현, AI로 만든 비포·애프터 사진, 사용 전/후 비교 그림·일러스트(특히 모발이 늘어나 보이는 것), 빠진 머리카락·각질 클로즈업, 없는 사실(품절·재입고 등)을 지어내기, 별표(*)."""
sys.path.insert(0, R + 'scripts'); from landing import read_landing, DEFAULT
import cost as COST   # 이 사이트로 만든 소재의 AI 비용만 적는다
import bokgak_video as BV
def is_default(u):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(u or DEFAULT).query)
    return (u or DEFAULT).startswith('https://sooo.kr/') and q.get('product_no', ['108'])[0] == '108'
def camp_of(u, title=''):   # utm_campaign: 기본 상품은 스칼프처샴푸, 다른 상품은 상품명 줄임
    if is_default(u) or not title: return '스칼프처샴푸'
    t = re.sub(r'\[[^\]]*\]|\([^)]*\)', '', title.split('|')[-1]); t = re.sub(r'\d+\s*(ml|mL|ML|EA|개입).*$', '', t)
    return re.sub(r'[^0-9A-Za-z가-힣+]', '', t)[:20] or '스칼프처샴푸'
def with_utm(u, ymd, nn, kt='image', camp='스칼프처샴푸'):
    base = re.sub(r'([?&])utm_[a-z]+=[^&]*', r'\1', u).rstrip('?&').replace('?&', '?').replace('&&', '&')
    return base + ('&' if '?' in base else '?') + f'utm_source=meta&utm_medium=display&utm_campaign={camp}&utm_content={ymd}_{nn}_{kt}'
def landing_ctx(u):   # 다른 상품 랜딩 → 상품 사실·사진(대표+상세)
    L = read_landing(u); d = R + 'data/landing/' + hashlib.md5(u.encode()).hexdigest()[:10] + '/'; os.makedirs(d, exist_ok=True); got = []
    for i, x in enumerate([L['image']] + L['images'][:5]):
        if not x: continue
        try:
            b = urllib.request.urlopen(urllib.request.Request(x, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read()
            q = d + f'{i}' + os.path.splitext(urllib.parse.urlparse(x).path)[1]; open(q, 'wb').write(b); got.append(q)
        except Exception: pass
    if not got: raise RuntimeError('랜딩 상품 사진을 못 받음')
    from PIL import Image
    for q in got:   # 상세컷이 너무 길면 Gemini 입력용으로 줄임
        im = Image.open(q).convert('RGB'); im.thumbnail((1200, 3000)); im.save(q + '.jpg', quality=85)
    got = [q + '.jpg' for q in got]
    facts = (f"이번 광고 상품(랜딩): {L['title']} / 판매가 {L['price']}원 / 랜딩 {u}\n랜딩 문구: {L['text'][:1500]}\n"
             "근거는 랜딩 문구와 첨부한 상품 상세 이미지에서 확인되는 것만 쓴다(없는 수치·인증·순위를 지어내지 않는다).\n"
             "금지: '머리가 난다/자란다/발모/치료' 같은 의약품 표현, AI로 만든 비포·애프터 사진, 사용 전/후 비교 그림·일러스트(특히 모발이 늘어나 보이는 것), 빠진 머리카락·각질 클로즈업, 없는 사실(품절·재입고 등) 지어내기, 별표(*).")
    return {'facts': facts, 'product': got[:1], 'detail': got[1:4], 'title': L['title']}
CHECK = '✔ 화학박사가 개발한 두피 딥클렌징 샴푸\n✔ 1회 사용 후 두피 온도 -4.5°C (㈜휴먼피부임상시험센터, 21명)\n✔ 탈모 증상 완화 기능성\n✔ 국립낙동강생물자원관 기술이전 특허 성분\n✔ 500ml 대용량 2병'

def _cost(model, parts, cfg, r):
    try:
        if 'IMAGE' in (cfg.get('responseModalities') or []):
            nout = sum(1 for p in (r.get('candidates') or [{}])[0].get('content', {}).get('parts', []) if p.get('inlineData') or p.get('inline_data'))
            COST.log(R, model, out_img=nout, in_img=sum(1 for p in parts if 'inline_data' in p or 'inlineData' in p))
        else:
            u = r.get('usageMetadata') or {}
            COST.log(R, model, in_tok=u.get('promptTokenCount', 0), out_tok=u.get('candidatesTokenCount', 0))
    except Exception: pass   # 비용 기록 실패가 소재 제작을 막으면 안 된다

# 2026-10-20 AI Studio 월 한도가 차서 Vertex(같은 회사 결제계정, 강제 한도 없음)로 돌림. ~/.config/ad-reference/use_vertex 를 지우면 AI Studio 로 돌아감.
VERTEX = os.path.exists(os.path.expanduser('~/.config/ad-reference/use_vertex'))
VX_MODEL = {'nano-banana-pro-preview': 'gemini-3-pro-image'}   # Vertex 쪽 이름이 다른 모델
_VXT = {'tok': '', 'at': 0}
def _vx_token():
    if time.time() - _VXT['at'] > 1800 or not _VXT['tok']:
        import subprocess
        _VXT['tok'] = subprocess.check_output([os.path.expanduser('~/.local/bin/gcloud'), 'auth', 'print-access-token'], timeout=60).decode().strip(); _VXT['at'] = time.time()
    return _VXT['tok']
def gem(model, parts, cfg, timeout=300):
    body = {'contents': [{'role': 'user', 'parts': parts}], 'generationConfig': cfg}
    if VERTEX:
        url = f"https://aiplatform.googleapis.com/v1/projects/gen-lang-client-0027494071/locations/global/publishers/google/models/{VX_MODEL.get(model, model)}:generateContent"
        hdr = {'Authorization': 'Bearer ' + _vx_token(), 'Content-Type': 'application/json'}
    else:
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'; hdr = {'x-goog-api-key': KEY, 'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdr, method='POST')
    WAIT = [20, 40, 60, 90, 120]   # 서버 몰림(429)·일시 오류면 이만큼 기다렸다 다시(최대 6번)
    for k in range(6):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
            _cost(model, parts, cfg, r)   # 이 사이트로 만든 소재에 든 돈만 센다
            return r
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:300]
            if e.code in (429, 500, 503) and k < 5: print(f'Gemini {e.code} — {WAIT[k]}초 뒤 다시 시도({k + 2}/6)', flush=True); time.sleep(WAIT[k]); continue
            raise RuntimeError(f'HTTP {e.code}: {msg}')
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:   # 응답 시간 초과·연결 끊김도 두 번 더
            if k < 5: time.sleep(WAIT[k]); continue
            raise RuntimeError(f'Gemini 응답 없음(6번 시도): {e}')
def img_part(p):
    return {'inline_data': {'mime_type': mimetypes.guess_type(p)[0] or 'image/jpeg', 'data': base64.b64encode(open(p, 'rb').read()).decode()}}
def ref_image(it):
    for q in (R + f'data/ref_{it["id"]}_sheet.jpg', R + f'data/ref_{it["id"]}.jpg'):   # 직접 추가한 레퍼런스(영상은 장면 4컷)
        if str(it['id'])[0] in '89' and os.path.exists(q): return q   # 9 = 직접 추가, 8 = 소재공유방
    for u in [it.get('poster')] + list(reversed(it.get('imgs') or [])):
        if not u: continue
        try:
            data = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.facebook.com/'}), timeout=40).read()
            if len(data) > 20000: q = R + f'data/ref_{it["id"]}.jpg'; open(q, 'wb').write(data); return q
        except Exception: pass
    for p in (R + f'site/m/L{it["id"]}.jpg', R + f'site/m/A{it["id"]}.jpg'):   # A = 대행 계정 고효율 카드 사진
        if os.path.exists(p): return p
    return None

USER = []; UNOTE = ['']; DOCS = []   # DOCS = 참고 문서(기획안 등) [{lab,name,path,text}]   # 다운이 복각하기 창에서 올린 '쓸 에셋' [{i,kind,path,img,dur,name}], 메모
def fetch_user_assets(job, pre='U'):   # pre = 번호 앞글자(복각 창 U, 수정할 때 F)
    import subprocess
    USER.clear(); DOCS.clear(); UNOTE[0] = job.get('asset_note', '')
    from refdocs import doc_text
    d = R + f"data/user_assets/{job['job']}/"; os.makedirs(d, exist_ok=True)
    FF, FP = '/Users/daun/.local/bin/ffmpeg', '/Users/daun/.local/bin/ffprobe'
    for i, a in enumerate(job.get('assets') or [], 1):
        out = d + f"{i}.{a['ext']}"
        subprocess.run(['node', R + 'scripts/blob.mjs', 'fetchup', a['up'], out], cwd=R, capture_output=True, timeout=600)
        if not os.path.exists(out) or os.path.getsize(out) < 500: print('에셋 받기 실패', i, a.get('name'), flush=True); continue
        u = {'i': i, 'lab': f'{pre}{i}', 'kind': a['kind'], 'path': out, 'name': a.get('name', ''), 'dur': 0}
        if a['kind'] == 'audio':   # 나레이션·음악 파일(2026-11-04) — 그대로 경로만, 미리보기 이미지 없음
            u['dur'] = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout or 0)
            USER.append(u); subprocess.run(['node', R + 'scripts/blob.mjs', 'delup', a['up']], cwd=R, capture_output=True, timeout=300); continue
        if a['kind'] == 'doc':   # 기획안 등 문서 = 지시서
            DOCS.append({'lab': f'{pre}{i}', 'name': a.get('name', ''), 'path': out, 'text': doc_text(out)})
            subprocess.run(['node', R + 'scripts/blob.mjs', 'delup', a['up']], cwd=R, capture_output=True, timeout=300); continue
        if a['kind'] == 'video':
            u['dur'] = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out], capture_output=True, text=True).stdout or 0)
            u['img'] = d + f'{i}_frame.jpg'; subprocess.run([FF, '-y', '-v', 'error', '-ss', str(min(1.0, u['dur'] / 2)), '-i', out, '-frames:v', '1', '-q:v', '2', u['img']])
        else:
            u['img'] = d + f'{i}.jpg'
            from PIL import Image
            try: im = Image.open(out); im.seek(0); im.convert('RGB').save(u['img'], quality=92)
            except Exception: subprocess.run(['sips', '-s', 'format', 'jpeg', out, '--out', u['img']], capture_output=True)   # HEIC 등
            u['path'] = u['img']
        if os.path.exists(u['img']): USER.append(u)
        subprocess.run(['node', R + 'scripts/blob.mjs', 'delup', a['up']], cwd=R, capture_output=True, timeout=300)
    if USER: print('쓸 에셋', len(USER), '개 받음', flush=True)
JOB_USER = []; JOB_NOTE = ['']; JOB_DOCS = []
def item_assets(it):   # 이 소재에 쓸 에셋 = 복각 창에서 올린 것 + 직접 추가 레퍼런스에 첨부해 둔 것
    import subprocess
    USER[:] = [dict(u) for u in JOB_USER]; UNOTE[0] = JOB_NOTE[0]; DOCS[:] = [dict(d) for d in JOB_DOCS]
    cr = json.load(open(R + 'data/custom_refs.json')) if os.path.exists(R + 'data/custom_refs.json') else []
    c = next((x for x in cr if x['id'] == str(it['id'])), None)
    if not c or not c.get('assets'): return
    FF, FP = '/Users/daun/.local/bin/ffmpeg', '/Users/daun/.local/bin/ffprobe'
    for a in c['assets']:
        f = a['file']
        if not os.path.exists(f): continue
        if a['kind'] == 'doc':
            from refdocs import doc_text
            DOCS.append({'lab': f"R{a.get('i', 0)}", 'name': a.get('name', ''), 'path': f, 'text': doc_text(f)}); continue
        u = {'i': len(USER) + 1, 'lab': f"R{a.get('i', 0)}", 'kind': a['kind'], 'path': f, 'name': a.get('name', ''), 'dur': 0}
        if a['kind'] == 'audio':   # 나레이션·음악 파일(2026-11-04)
            u['dur'] = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True).stdout or 0)
            USER.append(u); continue
        if a['kind'] == 'video':
            u['dur'] = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f], capture_output=True, text=True).stdout or 0)
            u['img'] = f.rsplit('.', 1)[0] + '_frame.jpg'
            if not os.path.exists(u['img']): subprocess.run([FF, '-y', '-v', 'error', '-ss', str(min(1.0, u['dur'] / 2)), '-i', f, '-frames:v', '1', '-q:v', '2', u['img']])
        else:
            u['img'] = f.rsplit('.', 1)[0] + '_v.jpg'
            if not os.path.exists(u['img']):
                from PIL import Image
                try: im = Image.open(f); im.seek(0); im.convert('RGB').save(u['img'], quality=92)
                except Exception: subprocess.run(['sips', '-s', 'format', 'jpeg', f, '--out', u['img']], capture_output=True)
            u['path'] = u['img']
        if os.path.exists(u['img']): USER.append(u)
    if c.get('asset_note'): UNOTE[0] = ((f'복각 창 메모(U번호 기준): {UNOTE[0]} / ' if UNOTE[0] else '') + f"레퍼런스 메모(R번호 기준): {c['asset_note']}")
    print('레퍼런스에 첨부된 에셋', len(c['assets']), '개 같이 씀', flush=True)
def pdf_parts():   # PDF 기획안은 Gemini 에 파일째
    return [{'inline_data': {'mime_type': 'application/pdf', 'data': base64.b64encode(open(d['path'], 'rb').read()).decode()}} for d in DOCS if d['path'].lower().endswith('.pdf') and os.path.getsize(d['path']) < 15_000_000]
def user_txt():
    dtxt = ''.join(f"\n[참고 문서 {d['lab']} {d['name'][:30]}]{' (PDF 첨부)' if d['path'].lower().endswith('.pdf') else ''}\n{d['text'][:6000]}\n" for d in DOCS)
    if DOCS: dtxt = '\n★ 다운이 올린 참고 문서(기획안 등). 화면 소재가 아니라 지시서다 — 적힌 소구점·카피·장면 흐름·자막을 최우선으로 따른다:' + dtxt
    if not USER: return dtxt
    lst = ', '.join(f"{u.get('lab') or 'U%d' % u['i']}({'영상 %.1f초' % u['dur'] if u['kind'] == 'video' else '사진'}{' ' + u['name'][:20] if u['name'] else ''})" for u in USER)
    return f"\n다운(마케터)이 이번 소재에 꼭 쓰라고 고른 에셋 {len(USER)}개를 맨 뒤에 첨부했다: {lst}. 제품·장면은 이 에셋을 최우선으로 쓰고, 이 에셋에 있는 실제 제품·인물·장면을 그대로 살린다.{(' 다운 메모: ' + UNOTE[0]) if UNOTE[0] else ''} 첨부 사진 중 글씨가 빽빽한 문서·기획안 캡처는 화면 소재로 쓰지 말고 지시서로 읽는다.\n" + dtxt
def plan(it, ref, ctx=None):
    extra_fields = ',"title":"광고 제목(헤드라인) 한 줄","body":"광고 본문 전체(후킹 2줄 + 근거 체크 3~5줄 + 구매 유도, 줄바꿈은 \\n)"' if ctx else ''
    prompt = f"""너는 한국 메타 광고 크리에이티브 디렉터다. 아래 레퍼런스 광고(첨부 이미지 + 문구)의 '형식'을 그대로 빌려 {ctx['title'] if ctx else 'SOOO 스칼프처 샴푸'} 광고로 복각한다.
{ctx['facts'] if ctx else FACTS}
레퍼런스 브랜드/페이지: {it.get('page','')}
레퍼런스 문구: {(it.get('t') or '')[:600]}
레퍼런스 형식: {'영상 '+it['dur'] if it.get('dur') else '이미지'} · {it.get('days','?')}일째 게재 중
규칙: 레퍼런스의 구도·색 배치·글자 위치·연출 장치(가격 강조, 말풍선, 뉴스 자막, 사과문 등)를 최대한 똑같이 따라 하되 내용은 SOOO 근거로만 채운다. 원본 브랜드명·로고·인물 얼굴은 쓰지 않는다.{' 첫 첨부는 레퍼런스, 그 뒤 첨부는 이번 상품 사진·상세페이지다.' if ctx else ''}
{user_txt()}JSON만 출력:
{{"soguo":"광고 이름에 쓸 소구점 2~6자(한글, 공백 없이)","format":"레퍼런스 형식 한 줄 설명","why":"레퍼런스가 오래 도는 이유 한 줄","hook1":"본문 후킹 1줄(이모지 0~1개)","hook2":"본문 후킹 2줄째","headline":"이미지에 크게 넣을 한국어 문구(짧게, 줄바꿈은 \\n)","sub":"이미지에 작게 넣을 한국어 보조 문구(가격 등, 짧게)","image_prompt":"이미지 생성 지시(영어). 레퍼런스의 레이아웃을 구체적으로 묘사하고, 두 번째·세 번째 첨부(SOOO 제품 사진)의 샴푸·앰플을 그대로 넣으라고 쓸 것. 한국어 문구는 headline/sub 를 그대로 정확히 렌더링하라고 쓸 것"{extra_fields}}}"""
    extra = [img_part(x) for x in (ctx['product'] + ctx['detail'])] if ctx else []
    r = gem('gemini-3.1-pro-preview', [img_part(ref)] + extra + [img_part(u['img']) for u in USER] + pdf_parts() + [{'text': prompt}], {'temperature': 0.4, 'responseMimeType': 'application/json'})
    out = json.loads(r['candidates'][0]['content']['parts'][0]['text'])
    return out[0] if isinstance(out, list) else out   # 가끔 [{...}] 로 옴

def make_image(pl, ref, out, product=None):
    p = (pl['image_prompt'] + f"\nRender this Korean text exactly, crisp and correctly spelled: headline: \"{pl['headline']}\" ; small text: \"{pl['sub']}\"."
         "\nThe first image is the layout/style reference only (do not copy its brand, logo, people or text). The other images are the real products: keep their exact shape, color, pump and label. 4:5 vertical ad, photorealistic, clean, no watermark.")
    if USER: p += f"\nThe LAST {len(USER)} images are assets the marketer chose for this ad: use them as the main source (their real product, person and scene) and follow this note: {UNOTE[0] or '-'}."
    r = gem('nano-banana-pro-preview', [img_part(ref)] + [img_part(x) for x in (product or PRODUCT)] + [img_part(u['img']) for u in USER] + [{'text': p}],
            {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': '4:5'}}, timeout=400)
    for c in r.get('candidates', []):
        for part in c.get('content', {}).get('parts', []):
            b = part.get('inline_data') or part.get('inlineData')
            if b: open(out, 'wb').write(base64.b64decode(b['data'])); return True
    return False

PROG = {'i': 0, 'n': 1, 't0': 0, 'exp': 100}   # 진행률 표시용(몇 번째 소재 / 전체, 이 소재 시작 시각, 예상 초)
def step(job, it, msg, pct=0):   # 검수 페이지 진행 카드용(실패해도 무시). pct = 이 소재 안에서 진행 %
    try:
        import subprocess
        st = {'state': 'working', 'job': job, 'cur': str(it['id']), 'step': msg, 'pct': pct, 'i': PROG['i'], 'n': PROG['n'], 't0': PROG['t0'], 'exp': PROG['exp'], 'now': time.time()}
        subprocess.run(['node', R + 'scripts/blob.mjs', 'status', json.dumps(st, ensure_ascii=False)], timeout=60, cwd=R, capture_output=True)
    except Exception: pass

FULL = {'다운': '박다운', '화영': '김화영', '도현': '박도현', '근형': '박근형', '형태': '유형태', '다솔': '다솔'}   # 광고 이름 담당자 칸
BV.GEM, BV.IMGP = gem, img_part   # 영상 장면 재현(나노바나나 첫 화면)에 씀
class Cancel(Exception): pass
def cancelled(jid):
    try:
        import subprocess
        return subprocess.run(['node', R + 'scripts/blob.mjs', 'cancelled', jid], cwd=R, capture_output=True, text=True, timeout=60).stdout.strip() == '1'
    except Exception: return False

def main():
    job = json.load(open(sys.argv[1])); rv = json.load(open(R + 'data/review.json')) if os.path.exists(R + 'data/review.json') else []
    if job.get('type') == 'retry':   # 실패 카드의 '다시 복각하기' — 그때 설정 그대로
        old = next((x for x in rv if not x.get('ok') and x.get('job') == job['fjob'] and str(x.get('ref_id')) == str(job['fref'])), None)
        if not old: print('다시 할 실패 기록 없음'); return
        rt = old.get('retry') or {}
        it = rt.get('item')
        if not it:   # 예전 실패(설정 저장 전) → 레퍼런스 페이지 정보로
            import re as _re
            mm = json.loads(_re.search(r'const META=(\{.*?\});Object', open(R + 'site/index.html').read(), _re.S).group(1))
            cm = json.loads(_re.search(r'CMETA=(\{.*?\});', open(R + 'site/index.html').read(), _re.S).group(1)) if 'CMETA=' in open(R + 'site/index.html').read() else {}
            info = mm.get(str(job['fref'])) or cm.get(str(job['fref'])) or {'page': old.get('ref_page', '')}
            it = {'id': str(job['fref']), **info}
        it = {**it, 'again': True}; old['deleted'] = NOW.strftime('%m-%d %H:%M'); old['deleted_by'] = '다시 복각'
        job.update(items=[it], by=rt.get('by') or old.get('by') or job.get('by'), assets=[])
        json.dump(rv, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1)
        USER[:] = [dict(u) for u in rt.get('user', []) if os.path.exists(u.get('img') or u.get('path') or '')]; UNOTE[0] = rt.get('note', '')
        from refdocs import doc_text
        DOCS[:] = [{**d, 'text': doc_text(d['path'])} for d in rt.get('docs', []) if os.path.exists(d['path'])]
        JOB_USER[:] = [dict(u) for u in USER]; JOB_NOTE[0] = UNOTE[0]; JOB_DOCS[:] = [dict(d) for d in DOCS]; BV.USER = USER; BV.DOCS = DOCS
        print('다시 복각', it.get('page', '')[:20], f'에셋 {len(USER)}·문서 {len(DOCS)}', flush=True)
    else: fetch_user_assets(job); JOB_USER[:] = [dict(u) for u in USER]; JOB_NOTE[0] = UNOTE[0]; JOB_DOCS[:] = [dict(d) for d in DOCS]; BV.USER = USER; BV.DOCS = DOCS
    day = [x for x in rv if x['date'] == D and x.get('ok')]; os.makedirs(R + f'site/review/{D}', exist_ok=True)
    for k, it in enumerate(job['items']):
        PROG.update(i=k, n=len(job['items']), t0=time.time(), exp=110 if it.get('dur') else 100)   # 이미지 약 100초, 영상 약 110초
        if not it.get('again') and any(x['ref_id'] == str(it['id']) and x.get('ok') and not x.get('deleted') for x in rv): print('이미 복각한 레퍼런스라 건너뜀', it['id'], flush=True); continue   # 팀원끼리 겹침 방지
        if cancelled(job['job']): print('취소됨 — 남은 소재 건너뜀', flush=True); break
        item_assets(it); BV.UNOTE = UNOTE[0]   # 소재마다 쓸 에셋 다시 맞춤
        by = job.get('by') or '다운'
        rec = {'date': D, 'made': NOW.strftime('%H:%M'), 'job': job['job'], 'by': by, 'ref_id': str(it['id']), 'ref_page': it.get('page', ''), 'ref_days': it.get('days'),
               'ref_kind': '영상 ' + it['dur'] if it.get('dur') else '이미지', 'ref_text': (it.get('t') or '')[:300]}
        try:
            step(job['job'], it, '레퍼런스 분석 중', 5); ref = ref_image(it)
            if not ref: raise RuntimeError('레퍼런스 이미지를 못 받음')
            lu = it.get('landing') or DEFAULT; ctx = None if is_default(lu) else landing_ctx(lu)
            if ctx: step(job['job'], it, '랜딩 상품 읽는 중', 12)
            nn = f'{len(day) + 1:03d}'; vid = BV.ref_video(it) if it.get('dur') else None; kt = 'video' if vid else 'image'
            COST.CUR['date'], COST.CUR['no'] = D, nn   # 이 소재에 든 돈을 따로 셀 수 있게
            if vid:   # 영상 레퍼런스 → 드라이브 에셋 편집으로 영상 복각
                step(job['job'], it, '레퍼런스 영상 컷 분석 중', 15)
                ef = ',"title":"광고 제목 한 줄","body":"광고 본문 전체(줄바꿈은 \\n)"' if ctx else ''
                pl = BV.plan_video(gem, img_part, it, vid, ctx['facts'] if ctx else FACTS, ctx['product'] if ctx else PRODUCT, ef)
                if cancelled(job['job']): raise Cancel()
                step(job['job'], it, f"영상 편집 중 ({len(pl.get('cuts', []))}컷)", 55)
                pl['_ref'] = vid; pl['_user'] = [dict(u) for u in USER];   # 수정할 때도 같은 에셋 쓰게
                mp4 = R + f'site/review/{D}/{nn}.mp4'
                _nc = max(1, len(pl.get('cuts', [])))
                def _lg(m, _c=[0]):
                    print(m, flush=True); _c[0] += 1; step(job['job'], it, f'영상 편집 중 — {m}', 55 + int(40 * _c[0] / _nc))
                veo_s = BV.render(pl, mp4, ctx['product'] if ctx else PRODUCT, R + f'data/work/{D}_{nn}', log=_lg)
                out = R + f'site/review/{D}/{nn}.jpg'; BV.poster(mp4, out); rec.update(kind='video', media={'mp4': f'review/{D}/{nn}.mp4'}, veo_sec=veo_s)
            else:
                pl = plan(it, ref, ctx)
                if cancelled(job['job']): raise Cancel()
                step(job['job'], it, '이미지 만드는 중', 45)
                out = R + f'site/review/{D}/{nn}.jpg'
                if not make_image(pl, ref, out, ctx['product'] if ctx else None): raise RuntimeError('이미지 생성 실패')
                from PIL import Image
                im = Image.open(out).convert('RGB'); im.thumbnail((1080, 1350)); im.save(out, quality=90)
            yymmdd, ymd = NOW.strftime('%y%m%d'), NOW.strftime('%Y%m%d')
            v1 = {'v': 1, 'img': f'review/{D}/{nn}.jpg', 'plan': dict(pl), 'at': NOW.strftime('%m-%d %H:%M'), 'note': '처음 복각'}
            if vid: v1['mp4'] = f'review/{D}/{nn}.mp4'
            rec.update(no=nn, img=f'review/{D}/{nn}.jpg', ok=True, plan=pl, cur=1, versions=[v1],
                       ad_name=f"{yymmdd}_{nn} / {pl['soguo']} / {kt} / {FULL.get(by, '박다운')} / 뷰티매거진",
                       body=(pl.get('body') if ctx and pl.get('body') else f"[1+1🔥] 탈모샴푸 개당 2만원대!\n{pl['hook1']}\n{pl['hook2']}\n\n{CHECK}\n\n지금 공식몰에서 1+1로 만나보세요👇"),
                       landing=lu, landing_title=(ctx or {}).get('title', '스칼프처 샴푸 1+1 (108번)'), title=(pl.get('title') if ctx else '') or '',
                       link=with_utm(lu, ymd, nn, kt, camp=camp_of(lu, (ctx or {}).get('title', ''))))
            day.append(rec); print('완료', nn, pl['soguo'], flush=True)
        except Cancel:
            print('취소됨 — 만들기 전에 멈춤', flush=True); break
        except Exception as e:
            rec.update(ok=False, err=str(e)[:200], retry={'item': it, 'by': job.get('by'), 'user': [dict(u) for u in USER], 'docs': [{k: d[k] for k in ('lab', 'name', 'path')} for d in DOCS], 'note': UNOTE[0]}); print('실패', it['id'], e, flush=True)
        rv.append(rec); json.dump(rv, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1)
main()
