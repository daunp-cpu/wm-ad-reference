"""대행 계정 고효율 소재의 영상 주소(vsrc) 채우기 — agency.py 다음에 실행. 결과는 data/agency.json 에 덮어씀.
광고 토큰으로는 영상 source 를 안 줘서(페이지 토큰 필요) ① 우리가 관리하는 페이지면 페이지 토큰으로 video.source
② 아니면 광고에 연결된 인스타 게시물(effective_instagram_media_id)의 media_url. 주소는 며칠 뒤 만료 → 매일 아침 다시."""
import json, os, sys, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
R = '/Users/daun/ad-reference/'; G = 'https://graph.facebook.com/v21.0/'
def env(p):
    d = {}
    for l in open(p):
        if '=' in l and not l.startswith('#'): k, v = l.strip().split('=', 1); d[k] = v.strip('"\'')
    return d
T0 = env('/Users/daun/sooo-meta/.env')['META_ACCESS_TOKEN']
CEO = os.path.expanduser('~/.config/ad-reference/meta_ceo.env'); TC = env(CEO)['META_ACCESS_TOKEN'] if os.path.exists(CEO) else T0
BASE = ('칸디데', 'FnL 올영', '오브휴', 'SOOO')   # agency.py 의 다운 토큰 계정


def call(tok, path, p):
    try: return json.load(urllib.request.urlopen(G + path + '?' + urllib.parse.urlencode(dict(p, access_token=tok)), timeout=60))
    except Exception: return {}


PT = {}   # 페이지 id → 페이지 토큰
for t in (T0, TC):
    r = call(t, 'me/accounts', {'fields': 'id,access_token', 'limit': 200})
    while True:
        for p in r.get('data', []): PT.setdefault(p['id'], p['access_token'])
        nxt = r.get('paging', {}).get('next')
        if not nxt: break
        try: r = json.load(urllib.request.urlopen(nxt, timeout=60))
        except Exception: break


def one(x):
    tok = T0 if x['acct'] in BASE else TC
    fr = call(tok, x['video_id'], {'fields': 'from'}).get('from', {}).get('id')
    if fr in PT:
        v = call(PT[fr], x['video_id'], {'fields': 'source,length'})
        if v.get('source'): return x, v['source'], v.get('length')
    c = call(tok, x['id'], {'fields': 'creative{effective_instagram_media_id}'}).get('creative', {})
    if c.get('effective_instagram_media_id'):
        m = call(tok, c['effective_instagram_media_id'], {'fields': 'media_url,media_type'})
        if m.get('media_type') == 'VIDEO' and m.get('media_url'): return x, m['media_url'], None
    return x, None, None


ag = json.load(open(R + 'data/agency.json'))
todo = [x for x in ag if x.get('video_id')]
ok = 0
with ThreadPoolExecutor(6) as ex:
    for x, src, ln in ex.map(one, todo):
        x['vsrc'] = src
        if ln and not x.get('vlen'): x['vlen'] = ln
        ok += bool(src)
# 2026-11-11: 11/4 아침 인터넷 안 붙은 채 돌아 주소를 전부 빈칸(0/1591)으로 덮어써서 대행 탭 영상이 일주일 넘게 안 나옴 → 거의 못 받았으면 저장 안 함
if todo and ok < len(todo) * 0.3:
    print('대행 영상 주소', ok, '/', len(todo), '— 너무 적어서 저장 안 함(인터넷·토큰 확인)', file=sys.stderr); sys.exit(2)
json.dump(ag, open(R + 'data/agency.json', 'w'), ensure_ascii=False)
print('대행 영상 주소', ok, '/', len(todo), file=sys.stderr)
