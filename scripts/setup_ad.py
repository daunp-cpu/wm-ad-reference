"""검수 페이지 '세팅하기'·'ON/OFF' 처리. 사용: python3 -I setup_ad.py job.json
setup: {date,no,adset_id} → 이미지 업로드 → 크리에이티브 → 광고 생성(PAUSED). 광고 이름 = 업로드일_세트 안 순번 / 소구점 / image / 박다운 / 뷰티매거진
status: {date,no,on}       → 그 광고를 ACTIVE / PAUSED 로. 다운이 페이지에서 직접 누른 경우에만 실행됨."""
import json, os, sys, re, base64, datetime, urllib.request, urllib.parse, urllib.error
R = '/Users/daun/ad-reference/'
def env(p):
    d = {}
    for l in open(p):
        if '=' in l and not l.startswith('#'): k, v = l.strip().split('=', 1); d[k] = v.strip('"\'')
    return d
G = 'https://graph.facebook.com/v21.0/'
TOK = env('/Users/daun/sooo-meta/.env')['META_ACCESS_TOKEN']; ACC = 'act_YOUR_AD_ACCOUNT_ID'
PAGE, IG = '1154685114402994', '17841441288595196'; BEST_AD = '120252556403770391'   # 크리에이티브 기능은 베스트(공장탑특가)와 똑같이
BRS = json.load(open(R + 'data/brands.json')) if os.path.exists(R + 'data/brands.json') else {}
BC = {}   # 2026-11-10 브랜드(업체)별 계정 — 세팅 창에서 고른 계정(job.account) 또는 소재의 브랜드
KST = datetime.timezone(datetime.timedelta(hours=9)); NOW = datetime.datetime.now(KST)
def fail(msg, code=1):   # 실패 이유를 카드에 남기고 종료(75 = 메타 호출 한도 → 작업기가 3분 뒤 다시 시도)
    try:
        rv_ = json.load(open(R + 'data/review.json'))
        for x in rv_:
            if x['date'] == job['date'] and x.get('no') == job['no'] and x.get('ok'): x['setup_err'] = {'msg': msg[:200], 'at': NOW.strftime('%H:%M'), 'retry': code == 75, 'type': job['type']}
        json.dump(rv_, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1)
    except Exception: pass
    print('실패:', msg); sys.exit(code)
def _err(e):
    t = e.read().decode()[:600]
    if '"code":17' in t or '"code":4,' in t or '"code":613' in t or 'request limit' in t.lower(): fail('메타 호출 한도에 걸림 — 3분마다 자동으로 다시 시도해요', 75)
    try: m = json.loads(t)['error']; fail('메타 오류: ' + (m.get('error_user_msg') or m.get('message') or t))
    except (ValueError, KeyError): fail('메타 오류: ' + t)
def get(path, **p):
    p['access_token'] = TOK
    try: return json.load(urllib.request.urlopen(G + path + '?' + urllib.parse.urlencode(p), timeout=120))
    except urllib.error.HTTPError as e: _err(e)
def post(path, data):
    data = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in data.items()}; data['access_token'] = TOK
    try: return json.load(urllib.request.urlopen(urllib.request.Request(G + path, data=urllib.parse.urlencode(data).encode(), method='POST'), timeout=300))
    except urllib.error.HTTPError as e: _err(e)
job = json.load(open(sys.argv[1])); rv = json.load(open(R + 'data/review.json'))
rec = next(x for x in rv if x['date'] == job['date'] and x.get('no') == job['no'] and x.get('ok'))
AK = job.get('account') or (rec.get('meta_ad') or {}).get('account') or rec.get('brand') or 'SOOO'
if AK != 'SOOO':
    BC = BRS.get(AK) or {}
    if not BC.get('setup') or not os.path.exists(BC.get('token_env', '')): fail(f'{AK} 계정은 아직 메타 연결 전이라 세팅할 수 없어요')
    TOK = env(BC['token_env'])['META_ACCESS_TOKEN']; ACC = BC['account']; PAGE, IG = BC.get('page_id', ''), BC.get('ig_id', ''); BEST_AD = BC.get('best_ad', '')
def save(): json.dump(rv, open(R + 'data/review.json', 'w'), ensure_ascii=False, indent=1)
if job['type'] == 'status':
    if not rec.get('meta_ad'): raise SystemExit('아직 세팅 안 된 소재')
    st = 'ACTIVE' if job.get('on') else 'PAUSED'
    post(rec['meta_ad']['ad_id'], {'status': st})
    if st == 'ACTIVE':   # ON: 새로 만든(꺼진) 세트·캠페인이면 같이 켬
        a = get(rec['meta_ad']['ad_id'], fields='adset{id,status},campaign{id,status}')
        for k in ('adset', 'campaign'):
            if a[k]['status'] == 'PAUSED': post(a[k]['id'], {'status': 'ACTIVE'}); print(k, '켬')
    rec['meta_ad']['status'] = get(rec['meta_ad']['ad_id'], fields='status')['status']; rec['meta_ad']['changed'] = NOW.strftime('%m-%d %H:%M'); rec.pop('setup_err', None)
    save(); print('광고 상태', rec['meta_ad']['status']); sys.exit(0)
# ---- setup ----
if rec.get('meta_ad'): print('이미 세팅됨', rec['meta_ad']['ad_id']); sys.exit(0)
CF = 'name,objective,special_ad_categories,buying_type,bid_strategy,daily_budget,lifetime_budget,is_skadnetwork_attribution'
SF = 'name,campaign_id,daily_budget,lifetime_budget,optimization_goal,billing_event,bid_strategy,bid_amount,promoted_object,attribution_spec,targeting,destination_type,is_dynamic_creative'
camp = job.get('campaign_id')
same = lambda path, nm: next((x['id'] for x in get(path, fields='id,name', limit=500).get('data', []) if x['name'].strip() == nm.strip()), None)   # 같은 이름 있으면 재사용(중복 방지)
if job.get('new_campaign') and same(f'{ACC}/campaigns', job['new_campaign']): camp = same(f'{ACC}/campaigns', job['new_campaign']); print('같은 이름 캠페인 재사용', camp); job.pop('new_campaign')
if job.get('new_campaign'):   # 새 캠페인: 기준 캠페인 설정 그대로 복사(꺼진 상태로)
    src = get(job['copy_campaign'], fields=CF)
    d = {k: src[k] for k in ('objective', 'buying_type', 'bid_strategy', 'daily_budget', 'lifetime_budget') if src.get(k)}
    d.update(name=job['new_campaign'], status='PAUSED', special_ad_categories=src.get('special_ad_categories') or [])
    camp = post(f'{ACC}/campaigns', d)['id']; print('새 캠페인', camp)
adset = job.get('adset_id')
if job.get('new_adset') and same(f'{camp}/adsets', job['new_adset']): adset = same(f'{camp}/adsets', job['new_adset']); print('같은 이름 세트 재사용', adset); job.pop('new_adset')
if job.get('new_adset'):      # 새 세트: 기준 세트 설정 그대로 복사(예산만 바꿀 수 있음, 꺼진 상태로)
    src = get(job['copy_adset'], fields=SF)
    d = {k: src[k] for k in ('optimization_goal', 'billing_event', 'bid_strategy', 'bid_amount', 'promoted_object', 'attribution_spec', 'targeting', 'destination_type', 'daily_budget', 'lifetime_budget') if src.get(k)}
    ct = get(camp, fields='daily_budget,lifetime_budget')
    if ct.get('daily_budget') or ct.get('lifetime_budget'): d.pop('daily_budget', None); d.pop('lifetime_budget', None)   # 캠페인 예산(CBO)이면 세트 예산 없음
    elif job.get('budget'): d['daily_budget'] = int(job['budget']); d.pop('lifetime_budget', None)
    d.update(name=job['new_adset'], campaign_id=camp, status='PAUSED')
    adset = post(f'{ACC}/adsets', d)['id']; print('새 세트', adset)
aset = get(adset, fields='name,campaign{id,name},ads.limit(500){id}')   # 호출 한 번으로(메타 호출 한도 아끼기)
n = len((aset.get('ads') or {}).get('data', [])) + 1; nn = f'{n:03d}'
yymmdd, ymd = NOW.strftime('%y%m%d'), NOW.strftime('%Y%m%d'); pl = rec['plan']
KT = {'gif': 'GIF', 'video': 'video'}.get(rec.get('kind'), 'image') if any(v.get('mp4') for v in rec.get('versions', [])) or (rec.get('media') or {}).get('mp4') else 'image'
_nf = BC.get('name_fmt'); _person = {'다운': '박다운', '화영': '김화영', '도현': '박도현', '근형': '박근형', '형태': '유형태', '다솔': '다솔'}.get(job.get('by') or rec.get('by'), '박다운')
_ktk = {'image': '이미지', 'video': '영상', 'GIF': '영상'}.get(KT, KT)
name = job.get('ad_name') or (_nf.format(yymmdd=yymmdd, yyyymmdd=ymd, nn=nn, soguo=pl['soguo'], kt=KT, kt_ko=_ktk, person=_person) if _nf else None) or f"{yymmdd}_{nn} / {pl['soguo']} / {KT} / {({'다운': '박다운', '화영': '김화영', '도현': '박도현', '근형': '박근형', '형태': '유형태', '다솔': '다솔'}).get(job.get('by') or rec.get('by'), '박다운')} / 뷰티매거진"
if BC.get('link_prefix') and not (job.get('link') or '').startswith(BC['link_prefix']): fail(f"{AK} 는 {BC['link_prefix']} 링크가 필요해요 — " + BC.get('link_hint', ''))
if BC.get('utm') and not job.get('link'):   # 칸디데식: 랜딩 + utm (utm_content = 광고 이름 앞 코드)
    _base = re.sub(r'[&?]utm_[^&]*', '', rec.get('link') or BC.get('default_landing', ''))
    job['link'] = _base + ('&' if '?' in _base else '?') + BC['utm'].format(kt=KT, yymmdd=yymmdd, yyyymmdd=ymd, nn=nn)
link = job.get('link') or (BC and (rec.get('link') or BC.get('default_landing'))) or re.sub(r'utm_content=[^&]*', f'utm_content={ymd}_{nn}_{KT}', rec.get('link') or f"https://sooo.kr/product/detail.html?product_no=108&cate_no=1&display_group=2&utm_source=meta&utm_medium=display&utm_campaign=스칼프처샴푸&utm_content=x")
ver = next((v for v in rec.get('versions', []) if v['v'] == job.get('version')), None); src_img = ver['img'] if ver else rec['img']   # 확인 창에서 보던 버전
img = post(f'{ACC}/adimages', {'bytes': base64.b64encode(open(R + 'site/' + src_img, 'rb').read()).decode()})
h = list(img['images'].values())[0]['hash']
vv = ver or next((v for v in rec.get('versions', []) if v['v'] == rec.get('cur', 1)), {})
mp4 = vv.get('mp4') or ((rec.get('media') or {}).get('mp4') if vv.get('v', 1) == 1 else None)   # 그 버전에 영상이 있으면 동영상 광고
vid = None
if mp4:
    import uuid, time
    bd = uuid.uuid4().hex; fn = os.path.basename(mp4)
    body = (f'--{bd}\r\nContent-Disposition: form-data; name="access_token"\r\n\r\n{TOK}\r\n--{bd}\r\nContent-Disposition: form-data; name="name"\r\n\r\n{name}\r\n'
            f'--{bd}\r\nContent-Disposition: form-data; name="source"; filename="{fn}"\r\nContent-Type: video/mp4\r\n\r\n').encode() + open(R + 'site/' + mp4, 'rb').read() + f'\r\n--{bd}--\r\n'.encode()
    try: vid = json.load(urllib.request.urlopen(urllib.request.Request(f'https://graph-video.facebook.com/v21.0/{ACC}/advideos', data=body, headers={'Content-Type': f'multipart/form-data; boundary={bd}'}, method='POST'), timeout=600))['id']
    except urllib.error.HTTPError as e: raise SystemExit('영상 업로드 오류: ' + e.read().decode()[:400])
    for _ in range(15):   # 메타 쪽 영상 처리 끝날 때까지(20초 간격 — 호출 한도 아끼기)
        time.sleep(20)
        if get(vid, fields='status')['status'].get('video_status') == 'ready': break
    print('영상 업로드', vid)
DP = R + 'data/best_dof.json'
DP = DP if AK == 'SOOO' else R + f'data/best_dof_{AK}.json'
if not BEST_AD: dof = {}
elif os.path.exists(DP) and NOW.timestamp() - os.path.getmtime(DP) < 86400: dof = json.load(open(DP))
else: dof = get(BEST_AD, fields='creative{degrees_of_freedom_spec}')['creative']['degrees_of_freedom_spec']['creative_features_spec']; json.dump(dof, open(DP, 'w'))
dof = {k: v for k, v in dof.items() if k != 'standard_enhancements'}
for k, on in (job.get('features') or {}).items(): dof[k] = {'enroll_status': 'OPT_IN' if on else 'OPT_OUT'}   # 확인 창 AI 기능 선택
TITLE, MSG = job.get('title') or rec.get('title') or '두피열+떡짐 잡는 탈모샴푸 1+1', job.get('body') or rec['body']
spec = ({'video_data': {'video_id': vid, 'image_hash': h, 'title': TITLE, 'message': MSG, **({'link_description': job['desc']} if job.get('desc') else {}), 'call_to_action': {'type': 'SHOP_NOW', 'value': {'link': link}}}} if vid else
        {'link_data': {'image_hash': h, 'link': link, 'message': MSG, 'name': TITLE, **({'description': job['desc']} if job.get('desc') else {}), 'call_to_action': {'type': 'SHOP_NOW', 'value': {'link': link}}}})
CPAS = {}
if BC.get('cpas'):   # 2026-11-10 FnL 협업광고: 광고 소스(제품세트) 필수·CTA 는 목표별 (스킬 fnl-meta-setup 5장)
    _a = get(adset, fields='promoted_object,campaign{objective}'); _ps = (_a.get('promoted_object') or {}).get('product_set_id')
    if not _ps: fail('이 세트에 제품세트(product_set)가 없어요 — FnL 협업광고 세트를 골라주세요')
    CPAS = {'creative_sourcing_spec': {'associated_product_set_id': _ps}}; dof = {'product_extensions': {'enroll_status': 'OPT_IN', 'action_metadata': {'type': 'MANUAL'}}}
    _cta = 'LEARN_MORE' if (_a.get('campaign') or {}).get('objective') in ('OUTCOME_TRAFFIC', 'LINK_CLICKS') else 'SHOP_NOW'
    for _k in ('link_data', 'video_data'):
        if _k in spec: spec[_k]['call_to_action']['type'] = _cta
PG = job.get('page_id') or PAGE; IGU = job['ig_id'] if 'ig_id' in job else IG   # 확인 창에서 고른 아이덴티티
def mk(dof):
    return post(f'{ACC}/adcreatives', {'name': name, 'object_story_spec': {'page_id': PG, **({'instagram_user_id': IGU} if IGU else {}), **spec},
                **({'degrees_of_freedom_spec': {'creative_features_spec': dof}} if dof else {}), **CPAS, 'contextual_multi_ads': {'enroll_status': 'OPT_OUT'}})
GEN = ('advantage_plus_creative', 'text_generation', 'audio', 'video_auto_crop', 'video_uncrop')
if CPAS: GEN = ()   # 협업광고는 생성 기능 안 씀
try: cr = mk(dof)
except SystemExit as e:   # 이 형식에서 메타가 안 받는 생성 기능이면 그것만 빼고 다시
    if not any(k in dof for k in GEN): raise
    print('생성 기능 일부 거절됨 → 빼고 다시:', str(e)[:200]); dropped = [k for k in GEN if k in dof]
    dof = {k: v for k, v in dof.items() if k not in GEN}; cr = mk(dof); job['features_dropped'] = dropped
ad = post(f'{ACC}/ads', {'name': name, 'adset_id': adset, 'creative': {'creative_id': cr['id']}, 'status': 'PAUSED'})
chk = get(ad['id'], fields='name,status,creative{object_story_spec}')
oss = chk['creative']['object_story_spec']; ok = (oss.get('link_data', {}).get('link') or oss.get('video_data', {}).get('call_to_action', {}).get('value', {}).get('link')) == link
rec['meta_ad'] = {'ad_id': ad['id'], 'account': AK, 'name': name, 'link': link, 'adset': aset['name'], 'campaign': aset['campaign']['name'], 'status': chk['status'], 'img': src_img, 'title': job.get('title'), 'desc': job.get('desc'), 'features': job.get('features'), 'features_dropped': job.get('features_dropped'), 'at': NOW.strftime('%m-%d %H:%M'), 'checked': ok}
rec.pop('setup_err', None); rec['ad_name'], rec['link'] = name, link; save()
_mc = R + ('data/meta_cache.json' if AK == 'SOOO' else f'data/meta_cache_{AK}.json')
if os.path.exists(_mc): os.remove(_mc)   # 새 세트가 바로 목록에 보이게
json.dump({'campaign_id': aset['campaign']['id'] if 'id' in aset['campaign'] else camp, 'adset_id': adset, 'page_id': PG, 'ig_id': IGU}, open(R + ('data/setup_prefs.json' if AK == 'SOOO' else f'data/setup_prefs_{AK}.json'), 'w')); print('세팅 완료', ad['id'], name, chk['status'], '링크 확인' if ok else '⚠️ 링크 확인 필요')
