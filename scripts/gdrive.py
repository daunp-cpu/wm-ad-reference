"""구글 드라이브 폴더 재귀 목록/다운로드 (gcloud 로그인 토큰, 회사 프로젝트로 과금 없음)."""
import json, os, subprocess, sys, urllib.request, urllib.parse
PRJ = (json.load(open(os.path.expanduser('~/.config/advideo/config.json'))).get('vertex_project') if os.path.exists(os.path.expanduser('~/.config/advideo/config.json')) else None) or os.environ.get('GCP_PROJECT', 'gen-lang-client-0027494071')   # 호출 한도·과금이 잡힐 구글 클라우드 프로젝트
TOK = subprocess.check_output([next(g for g in (os.path.expanduser('~/.advideo/bin/gcloud'), os.path.expanduser('~/.local/bin/gcloud'), 'gcloud') if g == 'gcloud' or os.path.exists(g)), 'auth', 'print-access-token']).decode().strip()
H = {'Authorization': 'Bearer ' + TOK, 'x-goog-user-project': PRJ}
def api(path, **q):
    u = 'https://www.googleapis.com/drive/v3/' + path + '?' + urllib.parse.urlencode(q)
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=60).read())
def ls(fid):
    out, tok = [], None
    while True:
        q = dict(q=f"'{fid}' in parents and trashed=false", fields='nextPageToken,files(id,name,mimeType,size,videoMediaMetadata(width,height,durationMillis))',
                 pageSize=1000, supportsAllDrives='true', includeItemsFromAllDrives='true')
        if tok: q['pageToken'] = tok
        r = api('files', **q); out += r['files']; tok = r.get('nextPageToken')
        if not tok: return out
def walk(fid, path=''):
    for f in ls(fid):
        p = path + '/' + f['name']
        if f['mimeType'].endswith('folder'): yield from walk(f['id'], p)
        else: yield p, f
def get(fid, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    u = f'https://www.googleapis.com/drive/v3/files/{fid}?alt=media&supportsAllDrives=true'
    with urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=600) as r, open(dst, 'wb') as w:
        while True:
            b = r.read(1 << 20)
            if not b: break
            w.write(b)
if __name__ == '__main__':
    if sys.argv[1] == 'ls':
        rows = []
        for p, f in walk(sys.argv[2]):
            v = f.get('videoMediaMetadata') or {}
            rows.append({'path': p, 'id': f['id'], 'size': int(f.get('size', 0)), 'mime': f['mimeType'], 'dur': round(int(v.get('durationMillis', 0)) / 1000, 1), 'wh': f"{v.get('width','')}x{v.get('height','')}" if v else ''})
        json.dump(rows, open(sys.argv[3], 'w'), ensure_ascii=False, indent=1)
        for r in rows: print(f"{r['size']/1e6:7.1f}MB {r['dur']:5}s {r['wh']:>9}  {r['path']}")
        print(len(rows), '개', round(sum(r['size'] for r in rows) / 1e9, 2), 'GB')
    elif sys.argv[1] == 'get':   # gdrive.py get <파일id> <저장경로>
        get(sys.argv[2], sys.argv[3]); print(sys.argv[3])
    elif sys.argv[1] == 'thumb':   # gdrive.py thumb <파일id> <저장경로> — 영상 미리보기 그림만
        m = api('files/' + sys.argv[2], fields='thumbnailLink', supportsAllDrives='true')
        open(sys.argv[3], 'wb').write(urllib.request.urlopen(urllib.request.Request(m['thumbnailLink'].replace('=s220', '=s600'), headers=H), timeout=60).read()); print(sys.argv[3])
