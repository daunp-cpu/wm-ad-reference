"""대행 메타 계정의 고효율 광고(계정 평균 ROAS 이상 + 구매수 중앙값 이상)와 실제 집행 일수·소재 정보.
결과: data/agency.json. 토큰: ~/sooo-meta/.env(다운, 기존 4개 계정) + ~/.config/ad-reference/meta_ceo.env(대표님 계정, 있으면).
대표님 계정들도 전체 기간(집행 종료 광고 포함)·여러 계정 동시 수집(10/22 다운: 라이브 아니어도 오래 집행된 고효율은 다). ONLY_CEO=1 이면 대표님 계정만 새로 받고 기존 4개는 파일 결과 유지."""
import json, urllib.request, urllib.parse, sys, time, datetime, statistics, os
from concurrent.futures import ThreadPoolExecutor
def env(p):
    d = {}
    for l in open(p):
        if '=' in l and not l.startswith('#'): k, v = l.strip().split('=', 1); d[k] = v.strip('"\'')
    return d
R = '/Users/daun/ad-reference/'; G = 'https://graph.facebook.com/v21.0/'
TOK0 = env('/Users/daun/sooo-meta/.env')['META_ACCESS_TOKEN']; CEO = os.path.expanduser('~/.config/ad-reference/meta_ceo.env')
ONLY_CEO = os.environ.get('ONLY_CEO') == '1'


def call(tok, path, params):
    u = G + path + '?' + urllib.parse.urlencode(dict(params, access_token=tok))
    for k in range(4):
        try: return json.load(urllib.request.urlopen(u, timeout=180))
        except Exception as e:
            body = getattr(e, 'read', lambda: b'')()[:300]
            if b'"code":190' in body: print('TOKEN_EXPIRED', path[:30], file=sys.stderr); return {'error': 'token'}
            if k == 3: return {'error': body.decode('utf8', 'ignore')}
            time.sleep(8)


def get(tok, path, params):
    out = []; r = call(tok, path, params)
    while True:
        out += r.get('data', []); nxt = r.get('paging', {}).get('next')
        if not nxt: return out
        for k in range(4):
            try: r = json.load(urllib.request.urlopen(nxt, timeout=180)); break
            except Exception: time.sleep(8)
        else: return out


def val(lst, t='omni_purchase'):
    for a in lst or []:
        if a['action_type'] == t: return float(a['value'])
    return 0.0


BASE = {'칸디데': ('204023223710992', 300000), 'FnL 올영': ('7647979655212098', 100000), '오브휴': ('1339660517182672', 50000), 'SOOO': ('1363134018754563', 50000)}
JOBS = [] if ONLY_CEO else [(n, a, m, TOK0, False) for n, (a, m) in BASE.items()]
if os.path.exists(CEO):   # 대표님 계정으로 보이는 광고 계정(기존 4개·비활성·지출 적은 계정 제외)
    ce = env(CEO); TC = ce['META_ACCESS_TOKEN']
    if datetime.date.fromisoformat(ce['EXPIRES']) - datetime.date.today() <= datetime.timedelta(days=14): print('CEO_TOKEN_EXPIRING', ce['EXPIRES'], file=sys.stderr)
    have = {a for a, _ in BASE.values()}
    F = {'fields': 'name,account_id,account_status,amount_spent,currency', 'limit': 200}
    allacc = {x['account_id']: x for x in get(TC, 'me/adaccounts', F)}
    for bz in get(TC, 'me/businesses', {'fields': 'id,name', 'limit': 100}):   # 비즈니스 관리자로만 보이는 계정까지
        for kind in ('owned_ad_accounts', 'client_ad_accounts'):
            for x in get(TC, f"{bz['id']}/{kind}", F): allacc.setdefault(x['account_id'], x)
    for a in allacc.values():
        krw = a.get('currency', 'KRW') == 'KRW'
        if a['account_id'] in have or int(a.get('amount_spent') or 0) < (1000000 if krw else 100000): continue   # 비활성·종료 계정도 과거 광고는 읽힘
        JOBS.append((a['name'].strip(), a['account_id'], 50000 if krw else 40, TC, True))
today = datetime.date.today()


def one(job):
    name, a, mins, tok, ceo = job
    q = {'level': 'ad', 'limit': 500, 'fields': 'ad_id,ad_name,spend,impressions,actions,action_values,catalog_segment_actions,catalog_segment_value',
         'filtering': json.dumps([{'field': 'spend', 'operator': 'GREATER_THAN', 'value': mins}])}
    q['date_preset'] = 'maximum'   # 전체 기간(메타 최대 37개월) — 지금 꺼진 광고도 포함
    rows = get(tok, 'act_%s/insights' % a, q); L = []
    for r in rows:
        sp = float(r['spend']); fnl = 'Collaborative' in name or name == 'FnL 올영'
        p, v = (val(r.get('catalog_segment_actions')), val(r.get('catalog_segment_value'))) if fnl else (val(r.get('actions')), val(r.get('action_values')))
        L.append(dict(acct=name, id=r['ad_id'], name=r['ad_name'], spend=sp, pur=p, val=v, roas=v / sp if sp else 0))
    if not L: print(name, 0, file=sys.stderr); return []
    acc = sum(x['val'] for x in L) / max(1, sum(x['spend'] for x in L)); pm = statistics.median([x['pur'] for x in L])
    sel = [x for x in L if x['roas'] >= acc and x['pur'] >= max(5, pm)]
    sel = sorted(sel, key=lambda x: -x['val'])[:150] if ceo else sel   # 큰 계정은 매출 큰 순 150개까지
    for x in sel: x['acct_roas'] = acc
    days = {}; ids = [x['id'] for x in sel]; s = datetime.date.fromisoformat(rows[0]['date_start'])   # 실제 집행일(지출 발생일)
    while s <= today:
        e = min(s + datetime.timedelta(days=89), today)
        for i in range(0, len(ids), 50):
            for r in get(tok, 'act_%s/insights' % a, {'level': 'ad', 'time_increment': 1, 'limit': 500, 'fields': 'ad_id,spend', 'time_range': json.dumps({'since': s.isoformat(), 'until': e.isoformat()}),
                                                     'filtering': json.dumps([{'field': 'ad.id', 'operator': 'IN', 'value': ids[i:i + 50]}, {'field': 'spend', 'operator': 'GREATER_THAN', 'value': 0}])}):
                days.setdefault(r['ad_id'], []).append(r['date_start'])
        s = e + datetime.timedelta(days=1)
    def cre(i): return i, call(tok, i, {'fields': 'effective_status,creative.thumbnail_width(720).thumbnail_height(720){object_type,thumbnail_url,image_url,video_id,body,object_story_spec,asset_feed_spec}'})
    with ThreadPoolExecutor(6) as ex: C = dict(ex.map(cre, ids))
    for x in sel:
        dd = days.get(x['id'], []); x['first'], x['last'], x['days'] = (min(dd), max(dd), len(dd)) if dd else (None, None, 0)
        c = C.get(x['id'], {}); cr = c.get('creative', {}); x['status'] = c.get('effective_status')
        x['img'] = cr.get('image_url') or cr.get('thumbnail_url'); x['body'] = (cr.get('body') or '')[:200]
        v = cr.get('video_id') or ((cr.get('object_story_spec') or {}).get('video_data') or {}).get('video_id')
        if not v and (cr.get('asset_feed_spec') or {}).get('videos'): v = cr['asset_feed_spec']['videos'][0].get('video_id')
        x['video_id'] = v
        if v:
            vi = call(tok, v, {'fields': 'source,length,picture'})
            if 'error' not in vi: x['vsrc'], x['vlen'], x['img'] = vi.get('source'), vi.get('length'), vi.get('picture') or x['img']
    print(name, len(sel), file=sys.stderr, flush=True); return sel


res = [x for x in json.load(open(R + 'data/agency.json')) if x['acct'] in BASE] if ONLY_CEO and os.path.exists(R + 'data/agency.json') else []
with ThreadPoolExecutor(5) as ex:   # 계정별 동시 수집(호출 한도는 계정 단위)
    for sel in ex.map(one, JOBS): res += sel
if res: json.dump(res, open(R + 'data/agency.json', 'w'), ensure_ascii=False)
print('대행 고효율 합계', len(res), file=sys.stderr)
