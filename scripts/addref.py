"""레퍼런스 직접 추가 처리. 사용: python3 -I addref.py job.json
Blob 조각 합치기 → 이미지면 site/m/L<id>.jpg, 영상이면 대표컷 + 장면 4컷 묶음(data/ref_<id>_sheet.jpg, 복각 기획용) → data/custom_refs.json 맨 앞에 추가."""
import json, os, sys, subprocess, datetime, time
R = '/Users/daun/ad-reference/'
KST = datetime.timezone(datetime.timedelta(hours=9)); NOW = datetime.datetime.now(KST)
job = json.load(open(sys.argv[1]))
rid = '9' + str(int(time.time() * 1000))   # 숫자 id(복각 API 규칙), 9로 시작 = 직접 추가
os.makedirs(R + 'data/custom', exist_ok=True)
src = R + f'data/custom/{rid}.{job["ext"]}'
n = subprocess.run(['node', R + 'scripts/blob.mjs', 'fetchup', job['up'], src], cwd=R, capture_output=True, text=True, timeout=600)
if n.returncode or not os.path.exists(src) or os.path.getsize(src) < 1000: raise SystemExit('업로드 파일 합치기 실패: ' + (n.stderr or '')[-300:])
if int((n.stdout or '0').strip() or 0) != job['n']: raise SystemExit(f'조각 수가 안 맞음 ({n.stdout.strip()}/{job["n"]})')
from PIL import Image
thumb = R + f'site/m/L{rid}.jpg'; dur = ''
if job['kind'] == 'image':
    im = Image.open(src); im.seek(0); im = im.convert('RGB')
    big = im.copy(); big.thumbnail((1600, 2000)); big.save(R + f'data/ref_{rid}.jpg', quality=90)   # 복각 기획용(원본 화질)
    im.thumbnail((480, 600)); im.save(thumb, quality=80)
else:
    FF = next((x for x in ('/Users/daun/.local/bin/ffmpeg', '/opt/homebrew/bin/ffmpeg') if os.path.exists(x)), 'ffmpeg')
    FP = FF.replace('ffmpeg', 'ffprobe')
    sec = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout.strip() or 0)
    dur = '%d:%02d' % (int(sec) // 60, int(sec) % 60)
    subprocess.run([FF, '-y', '-v', 'error', '-ss', str(min(1.0, sec / 3)), '-i', src, '-frames:v', '1', '-vf', 'scale=480:-2', thumb], check=True)
    subprocess.run([FF, '-y', '-v', 'error', '-i', src, '-t', '60', '-vf', 'scale=480:-2', '-an', '-c:v', 'libx264', '-crf', '28', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', R + f'site/m/L{rid}.mp4'], check=True)   # 카드 재생용(소리 없음, 색 그대로)
    # 장면 4컷(처음~끝 고르게) 가로로 이어 붙여 기획용 1장
    fr = []
    for k in range(4):
        q = R + f'data/custom/{rid}_f{k}.jpg'
        subprocess.run([FF, '-y', '-v', 'error', '-ss', str(sec * (k + 0.5) / 4), '-i', src, '-frames:v', '1', '-vf', 'scale=-2:900', q], check=True); fr.append(Image.open(q).convert('RGB'))
    W = sum(f.width for f in fr); sh = Image.new('RGB', (W, 900), 'white'); x = 0
    for f in fr: sh.paste(f, (x, 0)); x += f.width
    sh.save(R + f'data/ref_{rid}_sheet.jpg', quality=88)
ra = []   # 이 레퍼런스로 복각할 때 같이 쓸 '쓸 에셋'
for i, a in enumerate(job.get('assets') or [], 1):
    d = R + f'data/custom_assets/{rid}/'; os.makedirs(d, exist_ok=True); out = d + f"{i}.{a['ext']}"
    subprocess.run(['node', R + 'scripts/blob.mjs', 'fetchup', a['up'], out], cwd=R, capture_output=True, timeout=600)
    if os.path.exists(out) and os.path.getsize(out) > 500: ra.append({'i': i, 'kind': a['kind'], 'name': a.get('name', ''), 'file': out})
    subprocess.run(['node', R + 'scripts/blob.mjs', 'delup', a['up']], cwd=R, capture_output=True, timeout=300)
cr = json.load(open(R + 'data/custom_refs.json')) if os.path.exists(R + 'data/custom_refs.json') else []
cr.insert(0, {'id': rid, 'name': job.get('name') or '직접 추가한 레퍼런스', 'memo': job.get('memo', ''), 'src': job.get('src', ''), 'kind': job['kind'], 'dur': dur,
              'file': os.path.basename(src), 'added': NOW.strftime('%Y-%m-%d %H:%M'), 'job': job.get('job', ''), 'assets': ra, 'asset_note': job.get('asset_note', '')})
json.dump(cr, open(R + 'data/custom_refs.json', 'w'), ensure_ascii=False, indent=1)
subprocess.run(['node', R + 'scripts/blob.mjs', 'delup', job['up']], cwd=R, capture_output=True, timeout=300)
print('레퍼런스 추가', rid, job['kind'], dur, f'에셋 {len(ra)}개' if ra else '')
if job.get('bokgak'):   # '추가하고 바로 복각하기' → 작업기가 이어서 bokgak.py 실행
    it = {'id': rid, 'page': job.get('name') or '직접 추가한 레퍼런스', 't': job.get('memo', ''), 'dur': dur, 'days': '직접 추가', 'poster': '', 'imgs': [], 'video': ''}
    if job['bokgak'].get('landing'): it['landing'] = job['bokgak']['landing']
    json.dump({'job': job.get('job', ''), 'by': job.get('by') or '다운', 'brand': job['bokgak'].get('brand') or 'SOOO', 'items': [it], 'command': job['bokgak'].get('command', '')}, open(f"/tmp/adref_follow_{job.get('job', 'x')}.json", 'w'), ensure_ascii=False)
    print('바로 복각 이어서 함', rid)
