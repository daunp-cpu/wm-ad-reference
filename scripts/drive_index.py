"""SOOO 구글 드라이브 에셋 목록 → data/drive_index.json (daily.sh 에서 매일, 2026-11-04 다운 요청 + 복각 속도 개선).
Claude 복각 작업이 매번 드라이브를 훑지 않고 이 목록에서 바로 고르게 한다. 받은 적 있는 파일은 local 에 로컬 경로.
루트 = 다운이 준 두 폴더(하위에 시딩·제품·신뢰·WM 촬영·WM 제작이 다 들어 있음)."""
import json, os, subprocess, sys, time
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = {'광고주 에셋(시딩·제품·신뢰)': 'YOUR_DRIVE_FOLDER_ID_1', 'WM 에셋(촬영·제작)': 'YOUR_DRIVE_FOLDER_ID_2'}
LOCAL = [os.path.expanduser('~/Downloads/SOOO'), R + '/data/drive_cache']
sys.path.insert(0, R + '/scripts')
import gdrive
have = {}
for d in LOCAL:
    for dp, _, fs in os.walk(d):
        for f in fs: have.setdefault(f, os.path.join(dp, f))
rows = []
for label, fid in ROOTS.items():
    for p, f in gdrive.walk(fid):
        v = f.get('videoMediaMetadata') or {}
        if f['mimeType'].startswith('application/vnd.google-apps'): continue   # 시트·문서는 에셋 아님
        rows.append({'root': label, 'path': p, 'id': f['id'], 'mime': f['mimeType'], 'mb': round(int(f.get('size', 0)) / 1e6, 1),
                     'dur': round(int(v.get('durationMillis', 0)) / 1000, 1), 'wh': f"{v.get('width','')}x{v.get('height','')}" if v else '',
                     'local': have.get(f['name'])})
json.dump({'at': time.strftime('%F %T'), 'roots': ROOTS, 'files': rows}, open(R + '/data/drive_index.json', 'w'), ensure_ascii=False, indent=0)
print(len(rows), '개 →', R + '/data/drive_index.json', '| 로컬에 있음', sum(1 for r in rows if r['local']))
