"""SOOO 드라이브 에셋(~/Downloads/SOOO/SOOO_에셋) 목록 → data/assets.json + data/assets_grid.jpg(번호 붙은 썸네일 한 장, Gemini 컷 고르기용).
python3 -I asset_catalog.py   (에셋 폴더가 바뀌면 다시 실행)"""
import json, os, subprocess
from PIL import Image, ImageDraw, ImageFont
R = '/Users/daun/ad-reference/'; A = '/Users/daun/Downloads/SOOO/SOOO_에셋/'
FF, FP = '/Users/daun/.local/bin/ffmpeg', '/Users/daun/.local/bin/ffprobe'
# 다른 브랜드 레퍼런스·비포애프터·목소리·완성본 버전들은 제외, 단독 컷만
SUB = ['AI영상_기획소재1']
SKIP = ('B&A', '비포', 'v1', 'v2', 'v3', 'v5', 'v6', 'v7')
files = sorted(f for f in os.listdir(A) if f.endswith('.mp4')) + [f'{d}/{f}' for d in SUB for f in sorted(os.listdir(A + d)) if f.endswith('.mp4')]
files += ['IMG_3060_편집/SOOO_대표님_병맛_v8.mp4', 'IMG_3056_편집/SOOO_대표님_병맛2_v4.mp4']   # 대표님 출연 확정본(구간 잘라 쓰기)
out = []; os.makedirs(R + 'data/asset_thumbs', exist_ok=True)
for i, f in enumerate(files, 1):
    if not os.path.exists(A + f) or (any(k in f for k in SKIP) and '대표님' not in f): continue
    d = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', A + f], capture_output=True, text=True).stdout or 0)
    t = R + f'data/asset_thumbs/{len(out) + 1:02d}.jpg'
    subprocess.run([FF, '-y', '-v', 'error', '-ss', str(d / 2), '-i', A + f, '-frames:v', '1', '-vf', 'scale=180:320:force_original_aspect_ratio=increase,crop=180:320', t], check=True)
    nm = os.path.splitext(os.path.basename(f))[0]
    out.append({'n': len(out) + 1, 'file': f, 'dur': round(d, 2), 'name': nm, 'text': nm[:3] in ('01_', '02_', '03_') or '대표님' in nm})   # 화면에 글자·자막이 이미 박힌 클립
F = ImageFont.truetype('/Users/daun/Library/Fonts/Paperlogy-7Bold.ttf', 15)
cols = 8; rows = (len(out) + cols - 1) // cols; W, H = 180, 320 + 40
g = Image.new('RGB', (cols * W, rows * H), 'white'); dr = ImageDraw.Draw(g)
for k, x in enumerate(out):
    cx, cy = (k % cols) * W, (k // cols) * H
    g.paste(Image.open(R + f"data/asset_thumbs/{x['n']:02d}.jpg"), (cx, cy))
    dr.rectangle([cx, cy, cx + 34, cy + 24], fill='black'); dr.text((cx + 4, cy + 3), str(x['n']), font=F, fill='yellow')
    dr.text((cx + 3, cy + 323), x['name'][:13], font=F, fill='black'); dr.text((cx + 3, cy + 341), f"{x['dur']}초" + (' · 글자있음' if x['text'] else ''), font=F, fill='red' if x['text'] else 'gray')
g.save(R + 'data/assets_grid.jpg', quality=85)
json.dump(out, open(R + 'data/assets.json', 'w'), ensure_ascii=False, indent=1)
print('에셋', len(out))
