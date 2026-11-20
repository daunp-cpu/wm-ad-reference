"""#소재공유방에서 링크 없이 파일(화면 녹화·캡처)만 올린 글 → 레퍼런스 카드.
파일은 다운의 크롬(슬랙 로그인됨)으로 받는다: files.slack.com 다운로드 주소를 열면 ~/Downloads 에 떨어짐 → 바로 data/slack/files/<파일ID> 로 옮김.
사용: python3 -I slack_files.py          (받을 것만 받고 카드 만들기)
id = '8' + 메시지 ts + 'F' 순번 대신 숫자 9x (링크 카드와 안 겹치게 '8'+ts+'9'+순번)."""
import glob, json, os, re, subprocess, time
from PIL import Image
R = '/Users/daun/ad-reference/'; TEAM = 'YOUR_SLACK_TEAM_ID'
FF = '/Users/daun/.local/bin/ffmpeg'; FP = '/Users/daun/.local/bin/ffprobe'
WHO = {'김화영': '화영', '박다운': '다운', '박도현': '도현', '박근형': '근형', '유형태': '형태', '다솔': '다솔'}
DL = os.path.expanduser('~/Downloads/'); FD = R + 'data/slack/files/'; os.makedirs(FD, exist_ok=True)
msgs = json.load(open(R + 'data/slack/messages.json'))
OUT = R + 'data/slack_refs.json'; have = {x['id']: x for x in json.load(open(OUT))}
def linked(m): return any(('instagram.com/' in l and ('/p/' in l or '/reel/' in l)) or 'ads/library' in l for l in m['links'])
def fetch(fid, name):
    """크롬으로 받기 → 새로 생긴 파일을 data/slack/files 로 옮김."""
    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else 'bin'; dst = FD + f'{fid}.{ext}'
    if os.path.exists(dst): return dst
    before = set(os.listdir(DL)); t0 = time.time()
    subprocess.run(['open', '-g', f'https://files.slack.com/files-pri/{TEAM}-{fid}/download/{name}'])
    while time.time() - t0 < 180:
        time.sleep(2)
        new = [f for f in set(os.listdir(DL)) - before if not f.endswith(('.crdownload', '.download', '.part')) and not f.startswith('.')]
        if new:
            f = max(new, key=lambda f: os.path.getmtime(DL + f)); time.sleep(1); os.rename(DL + f, dst); return dst
    return None
n = 0
for m in msgs:
    if linked(m) or not m.get('files'): continue
    base = '8' + m['ts'].replace('.', '')
    for i, f in enumerate(m['files'], 1):
        if not f.get('mime', '').startswith(('image', 'video')): continue
        rid = base + f'9{i}'
        if rid in have and os.path.exists(R + f'site/m/L{rid}.jpg'): continue
        p = fetch(f['id'], f['name'])
        if not p: print('받기 실패', f['name']); continue
        kind, dur = 'image', ''
        try:
            if f['mime'].startswith('video'):
                src = R + f'data/custom/{rid}.mp4'
                subprocess.run([FF, '-y', '-v', 'error', '-i', p, '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', src], check=True)
                sec = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout or 0)
                subprocess.run([FF, '-y', '-v', 'error', '-ss', str(min(1.0, sec / 2)), '-i', src, '-frames:v', '1', '-q:v', '2', R + f'data/ref_{rid}.jpg'], check=True)
                subprocess.run([FF, '-y', '-v', 'error', '-i', src, '-t', '60', '-vf', 'scale=480:-2', '-an', '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', R + f'site/m/L{rid}.mp4'], check=True)
                kind, dur = 'video', '%d:%02d' % (int(sec) // 60, int(sec) % 60)
            else:
                im = Image.open(p).convert('RGB'); im.save(R + f'data/ref_{rid}.jpg', quality=92)
            im = Image.open(R + f'data/ref_{rid}.jpg').convert('RGB'); im.thumbnail((480, 600)); im.save(R + f'site/m/L{rid}.jpg', quality=80)
        except Exception as e:
            print('변환 실패', f['name'], str(e)[:80]); continue
        have[rid] = {'id': rid, 'by': WHO.get(m['name'], m['name']), 'at': m['at'], 'ts': m['ts'], 'note': (m['text'] or '(파일 공유)')[:300],
                     'link': f"https://YOUR-WORKSPACE.slack.com/archives/YOUR_SLACK_CHANNEL_ID/p{m['ts'].replace('.', '')}", 'account': '', 'likes': '', 'caption': '',
                     'kind': kind, 'dur': dur, 'react': m.get('react', ''), 'src': 'file'}
        n += 1; print('파일 카드', rid, kind, dur, f['name'][:30], flush=True)
        json.dump(sorted(have.values(), key=lambda x: (x['ts'], x['id']), reverse=True), open(OUT, 'w'), ensure_ascii=False, indent=1)
print('파일 카드 새로', n, '개 / 전체', len(have))
