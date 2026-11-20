"""복각 검수 한 번에(2026-11-04 속도 개선): 레퍼런스 vs 결과 같은 시각 나란히 + 결과 0.5초 시트 + 받아쓰기.
사용: python -I qc.py <결과.mp4|jpg> [--ref 레퍼런스.mp4|jpg] [--t 1.0,5.5,12] [--out 폴더] [--no-asr]
 - --t 없으면 처음·1/4·중간·3/4·끝 5곳. 이미지끼리면 한 장 나란히.
 - 출력: <out>/qc_cmp.jpg(왼쪽 레퍼런스 | 오른쪽 결과, 시각 표시), <out>/qc_sheet.jpg, 받아쓰기는 화면에 출력(맥 GPU mlx-whisper)."""
import os, subprocess, sys, json
from PIL import Image, ImageDraw, ImageFont
a = sys.argv[1:]
def opt(k, d=None):
    if k in a: i = a.index(k); v = a[i + 1]; del a[i:i + 2]; return v
    return d
ref = opt('--ref'); ts = opt('--t'); out = opt('--out'); asr = '--no-asr' not in a
a = [x for x in a if x != '--no-asr']; res = a[0]; out = out or os.path.dirname(os.path.abspath(res))
os.makedirs(out, exist_ok=True)
KIT = os.path.dirname(os.path.abspath(__file__))
F = ImageFont.truetype('/Users/daun/Library/Fonts/Pretendard-Bold.otf', 30)
isv = lambda p: p and p.lower().endswith(('.mp4', '.mov', '.m4v', '.webm'))
def dur(p): return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout.strip() or 0)
def frame(p, t, h=960):
    if not isv(p): im = Image.open(p).convert('RGB')
    else:
        q = f'{out}/_qc_{abs(hash((p, t)))}.png'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.2f}', '-i', p, '-frames:v', '1', q], check=True)
        im = Image.open(q).convert('RGB'); os.remove(q)
    return im.resize((int(im.width * h / im.height), h), Image.LANCZOS)
D = dur(res) if isv(res) else 0
T = [float(x) for x in ts.split(',')] if ts else ([0.3, D * .25, D * .5, D * .75, max(D - 0.3, 0)] if D else [0])
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(8) as ex:   # 프레임 뽑기 동시에
    FR = {(p, t): ex.submit(frame, p, t) for t in T for p in (ref, res) if p}
    FR = {k: v.result() for k, v in FR.items()}
cols = []
for t in T:
    pair = [FR[(p, t)] for p in (ref, res) if p]
    w = sum(p.width for p in pair) + 8 * (len(pair) - 1); c = Image.new('RGB', (w, 1010), (255, 255, 255)); x = 0
    for p in pair: c.paste(p, (x, 50)); x += p.width + 8
    ImageDraw.Draw(c).text((10, 8), (f'{t:.1f}s  ' if D else '') + ('레퍼런스 | 결과' if ref else '결과'), font=F, fill=(220, 30, 30))
    cols.append(c)
W = sum(c.width for c in cols) + 20 * (len(cols) - 1); cmp = Image.new('RGB', (W, 1010), (255, 255, 255)); x = 0
for c in cols: cmp.paste(c, (x, 0)); x += c.width + 20
if cmp.width > 4000: cmp = cmp.resize((4000, int(1010 * 4000 / cmp.width)), Image.LANCZOS)
cmp.save(f'{out}/qc_cmp.jpg', quality=88); print('비교:', f'{out}/qc_cmp.jpg')
if D:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', res, '-vf', 'fps=2,scale=200:-1,tile=8x9', '-frames:v', '1', f'{out}/qc_sheet.jpg'])
    print('시트:', f'{out}/qc_sheet.jpg', f'(길이 {D:.2f}초)')
    if asr and subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index', '-of', 'csv=p=0', res], capture_output=True, text=True).stdout.strip():
        print('--- 받아쓰기(결과)')
        subprocess.run([f'{KIT}/venv/mlxw/bin/python', '-I', f'{KIT}/mlxw.py', res], stderr=subprocess.DEVNULL)
