"""#소재공유방(data/slack/messages.json) → 레퍼런스 카드용 data/slack_refs.json.
인스타 링크마다 대표 이미지·계정·좋아요·캡션(og 태그), 릴스는 영상도 받아서(yt-dlp) 카드 재생·영상 복각에 씀. 이미 받은 건 건너뜀.
id = '8' + 메시지 ts 숫자(직접 추가 '9'와 구분)."""
import json, os, re, html, subprocess, urllib.request
from PIL import Image
R = '/Users/daun/ad-reference/'; FF = '/Users/daun/.local/bin/ffmpeg'; FP = '/Users/daun/.local/bin/ffprobe'
WHO = {'김화영': '화영', '박다운': '다운', '박도현': '도현', '박근형': '근형', '유형태': '형태'}
msgs = json.load(open(R + 'data/slack/messages.json'))
OUT = R + 'data/slack_refs.json'; have = {x['id']: x for x in (json.load(open(OUT)) if os.path.exists(OUT) else [])}
os.makedirs(R + 'data/custom', exist_ok=True)


def og(u):
    h = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (compatible; facebookexternalhit/1.1)'}), timeout=40).read().decode('utf-8', 'ignore')
    g = lambda k: html.unescape((re.search(r'<meta property="og:%s" content="([^"]*)"' % k, h) or [None, ''])[1])
    return g('image'), g('title'), g('description')


LABELS = json.load(open(R + 'data/slack/labels.json')) if os.path.exists(R + 'data/slack/labels.json') else {}   # 글 안 번호별 설명(링크별 메모)
LIB = {x['id']: x for x in json.load(open(R + 'data/library-raw.json'))} if os.path.exists(R + 'data/library-raw.json') else {}
def save(): json.dump(sorted(have.values(), key=lambda x: (x['ts'], x['id']), reverse=True), open(OUT, 'w'), ensure_ascii=False, indent=1)
def links_of(m):
    """글 하나의 모든 레퍼런스 링크(순서 유지, 중복 제거): 인스타 게시물·릴스 + 메타 광고 라이브러리."""
    out, seen = [], set()
    for l in m['links']:
        if 'instagram.com/' in l and ('/p/' in l or '/reel/' in l):
            u = l.split('?')[0]; k = u.rstrip('/').split('/')[-1]
            if k not in seen: seen.add(k); out.append(('ig', k, u))
        elif 'facebook.com/ads/library' in l and re.search(r'id=(\d+)', l):
            k = re.search(r'id=(\d+)', l).group(1)
            if k not in seen: seen.add(k); out.append(('fb', k, 'https://www.facebook.com/ads/library/?id=' + k))
    return out
def thumb(rid, data):
    open(R + f'data/ref_{rid}.jpg', 'wb').write(data)
    im = Image.open(R + f'data/ref_{rid}.jpg').convert('RGB'); im.save(R + f'data/ref_{rid}.jpg', quality=92); im.thumbnail((480, 600)); im.save(R + f'site/m/L{rid}.jpg', quality=80)
def vid_meta(src, rid):
    sec = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout or 0)
    subprocess.run([FF, '-y', '-v', 'error', '-i', src, '-t', '60', '-vf', 'scale=480:-2', '-an', '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', R + f'site/m/L{rid}.mp4'], check=True)
    return '%d:%02d' % (int(sec) // 60, int(sec) % 60)
FBM = json.load(open(R + 'data/slack/fb_media.json')) if os.path.exists(R + 'data/slack/fb_media.json') else {}
def text_card(note, key):
    """이미지를 못 구한 광고 라이브러리 링크용 카드 그림(설명 + 광고 ID)."""
    from PIL import ImageDraw, ImageFont
    import io
    W_, H_ = 480, 600; im = Image.new('RGB', (W_, H_), (34, 36, 48)); d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype('/Users/daun/Library/Fonts/Pretendard-Bold.otf', 30); f2 = ImageFont.truetype('/Users/daun/Library/Fonts/Pretendard-Medium.otf', 20)
    d.text((32, 40), '인스타그램' if not key.isdigit() else '메타 광고 라이브러리', font=f2, fill=(160, 170, 200)); y = 90; line = ''
    for ch in (note or '(설명 없음)'):
        if d.textlength(line + ch, font=f1) > W_ - 64 or ch == '\n':
            d.text((32, y), line, font=f1, fill='white'); y += 44; line = '' if ch == '\n' else ch
            if y > H_ - 140: break
        else: line += ch
    if line and y <= H_ - 140: d.text((32, y), line, font=f1, fill='white')
    d.text((32, H_ - 90), '이미지를 못 받아왔어요' if not key.isdigit() else '광고가 내려가 이미지가 없어요', font=f2, fill=(255, 190, 120)); d.text((32, H_ - 56), 'ID ' + key + '  · 눌러서 원본 보기', font=f2, fill=(160, 170, 200))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=90); return b.getvalue()
SEENK = set()
for m in msgs:
    L = links_of(m)
    if not L: continue
    base = '8' + m['ts'].replace('.', ''); lab = LABELS.get(m['ts'], {})
    first_ig = next((i for i, x in enumerate(L) if x[0] == 'ig'), None)
    for i, (src, key, url) in enumerate(L):
        if key in SEENK: continue   # 같은 링크를 여러 글에 올렸으면 처음 것만
        SEENK.add(key)
        rid = base if i == first_ig else base + f'{i + 1:02d}'   # 첫 인스타 링크는 예전 번호 그대로(복각 기록 유지)
        note = (lab.get(key) or m['text'])[:300]
        if rid in have and os.path.exists(R + f'site/m/L{rid}.jpg'):
            if have[rid].get('note') != note and lab.get(key): have[rid]['note'] = note
            continue
        try:
            if src == 'ig':
                kind = 'video' if '/reel/' in url else 'image'
                try: img, title, desc = og(url)
                except Exception: img, title, desc = '', '', ''
                if img: thumb(rid, urllib.request.urlopen(urllib.request.Request(img, headers={'User-Agent': 'Mozilla/5.0'}), timeout=40).read())
                else: thumb(rid, text_card(note, url.rstrip('/').split('/')[-1]).replace(b'', b''))   # 인스타가 대표 이미지를 안 줌 → 글자 카드
                dur = ''
                if kind == 'video':   # 릴스 원본 → 영상 복각용, 480p 사본 → 카드 재생용
                    sv = R + f'data/custom/{rid}.mp4'
                    if not os.path.exists(sv): subprocess.run([os.path.expanduser('~/.local/bin/uvx'), 'yt-dlp', '-q', '-f', 'mp4/best', '-o', sv, url], timeout=300, capture_output=True)
                    if os.path.exists(sv): dur = vid_meta(sv, rid)
                    else: kind = 'image'
                acct = re.sub(r' on Instagram.*$', '', title, flags=re.S).strip()
                likes = (re.match(r'([\d.,KkM]+) likes', desc) or [None, ''])[1]
                cap = re.sub(r'^.*?: "', '', desc).rstrip('"')[:400]
            else:   # 메타 광고 라이브러리: 사이트가 이미 수집한 광고면 그 이미지·영상을 씀
                ad = LIB.get(key); acct, likes, cap, dur, kind = '', '', '', '', 'image'
                got = None
                for p in (R + f'site/m/L{key}.jpg', R + f'site/m/A{key}.jpg', R + f'data/ref_{key}.jpg'):
                    if os.path.exists(p): got = open(p, 'rb').read(); break
                if not got and ad:
                    for u in [ad.get('poster')] + (eval(ad['imgs']) if isinstance(ad.get('imgs'), str) and ad['imgs'].startswith('[') else (ad.get('imgs') or [])):
                        if not u: continue
                        try:
                            got = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.facebook.com/'}), timeout=40).read()
                            if len(got) > 20000: break
                        except Exception: got = None
                fm = FBM.get(key) or {}   # 브라우저로 따로 뽑아 둔 광고 라이브러리 이미지·영상(data/slack/fb_media.json)
                if not got and fm.get('poster'):
                    try: got = urllib.request.urlopen(urllib.request.Request(fm['poster'], headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.facebook.com/'}), timeout=40).read()
                    except Exception: got = None
                if fm: acct = fm.get('page', ''); cap = fm.get('text', '')
                if not got:   # 광고가 내려가 이미지를 못 구함 → 설명·링크를 적은 글자 카드(누르면 광고 라이브러리로)
                    got = text_card(note, key); kind = 'image'; acct = acct or '광고 라이브러리(이미지 없음)'
                thumb(rid, got)
                if fm.get('video') and not os.path.exists(R + f'data/custom/{rid}.mp4'):
                    try:
                        sv = R + f'data/custom/{rid}.mp4'; open(sv, 'wb').write(urllib.request.urlopen(urllib.request.Request(fm['video'], headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.facebook.com/'}), timeout=120).read())
                        if os.path.getsize(sv) > 50000: kind = 'video'; dur = vid_meta(sv, rid)
                    except Exception: pass
                if ad: cap = (ad.get('text') or '').strip()[:400]
                for p in (R + f'data/ref_{key}.mp4', R + f'data/custom/{key}.mp4'):
                    if os.path.exists(p): kind = 'video'; dur = vid_meta(p, rid); break
                if kind == 'image' and ad and ad.get('video'):
                    try:
                        sv = R + f'data/custom/{rid}.mp4'; open(sv, 'wb').write(urllib.request.urlopen(urllib.request.Request(ad['video'], headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read())
                        if os.path.getsize(sv) > 50000: kind = 'video'; dur = vid_meta(sv, rid)
                    except Exception: pass
            have[rid] = {'id': rid, 'by': WHO.get(m['name'], m['name']), 'at': m['at'], 'ts': m['ts'], 'note': note, 'link': url, 'account': acct, 'likes': likes,
                         'caption': cap, 'kind': kind, 'dur': dur, 'react': m.get('react', ''), 'src': src}
            print('가져옴', rid, src, kind, dur, (acct or key)[:20], flush=True)
        except Exception as e:
            print('실패', url, str(e)[:100], flush=True)
        save()
# 게시물(/p/) 중 실제 영상인 것도 영상으로(한 번만 시도)
for x in have.values():
    if x['kind'] != 'image' or '/p/' not in x['link'] or x.get('vtry'): continue
    x['vtry'] = 1; rid = x['id']; src = R + f'data/custom/{rid}.mp4'
    subprocess.run([os.path.expanduser('~/.local/bin/uvx'), 'yt-dlp', '-q', '-f', 'mp4/best', '--no-playlist', '--playlist-items', '1', '-o', src, x['link']], timeout=300, capture_output=True)
    if os.path.exists(src) and os.path.getsize(src) > 100000:
        sec = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout or 0)
        if sec >= 2:
            x['kind'] = 'video'; x['dur'] = '%d:%02d' % (int(sec) // 60, int(sec) % 60)
            subprocess.run([FF, '-y', '-v', 'error', '-i', src, '-t', '60', '-vf', 'scale=480:-2', '-an', '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', R + f'site/m/L{rid}.mp4'], check=True)
            print('게시물→영상', rid, x['dur'], flush=True)
        else: os.remove(src)
    json.dump(sorted(have.values(), key=lambda x: x['ts'], reverse=True), open(OUT, 'w'), ensure_ascii=False, indent=1)
print('소재공유방 레퍼런스', len(have))
