"""영상 레퍼런스 → 영상 복각(bokgak.py 가 불러 씀). 드라이브 에셋을 잘라 붙이고 한글 자막을 얹어 9:16 mp4.
Gemini 가 레퍼런스를 컷으로 뜯어 컷마다 고름: gen(레퍼런스 그 순간 화면을 나노바나나로 SOOO 버전 첫 화면 → Veo fast 로 같은 움직임) /
에셋(드라이브) / 제품 사진. Veo 1편 최대 16초. 색 보정 없음. 1편 약 3,000~3,500원."""
import base64, hashlib, json, os, subprocess, time, urllib.request, urllib.error
from PIL import Image, ImageDraw, ImageFont, ImageColor
R = '/Users/daun/ad-reference/'; A = '/Users/daun/Downloads/SOOO/SOOO_에셋/'
FF = '/Users/daun/.local/bin/ffmpeg'; FONT = '/Users/daun/Library/Fonts/Paperlogy-9Black.ttf'
import sys; sys.path.insert(0, R + 'scripts'); import cost as COST
W, H, FPS, VEO_MAX = 1080, 1920, 30, 40   # 10/20 다운: 없는 장면은 전부 AI 재현 → Veo 상한 40초
USER = []; UNOTE = ''; DOCS = []   # 다운이 복각하기 창에서 올린 '쓸 에셋'(bokgak.py 가 넣어 줌)
GEM = IMGP = None   # bokgak.py 가 Gemini 호출 함수를 넣어 줌(장면 재현 첫 화면용)
PRODUCT = []


def ref_video(it):
    """직접 올린 원본 → 광고 라이브러리 영상 주소 순으로 레퍼런스 영상 파일 찾기."""
    for ext in ('mp4', 'mov', 'm4v', 'webm'):
        q = R + f"data/custom/{it['id']}.{ext}"
        if os.path.exists(q): return q
    q = R + f"data/ref_{it['id']}.mp4"
    if os.path.exists(q): return q
    if it.get('video'):
        try:
            b = urllib.request.urlopen(urllib.request.Request(it['video'], headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read()
            if len(b) > 50000: open(q, 'wb').write(b); return q
        except Exception: pass
    return None


def plan_video(gem, img_part, it, vid, facts, product, extra_fields):
    small = vid.rsplit('.', 1)[0] + '_360.mp4'   # 분석용 작은 사본
    if not os.path.exists(small):
        subprocess.run([FF, '-y', '-v', 'error', '-i', vid, '-t', '60', '-vf', 'scale=-2:640,fps=15', '-c:v', 'libx264', '-crf', '30', '-c:a', 'aac', '-b:a', '64k', small], check=True)
    assets = json.load(open(R + 'data/assets.json'))
    alist = '\n'.join(f"{a['n']}. {a['name']} ({a['dur']}초{', 화면에 글자·자막 이미 있음 → 이 컷엔 자막 넣지 말 것' if a.get('text') else ''})" for a in assets)
    ulist = '\n'.join(f"{u.get('lab') or 'U%d' % u['i']}. {'영상 %.1f초' % u['dur'] if u['kind'] == 'video' else '사진'} {u['name'][:30]}" for u in USER)
    utxt = (f"\n★ 다운(마케터)이 이번 영상에 꼭 쓰라고 고른 에셋(맨 뒤 첨부, 영상은 대표 장면): \n{ulist}\n이 에셋을 드라이브 에셋·생성보다 최우선으로 쓴다: \"src\":\"user\",\"user\":\"라벨(예 U1, R2)\",\"from\":시작초." + (f" 다운 메모: {UNOTE}" if UNOTE else '') + "\n") if USER else ''
    dtxt = ''.join(f"\n[참고 문서 {d['lab']} {d['name'][:30]}]\n{d['text'][:6000]}\n" for d in DOCS)
    if DOCS: utxt += '\n★ 다운이 올린 참고 문서(기획안 등) — 화면 소재가 아니라 지시서다. 적힌 소구점·카피·장면 흐름·자막을 최우선으로 따른다:' + dtxt + '\n'
    prompt = f"""너는 한국 메타 릴스 광고 편집 감독이다. 첫 첨부 영상(레퍼런스)의 흐름을 그대로 따라 SOOO 광고 영상으로 복각한다.
{facts}
레퍼런스: {it.get('page', '')} · {(it.get('t') or '')[:400]}
1) 레퍼런스를 0.5초 단위로 보고 컷을 나눈다(컷 길이·순서·자막 위치·강조 방식을 그대로).
2) 목표는 레퍼런스와 최대한 똑같은 영상이다. 컷 화면은 다음 중 고른다.
 - "gen": 레퍼런스의 그 순간 화면(ref_t 초)을 구도·카메라·인물 동작·조명까지 그대로 다시 만든다. frame_prompt = 그 화면을 SOOO 버전으로 바꾼 첫 화면 묘사(제품이 나오면 SOOO 샴푸·앰플로), motion_prompt = 레퍼런스 그 컷의 움직임(카메라·인물·제품 움직임). ★ 기본은 무조건 gen — 레퍼런스 장면을 우리 제품으로 가장 똑같이 AI 재현한다. 합계 {VEO_MAX}초 이하(컷당 4~8초 단위로 생성 후 필요한 만큼 자름).
 - "asset": 두 번째 첨부 SOOO 드라이브 에셋이 레퍼런스 그 장면과 '완전히 똑같을 때만'(같은 구도·같은 행동·같은 피사체. 분위기만 비슷한 에셋을 끼워 넣는 짜집기는 금지; 번호+시작 초, 36·37 대표님 클립은 구간 잘라 쓰기).
 - "photo": 실제 제품 사진(세 번째부터, 0번부터) — 라벨이 크게 보여야 하는 제품 정면·오퍼 화면.
 화면에 글자·자막은 그리지 않는다(자막은 texts 로 따로 얹음).
3) 자막은 레퍼런스 자막 하나당 우리 texts 하나로, 레퍼런스 화면에 보이는 순서(위→아래)대로 1:1 대응시킨다(개수 같게, 줄 수도 같게, 줄바꿈 \\n). 위치·크기·글꼴·색·테두리·배경은 편집할 때 레퍼런스 화면에서 실측해 똑같이 맞춘다.
4) 자막 내용과 화면이 맞아야 한다(고민 문장엔 고민 장면, 제품 설명엔 제품 장면). 글자가 이미 있는 에셋 컷은 texts 를 비운다.
5) 마지막 컷은 제품·1+1·가격 오퍼, 자막 middle(03 끝카드를 쓰면 자막 없이). 전체 8~20초.
{utxt}에셋 목록:
{alist}
JSON만: {{"soguo":"소구점 2~6자","format":"형식 한 줄","why":"오래 도는 이유","ref_breakdown":"레퍼런스 컷 흐름(초 단위)","hook1":"","hook2":"","headline":"","sub":"",
"cuts":[{{"ref":"레퍼런스 구간","ref_t":0.0,"dur":1.5,"src":"user|gen|asset|photo","user":0,"asset":0,"from":0.0,"photo":0,"frame_prompt":"","motion_prompt":"","texts":[{{"t":"자막","pos":"middle","size":"xl|l|m|s","color":"#FFFFFF","box":""}}]}}]{extra_fields}}}"""
    parts = [{'inline_data': {'mime_type': 'video/mp4', 'data': base64.b64encode(open(small, 'rb').read()).decode()}}, img_part(R + 'data/assets_grid.jpg')] + [img_part(p) for p in product] + [img_part(u['img']) for u in USER] + [{'inline_data': {'mime_type': 'application/pdf', 'data': base64.b64encode(open(d['path'], 'rb').read()).decode()}} for d in DOCS if d['path'].lower().endswith('.pdf') and os.path.getsize(d['path']) < 15_000_000] + [{'text': prompt}]
    out = json.loads(gem('gemini-3.1-pro-preview', parts, {'temperature': 0.4, 'responseMimeType': 'application/json'}, timeout=400)['candidates'][0]['content']['parts'][0]['text'])
    out = out[0] if isinstance(out, list) else out
    measure_texts(gem, img_part, vid, out, vid.rsplit('.', 1)[0] + '_measure')   # 자막 실측
    return out


def veo(prompt, sec, image=None):
    """Vertex Veo 3.1 fast 720p 소리 없음(image 가 있으면 그 화면에서 시작). 같은 장면은 저장본 재사용."""
    sec = 4 if sec <= 4 else (6 if sec <= 6 else 8); os.makedirs(R + 'data/veo', exist_ok=True)
    ib = open(image, 'rb').read() if image else b''
    q = R + 'data/veo/' + hashlib.md5(f'{prompt}|{sec}|fast'.encode() + ib).hexdigest()[:16] + '.mp4'
    if os.path.exists(q): return q, 0
    base = 'https://us-central1-aiplatform.googleapis.com/v1/projects/gen-lang-client-0027494071/locations/us-central1/publishers/google/models/veo-3.1-fast-generate-001'
    def call(u, b):
        t = subprocess.check_output([os.path.expanduser('~/.local/bin/gcloud'), 'auth', 'print-access-token']).decode().strip()
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(u, data=json.dumps({k: v for k, v in b.items() if k != '_try'}).encode(), method='POST', headers={'Authorization': f'Bearer {t}', 'Content-Type': 'application/json'}), timeout=300).read())
        except urllib.error.HTTPError as e:
            m = e.read().decode()[:300]
            if e.code in (429, 500, 503) and b.get('_try', 0) < 5:   # 서버 몰림이면 기다렸다 다시(최대 6번)
                w = [20, 40, 60, 90, 120][b.get('_try', 0)]; print(f'Veo {e.code} — {w}초 뒤 다시', flush=True); time.sleep(w)
                return call(u, {**b, '_try': b.get('_try', 0) + 1})
            raise RuntimeError('Veo 오류: ' + m)
    inst = {'prompt': prompt + (' (첫 화면의 제품 모양·라벨·글자를 그대로 유지, 새 글자 추가 없음)' if image else ' (화면에 글자·로고·라벨 없음)')}
    if image: inst['image'] = {'bytesBase64Encoded': base64.b64encode(ib).decode(), 'mimeType': 'image/jpeg'}
    op = call(base + ':predictLongRunning', {'instances': [inst], 'parameters': {'aspectRatio': '9:16', 'durationSeconds': sec, 'resolution': '720p', 'generateAudio': False, 'sampleCount': 1}})['name']
    for _ in range(60):
        time.sleep(15); r = call(base + ':fetchPredictOperation', {'operationName': op})
        if r.get('done'):
            v = (r.get('response') or {}).get('videos') or []
            if not v: raise RuntimeError('Veo 생성 실패')
            open(q, 'wb').write(base64.b64decode(v[0]['bytesBase64Encoded']))
            try: COST.log(R, 'veo-3.1-fast-generate-001', sec=sec)   # 저장본 재사용은 과금 없음 → 실제 생성할 때만 적는다
            except Exception: pass
            return q, sec
    raise RuntimeError('Veo 시간 초과')


def keyframe(ref, t, prompt, product, work):
    """레퍼런스 t초 화면 → 나노바나나 프로로 같은 구도의 SOOO 버전 9:16 첫 화면(저장본 재사용)."""
    fr = f'{work}/ref_{t:.1f}.jpg'
    subprocess.run([FF, '-y', '-v', 'error', '-ss', f'{max(0.0, t):.2f}', '-i', ref, '-frames:v', '1', '-q:v', '2', fr], check=True)
    key = hashlib.md5(open(fr, 'rb').read() + prompt.encode()).hexdigest()[:16]; os.makedirs(R + 'data/keyframes', exist_ok=True); q = R + f'data/keyframes/{key}.jpg'
    if os.path.exists(q): return q, 0
    p = (f"Recreate the FIRST image as a new vertical 9:16 photo for a SOOO scalp shampoo ad: {prompt}. Keep the same composition, camera angle, framing, pose and lighting as the first image. "
         "If a product appears, it must be the real SOOO product from the other images (exact shape, color, pump and label): the shampoo is a MUTED BROWN-PINK translucent bottle with a WHITE pump (NOT purple, NOT lavender); only the small ampoule is light lavender. "
         "Use a clearly DIFFERENT person from the original (different face, hairstyle and outfit; never copy a real person's face). No text, no captions, no logos other than SOOO's own label. Photorealistic.")
    r = GEM('nano-banana-pro-preview', [IMGP(fr)] + [IMGP(x) for x in product] + [{'text': p}], {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': '9:16'}}, timeout=400)
    b = next((pt.get('inline_data') or pt.get('inlineData') for c in r.get('candidates', []) for pt in c.get('content', {}).get('parts', []) if pt.get('inline_data') or pt.get('inlineData')), None)
    if not b: raise RuntimeError('장면 첫 화면 생성 실패')
    open(q, 'wb').write(base64.b64decode(b['data'])); im = Image.open(q).convert('RGB'); im.save(q, quality=92); return q, 1


FONTS = {'pretendard_black': 'Pretendard-Black.otf', 'pretendard_bold': 'Pretendard-Bold.otf', 'pretendard_medium': 'Pretendard-Medium.otf', 'aggro': 'SBAggroB.ttf',
         'paperlogy_black': 'Paperlogy-9Black.ttf', 'pop_round': 'ONEMobilePOPOTF.otf', 'gmarket_bold': 'GmarketSans-Bold.otf', 'handwriting': 'GamjaFlower.ttf'}
def font_path(k):
    f = FONTS.get(k or '', 'Pretendard-Black.otf'); q = os.path.expanduser('~/Library/Fonts/' + f)
    return q if os.path.exists(q) else FONT


def measure_texts(gem, img_part, ref, plan, work):
    """레퍼런스 각 컷 화면(ref_t)의 자막을 실측 → 우리 texts 에 위치·크기·글꼴·색·테두리·배경을 그대로 입힘(10/20 다운: 자막 똑같이)."""
    acc = 0.0
    for c in plan.get('cuts', []):   # ref_t 없는 예전 계획 → 컷 설명의 '2.5-4.5초' 또는 컷 길이 누적으로 시점 추정
        if c.get('ref_t') in (None, '', 0, 0.0) and acc > 0:
            import re as _re
            m = _re.search(r'(\d+(?:\.\d+)?)\s*[-~]', str(c.get('ref', '')))
            c['ref_t'] = float(m.group(1)) + 0.3 if m else acc + 0.3
        acc += float(c.get('dur') or 2)
    cuts = [c for c in plan.get('cuts', []) if c.get('texts')]
    if not cuts or not ref or not os.path.exists(ref): return
    os.makedirs(work, exist_ok=True)
    try: rw, rh = [int(v) for v in subprocess.run([FF.replace('ffmpeg', 'ffprobe'), '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', ref], capture_output=True, text=True).stdout.strip().split(',')[:2]]
    except Exception: rw, rh = W, H
    parts = []
    for k, c in enumerate(cuts):
        fr = f'{work}/m_{k}.jpg'; subprocess.run([FF, '-y', '-v', 'error', '-ss', f"{max(0.0, float(c.get('ref_t') or 0)):.2f}", '-i', ref, '-frames:v', '1', '-q:v', '2', fr])
        if os.path.exists(fr): parts += [{'text': f'화면 {k}'}, img_part(fr)]
    q = ('각 화면에 보이는 자막·글자 오버레이(광고 문구)를 위→아래 순서로 전부 찾아 실측한다. 화면 속 제품 라벨 글씨는 빼고, 편집으로 얹은 자막만.\n'
         'JSON만: [{"frame":0,"texts":[{"box_2d":[ymin,xmin,ymax,xmax](0~1000, 글자 영역 딱 맞게),"lines":줄 수,"text":"원문",'
         '"font":"pretendard_black|pretendard_bold|pretendard_medium|aggro|paperlogy_black|pop_round|gmarket_bold|handwriting" 중 가장 비슷한 것,'
         '"color":"#글자색","stroke":"#테두리색 또는 빈칸","stroke_w":테두리 두께(글자 높이 대비 0~0.2),"bg":"#글자 뒤 박스색 또는 빈칸","bg_alpha":0~1,"align":"left|center|right",'
         '"hl":[{"word":"색이 다른 강조 단어","color":"#"}]}]}]')
    try:
        r = gem('gemini-3.1-pro-preview', parts + [{'text': q}], {'temperature': 0.1, 'responseMimeType': 'application/json'}, timeout=300)
        got = json.loads(r['candidates'][0]['content']['parts'][0]['text'])
    except Exception as e: print('자막 실측 실패(기본 스타일로):', str(e)[:100], flush=True); return
    a = rw / rh; sc = (W / H) / a   # 레퍼런스가 우리 9:16 보다 넓으면 좌우가 잘림(꽉 차게 크롭)
    def mapx(x): return (x - (1 - sc) / 2) / sc if sc < 1 else x
    def mapy(y): return (y - (1 - 1 / sc) / 2) * sc if sc > 1 else y
    for g in got if isinstance(got, list) else []:
        k = int(g.get('frame', -1))
        if not 0 <= k < len(cuts): continue
        ms = g.get('texts') or []
        for j, t in enumerate(cuts[k]['texts']):
            if j >= len(ms): break
            m = ms[j]; y0, x0, y1, x1 = [v / 1000 for v in m.get('box_2d', [0, 0, 0, 0])]
            if y1 <= y0 or x1 <= x0: continue
            t.update(bx=[max(0.0, mapx(x0)), max(0.0, mapy(y0)), min(1.0, mapx(x1)), min(1.0, mapy(y1))], lines=int(m.get('lines') or 1), font=m.get('font'), color=m.get('color') or t.get('color'),
                     stroke=m.get('stroke') or '', stroke_w=float(m.get('stroke_w') or 0), box=m.get('bg') or '', bg_alpha=float(m.get('bg_alpha') if m.get('bg_alpha') is not None else 1), align=m.get('align') or 'center', hl=m.get('hl') or [])
    print('자막 실측', sum(1 for c in cuts for t in c['texts'] if t.get('bx')), '개', flush=True)


def text_measured(dr, t):
    """실측 상자 안에 같은 글꼴·색·테두리·배경으로(줄 수·폭에 맞춰 글자 크기 자동)."""
    X0, Y0, X1, Y1 = t['bx'][0] * W, t['bx'][1] * H, t['bx'][2] * W, t['bx'][3] * H; bw, bh = X1 - X0, Y1 - Y0
    fp = font_path(t.get('font')); n = max(1, int(t.get('lines') or 1))
    paras = str(t.get('t', '')).split('\n')
    def wrap(sz):
        ft = ImageFont.truetype(fp, sz); out = []
        for para in paras:
            cur = ''
            for wd in para.split(' '):
                nx = (cur + ' ' + wd).strip()
                if cur and dr.textlength(nx, font=ft) > bw * 1.08: out.append(cur); cur = wd
                else: cur = nx
            out.append(cur)
        return ft, out
    s = max(24, int(bh / n / 1.15)); f, lines = wrap(s)
    while s > 24 and (max(dr.textlength(l, font=f) for l in lines) > bw * 1.12 or len(lines) * s * 1.15 > bh * 1.25): s -= 3; f, lines = wrap(s)
    lh = s * 1.15; y = Y0 + (bh - len(lines) * lh) / 2; hl = {h.get('word'): h.get('color') for h in t.get('hl') or [] if h.get('word')}
    for ln in lines:
        w = dr.textlength(ln, font=f); al = t.get('align') or 'center'
        x = X0 if al == 'left' else (X1 - w if al == 'right' else X0 + (bw - w) / 2)
        x = max(20, min(x, W - 20 - w))
        if t.get('box'):
            c = col(t['box'], '#000000'); c = ImageColor.getrgb(c) if isinstance(c, str) else c
            pad = s * 0.22; dr.rounded_rectangle([x - pad, y - pad * 0.5, x + w + pad, y + s * 1.1 + pad * 0.3], radius=int(s * 0.18), fill=(*c[:3], int(255 * max(0.0, min(1.0, t.get('bg_alpha', 1))))))
        sw = int(max(0, min(0.2, float(t.get('stroke_w') or 0))) * s) if t.get('stroke') else 0
        cx = x
        for wd in ln.split(' '):   # 강조 단어는 그 색으로
            seg = wd + ' '; fill = col(hl.get(wd.strip('!?.,~')) or t.get('color'))
            dr.text((cx, y), seg, font=f, fill=fill, stroke_width=sw, stroke_fill=col(t.get('stroke'), '#000000') if sw else None); cx += dr.textlength(seg, font=f)
        y += lh


SZ = {'xl': 112, 'l': 88, 'm': 66, 's': 48}; POS = {'top': 0.16, 'middle': 0.46, 'bottom': 0.66}   # 위 11%·아래 22% 안전 구역 밖


def col(c, d='#FFFFFF'):   # Gemini 가 rgba(0,0,0,0.5) 같은 색을 주면 PIL 이 못 읽음 → 튜플로
    import re as _re
    if not c: return d
    m = _re.match(r'rgba?\(([^)]*)\)', str(c).strip())
    if m:
        v = [float(x) for x in m.group(1).split(',')]
        return (int(v[0]), int(v[1]), int(v[2]), int((v[3] if len(v) > 3 else 1) * 255 if (v[3] if len(v) > 3 else 1) <= 1 else v[3]))
    try: ImageColor.getrgb(c); return c
    except Exception: return d


def text_png(texts, out):
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
    for t in texts or []:
        if t.get('bx'): text_measured(dr, t); continue   # 레퍼런스 실측 스타일
        s = SZ.get(t.get('size'), 66); MW = W - 200   # 좌우 여백·오른쪽 아이콘 자리 뺀 폭
        def wrap(sz):
            ft = ImageFont.truetype(FONT, sz); out = []
            for para in str(t.get('t', '')).split('\n'):
                cur = ''
                for wd in para.split(' '):
                    nx = (cur + ' ' + wd).strip()
                    if cur and dr.textlength(nx, font=ft) > MW: out.append(cur); cur = wd
                    else: cur = nx
                out.append(cur)
            return ft, out
        f, lines = wrap(s)
        while s > 40 and (max(dr.textlength(l, font=f) for l in lines) > MW or len(lines) > 4): s -= 6; f, lines = wrap(s)
        y = int(H * POS.get(t.get('pos'), 0.46)) - len(lines) * s * 0.62
        for ln in lines:
            w = dr.textlength(ln, font=f); x = max(60, min((W - w) / 2, W - 130 - w)) if w < W - 190 else 60   # 오른쪽 아이콘 자리 피함
            if t.get('box'): dr.rounded_rectangle([x - 22, y - 10, x + w + 22, y + s * 1.12], radius=18, fill=col(t['box'], '#000000'))
            dr.text((x, y), ln, font=f, fill=col(t.get('color')), stroke_width=0 if t.get('box') else max(3, s // 14), stroke_fill='#000000'); y += s * 1.25
    im.save(out)


def render(plan, out, product, work, log=print):
    """컷 계획 → mp4. 반환: 새로 만든 Veo 초."""
    assets = {a['n']: a for a in json.load(open(R + 'data/assets.json'))}; os.makedirs(work, exist_ok=True)
    enc = ['-an', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p']; seg = []; used = total = 0
    for i, c in enumerate(plan['cuts']):
        d = max(0.6, min(float(c.get('dur') or 2), 8)); o = f'{work}/c{i:02d}.mp4'; src = c.get('src')
        if i == len(plan['cuts']) - 1: d = max(d, 2.5)   # 마지막 오퍼 화면은 충분히
        ref = plan.get('_ref')
        if src == 'user':   # 다운이 올린 에셋 그대로
            k = str(c.get('user') or '').strip().upper(); u = next((x for x in USER if k in (x.get('lab', ''), str(x['i']), 'U%d' % x['i'])), None)   # 라벨(U1·R2) 또는 번호
            if not u: src = 'photo'
            elif u['kind'] == 'video': clip = u['path']; start = max(0.0, min(float(c.get('from') or 0), max(0.0, u['dur'] - d)))
            else: src = 'uphoto'; uimg = u['img']
        if src in ('gen', 'veo') and total + d > VEO_MAX: src = 'photo'   # Veo 상한 넘으면 제품 사진
        if src == 'gen' and not (ref and os.path.exists(ref) and GEM): src = 'veo'
        if src in ('user', 'uphoto'): pass   # 위에서 다운 에셋으로 정함
        elif src == 'gen':
            kf, k = keyframe(ref, float(c.get('ref_t') or 0), c.get('frame_prompt') or c.get('ref') or '', product, work); plan['_frames'] = plan.get('_frames', 0) + k
            p, s = veo(c.get('motion_prompt') or c.get('ref') or '자연스러운 움직임', d, image=kf); used += s; total += d; clip, start = p, 0.0
        elif src == 'veo': p, s = veo(c.get('veo_prompt') or c.get('motion_prompt') or '밝은 욕실, 부드러운 자연광', d); used += s; total += d; clip, start = p, 0.0
        elif src == 'asset' and int(c.get('asset') or 0) in assets:
            a = assets[int(c['asset'])]; clip = A + a['file']; start = max(0.0, min(float(c.get('from') or 0), a['dur'] - d))
            if a.get('text'): c = {**c, 'texts': []}   # 글자 박힌 클립엔 자막 안 얹음
            if i == len(plan['cuts']) - 1 and a['name'].startswith('03_'): d = a['dur']; start = 0.0   # 1+1 끝카드는 가격까지 끝까지
        else: src = 'photo'
        if src in ('photo', 'uphoto'):   # 제품 사진(또는 다운이 올린 사진)에 천천히 다가가기. 흰 배경 사진은 흰 바탕에 통째로, 아니면 꽉 차게
            ph = uimg if src == 'uphoto' else product[min(int(c.get('photo') or 0), len(product) - 1)]; n = int(d * FPS); BW, BH = int(W * 1.1), int(H * 1.1)
            white = Image.open(ph).convert('L').resize((40, 40)).getpixel((1, 1)) > 235
            vf = f'scale={BW}:{BH}:force_original_aspect_ratio=decrease,pad={BW}:{BH}:(ow-iw)/2:(oh-ih)/2:white' if white else f'scale={BW}:{BH}:force_original_aspect_ratio=increase,crop={BW}:{BH}'
            subprocess.run([FF, '-y', '-v', 'error', '-loop', '1', '-i', ph, '-t', f'{d:.2f}', '-vf', vf + f",zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},setsar=1"] + enc + [o + '.raw.mp4'], check=True)
        else:   # 에셋·Veo 클립 구간 자르기, 9:16 꽉 차게(블러 없음)
            subprocess.run([FF, '-y', '-v', 'error', '-ss', f'{start:.2f}', '-i', clip, '-t', f'{d:.2f}', '-vf', f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},tpad=stop_mode=clone:stop_duration={d:.2f}', '-t', f'{d:.2f}'] + enc + [o + '.raw.mp4'], check=True)
        tp = f'{work}/t{i:02d}.png'; text_png(c.get('texts'), tp)
        subprocess.run([FF, '-y', '-v', 'error', '-i', o + '.raw.mp4', '-i', tp, '-filter_complex', 'overlay=0:0', '-r', str(FPS)] + enc + [o], check=True)
        seg.append(o); log(f'컷 {i + 1}/{len(plan["cuts"])} {src} {d:.1f}초')
    open(f'{work}/list.txt', 'w').write(''.join(f"file '{s}'\n" for s in seg))
    subprocess.run([FF, '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', f'{work}/list.txt', '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-shortest',
                    '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', out], check=True)
    return used


def poster(mp4, out):
    subprocess.run([FF, '-y', '-v', 'error', '-ss', '0.6', '-i', mp4, '-frames:v', '1', '-q:v', '3', out], check=True)
