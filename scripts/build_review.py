"""data/review.json → site/review.html(날짜별 탭 검수 페이지) + site/refstatus.json(레퍼런스별 제작완료·세팅완료 표시용).
세팅완료 = SOOO 메타 계정에 같은 '날짜_번호 / 소구점' 으로 시작하는 광고가 있으면."""
import re, json, os, html, urllib.request, urllib.parse, datetime
import sys; sys.path.insert(0, '/Users/daun/ad-reference/scripts'); import cost as COST
from spend_ui import SPEND_CSS, SPEND_DLG, SPEND_JS
from spend_ui import DATECAL_CSS, DATECAL_DLG, DATECAL_JS
R = '/Users/daun/ad-reference/'; CHECK = '✔ 화학박사가 개발한 두피 딥클렌징 샴푸\n✔ 1회 사용 후 두피 온도 -4.5°C (㈜휴먼피부임상시험센터, 21명)\n✔ 탈모 증상 완화 기능성\n✔ 국립낙동강생물자원관 기술이전 특허 성분\n✔ 500ml 대용량 2병'; esc = lambda s: html.escape(str(s or ''))
rv = json.load(open(R + 'data/review.json')) if os.path.exists(R + 'data/review.json') else []
def env(p):
    d = {}
    for l in open(p):
        if '=' in l and not l.startswith('#'): k, v = l.strip().split('=', 1); d[k] = v.strip('"\'')
    return d
import time as _t
CP = R + 'data/meta_cache.json'; CACHE = json.load(open(CP)) if os.path.exists(CP) else {}
USE_CACHE = bool(CACHE) and _t.time() - CACHE.get('at', 0) < 600 and os.environ.get('FRESH') != '1'   # 메타 호출 한도 보호
names = []
try:
    if USE_CACHE: raise RuntimeError('10분 안 저장본 사용')
    T = env('/Users/daun/sooo-meta/.env')['META_ACCESS_TOKEN']
    u = 'https://graph.facebook.com/v21.0/act_YOUR_AD_ACCOUNT_ID/ads?' + urllib.parse.urlencode({'fields': 'name', 'limit': 500, 'access_token': T})
    while u:
        d = json.load(urllib.request.urlopen(u, timeout=60)); names += [a['name'] for a in d.get('data', [])]; u = d.get('paging', {}).get('next')
except Exception as e: print('메타 조회 실패(세팅완료 표시는 이전 상태 유지 안 함):', str(e)[:120])
ACCT = []
try:
    if USE_CACHE: raise RuntimeError('10분 안 저장본 사용')
    def g(path, **p):
        p['access_token'] = T; out = []; u = 'https://graph.facebook.com/v21.0/' + path + '?' + urllib.parse.urlencode(p)
        while u:
            d = json.load(urllib.request.urlopen(u, timeout=60)); out += d.get('data', []); u = d.get('paging', {}).get('next')
        return out
    flt = json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': ['ACTIVE', 'PAUSED', 'CAMPAIGN_PAUSED', 'ADSET_PAUSED', 'IN_PROCESS', 'WITH_ISSUES']}])
    for c in g('act_YOUR_AD_ACCOUNT_ID/campaigns', fields='id,name,effective_status,daily_budget,created_time', filtering=flt, limit=100):
        sets = g(c['id'] + '/adsets', fields='id,name,effective_status,daily_budget,created_time,ads.limit(500){id}', filtering=flt, limit=100)
        ACCT.append({'id': c['id'], 'name': c['name'], 'st': c['effective_status'], 'cbo': bool(c.get('daily_budget')), 'at': c['created_time'],
                     'sets': [{'id': x['id'], 'name': x['name'], 'st': x['effective_status'], 'budget': int(x.get('daily_budget') or 0), 'n': len((x.get('ads') or {}).get('data', [])), 'at': x['created_time']} for x in sets]})
    ACCT.sort(key=lambda c: c['at'], reverse=True)
    for c in ACCT: c['sets'].sort(key=lambda x: x['at'], reverse=True)
    def _st(x):   # 2026-11-04 속도: 광고별 상태 조회를 한 개씩 → 동시에(결과 같음)
        try: x['meta_ad']['status'] = json.load(urllib.request.urlopen('https://graph.facebook.com/v21.0/%s?fields=status,effective_status&access_token=%s' % (x['meta_ad']['ad_id'], T), timeout=30))['status']
        except Exception: pass
    from concurrent.futures import ThreadPoolExecutor as _TP
    with _TP(12) as _ex: list(_ex.map(_st, [x for x in rv if x.get('meta_ad')]))
except Exception as e: print('계정 구조 조회 실패:', str(e)[:120])
IDENT = []   # 고를 수 있는 페이지·인스타(이 광고 계정 연결 페이지 + SOOO 브랜드 페이지만)
try:
    if USE_CACHE: raise RuntimeError('10분 안 저장본 사용')
    gq = lambda p, **q: json.load(urllib.request.urlopen('https://graph.facebook.com/v21.0/' + p + '?' + urllib.parse.urlencode(dict(q, access_token=T)), timeout=60)).get('data', [])
    pp = gq('act_YOUR_AD_ACCOUNT_ID/promote_pages', fields='id,name,instagram_business_account{id,username}', limit=50)
    ma = [x for x in gq('me/accounts', fields='id,name,instagram_business_account{id,username}', limit=100) if 'SOOO' in x['name'].upper()]
    for x in pp + ma:
        if any(i['id'] == x['id'] for i in IDENT): continue
        ig = x.get('instagram_business_account') or {}
        IDENT.append({'id': x['id'], 'name': x['name'], 'ig': ig.get('id', ''), 'igname': ig.get('username', ''), 'linked': x in pp})
except Exception as e: print('아이덴티티 조회 실패:', str(e)[:120])
if names and ACCT and IDENT: json.dump({'at': _t.time(), 'names': names, 'ACCT': ACCT, 'IDENT': IDENT}, open(CP, 'w'), ensure_ascii=False)
else:
    names = names or CACHE.get('names', []); ACCT = ACCT or CACHE.get('ACCT', []); IDENT = IDENT or CACHE.get('IDENT', [])
    if CACHE: print('메타 목록은 저장본 사용(%d분 전)' % ((_t.time() - CACHE.get('at', 0)) // 60))
if not IDENT: IDENT = [{'id': '1154685114402994', 'name': '뷰티매거진', 'ig': '17841441288595196', 'igname': 'beautymag.kr', 'linked': True}]
# 2026-11-10 브랜드(업체)별 광고 계정 — data/brands.json. SOOO 는 위 그대로, 나머지는 계정마다 따로(10분 저장본)
BRS = json.load(open(R + 'data/brands.json')) if os.path.exists(R + 'data/brands.json') else {}
ACCTS, IDENTS, BR_SET = {'SOOO': ACCT}, {'SOOO': IDENT}, {}
for _bk, _bc in BRS.items():
    BR_SET[_bk] = {'label': _bc.get('label', _bk), 'setup': bool(_bc.get('setup')), 'name_fmt': _bc.get('name_fmt', ''), 'default_landing': _bc.get('default_landing', ''), 'link_prefix': _bc.get('link_prefix', ''), 'link_hint': _bc.get('link_hint', '')}
    if _bk == 'SOOO' or not _bc.get('setup') or not os.path.exists(_bc.get('token_env', '')): continue
    _cp = R + f'data/meta_cache_{_bk}.json'; _c = json.load(open(_cp)) if os.path.exists(_cp) else {}
    if _c and _t.time() - _c.get('at', 0) < 600 and os.environ.get('FRESH') != '1': ACCTS[_bk], IDENTS[_bk] = _c['ACCT'], _c['IDENT']; continue
    try:
        _T = env(_bc['token_env'])['META_ACCESS_TOKEN']
        def _g(path, **p):
            p['access_token'] = _T; out = []; u = 'https://graph.facebook.com/v21.0/' + path + '?' + urllib.parse.urlencode(p)
            while u:
                d = json.load(urllib.request.urlopen(u, timeout=60)); out += d.get('data', []); u = d.get('paging', {}).get('next')
            return out
        _flt = json.dumps([{'field': 'effective_status', 'operator': 'IN', 'value': ['ACTIVE', 'PAUSED', 'CAMPAIGN_PAUSED', 'ADSET_PAUSED', 'IN_PROCESS', 'WITH_ISSUES']}])
        _A = []   # 계정 단위로 한 번에(캠페인마다 부르면 큰 계정은 호출 한도) — 켜져 있거나 최근 120일 안에 만든 것만
        import datetime as _dt
        _cut = (_dt.datetime.utcnow() - _dt.timedelta(days=120)).strftime('%Y-%m-%d')
        _cs = [c for c in _g(_bc['account'] + '/campaigns', fields='id,name,effective_status,daily_budget,created_time', filtering=_flt, limit=200) if c['effective_status'] == 'ACTIVE' or c['created_time'][:10] >= _cut]
        _ss = _g(_bc['account'] + '/adsets', fields='id,name,campaign_id,effective_status,daily_budget,created_time,ads.limit(0).summary(true)', filtering=_flt, limit=200)
        for c in _cs:
            sets = [x for x in _ss if x.get('campaign_id') == c['id']]
            _A.append({'id': c['id'], 'name': c['name'], 'st': c['effective_status'], 'cbo': bool(c.get('daily_budget')), 'at': c['created_time'],
                       'sets': sorted([{'id': x['id'], 'name': x['name'], 'st': x['effective_status'], 'budget': int(x.get('daily_budget') or 0), 'n': ((x.get('ads') or {}).get('summary') or {}).get('total_count', 0), 'at': x['created_time']} for x in sets], key=lambda x: x['at'], reverse=True)})
        _A.sort(key=lambda c: c['at'], reverse=True)
        _I = [{'id': _bc['page_id'], 'name': _bc.get('page_label', _bk), 'ig': _bc.get('ig_id', ''), 'igname': _bc.get('ig_name', ''), 'linked': True}] if _bc.get('page_id') else []
        ACCTS[_bk], IDENTS[_bk] = _A, _I; json.dump({'at': _t.time(), 'ACCT': _A, 'IDENT': _I}, open(_cp, 'w'), ensure_ascii=False)
    except Exception as e:
        print(_bk, '계정 구조 조회 실패:', str(e)[:120]); ACCTS[_bk], IDENTS[_bk] = _c.get('ACCT', []), _c.get('IDENT', [])
PREF = json.load(open(R + 'data/setup_prefs.json')) if os.path.exists(R + 'data/setup_prefs.json') else {}
def norm(s): return s.replace(' ', '')
for x in rv:
    if x.get('ok'):
        key = norm(re.split(r' / (?:image|GIF|video|img)', x['ad_name'])[0])   # 예: 261019_001/가격폭탄
        x['live'] = bool(x.get('meta_ad')) or any(norm(n).startswith(key) for n in names)
rv = [x for x in rv if not x.get('deleted')]   # 삭제한 소재는 빼기
ITEMCOST = COST.by_item(R)   # 소재별로 든 AI 비용(원)
for x in rv: x.setdefault('by', '다운')
st = {}   # 레퍼런스 id → {s: 세팅완료/제작완료/실패, d: '10.19'}
for x in rv:
    if not x.get('ref_id'): continue
    s_ = '세팅완료' if x.get('live') else ('제작완료' if x.get('ok') else '실패')
    d_ = '%d.%d' % tuple(int(t) for t in x['date'].split('-')[1:])
    o = st.get(x['ref_id']); rk = {'세팅완료': 2, '제작완료': 1, '실패': 0}
    if o and (rk[o['s']], o['d']) >= (rk[s_], d_): continue
    st[x['ref_id']] = {'s': s_, 'd': d_, 'by': x['by']}
json.dump(st, open(R + 'site/refstatus.json', 'w'), ensure_ascii=False)
dates = sorted({x['date'] for x in rv}, reverse=True)
def lab(d): y, m, dd = d.split('-'); return f'{int(m)}월 {int(dd)}일'
PEOPLE = ['화영', '다운', '도현', '근형', '형태','다솔']
ptabs = ''.join(f'<button class="ptab" data-p="{p}">{p} <small>{sum(1 for x in rv if x["by"]==p and x.get("ok"))}</small></button>' for p in PEOPLE)
OLDATTR = {d: ('' if d in dates[:3] else ' data-old="1"') for d in dates}   # 날짜 탭은 최근 3개만 보이고, 나머지는 달력에서 고르면 나타난다
tabs = ''.join(f'<button class="tab" data-p="{p}" data-d="{d}"{OLDATTR[d]}>{lab(d)} <small>{sum(1 for x in rv if x["date"]==d and x["by"]==p and x.get("ok"))}</small></button>' for p in PEOPLE for d in dates if any(x["date"]==d and x["by"]==p for x in rv))
DAYCNT = {p: {d: n for d in dates for n in [sum(1 for x in rv if x['date'] == d and x['by'] == p and x.get('ok'))] if n} for p in PEOPLE}   # 달력에 찍을 날짜별 소재 수
import shutil, subprocess
RD = R + 'site/r/'; os.makedirs(RD, exist_ok=True)
def refmedia(i):   # 검수 카드 밑에 띄울 레퍼런스 원본 → site/r/<id>.mp4·.jpg 로 복사, (영상, 사진) 웹 경로
    i = str(i or ''); v = p = ''
    if not i: return v, p
    for q in [R + f'data/custom/{i}.{e}' for e in ('mp4', 'mov', 'm4v', 'webm')] + [R + f'data/ref_{i}.mp4', R + f'site/m/L{i}.mp4']:
        if not os.path.exists(q): continue
        o = RD + i + '.mp4'
        if not os.path.exists(o) or os.path.getmtime(o) < os.path.getmtime(q):
            if q.endswith('.mp4') and os.path.getsize(q) < 8e6: shutil.copy(q, o)
            else: subprocess.run(['/Users/daun/.local/bin/ffmpeg', '-y', '-v', 'error', '-i', q, '-vf', 'scale=540:-2', '-c:v', 'libx264', '-crf', '28', '-c:a', 'aac', '-movflags', '+faststart', o])
        if os.path.exists(o): v = 'r/' + i + '.mp4'
        break
    for q in (R + f'data/ref_{i}.jpg', R + f'site/m/L{i}.jpg', R + f'site/m/A{i}.jpg', R + f'data/ref_{i}_sheet.jpg'):
        if not os.path.exists(q): continue
        o = RD + i + '.jpg'
        if not os.path.exists(o) or os.path.getmtime(o) < os.path.getmtime(q): shutil.copy(q, o)
        p = 'r/' + i + '.jpg'; break
    return v, p
def refblock(x):   # 레퍼런스 원본 = 출처 줄 밑 작은 썸네일 버튼 → 누르면 팝업(10/22 다운: 너무 크게 보임)
    v, p = refmedia(x.get('ref_id'))
    if not (v or p): return '<span class="rno">원본 파일이 저장돼 있지 않아요 · "원본 ↗" 링크로 확인해 주세요</span>'
    th = f'<img src="{p}" alt="" loading="lazy">' if p else '<i>▶</i>'
    return f'<button type="button" class="rthumb" data-v="{v or ""}" data-p="{p or ""}" title="레퍼런스 원본 크게 보기">{th}<span>레퍼런스 원본 보기{" ▶ 영상" if v else ""}</span></button>'
cards = []
for x in sorted(rv, key=lambda x: (x['date'], x.get('no') or 'zz')):
    ref = f'<a href="https://www.facebook.com/ads/library/?id={x["ref_id"]}" target="_blank" rel="noopener">{esc(x["ref_page"]) or "레퍼런스"} 원본 ↗</a> · {esc(x["ref_kind"])}{" · %s일째" % x["ref_days"] if x.get("ref_days") else ""}'
    if not x.get('ok'):
        e = x.get('err') or ''
        why = ('구글 클라우드 로그인 만료 — Claude 에게 다시 로그인을 요청해 주세요(그 뒤 다시 복각하기)' if ('Reauthentication' in e or 'gcloud' in e or 'print-access-token' in e) else 'AI(Gemini) 이번 달 사용 한도 초과 — 관리자가 한도를 올린 뒤 다시 복각하기를 눌러주세요' if 'spending cap' in e or 'RESOURCE_EXHAUSTED' in e
               else 'AI 응답이 늦어 멈춤 — 잠시 뒤 다시 복각하기를 눌러주세요' if ('timed out' in e or '응답 없음' in e) else '제작 중 오류 — 다시 복각하기를 눌러주세요 (계속되면 Claude 에게 알려주세요)')
        cards.append(f'<article class="card fail" data-p="{x["by"]}" data-d="{x["date"]}"><div class="body"><div class="top"><button type="button" class="del" data-fjob="{esc(x.get("job",""))}" data-fref="{esc(str(x.get("ref_id","")))}" title="이 실패 기록 삭제">삭제</button><span class="no">실패</span>{ref}<span class="ref">{esc(x.get("made",""))}</span></div><p class="note"><b>{why}</b><br><small>원인: {esc(e[:140])}</small></p><div class="rtr"><button type="button" class="retry" data-fjob="{esc(x.get("job",""))}" data-fref="{esc(str(x.get("ref_id","")))}">↻ 다시 복각하기</button><span class="rts">처음 넣은 설정(이름·랜딩·참고 파일·메모) 그대로 다시 만들어요{" · 이미 만든 장면은 다시 돈 안 들어요" if "영상" in (x.get("ref_kind") or "") else ""}</span></div></div></article>'); continue
    pl = x['plan']; badge = '<span class="st live">세팅완료</span>' if x.get('live') else '<span class="st pre">세팅 전</span>'
    if x.get('revised'): badge += f'<span class="st rev">수정완료_{x["revised"]}</span>'
    vs = x.get('versions') or [{'v': 1, 'img': x['img'], 'plan': pl, 'at': x.get('made', ''), 'note': '처음 복각'}]
    cur = x.get('cur', vs[-1]['v'])
    def body_of(v):
        q = v['plan']
        if q.get('body'): return q['body']   # 다른 상품 랜딩은 그 상품용 본문
        return f"[1+1🔥] 탈모샴푸 개당 2만원대!\n{q['hook1']}\n{q['hook2']}\n\n{CHECK}\n\n지금 공식몰에서 1+1로 만나보세요👇"
    KT = {'gif': 'GIF', 'video': 'video'}.get(x.get('kind'), 'image'); md = x.get('media') or {}
    PN = {'다운': '박다운', '화영': '김화영', '도현': '박도현', '근형': '박근형', '형태': '유형태', '다솔': '다솔'}.get(x.get('by'), '박다운')   # 만든 사람 이름
    def name_of(v): return f"{x['ad_name'].split('_')[0]}_{x['no']} / {v['plan']['soguo']} / {KT} / {PN} / 뷰티매거진"
    vdata = esc(json.dumps([{'v': v['v'], 'img': v['img'], 'name': name_of(v), 'body': body_of(v), 'mp4': v.get('mp4') or (md.get('mp4', '') if v['v'] == 1 else ''), 'note': v.get('note', ''), 'fb': v.get('feedback', ''), 'at': v.get('at', ''), 'from': v.get('from'), 'review': v.get('review') or []} for v in vs], ensure_ascii=False))
    vbtn = ''.join(f'<button type="button" class="vb" data-v="{v["v"]}">v{v["v"]}{"★" if v["v"] == cur else ""}</button>' for v in vs)
    cards.append(f'''<article class="card" data-p="{x["by"]}" data-d="{x["date"]}" data-brand="{esc(x.get("brand") or "SOOO")}" data-cur="{cur}" data-vs="{vdata}"><div class="media">{f'<video class="mv" src="{md["mp4"]}" poster="{x["img"]}" autoplay muted loop playsinline controls preload="metadata"></video>' if md.get("mp4") else ""}<img class="mi" src="{x["img"]}" alt="{esc(pl["soguo"])} 복각 소재" loading="lazy" {"hidden" if md.get("mp4") else ""}></div><div class="body">
<div class="top"><span class="delw"><button type="button" class="del" data-date="{x["date"]}" data-no="{x["no"]}" data-live="{1 if x.get("meta_ad") else ""}" title="이 소재 삭제">삭제</button>{f'<span class="cst">약 {ITEMCOST[x["date"] + "/" + x["no"]]:,}원</span>' if ITEMCOST.get(x["date"] + "/" + x["no"]) else ""}</span><span class="no">{x["no"]}</span>{f'<span class="brd">{esc(x.get("brand"))}</span>' if x.get("brand") and x.get("brand") != "SOOO" else ""}<span class="ttl">{esc(pl["soguo"])}</span>{badge}<span class="ref">{x["made"]} 제작</span></div>
<div class="vers"><span class="vl">버전</span>{vbtn}<span class="vinfo"></span><button type="button" class="usev" hidden>이 버전으로 쓰기</button></div><details class="vrev" hidden><summary></summary><div class="vrevb"></div></details>
<p class="ref">{ref}<br>{refblock(x)}<br>형식: {esc(pl.get("format"))}<br>오래 도는 이유: {esc(pl.get("why"))}</p>
<dl class="kv"><dt>광고 이름</dt><dd class="mono vname">{esc(x["ad_name"])}</dd><dt>본문</dt><dd><div class="copy vbody">{esc(x["body"])}</div></dd><dt>랜딩</dt><dd>{esc(x.get("landing_title") or "자사몰 · 스칼프처 샴푸 1+1 (108번)")}</dd><dt>버튼</dt><dd>지금 구매하기</dd><dt>링크</dt><dd class="mono">{esc(x["link"])}</dd>
<dt>파일</dt><dd><a class="dl" href="{x["img"]}" download>{"대표컷" if md else "이 버전 이미지"} 받기</a>{f' · <a href="{md["mp4"]}" download>mp4 받기</a>' if md.get("mp4") else ""}{f' · <a href="{md["gif"]}" download>GIF 받기</a>' if md.get("gif") else ""}</dd>
{f'<dt>메모</dt><dd>{esc(x["memo"])}</dd>' if x.get("memo") else ""}</dl>
<div class="fb" data-key="{x["date"]}_{x["no"]}"><textarea placeholder="지금 보고 있는 버전을 기준으로 고쳐요. 피드백을 적고 수정하기를 누르면 몇 분 안에 새 버전으로 올라와요. 예) 가격을 더 크게, 배경을 연보라로, 후킹 문구를 더 짧게" rows="3"></textarea>
<label class="fbdz"><input type="file" class="fbf" multiple accept="image/*,video/*,audio/*,.mp3,.wav,.m4a,.aac,.pdf,.txt,.md,.doc,.docx,.rtf,.pptx"><span class="dzi">📎</span><span class="dzt"><b>수정 참고 파일 추가</b><span class="dzs">사진·영상·음성(나레이션 mp3·wav·m4a)·기획안(PDF·워드·PPT)을 끌어다 놓거나 눌러서 고르세요 · 최대 10개 · 피드백에서 F1, F2… 로 부르면 돼요</span></span><span class="dzc"></span></label><div class="uprev fbp"></div>
<div class="fbr"><span class="fbs"></span><button type="button" class="go" data-date="{x["date"]}" data-no="{x["no"]}">수정하기</button></div>{f'<div class="rerr">⚠ {esc(x["revise_err"]["at"])} 수정 요청이 처리되지 않았어요 — {esc(x["revise_err"]["msg"])}</div>' if (x.get("revise_err") or {}).get("at","") > max([v.get("at") or "" for v in (x.get("versions") or [])] + [""]) else ""}
<div class="ops" data-date="{x["date"]}" data-no="{x["no"]}" data-ad="{esc((x.get("meta_ad") or {}).get("ad_id",""))}" data-st="{esc((x.get("meta_ad") or {}).get("status",""))}" data-soguo="{esc(pl["soguo"])}" data-kind="{KT}" data-by="{x["by"]}" data-link="{esc(x.get("link",""))}" data-title="{esc(x.get("title") or "두피열+떡짐 잡는 탈모샴푸 1+1")}" data-lt="{esc(x.get("landing_title",""))}">
<button type="button" class="setup">{"세팅완료 · " + esc(x["meta_ad"]["adset"]) if x.get("meta_ad") else "세팅하기"}</button>
<button type="button" class="on" {"" if x.get("meta_ad") else "disabled"}>ON</button><button type="button" class="off" {"" if x.get("meta_ad") else "disabled"}>OFF</button><span class="ops-s"></span>{f'<span class="serr">⚠ {"세팅" if x["setup_err"].get("type")=="setup" else "ON/OFF"} 실패({x["setup_err"]["at"]}): {esc(x["setup_err"]["msg"])}{"" if x["setup_err"].get("retry") else " — 다시 눌러주세요"}</span>' if x.get("setup_err") else ""}{f'<a class="amgr" href="https://adsmanager.facebook.com/adsmanager/manage/ads/edit?act=1363134018754563&selected_ad_ids={x["meta_ad"]["ad_id"]}" target="_blank" rel="noopener" title="메타 광고관리자 편집 화면에서 Advantage+ 미리보기와 AI 생성 후보(어드밴티지+ 크리에이티브 생성 → 사용해보기)를 보고 고를 수 있어요">Advantage+ 미리보기·AI 후보 보기 ↗</a>' if x.get("meta_ad") else ""}</div></div></div></article>''')
# 이 사이트로 소재를 만들며 실제 호출한 AI 비용(data/cost.json)
COST.seed(R)          # 기록 심기 전 소재는 건당 추정으로 한 번만 채운다
_won, _n, _est = COST.month_total(R)   # 표시는 이번 달치만(달마다 새로 센다). 기록 자체는 다 남는다
_allwon = COST.total(R)[0]
_mon = int(datetime.date.today().strftime('%m'))
# ZCRE 생성 탭 크레딧(data/zcre/state.json — 이번 달 사용·잔액)
_zs = json.load(open(R + 'data/zcre/state.json')) if os.path.exists(R + 'data/zcre/state.json') else {}
_zm = datetime.date.today().strftime('%Y-%m')
_zused = sum(float(x.get('used') or 0) for x in _zs.get('items', []) if x.get('state') == 'done' and (x.get('done_at') or '').startswith(_zm))
_zfmt = lambda v: f'{v:,.0f}' if float(v).is_integer() else f'{v:,.1f}'
ZTXT = (f' · ZCRE {_zfmt(_zused)} 크레딧 사용' + (f' · 잔액 {_zfmt(float(_zs["balance"]))}' if _zs.get('balance') is not None else '')) if _zs else ''
SPEND = f'<button type="button" class="spend">{_mon}월 사용 금액 {_won:,}원 <small>· {_n}건{f" (이전 {_est}건은 추정)" if _est else ""}{ZTXT} · 눌러서 날짜별 보기</small></button>' if _won or _allwon or _zs else ''
SPEND_DLG_H = SPEND_DLG if _won else ''
SPEND_JS_H = ('<script>' + SPEND_JS.replace('__SPENDD__', json.dumps(COST.by_day(R), ensure_ascii=False)).replace('__SEST__', str(_est)) + '</script>') if _won else ''
DATECAL_JS_H = '<script>' + DATECAL_JS.replace('__DAYCNT__', json.dumps(DAYCNT, ensure_ascii=False)) + '</script>'

page = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SOOO 복각 소재 검수</title><style>
:root{{--bg:#f4f2fa;--s:#fff;--fg:#1b1730;--mu:#625c78;--ln:#ddd8ea;--ac:#5c3abe;--acs:#ece6fb;--ok:#167a4a;--oks:#dff3e8;--wr:#a2541a;--wrs:#fbeadc}}
@media (prefers-color-scheme:dark){{:root{{--bg:#141220;--s:#1d1a2c;--fg:#ebe8f5;--mu:#a49dbd;--ln:#322d47;--ac:#b49cff;--acs:#2a2347;--ok:#5fd39a;--oks:#173226;--wr:#f0a066;--wrs:#3a2617}}}}
*{{box-sizing:border-box}}[hidden]{{display:none!important}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"Apple SD Gothic Neo",sans-serif}}
.w{{max-width:1100px;margin:0 auto;padding:28px max(16px,env(safe-area-inset-left)) 80px}}h1{{margin:0;font-size:28px}}
nav{{display:flex;gap:14px;margin:6px 0 12px;flex-wrap:wrap}}nav a{{color:var(--ac);font-weight:700;text-decoration:none}}.lede{{color:var(--mu);margin:0 0 16px}}
.tabs{{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 18px}}.tab{{border:1px solid var(--ln);background:var(--s);color:var(--fg);border-radius:999px;padding:7px 14px;font-weight:700;cursor:pointer}}
.tab[aria-pressed=true]{{background:var(--ac);color:var(--s);border-color:var(--ac)}}.tab small{{opacity:.7;margin-left:2px}}
.card{{background:var(--s);border:1px solid var(--ln);border-radius:14px;display:grid;grid-template-columns:minmax(0,320px) minmax(0,1fr);overflow:hidden;margin-bottom:16px}}
.card.fail{{grid-template-columns:1fr}}@media (max-width:720px){{.card{{grid-template-columns:1fr}}}}
.media{{background:#0d0b16;display:flex;flex-direction:column;align-items:stretch;justify-content:center}}.media img,.media video{{width:100%;display:block}}
.rthumb{{display:inline-flex;align-items:center;gap:8px;margin:6px 0 2px;padding:3px 10px 3px 3px;border:1px solid var(--ln,#ddd);border-radius:8px;background:var(--s,#f6f5fb);cursor:pointer;font:inherit;font-size:12.5px;font-weight:700;color:var(--ac)}}.rthumb:hover{{border-color:var(--ac)}}.rthumb img,.rthumb i{{width:34px;height:42px;object-fit:cover;border-radius:5px;background:#0d0b16;color:#fff;font-style:normal;display:flex;align-items:center;justify-content:center}}#refdlg{{border:0;border-radius:12px;padding:0;background:#0d0b16;max-width:min(92vw,300px)}}#refdlg::backdrop{{background:rgba(0,0,0,.6)}}#refdlg .rw{{display:flex;padding:8px 8px 4px;justify-content:center}}#refdlg figure{{margin:0;display:flex;flex-direction:column;gap:4px;color:#fff;font-size:12px;font-weight:800}}#refdlg video,#refdlg img{{max-height:min(420px,60vh);max-width:100%;border-radius:6px;background:#000}}#refdlg .rb{{display:flex;padding:0 8px 8px;justify-content:flex-end}}#refdlg .rb button{{border:0;border-radius:8px;padding:7px 12px;font:inherit;font-weight:700;font-size:13px;cursor:pointer}}.refm{{border-top:3px solid var(--ac);background:#0d0b16;display:flex;flex-direction:column}}.rl{{color:#fff;background:var(--ac);font-size:12px;font-weight:800;padding:3px 10px;align-self:flex-start;border-radius:0 0 8px 0}}.rsync{{border:0;background:#2a2347;color:#fff;font-weight:700;font-size:12.5px;padding:7px 10px;cursor:pointer}}.rsync:hover{{background:var(--ac)}}.rno{{color:#a49dbd;font-size:12px;padding:10px 12px}}
.body{{padding:16px 18px;display:flex;flex-direction:column;gap:10px;min-width:0}}.top{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}}
.no{{font-weight:800;background:var(--ac);color:var(--s);border-radius:6px;padding:1px 9px}}.ttl{{font-weight:800;font-size:18px}}
.st{{font-size:12px;font-weight:800;border-radius:5px;padding:1px 7px;background:var(--wrs);color:var(--wr)}}.st.live{{background:var(--oks);color:var(--ok)}}.st.pre{{background:#fde4e4;color:#c62828}}
.ptabs{{display:flex;gap:8px;margin:8px 0 6px}}.ptab{{border:2px solid var(--ac);background:var(--s);color:var(--ac);border-radius:10px;padding:8px 18px;font-weight:800;font-size:16px;cursor:pointer}}.ptab[aria-pressed=true]{{background:var(--ac);color:#fff}}.ptab small{{opacity:.75}}
.notab{{color:var(--mu);font-size:14px;padding:6px 0}}.pg .cx{{margin-left:auto;border:1px solid #c62828;color:#c62828;background:transparent;border-radius:999px;padding:5px 14px;font-weight:800;cursor:pointer}}
.ref{{font-size:13px;color:var(--mu);margin:0}}.ref a{{color:var(--ac);font-weight:700;text-decoration:none}}
.kv{{display:grid;grid-template-columns:72px minmax(0,1fr);gap:6px 12px;font-size:14px;margin:0}}.kv dt{{font-size:12px;color:var(--mu);padding-top:2px}}.kv dd{{margin:0;min-width:0;word-break:break-all}}
.kv a{{color:var(--ac);font-weight:700}}.copy{{white-space:pre-wrap;background:var(--acs);border-radius:8px;padding:10px 12px}}.mono{{font-family:ui-monospace,monospace;font-size:12.5px}}
.st.rev{{background:var(--acs);color:var(--ac)}}.st.ing{{background:#fff1d6;color:#9a5b00}}
.fb textarea{{width:100%;border:1px solid var(--ln);border-radius:8px;padding:10px;font:inherit;background:var(--bg);color:var(--fg);resize:vertical}}
.fbr{{display:flex;justify-content:flex-end;align-items:center;gap:10px;margin-top:6px}}.fbr button{{border:0;border-radius:999px;padding:8px 18px;font-weight:800;background:var(--ac);color:#fff;cursor:pointer}}
.fbr button:disabled{{opacity:.5}}.rerr{{margin-top:6px;padding:8px 10px;border-radius:8px;background:#fdecec;color:#b42318;font-size:13px;line-height:1.5}}.fbs{{font-size:13px;color:var(--mu)}}.ops{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;border-top:1px dashed var(--ln);padding-top:10px}}.ops button{{border:1px solid var(--ln);background:var(--s);color:var(--fg);border-radius:999px;padding:7px 16px;font-weight:800;cursor:pointer}}
.ops .setup{{background:var(--ac);color:#fff;border-color:var(--ac)}}.ops .setup.done{{background:var(--oks);color:var(--ok);border-color:var(--ok)}}.ops button:disabled{{opacity:.4;cursor:default}}
.ops .on.lit{{background:#1f9d55;color:#fff;border-color:#1f9d55}}.ops .off.lit{{background:#6b6f80;color:#fff;border-color:#6b6f80}}.ops-s{{font-size:13px;color:var(--mu)}}.lv{{color:#1f9d55;font-weight:800}}.rtr{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:10px}}.retry{{border:0;border-radius:999px;background:var(--ac);color:#fff;font-weight:800;padding:9px 18px;cursor:pointer;font-size:14px}}.retry:disabled{{opacity:.6}}.rts{{font-size:12.5px;color:var(--mu)}}.qd{{color:#9a5b00;font-weight:700}}.serr{{color:#c62828;font-size:12.5px;font-weight:700;flex-basis:100%}}.del{{order:9;margin-left:auto;border:1px solid var(--ln);background:transparent;color:var(--mu);border-radius:999px;padding:2px 10px;font-size:12px;cursor:pointer}}.del:hover{{border-color:#c62828;color:#c62828}}.pz{{color:#6b6f80;font-weight:700}}.amgr{{margin-left:auto;font-size:13px;color:var(--ac);font-weight:700}}
dialog{{border:0;border-radius:10px;padding:0;max-width:min(1080px,calc(100vw - 32px));width:100%;max-height:calc(100vh - 32px);background:#f0f2f5;color:#1c1e21;overflow:hidden}}
.mx{{display:flex;flex-direction:column;max-height:calc(100vh - 32px)}}.mx-h{{display:flex;align-items:center;gap:12px;padding:12px 18px;background:#fff;border-bottom:1px solid #dadde1}}.mx-crumb{{font-size:13px;color:#65676b;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.mx-x{{border:0;background:none;font-size:18px;cursor:pointer;color:#65676b}}.mx-b{{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:16px;padding:16px;overflow:auto}}@media (max-width:860px){{.mx-b{{grid-template-columns:1fr}}}}
.mx-l{{display:flex;flex-direction:column;gap:12px;min-width:0}}.mx-l section{{background:#fff;border-radius:8px;padding:14px 16px;display:flex;flex-direction:column;gap:8px;box-shadow:0 1px 2px rgba(0,0,0,.1)}}.mx-l h4{{margin:0;font-size:15px}}
.mx label{{font-size:13px;font-weight:600;display:flex;flex-direction:column;gap:4px;color:#1c1e21}}.mx small{{color:#65676b;font-size:12px;font-weight:400}}
.mx input,.mx select,.mx textarea{{font:inherit;font-size:14px;padding:8px 10px;border:1px solid #ccd0d5;border-radius:6px;background:#fff;color:#1c1e21}}.mx textarea{{resize:vertical}}
.idn{{display:grid;grid-template-columns:130px 1fr;gap:4px 10px;font-size:13.5px}}.idn span{{color:#65676b}}.med{{display:flex;gap:10px;align-items:center;font-weight:400}}.med img{{width:72px;border-radius:4px}}
.mx-r{{position:sticky;top:0;align-self:start}}.pvh{{font-size:13px;font-weight:700;color:#65676b;margin-bottom:6px}}.fbp{{background:#fff;border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,.15);overflow:hidden}}
.fbp-h{{display:flex;gap:8px;align-items:center;padding:10px 12px}}.fbp-h div{{display:flex;flex-direction:column;line-height:1.25}}.av{{width:36px;height:36px;border-radius:50%;background:#b9a6e8;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800}}
.fbp-t{{white-space:pre-wrap;font-size:13.5px;padding:0 12px 10px;max-height:190px;overflow:auto}}.fbp img{{width:100%;display:block}}.fbp-f{{display:flex;justify-content:space-between;align-items:center;gap:10px;background:#f0f2f5;padding:10px 12px}}
.fbp-f div{{display:flex;flex-direction:column;min-width:0;line-height:1.3}}.fbp-f b{{font-size:14px}}.ctab{{background:#e4e6eb;border-radius:6px;padding:7px 12px;font-weight:700;font-size:13px;white-space:nowrap}}
.mx-f{{display:flex;align-items:center;gap:8px;padding:12px 18px;background:#fff;border-top:1px solid #dadde1}}.mx-f .warn{{flex:1;font-size:12.5px;color:#a2541a}}
.mx-f button{{border:0;border-radius:6px;padding:9px 18px;font-weight:700;cursor:pointer}}.mx-f .ok{{background:#0866ff;color:#fff}}.mx-f .cancel{{background:#e4e6eb;color:#1c1e21}}dialog::backdrop{{background:rgba(0,0,0,.45)}}
.dl2{{padding:18px 20px;display:flex;flex-direction:column;gap:10px}}.dl2 h3{{margin:0}}.dl2 label{{font-size:12.5px;color:var(--mu);display:flex;flex-direction:column;gap:4px}}
.dl2 select,.dl2 input{{font:inherit;padding:8px 10px;border:1px solid var(--ln);border-radius:8px;background:var(--bg);color:var(--fg)}}.dl2 .pv{{background:var(--acs);border-radius:8px;padding:10px 12px;font-size:13px;word-break:break-all}}
.dl2 .row{{display:flex;justify-content:flex-end;gap:8px}}.dl2 .row button{{border:0;border-radius:999px;padding:9px 18px;font-weight:800;cursor:pointer}}.dl2 .ok{{background:var(--ac);color:#fff}}.dl2 .cancel{{background:var(--bg);color:var(--fg)}}.dl2 .warn{{font-size:12.5px;color:var(--wr)}}
.cb{{display:flex;gap:6px}}.cb select,.cb input{{flex:1;min-width:0}}.back{{border:1px solid #ccd0d5;background:#fff;color:#1c1e21;border-radius:8px;padding:0 10px;cursor:pointer}}

.utm{{font-size:12.5px;color:#1c1e21;font-weight:400;font-family:ui-monospace,monospace;background:#f0f2f5;border-radius:6px;padding:6px 8px;word-break:break-all;margin-top:-4px}}
.aia{{display:flex;gap:6px;margin-bottom:6px}}.aia button{{border:1px solid #ccd0d5;background:#fff;color:#1c1e21;border-radius:999px;padding:3px 10px;font-size:12px;cursor:pointer}}
#genL{{display:grid;grid-template-columns:1fr 1fr;gap:2px 10px}}#genL label{{flex-direction:row;align-items:center;gap:6px;font-weight:400}}#genL input{{width:auto}}
#aiL{{display:grid;grid-template-columns:1fr 1fr;gap:2px 10px}}@media (max-width:520px){{#aiL{{grid-template-columns:1fr}}}}#aiL label{{flex-direction:row;align-items:center;gap:6px;font-weight:400}}#aiL input{{width:auto}}

.pg{{display:flex;gap:12px;align-items:center;background:var(--s);border:2px dashed var(--ac);border-radius:14px;padding:10px 14px;margin-bottom:10px}}.pg img{{width:56px;height:70px;object-fit:cover;border-radius:6px;background:var(--acs)}}
.uprev{{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}}.uprev:empty{{display:none}}.uprev figure{{margin:0;width:84px;position:relative}}.uprev img,.uprev video{{width:84px;height:110px;object-fit:cover;border-radius:6px;display:block;background:#000}}.uprev b{{position:absolute;top:3px;left:3px;background:#000;color:#ffd54a;border-radius:4px;padding:0 5px;font-size:12px}}.uprev figcaption{{font-size:10.5px;color:var(--mu);overflow:hidden;white-space:nowrap}}.uprev .udoc{{display:flex;align-items:center;justify-content:center;width:84px;height:110px;border-radius:6px;background:var(--acs);color:var(--ac);font-size:12px;font-weight:800;text-align:center}}.fbdz{{display:flex;align-items:center;gap:12px;margin-top:8px;padding:14px 16px;border:2px dashed var(--ac);border-radius:12px;background:var(--acs);cursor:pointer;transition:background .15s}}.fbdz:hover,.fbdz.over{{background:color-mix(in srgb,var(--ac) 18%,var(--s))}}
.fbdz.has{{border-style:solid}}.fbdz input{{position:absolute;width:1px;height:1px;opacity:0}}.dzi{{font-size:28px;line-height:1}}.dzt{{display:flex;flex-direction:column;gap:2px;flex:1;min-width:0}}.dzt b{{font-size:15px;color:var(--ac)}}.dzs{{font-size:12.5px;color:var(--mu)}}.dzc{{font-weight:800;color:var(--ac);white-space:nowrap}}
.fbfl{{display:flex;flex-direction:column;gap:3px;font-size:12.5px;font-weight:700;margin-top:6px}}.fbfl small{{color:var(--mu);font-weight:400}}
.pg b{{font-size:16px}}.tnotes{{position:fixed;top:84px;right:16px;display:flex;flex-direction:column;gap:8px;z-index:50;max-width:min(380px,calc(100vw - 32px))}}.tnote{{background:#1f2433;color:#fff;border-radius:12px;padding:12px 16px;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.25);animation:tn .3s}}@keyframes tn{{from{{transform:translateY(-8px);opacity:0}}}}.tnote b{{color:#ffd54a}}.tnote b:first-child{{color:#fff}}.livebar{{background:#fff4d6;border:1px solid #f0c24a;color:#5a4300;border-radius:10px;padding:8px 14px;font-size:14px;margin:0 0 12px}}.livebar a{{color:#5c3abe;font-weight:800;margin-left:6px}}.pgb{{flex:1;min-width:0}}.pg .bar{{height:10px;background:var(--acs);border-radius:999px;overflow:hidden;margin:6px 0 2px}}.pg .bar i{{display:block;height:100%;background:var(--ac);border-radius:999px;transition:width .8s}}.pg.all{{border-style:solid;background:var(--acs)}}.pg .ps{{color:var(--mu);font-size:13px}}.pg .dot{{width:10px;height:10px;border-radius:50%;background:var(--ac);animation:bl 1s infinite alternate;flex:none}}@keyframes bl{{to{{opacity:.2}}}}@media (prefers-reduced-motion:reduce){{.pg .dot{{animation:none}}}}
.vers{{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:13px}}.vl{{color:var(--mu)}}.vb{{border:1px solid var(--ln);background:var(--s);color:var(--ac);border-radius:6px;padding:1px 9px;font-weight:800;cursor:pointer;font-size:12.5px}}.vb[aria-pressed=true]{{background:var(--ac);color:#fff;border-color:var(--ac)}}.vinfo{{color:var(--mu)}}.brd{{background:#ffe9c7;color:#8a4b00;border-radius:999px;padding:1px 8px;font-size:11.5px;font-weight:800;margin-right:4px}}.vrev{{font-size:12.5px;background:var(--s);border:1px solid var(--ln);border-radius:8px;padding:6px 10px;margin-top:6px}}.vrev summary{{cursor:pointer;font-weight:800;color:var(--ac)}}.vrevb p{{margin:6px 0 0}}.vrevb .pass{{color:#1a8a4a;font-weight:800}}.vrevb .fail{{color:#c0392b;font-weight:800}}.vrevb ul{{margin:2px 0 0 16px;padding:0}}.usev{{border:1px solid var(--ac);background:transparent;color:var(--ac);border-radius:999px;padding:2px 10px;font-weight:800;cursor:pointer;font-size:12.5px}}
{SPEND_CSS}{DATECAL_CSS}\n.delw{{order:9;margin-left:auto;display:inline-flex;flex-direction:column;align-items:center;gap:2px}}.delw .del{{order:0;margin-left:0}}.cst{{font-size:10px;color:var(--mu);white-space:nowrap}}
.revbadge{{background:#c62828;color:#fff;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:800;margin-left:8px;animation:revb 1.2s ease-in-out infinite}}
@keyframes revb{{50%{{opacity:.45}}}}
.card.revving{{box-shadow:0 0 0 2px #c62828 inset}}
.note{{color:var(--wr);background:var(--wrs);border-radius:6px;padding:6px 10px;margin:0;font-size:13px}}.empty{{color:var(--mu)}}.hd{{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}}.jump{{background:var(--ac);color:#fff;font-weight:800;border-radius:999px;padding:9px 18px;text-decoration:none}}
</style></head><body><div class="w"><div class="hd"><h1>SOOO 복각 소재 검수</h1><a class="jump" href="index.html">← 레퍼런스 고르러 가기</a>{SPEND}</div><nav><a href="index.html">광고 라이브러리 레퍼런스</a><a href="agency.html">대행 계정 고효율 소재</a><a href="review.html">복각 소재 검수</a></nav>
<p class="lede">레퍼런스 페이지에서 고른 소재를 SOOO 버전으로 자동 복각한 결과입니다. 날짜별로 모입니다. 광고는 아직 만들지 않았고, 확인 후 PAUSED로 세팅합니다.</p>
<div class="ptabs">{ptabs}</div><div class="tabs"><button type="button" class="calbtn">📅 날짜</button>{tabs}<span class="notab" hidden>아직 만든 소재가 없어요. 레퍼런스 페이지에서 골라 복각하기를 눌러주세요.</span></div>
<dialog id="dlg"><form method="dialog" class="mx">
<div class="mx-h"><b>광고 세팅</b><span class="mx-crumb" id="crumb"></span><button value="cancel" class="mx-x" aria-label="닫기">✕</button></div>
<div class="mx-b"><div class="mx-l">
<section><h4>광고 계정</h4><select id="accSel"></select><small id="accHint"></small></section>
<section><h4>담당자 <small style="color:#c62828">(필수)</small></h4><select id="wSel"><option value="">이름 선택</option><option>화영</option><option>다운</option><option>도현</option><option>근형</option><option>형태</option><option>다솔</option></select></section>
<section><h4>캠페인</h4><div class="cb"><select id="cSel"></select><input id="cNew" hidden placeholder="새 캠페인 이름"><button type="button" class="back" id="cBack" hidden>목록</button></div><small id="cHint" hidden>목표·입찰·예산 설정은 <b id="cSrc"></b> 그대로 복사</small></section>
<section><h4>광고 세트</h4><div class="cb"><select id="sSel"></select><input id="sNew" hidden placeholder="새 광고 세트 이름"><button type="button" class="back" id="sBack" hidden>목록</button></div><small id="sHint" hidden>타겟·노출 위치·최적화 설정은 <b id="sSrc"></b> 그대로 복사</small>
<label id="bL" hidden>일일 예산 (원)<input id="bud" type="number" step="10000"></label></section>
<section><h4>광고 이름</h4><input id="aName"><small>네이밍 규칙으로 자동 생성 · 고쳐도 돼요</small></section>
<section><h4>아이덴티티</h4><label>Facebook 페이지<select id="pSel"></select></label><label>Instagram 계정<select id="iSel"></select></label><small id="pHint"></small></section>
<section><h4>광고 설정</h4><div class="idn"><span>형식</span><b id="aFmt">단일 이미지</b><span>멀티 광고주 광고</span><b>사용 안 함</b></div></section>
<section><h4>광고 크리에이티브</h4>
<label>미디어<div class="med"><img id="aImg" alt="선택한 버전 이미지"><span>지금 보고 있는 버전 <b id="aVer"></b> · <span id="aRat"></span><br><small>다른 버전으로 올리려면 창을 닫고 카드에서 버전을 바꾼 뒤 다시 세팅하기</small></span></div></label>
<label>기본 문구<textarea id="aBody" rows="8"></textarea></label>
<label>제목<input id="aTitle"></label>
<label>설명 <small>(선택)</small><input id="aDesc" placeholder="비우면 설명 없이"></label>
<label>행동 유도<select id="aCta" disabled><option>지금 구매하기</option></select></label></section>
<section><h4>Advantage+ 크리에이티브</h4><small>메타 AI가 소재를 자동으로 바꿔 보여주는 기능 · 기본값은 베스트 광고(공장탑특가)와 같게</small><div class="aia"><button type="button" id="aiAll">기본값</button><button type="button" id="aiNone">전부 끄기</button></div><div id="aiL"></div></section>
<section><h4>어드밴티지+ 크리에이티브 생성 <small style="background:#efe7ff;color:#6b3fd4;border-radius:999px;padding:1px 8px">Meta AI</small></h4><div id="genL" class="genl"></div><small>"N개 미디어 · 사용해보기"(AI가 만든 이미지·영상 후보 고르기)는 메타가 API로 안 열어줘서, 세팅 후 카드의 <b>Advantage+ 미리보기·AI 후보 보기</b>를 누르면 메타 화면에서 바로 보고 고를 수 있어요.</small></section>
<section><h4>랜딩 페이지</h4><label>웹사이트 URL<input id="aLink"></label><label>URL 매개변수 (UTM)<div class="utm" id="utm"></div></label></section>
</div>
<div class="mx-r"><div class="pvh">광고 미리보기 · Facebook 피드</div><div class="fbp">
<div class="fbp-h"><span class="av">뷰</span><div><b>뷰티매거진</b><small>광고 · 🌐</small></div></div>
<div class="fbp-t" id="pBody"></div><img id="pImg" alt="미리보기 이미지"><video id="pVid" hidden autoplay muted loop playsinline controls style="width:100%;display:block"></video>
<div class="fbp-f"><div><small>SOOO.KR</small><b id="pTitle"></b><small id="pDesc"></small></div><span class="ctab">지금 구매하기</span></div></div></div></div>
<div class="mx-f"><span class="warn" id="warn"></span><button value="cancel" class="cancel">취소</button><button id="doSet" class="ok" value="ok">세팅하기</button></div></form></dialog><div class="tnotes" id="tnotes" aria-live="polite"></div><div id="prog" aria-live="polite"></div><div id="list">{"".join(cards) or '<p class="empty">아직 복각한 소재가 없습니다.</p>'}</div></div>
<script>const QA=(R,s)=>[...(R.matches&&R.matches(s)?[R]:[]),...R.querySelectorAll(s)];
const ck=c=>{{const d=c.querySelector('.del')||{{dataset:{{}}}};return c.dataset.p+'|'+c.dataset.d+'|'+(d.dataset.no||('f'+d.dataset.fjob+'_'+d.dataset.fref))}};
const SRC=new Map();document.querySelectorAll('#list > .card').forEach(c=>SRC.set(ck(c),c.outerHTML));   // 처음 받은 카드 원본(배포가 바뀌면 달라진 카드만 교체)
let LOCAL=[],WAITDEP=0,LASTSR=0;const DONEK=new Set();   // LOCAL = 이 탭에서 방금 보낸 요청(서버 목록에 뜨기 전에도 바로 표시), DONEK = 끝났지만 화면 반영 대기
function jt(j){{const m=/^([0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})T([0-9]{{2}})-([0-9]{{2}})-([0-9]{{2}})-([0-9]{{3}})Z$/.exec(j||'');return m?Date.parse(m[1]+'T'+m[2]+':'+m[3]+':'+m[4]+'.'+m[5]+'Z'):0}}
function mergeL(pend){{const have=new Set(pend.map(p=>p.job));LOCAL=LOCAL.filter(l=>Date.now()-l.at<(have.has(l.job)?20000:360000));return pend.concat(LOCAL.filter(l=>!have.has(l.job)))}}
function addLocal(o){{o.at=Date.now();LOCAL.push(o);kick()}}
let ts=[...document.querySelectorAll('.tab')],ps=[...document.querySelectorAll('.ptab')];let P='화영',DD='';
function sh(p,d){{P=p;const mine=ts.filter(t=>t.dataset.p===p);if(!mine.some(t=>t.dataset.d===d))d=(mine[0]||{{dataset:{{}}}}).dataset.d||'';DD=d;
 ps.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.p===p)));ts.forEach(t=>{{t.hidden=t.dataset.p!==p||(!!t.dataset.old&&t.dataset.d!==d);t.setAttribute('aria-pressed',String(t.dataset.p===p&&t.dataset.d===d))}});
 document.querySelector('.notab').hidden=!!mine.length;document.querySelectorAll('.card').forEach(c=>c.hidden=!(c.dataset.p===p&&c.dataset.d===d));history.replaceState(null,'','?p='+encodeURIComponent(p)+'&d='+d)}}
function bindTabs(){{ps.forEach(b=>b.onclick=()=>sh(b.dataset.p,DD));ts.forEach(t=>t.onclick=()=>sh(t.dataset.p,t.dataset.d))}}bindTabs();
{{const u=new URLSearchParams(location.search);let p0=u.get('p');try{{p0=p0||localStorage.getItem('bokgak-who')}}catch(e){{}}sh(['화영','다운','도현','근형','형태','다솔'].includes(p0)?p0:'화영',u.get('d')||'')}}
let RQ={{}};try{{RQ=JSON.parse(localStorage.getItem('revise-req')||'{{}}')}}catch(e){{}}
function save(){{try{{localStorage.setItem('revise-req',JSON.stringify(RQ))}}catch(e){{}}}}
const JUST=new URLSearchParams(location.search).get('just');let SEEN=new Set(),T0=Date.now();

// 팀원 제작 알림: 다른 사람이 복각을 시작하면 오른쪽 위 알림(내가 누른 건 제외), 첫 로딩 때 진행 중인 건 알림 없이 띠로만
let SEENJ=null;
function teamNotice(pend,mine){{const jobs=pend.filter(p=>p.type==='bokgak'&&p.items&&p.items.length);
 if(SEENJ===null){{SEENJ=new Set(jobs.map(p=>p.job))}}else jobs.forEach(p=>{{if(SEENJ.has(p.job))return;SEENJ.add(p.job);if(mine.has(p.job))return;
  const nm=(p.items[0].page||'레퍼런스').slice(0,30)+(p.items.length>1?' 외 '+(p.items.length-1)+'개':'');
  const t=document.createElement('div');t.className='tnote';t.innerHTML='<b>🔔 '+(p.by||'팀원')+'님</b>이 <b>'+nm.replace(/</g,'&lt;')+'</b> 소재 제작을 시작했어요';document.getElementById('tnotes').append(t);setTimeout(()=>t.remove(),9000)}});
 const lv=document.getElementById('livebar');if(!lv)return;
 lv.innerHTML=jobs.length?'<b>지금 제작 중</b> — '+jobs.map(p=>(p.by||'팀원')+': '+(p.items[0].page||'레퍼런스').slice(0,24).replace(/</g,'&lt;')+(p.items.length>1?' 외 '+(p.items.length-1)+'개':'')).join(' · ')+' <a href="review.html">진행 상황 보기 →</a>':'';lv.hidden=!jobs.length}}
let LAST=[[],null];
function mm(sec){{sec=Math.max(0,Math.round(sec));return sec<60?sec+'초':Math.floor(sec/60)+'분 '+(sec%60?sec%60+'초':'')}}
function prog(pend,st0,sts){{LAST=[pend,st0,sts];const el=document.getElementById('prog');const rows=[];let tot=0,totDone=0,totLeft=0;
 const skew=st0&&st0.now?Date.now()/1000-st0.now:0;   // 맥·브라우저 시계 차이
 document.querySelectorAll('.card.revving').forEach(c=>{{c.classList.remove('revving');const b=c.querySelector('.revbadge');if(b)b.remove()}});
 pend.filter(p=>(p.type==='bokgak'&&p.items)||(p.type==='addref'&&p.go)||p.type==='retry'||p.type==='revise').forEach(p=>{{const st=(sts&&sts[p.job])||(st0&&st0.job===p.job?st0:null);const curLeft=st&&st.state==='working'?Math.max(5,((st.exp)||100)-(Date.now()/1000-skew-(st.t0||0))):0;(p.items||[p.type==='revise'?{{id:p.date+'_'+p.no,page:'수정 · '+p.no+' '+((document.querySelector(`.fb[data-key="${{p.date}}_${{p.no}}"]`)||{{closest:()=>null}}).closest('.card')?.querySelector('.ttl')?.textContent||''),rev:1}}:{{id:'',page:p.type==='retry'?'실패한 소재 다시':(p.name||'직접 추가한 레퍼런스')+' (등록 → 복각)'}}]).forEach((it,i)=>{{const mine=st&&st.job===p.job&&st.state==='working';const cur=mine&&(st.all||st.cur===it.id||p.type!=='bokgak');
  const exp=(mine&&st.exp)||(it.rev?70:100);let pct=0,txt,left;
  if(cur){{const el_=Date.now()/1000-skew-(st.t0||0);pct=Math.min(97,Math.max(st.pct||0,Math.round(el_/exp*100)));left=Math.max(5,exp-el_);txt=(st.step||'만드는 중')}}
  else if(mine&&i<st.i){{pct=100;left=0;txt='완료 ✓ (페이지 올리는 중)'}}
  else{{const ahead=mine?(i-st.i-1):i;const wait=(mine?curLeft:0)+ahead*exp;left=wait+exp;txt=mine?'순서 기다리는 중 · 약 '+mm(wait)+' 뒤 시작':'요청 접수됨 · 1분 안에 Claude 가 시작'}}
  tot++;totDone+=pct;totLeft+=left;
  if(it.rev){{const fbx=document.querySelector(`.fb[data-key="${{it.id}}"] .fbs`);if(fbx)fbx.innerHTML=`<b>수정 중 · ${{pct}}%</b> · ${{txt}}${{left?' · 약 '+mm(left)+' 남음':''}}`;
   const fw=document.querySelector(`.fb[data-key="${{it.id}}"]`),cd=fw&&fw.closest('.card');
   if(cd){{cd.classList.add('revving');let bg=cd.querySelector('.revbadge');
    if(!bg){{const no=cd.querySelector('.no');if(no)no.insertAdjacentHTML('afterend','<span class="revbadge">수정 중…</span>');bg=cd.querySelector('.revbadge')}}
    if(bg)bg.textContent=`수정 중… ${{pct}}%`}}}}
  rows.push(`<div class="pg"><span class="dot"></span><img src="m/L${{it.id}}.jpg" alt="" onerror="this.style.visibility='hidden'"><div class="pgb"><b>${{p.by?p.by+' · ':''}}${{(it.page||'레퍼런스').replace(/</g,'&lt;')}} ${{it.rev?(pct>=100?' 수정 완료':' 수정 중…'):(pct>=100?' 소재 복각 완료':' 소재 복각중…')}}</b><div class="ps">${{txt}}</div>
   <div class="bar"><i style="width:${{pct}}%"></i></div><div class="ps"><b>${{pct}}% 완료</b> · 약 ${{100-pct}}% 남음${{left?' · 약 '+mm(left)+' 남음':''}}</div></div>${{i===0?`<button type="button" class="cx" data-job="${{p.job}}">취소</button>`:''}}</div>`)}});}});
 if(tot>1){{const ap=Math.round(totDone/tot);rows.unshift(`<div class="pg all"><div class="pgb"><b>전체 ${{tot}}개 중 ${{Math.floor(totDone/100)}}개 완료 · ${{ap}}%</b><div class="bar"><i style="width:${{ap}}%"></i></div><div class="ps">약 ${{100-ap}}% 남음 · 다 끝나기까지 약 ${{mm(totLeft)}}</div></div></div>`)}}
 if(!rows.length&&JUST&&!SEEN.has(JUST)&&Date.now()-T0<90000)rows.push('<div class="pg"><span class="dot"></span><div><b>복각 요청 접수됨…</b><div class="ps">잠시 후 소재별 진행 상황이 여기에 떠요</div></div></div>');
 el.onclick=async e=>{{const b=e.target.closest('.cx');if(!b)return;if(!confirm('이 복각 요청을 취소할까요?\\n이미 만들고 있는 소재는 그것까지만 끝나고 나머지는 멈춰요.'))return;b.disabled=true;b.textContent='취소 중…';
  try{{const r=await (await fetch('api/bokgak',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{type:'cancel',job:b.dataset.job}})}})).json();if(!r.ok)throw new Error(r.msg);b.textContent='취소됨';LOCAL=LOCAL.filter(l=>l.job!==b.dataset.job);kick()}}catch(err){{b.textContent='실패';b.disabled=false}}}};
 if(WAITDEP&&Date.now()-WAITDEP<300000)rows.unshift('<div class="pg"><span class="dot"></span><div><b>✓ 작업 끝 · 새 결과를 화면에 올리는 중…</b><div class="ps">보통 1~2분 · 새로고침 안 해도 끝나면 자동으로 바뀌어요</div></div></div>');
 el.innerHTML=rows.length?'<h3 style="margin:0 0 8px">'+(tot?'진행 중 '+tot+'개':'반영 중')+'</h3>'+rows.join(''):''}}
async function poll(){{let pend=[],st=null,sts=null;try{{const d=await (await fetch('api/bokgak')).json();pend=d.pending||[];st=d.status;sts=d.statuses||null}}catch(e){{return}}
 pend=mergeL(pend);ACTIVE=pend.length>0||!!(st&&st.state==='working')||!!(sts&&Object.keys(sts).length);
 PEND=pend;teamNotice(pend,new Set(JUST?[JUST]:[]));
 {{const q=pend.filter(p=>p.type==='setup').sort((a,b)=>a.job<b.job?-1:1);   // 세팅 대기열: 카드마다 순서 표시, 같은 소재 두 번 못 누르게
  document.querySelectorAll('.ops').forEach(o=>{{const k=q.findIndex(p=>p.date===o.dataset.date&&p.no===o.dataset.no);const b=o.querySelector('.setup');if(o.dataset.ad)return;
   if(k>=0){{b.disabled=true;b.textContent='세팅 대기 중';o.querySelector('.ops-s').innerHTML=`<span class="qd">⏳ ${{k+1}}/${{q.length}}번째 · ${{(st&&st.state==='working'&&st.job===q[k].job)?'지금 메타에 만드는 중':'순서대로 자동 진행(메타 호출 한도면 3분마다 재시도)'}}</span>`}}
   else if(b.textContent==='세팅 대기 중'&&!RQ[o.dataset.date+'_'+o.dataset.no]&&!DONEK.has(o.dataset.date+'_'+o.dataset.no)){{b.disabled=false;b.textContent='세팅하기';o.querySelector('.ops-s').textContent=''}}}})}}const nowB=new Set(pend.filter(p=>p.type==='bokgak'||p.type==='retry'||(p.type==='addref'&&p.go)).map(p=>p.job));const gone=[...SEEN].some(j=>!nowB.has(j));SEEN.forEach(j=>{{if(!nowB.has(j))SEEN.delete(j)}});nowB.forEach(j=>SEEN.add(j));if(gone)T0=0;prog(pend,st,sts);
 if(gone&&Date.now()-LASTSR>90000)WAITDEP=Date.now();   // 끝난 작업 → 배포(ver.json) 바뀌면 softRefresh 가 조용히 교체(예전엔 location.reload)
 // 다음 확인 시각은 tick() 이 정함(작업 중 10초 · 없으면 60초 · 탭 숨김이면 멈춤)
 const live=new Set(pend.map(p=>p.job));let doneAny=false;
 Object.entries(RQ).forEach(([k,j])=>{{if(!live.has(j)&&Date.now()-jt(j)>30000){{delete RQ[k];if(Date.now()-LASTSR>90000)DONEK.add(k);doneAny=true}}}});save();   // 30초 = 다른 서버 5초 캐시에 아직 안 보이는 경우
 document.querySelectorAll('.fb').forEach(f=>{{const s=f.querySelector('.fbs'),b=f.querySelector('.go');if(RQ[f.dataset.key]){{s.textContent='수정중… (몇 분 걸려요)';b.disabled=true}}else if(!b.dataset.busy){{b.disabled=false;if(s.textContent.startsWith('수정중'))s.textContent=''}}if(DONEK.has(f.dataset.key)&&!RQ[f.dataset.key]&&!b.dataset.busy)s.textContent='✓ 처리 끝 · 새 결과를 화면에 올리는 중…'}});
 DONEK.forEach(k=>{{const o=document.querySelector(`.ops[data-date="${{k.slice(0,10)}}"][data-no="${{k.slice(11)}}"]`);if(!o)return;const b=o.querySelector('.setup'),x=o.querySelector('.ops-s');if(!o.dataset.ad&&b.disabled)b.textContent='✓ 세팅 끝 · 반영 중…';if(/중…|대기/.test(x.textContent))x.textContent='✓ 처리 끝 · 화면에 반영 중…'}});
 if(doneAny&&Date.now()-LASTSR>90000)WAITDEP=Date.now()}}   // 90초 안에 이미 새 판을 받았으면(작업기가 배포 뒤 완료 표시) 대기 표시 안 함
const bV=R=>QA(R,'.card[data-vs]').forEach(c=>{{const vs=JSON.parse(c.dataset.vs);c.dataset.view=c.dataset.cur;
 function show(v){{const x=vs.find(y=>y.v==v);if(!x)return;c.dataset.view=v;c.querySelector('.mi').src=x.img;const mv=c.querySelector('.mv');if(mv){{mv.hidden=!x.mp4;c.querySelector('.mi').hidden=!!x.mp4;if(x.mp4&&mv.getAttribute('src')!==x.mp4){{mv.src=x.mp4;mv.play().catch(()=>{{}})}}}}c.querySelector('.dl').href=x.img;c.querySelector('.vname').textContent=x.name;c.querySelector('.vbody').textContent=x.body;
  c.querySelectorAll('.vb').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.v==v)));
  c.querySelector('.vinfo').textContent=(x.at?x.at+' · ':'')+(x.from?'v'+x.from+' 기준 수정: '+x.fb+(x.note?' → '+x.note:''):x.note);
  {{const d=c.querySelector('.vrev');if(d){{const rv=x.review||[];d.hidden=!rv.length;if(rv.length){{const E=t=>String(t||'').replace(/[&<>]/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}})[m]);d.querySelector('summary').textContent='🔍 리뷰어 검수 '+rv.length+'바퀴 — '+(rv[rv.length-1].verdict==='PASS'?'통과':'남은 지적 있음');d.querySelector('.vrevb').innerHTML=rv.map(r=>'<p><b>'+E(r.round)+'바퀴</b> <span class="'+(r.verdict==='PASS'?'pass':'fail')+'">'+E(r.verdict)+'</span></p>'+((r.issues||[]).length?'<div>지적:</div><ul>'+r.issues.map(i=>'<li>'+E(i)+'</li>').join('')+'</ul>':'')+((r.fixed||[]).length?'<div>고친 것:</div><ul>'+r.fixed.map(i=>'<li>'+E(i)+'</li>').join('')+'</ul>':'')).join('')}}}}}}
  c.querySelector('.usev').hidden=(v==c.dataset.cur)}}
 c.querySelectorAll('.vb').forEach(b=>b.onclick=()=>show(b.dataset.v));show(c.dataset.cur);
 c.querySelector('.usev').onclick=async e=>{{const b=e.target;b.disabled=true;b.textContent='바꾸는 중…';const g=c.querySelector('.go');
  try{{const r=await (await fetch('api/bokgak',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{type:'select',date:g.dataset.date,no:g.dataset.no,version:+c.dataset.view}})}})).json();if(!r.ok)throw new Error(r.msg);
   RQ[c.querySelector('.fb').dataset.key]=r.job;save();addLocal({{job:r.job,type:'select',date:g.dataset.date,no:g.dataset.no}});b.textContent='v'+c.dataset.view+'로 바꾸는 중… (몇 분)'}}catch(err){{b.textContent='실패: '+err.message;b.disabled=false}}}}}});
async function upFile(f,msg){{   // 2.5MB 조각으로 올리기
 const up=(self.crypto&&crypto.randomUUID?crypto.randomUUID().replace(/-/g,''):Date.now().toString(36)+Math.random().toString(36).slice(2)).slice(0,24),CH=2.5*1024*1024,n=Math.max(1,Math.ceil(f.size/CH));
 for(let i=0;i<n;i++){{msg(Math.round(i/n*100));const data=await new Promise((ok,no)=>{{const fr=new FileReader();fr.onload=()=>ok(fr.result.split(',')[1]);fr.onerror=no;fr.readAsDataURL(f.slice(i*CH,(i+1)*CH))}});
  const r=await (await fetch('api/bokgak',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{type:'chunk',up,i,data}})}})).json();if(!r.ok)throw new Error(r.msg)}}
 return {{up,n,ext:(f.name.split('.').pop()||'').toLowerCase(),kind:f.type.startsWith('video')?'video':f.type.startsWith('image')?'image':(f.type.startsWith('audio')||/\.(mp3|wav|m4a|aac)$/i.test(f.name))?'audio':'doc',name:f.name.slice(0,60)}}}}
const bF=R=>QA(R,'.fbf').forEach(inp=>inp.onchange=()=>{{const pv=inp.closest('.fb').querySelector('.fbp'),dz=inp.closest('.fbdz');dz.classList.toggle('has',inp.files.length>0);dz.querySelector('.dzc').textContent=inp.files.length?Math.min(10,inp.files.length)+'개 붙임':'';pv.innerHTML=[...inp.files].slice(0,10).map((f,i)=>{{const u=URL.createObjectURL(f);
 return `<figure><b>F${{i+1}}</b>${{f.type.startsWith('video')?`<video src="${{u}}" muted autoplay loop playsinline></video>`:f.type.startsWith('image')?`<img src="${{u}}" alt="">`:(f.type.startsWith('audio')||/\.(mp3|wav|m4a|aac)$/i.test(f.name))?`<span class="udoc">🎵 음성<br>나레이션·음악</span>`:`<span class="udoc">📄 ${{(f.name.split('.').pop()||'').toUpperCase()}}<br>기획안·문서</span>`}}<figcaption>${{f.name.replace(/</g,'&lt;').slice(0,18)}}</figcaption></figure>`}}).join('')}});
const bZ=R=>QA(R,'.fbdz').forEach(dz=>{{const inp=dz.querySelector('.fbf');
 ['dragenter','dragover'].forEach(ev=>dz.addEventListener(ev,e=>{{e.preventDefault();dz.classList.add('over')}}));['dragleave','drop'].forEach(ev=>dz.addEventListener(ev,e=>{{e.preventDefault();dz.classList.remove('over')}}));
 dz.addEventListener('drop',e=>{{if(e.dataTransfer.files.length){{inp.files=e.dataTransfer.files;inp.dispatchEvent(new Event('change'))}}}})}});
const bG=R=>QA(R,'.fb .go').forEach(b=>b.onclick=async()=>{{const f=b.closest('.fb'),t=f.querySelector('textarea'),s=f.querySelector('.fbs');const fb=t.value.trim();if(!fb){{s.textContent='피드백을 적어주세요';return}}
 b.disabled=true;b.dataset.busy=1;s.textContent='요청 중…';const fi=f.querySelector('.fbf'),assets=[];
 try{{for(const [k,af] of [...fi.files].slice(0,10).entries()){{if(af.size>150*1024*1024)throw new Error('F'+(k+1)+' 파일이 150MB 넘어요');assets.push(await upFile(af,p=>s.textContent=`파일 올리는 중… ${{k+1}}/${{Math.min(10,fi.files.length)}} (${{p}}%)`))}}}}
 catch(e){{s.textContent='파일 올리기 실패: '+e.message;b.disabled=false;delete b.dataset.busy;return}}
 try{{const r=await (await fetch('api/bokgak',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{type:'revise',date:b.dataset.date,no:b.dataset.no,feedback:fb,assets,base:+b.closest('.card').dataset.view}})}})).json();
  if(!r.ok)throw new Error(r.msg);RQ[f.dataset.key]=r.job;save();addLocal({{job:r.job,type:'revise',date:b.dataset.date,no:b.dataset.no}});t.value='';fi.value='';f.querySelector('.fbp').innerHTML='';f.querySelector('.fbdz').classList.remove('has');f.querySelector('.dzc').textContent='';s.textContent='수정중… (몇 분 걸려요)'}}catch(e){{s.textContent='요청 실패: '+e.message;b.disabled=false}}delete b.dataset.busy}});
let BUILT={int(_t.time())},ACCT={json.dumps(ACCT, ensure_ascii=False)},PREF={json.dumps(PREF)},IDENT={json.dumps(IDENT, ensure_ascii=False)};
let ACCTS={json.dumps(ACCTS, ensure_ascii=False)},IDENTS={json.dumps(IDENTS, ensure_ascii=False)},BR_SET={json.dumps(BR_SET, ensure_ascii=False)},curAcc='SOOO';
const dlg=document.getElementById('dlg'),cSel=document.getElementById('cSel'),sSel=document.getElementById('sSel');let OP=null;
const STL={{ACTIVE:'켜짐',PAUSED:'꺼짐',CAMPAIGN_PAUSED:'캠페인 꺼짐',ADSET_PAUSED:'세트 꺼짐',IN_PROCESS:'검수 중',WITH_ISSUES:'문제 있음'}};
const AI=[['text_optimizations','텍스트 개선 (본문·제목 바꿔 노출)',1],['image_templates','이미지 템플릿 (테두리·문구 오버레이)',1],['image_animation','이미지 애니메이션',1],['enhance_cta','CTA 개선',1],
 ['cv_transformation','시각 효과',1],['inline_comment','관련 댓글 표시',1],['ads_with_benefits','혜택 표시',1],['image_background_gen','배경 생성',0],['image_uncrop','이미지 확장',0],['image_touchups','이미지 보정',0],['image_brightness_and_contrast','밝기·대비 조정',0],['add_text_overlay','텍스트 추가',0]];
const GEN=[['advantage_plus_creative','어드밴티지+ 크리에이티브 생성 (큰 스위치)',1],['text_generation','텍스트 생성 (AI가 문구 후보)',1],['audio','음악 추가',1],['video_auto_crop','영상 자동 자르기',1],['video_uncrop','영상 화면 확장',1]];
document.getElementById('aiL').innerHTML=AI.map(([k,t])=>`<label><input type="checkbox" data-k="${{k}}">${{t}}</label>`).join('');
document.getElementById('genL').innerHTML=GEN.map(([k,t])=>`<label><input type="checkbox" data-k="${{k}}">${{t}}</label>`).join('');
const aiSet=f=>{{document.querySelectorAll('#aiL input').forEach(i=>i.checked=f(AI.find(a=>a[0]===i.dataset.k)));document.querySelectorAll('#genL input').forEach(i=>i.checked=f(GEN.find(a=>a[0]===i.dataset.k)))}};
document.getElementById('aiAll').onclick=()=>aiSet(a=>!!a[2]);document.getElementById('aiNone').onclick=()=>aiSet(()=>false);
const $=id=>document.getElementById(id);let DIRTY={{}};['aName','aLink'].forEach(id=>$(id).oninput=()=>{{DIRTY[id]=1;utm()}});
function utm(){{try{{const u=new URL($('aLink').value);$('utm').textContent=[...u.searchParams].filter(([k])=>k.startsWith('utm_')).map(([k,v])=>k+'='+v).join(' · ')||'UTM 없음'}}catch(e){{$('utm').textContent='링크 형식 확인 필요'}}}}
function combo(sel,inp,back,hint,isNew){{sel.hidden=isNew;inp.hidden=!isNew;back.hidden=!isNew;hint.hidden=!isNew;if(isNew)setTimeout(()=>inp.focus(),0)}}
$('cBack').onclick=()=>{{cSel.value=(ACCT[0]||{{}}).id;fillS()}};$('sBack').onclick=()=>{{const o=sSel.options[0];if(o&&o.value!=='__new'){{sSel.value=o.value;fillN()}}}};
function curC(){{return ACCT.find(c=>c.id===cSel.value)}}
function fillC(){{cSel.innerHTML='<option value="__new">＋ 새 캠페인 만들기</option>'+ACCT.map(c=>`<option value="${{c.id}}">${{c.name}} (${{STL[c.st]||c.st}})</option>`).join('');
 cSel.value=(PREF.campaign_id&&ACCT.some(c=>c.id===PREF.campaign_id))?PREF.campaign_id:(ACCT[0]||{{}}).id||'__new'}}
function fillS(){{const nc=cSel.value==='__new';combo(cSel,$('cNew'),$('cBack'),$('cHint'),nc);$('cSrc').textContent=(ACCT.find(c=>c.id===PREF.campaign_id)||ACCT[0]||{{}}).name||'';const base=nc?null:curC(),sets=base?base.sets:[];
 sSel.innerHTML='<option value="__new">＋ 새 세트 만들기</option>'+sets.map(x=>`<option value="${{x.id}}">${{x.name}} (${{STL[x.st]||x.st}}${{x.budget?' · 일 '+x.budget.toLocaleString()+'원':''}} · 광고 ${{x.n}}개)</option>`).join('');
 sSel.value=nc?'__new':((PREF.adset_id&&sets.some(x=>x.id===PREF.adset_id))?PREF.adset_id:(sets[0]||{{}}).id||'__new');$('sBack').disabled=!sets.length;fillN()}}
let PEND=[];
function sentL(){{try{{return JSON.parse(localStorage.getItem('setup-sent')||'[]')}}catch(e){{return[]}}}}
function queued(key){{const ids=new Set(PEND.filter(p=>p.type==='setup'&&p.adset===key).map(p=>p.job));   // 서버에 대기 중(팀원 것 포함)
 sentL().filter(x=>x.adset===key&&x.at>BUILT-30).forEach(x=>ids.add(x.job));return ids.size}}   // 이 페이지가 만들어진 뒤 내가 보낸 것
function srcSet(){{const b=cSel.value==='__new'?ACCT[0]:curC();const all=b?b.sets:[];return all.find(x=>x.id===PREF.adset_id)||all[0]||(ACCT[0]&&ACCT[0].sets[0])}}
function fillN(){{const ns=sSel.value==='__new',nc=cSel.value==='__new',src=srcSet(),c=nc?null:curC();combo(sSel,$('sNew'),$('sBack'),$('sHint'),ns);$('sSrc').textContent=src?src.name:'';
 $('bL').hidden=!ns||(c&&c.cbo);if(ns&&src&&!$('bud').value)$('bud').value=src.budget||100000;
 const set=ns?null:c.sets.find(x=>x.id===sSel.value);const qk=ns?'new:'+$('sNew').value.trim():sSel.value;const nn=String((set?set.n:0)+queued(qk)+1).padStart(3,'0');const d=new Date(Date.now()+9*3600e3),y=d.toISOString().slice(2,10).replace(/-/g,''),ymd=d.toISOString().slice(0,10).replace(/-/g,'');
 const KT=OP.dataset.kind,vid=KT!=='image'&&!!OP.closest('.card').querySelector('.mv:not([hidden])'),kt=vid?KT:'image';$('aFmt').textContent=vid?'단일 동영상 ('+(KT==='GIF'?'GIF를 mp4로':'mp4')+')':'단일 이미지';
 const _nf=curAcc!=='SOOO'&&(BR_SET[curAcc]||{{}}).name_fmt,_pp=({{'다운':'박다운','화영':'김화영','도현':'박도현','근형':'박근형','형태':'유형태','다솔':'다솔'}})[$('wSel').value]||'담당자';
 if(!DIRTY.aName&&_nf)$('aName').value=_nf.replace('{{yymmdd}}',y).replace('{{yyyymmdd}}',ymd).replace('{{nn}}',nn).replace('{{soguo}}',OP.dataset.soguo).replace('{{kt}}',kt).replace('{{kt_ko}}',({{image:'이미지',video:'영상',GIF:'영상'}})[kt]||kt).replace('{{person}}',_pp);
 else if(!DIRTY.aName)$('aName').value=`${{y}}_${{nn}} / ${{OP.dataset.soguo}} / ${{kt}} / ${{({{'다운':'박다운','화영':'김화영','도현':'박도현','근형':'박근형','형태':'유형태','다솔':'다솔'}})[$('wSel').value]||'담당자'}} / ${{(IDENT.find(x=>x.id===pSel.value)||{{name:'뷰티매거진'}}).name}}`;
 const _lp=(BR_SET[curAcc]||{{}}).link_prefix;$('aLink').placeholder=_lp?(BR_SET[curAcc].link_hint||_lp):'';
 if(_lp){{if(!DIRTY.aLink)$('aLink').value=''}}else if(!DIRTY.aLink)$('aLink').value=(OP.dataset.link||(curAcc!=='SOOO'?(BR_SET[curAcc]||{{}}).default_landing:'')||'https://sooo.kr/product/detail.html?product_no=108&cate_no=1&display_group=2&utm_source=meta&utm_medium=display&utm_campaign=스칼프처샴푸&utm_content=x').replace(/utm_content=[^&]*/,`utm_content=${{ymd}}_${{nn}}_${{kt}}`);utm();
 $('warn').textContent=(ns||nc)?'새로 만드는 캠페인·세트는 꺼진 상태로 만들어지고, 이 광고 ON을 누를 때 같이 켜집니다.':'광고는 꺼진 상태(OFF)로 만들어집니다. 이름·링크를 안 고치면 번호는 세팅하는 순간 세트 안 순번으로 확정됩니다.';if($('pBody'))pv()}}
cSel.onchange=fillS;sSel.onchange=fillN;
function pv(){{$('pBody').textContent=$('aBody').value;$('pTitle').textContent=$('aTitle').value;$('pDesc').textContent=$('aDesc').value;
 const cn=cSel.value==='__new'?($('cNew').value||'새 캠페인'):(curC()||{{}}).name,sn=sSel.value==='__new'?($('sNew').value||'새 광고 세트'):((curC()||{{sets:[]}}).sets.find(x=>x.id===sSel.value)||{{}}).name;$('crumb').textContent=cn+'  ›  '+sn+'  ›  '+$('aName').value}}
['aBody','aTitle','aDesc','cNew','sNew'].forEach(id=>$(id).addEventListener('input',pv));$('sNew').addEventListener('input',()=>{{if(!DIRTY.aName)fillN()}});$('aName').addEventListener('input',pv);
const pSel=document.getElementById('pSel'),iSel=document.getElementById('iSel');
pSel.innerHTML=IDENT.map(p=>`<option value="${{p.id}}">${{p.name}}${{p.linked?'':' (광고계정 미연결 · 실패할 수 있음)'}}</option>`).join('');
function fillI(){{const p=IDENT.find(x=>x.id===pSel.value)||{{}};iSel.innerHTML=(p.ig?`<option value="${{p.ig}}">@${{p.igname}}</option>`:'')+'<option value="">사용 안 함 (Facebook 페이지로 인스타에 노출)</option>';
 $('pHint').textContent=p.ig?'':'이 페이지에는 연결된 인스타 계정이 없어요';document.querySelectorAll('.fbp-h b').forEach(b=>b.textContent=p.name||'');document.querySelector('.fbp-h .av').textContent=(p.name||'?')[0];
 if(!DIRTY.aName&&OP)$('aName').value=$('aName').value.replace(/ \/ [^/]+$/,' / '+p.name)}}
pSel.onchange=fillI;
const accSel=$('accSel');accSel.innerHTML=Object.keys(BR_SET).map(k=>`<option value="${{k}}">${{BR_SET[k].label}} 계정${{BR_SET[k].setup?'':' (연결 전 · 세팅 불가)'}}</option>`).join('');
function useAcc(k){{curAcc=k;ACCT=k==='SOOO'?ACCTS.SOOO:(ACCTS[k]||[]);IDENT=k==='SOOO'?IDENTS.SOOO:(IDENTS[k]||[]);pSel.innerHTML=IDENT.map(p=>`<option value="${{p.id}}">${{p.name}}${{p.linked?'':' (광고계정 미연결 · 실패할 수 있음)'}}</option>`).join('');
 const ok=!!(BR_SET[k]||{{}}).setup&&(k==='SOOO'||ACCT.length>0);$('doSet').disabled=!ok;$('accHint').textContent=ok?'':'이 계정은 아직 메타 연결 전이라 세팅할 수 없어요(복각·다운로드는 돼요)';
 if(IDENT.length)pSel.value=PREF.page_id&&IDENT.some(p=>p.id===PREF.page_id)?PREF.page_id:IDENT[0].id;fillC();fillS();fillI()}}   // 2026-11-10 브랜드별 계정
accSel.onchange=()=>{{DIRTY.aName=0;DIRTY.aLink=0;useAcc(accSel.value)}};
$('wSel').onchange=()=>{{if(!DIRTY.aName)fillN()}};
function openDlg(o){{OP=o;DIRTY={{}};const c=o.closest('.card');$('bud').value='';$('cNew').value='';$('sNew').value='';
 $('aTitle').value=o.dataset.title;$('aDesc').value='';$('aBody').value=c.querySelector('.vbody').textContent;$('aVer').textContent='v'+c.dataset.view;
 const im=c.querySelector('.mi').src;$('aImg').onload=e=>{{const r=e.target.naturalWidth/e.target.naturalHeight;$('aRat').textContent=Math.abs(r-.5625)<.03?'9:16':Math.abs(r-.8)<.03?'4:5':Math.abs(r-1)<.03?'1:1':e.target.naturalWidth+'×'+e.target.naturalHeight}};$('aImg').src=im;$('pImg').src=im;const mv=c.querySelector('.mv');$('pImg').hidden=!!(mv&&!mv.hidden);$('pVid').hidden=!(mv&&!mv.hidden);if(mv)$('pVid').src=mv.src;$('wSel').value=o.dataset.by||'';aiSet(a=>!!a[2]);accSel.value=(c.dataset.brand&&BR_SET[c.dataset.brand])?c.dataset.brand:'SOOO';useAcc(accSel.value);if(curAcc==='SOOO'&&PREF.ig_id!==undefined&&[...iSel.options].some(o=>o.value===PREF.ig_id))iSel.value=PREF.ig_id;pv();dlg.showModal()}}
const bO=R=>QA(R,'.ops').forEach(o=>{{const st=o.dataset.st;o.querySelector('.on').classList.toggle('lit',st==='ACTIVE');o.querySelector('.off').classList.toggle('lit',!!o.dataset.ad&&st!=='ACTIVE');
 if(o.dataset.ad)o.querySelector('.ops-s').innerHTML=st==='ACTIVE'?'<span class="lv">● 집행중 · LIVE</span>':'<span class="pz">중단 · OFF</span>';
 if(o.dataset.ad)o.querySelector('.setup').classList.add('done');
 o.querySelector('.setup').onclick=()=>{{if(o.dataset.ad)return;openDlg(o)}};
 const tog=async on=>{{const s=o.querySelector('.ops-s');s.textContent=on?'켜는 중… (몇 분)':'끄는 중… (몇 분)';
  try{{const r=await (await fetch('api/bokgak',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{type:'status',date:o.dataset.date,no:o.dataset.no,on}})}})).json();if(!r.ok)throw new Error(r.msg);RQ[o.dataset.date+'_'+o.dataset.no]=r.job;save();addLocal({{job:r.job,type:'status',date:o.dataset.date,no:o.dataset.no}})}}catch(e){{s.textContent='실패: '+e.message}}}};
 o.querySelector('.on').onclick=()=>tog(true);o.querySelector('.off').onclick=()=>tog(false)}});
document.getElementById('doSet').onclick=async e=>{{e.preventDefault();const b={{type:'setup',account:curAcc,date:OP.dataset.date,no:OP.dataset.no,by:$('wSel').value,version:+OP.closest('.card').dataset.view,page_id:pSel.value,ig_id:iSel.value,title:$('aTitle').value.trim(),desc:$('aDesc').value.trim(),body:$('aBody').value.trim(),features:{{}}}};
 if(DIRTY.aName)b.ad_name=$('aName').value.trim();{{const lp=(BR_SET[curAcc]||{{}}).link_prefix;if(lp){{b.link=$('aLink').value.trim();if(!b.link.startsWith(lp))return alert(BR_SET[curAcc].link_hint||(lp+' 링크를 넣어주세요'))}}}}if(DIRTY.aLink){{b.link=$('aLink').value.trim();if(curAcc==='SOOO'?!/^https:\/\/sooo\.kr\//.test(b.link):!/^https:\/\//.test(b.link))return alert(curAcc==='SOOO'?'링크는 https://sooo.kr/ 로 시작해야 해요':'링크는 https:// 로 시작해야 해요')}}
 if(!b.by)return alert('담당자를 골라주세요');if(!b.title||!b.body)return alert('제목과 본문을 채워주세요');document.querySelectorAll('#aiL input,#genL input').forEach(i=>b.features[i.dataset.k]=i.checked);
 if(cSel.value==='__new'){{b.new_campaign=$('cNew').value.trim();b.copy_campaign=(PREF.campaign_id&&ACCT.some(c=>c.id===PREF.campaign_id))?PREF.campaign_id:(ACCT[0]||{{}}).id;if(!b.new_campaign)return alert('새 캠페인 이름을 적어주세요')}}else b.campaign_id=cSel.value;
 if(sSel.value==='__new'){{b.new_adset=document.getElementById('sNew').value.trim();const src=srcSet();b.copy_adset=src&&src.id;b.budget=document.getElementById('bud').value;if(!b.new_adset)return alert('새 세트 이름을 적어주세요')}}else b.adset_id=sSel.value;
 if(!b.campaign_id&&!b.new_campaign)return;const s=OP.querySelector('.ops-s');dlg.close();s.textContent='세팅 중… (몇 분)';OP.querySelector('.setup').disabled=true;
 try{{const r=await (await fetch('api/bokgak',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(b)}})).json();if(!r.ok)throw new Error(r.msg);RQ[OP.dataset.date+'_'+OP.dataset.no]=r.job;save();addLocal({{job:r.job,type:'setup',date:b.date,no:b.no,adset:b.adset_id||('new:'+b.new_adset)}});try{{const L=sentL().filter(x=>x.at>Date.now()/1000-3600);L.push({{job:r.job,adset:b.adset_id||('new:'+b.new_adset),at:Date.now()/1000}});localStorage.setItem('setup-sent',JSON.stringify(L))}}catch(e){{}}}}catch(err){{s.textContent='실패: '+err.message;OP.querySelector('.setup').disabled=false}}}};
const bD=R=>QA(R,'.del').forEach(b=>b.onclick=async()=>{{const c=b.closest('.card');
 if(!confirm(b.dataset.fref?'이 실패 기록을 지울까요?':b.dataset.live?'이 소재를 검수 페이지에서 삭제할까요?\\n메타에 세팅한 광고는 지워지지 않아요(그대로 남음).':'이 소재를 삭제할까요?\\n이 레퍼런스는 다시 복각할 수 있게 풀려요.'))return;b.disabled=true;b.textContent='삭제 중…';
 try{{const r=await (await fetch('api/bokgak',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(b.dataset.fref?{{type:'delete',fjob:b.dataset.fjob,fref:b.dataset.fref,by:c.dataset.p}}:{{type:'delete',date:b.dataset.date,no:b.dataset.no,by:c.dataset.p}})}})).json();if(!r.ok)throw new Error(r.msg);c.style.opacity=.35;b.textContent='삭제 요청됨 · 곧 사라져요';addLocal({{job:r.job,type:'delete'}})}}catch(e){{b.textContent='삭제 실패';b.disabled=false}}}});
setInterval(()=>{{if(!document.hidden&&(LAST[0].length||WAITDEP))prog(LAST[0],LAST[1],LAST[2])}},1000);   // 막대는 1초마다 갱신
const bR=R=>QA(R,'.retry').forEach(b=>b.onclick=async()=>{{const c=b.closest('.card');b.disabled=true;b.textContent='다시 복각 요청 중…';
 try{{const r=await (await fetch('api/bokgak',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{type:'retry',fjob:b.dataset.fjob,fref:b.dataset.fref,by:c.dataset.p}})}})).json();if(!r.ok)throw new Error(r.msg);
  b.textContent='↻ 다시 만드는 중… (위 진행 카드에서 확인)';c.style.opacity=.6;JUST0=r.job;addLocal({{job:r.job,type:'retry',by:c.dataset.p}})}}catch(e){{b.textContent='요청 실패: '+e.message;b.disabled=false}}}});
let JUST0=null;
{{   // (예전 임시: POST 가로채 4초 폴링 → addLocal·kick 으로 대체)
 try{{const y=sessionStorage.getItem('rv-scroll');if(y){{sessionStorage.removeItem('rv-scroll');addEventListener('load',()=>scrollTo(0,+y))}}}}catch(e){{}}}}
// ── 새로고침 없이 반영(2026-10-21) ──
// api 확인: 진행 중 작업이 있으면 10초, 없으면 60초(10분 넘게 손 안 대면 5분) — Blob 호출 아끼기. 탭이 안 보이면 멈췄다가 다시 보이면 바로 확인.
// 배포 확인: ver.json(정적 파일, Blob 안 씀) 30초(작업 중 10초). 바뀌면 검수 목록만 다시 받아 달라진 카드만 교체 — 쓰던 피드백·첨부·보던 버전·스크롤 유지, 창이 열려 있으면 닫힌 뒤에.
function bindAll(R){{bV(R);bF(R);bZ(R);bG(R);bO(R);bD(R);bR(R)}}
let VER=null,ACTIVE=false,LASTAPI=0,LASTACT=Date.now(),SRT=0;
['pointerdown','keydown','scroll','mousemove'].forEach(e=>addEventListener(e,()=>{{LASTACT=Date.now()}},{{passive:true}}));
function busyNow(){{return ACTIVE||LOCAL.length>0||Object.keys(RQ).length>0||(WAITDEP&&Date.now()-WAITDEP<300000)||(!!JUST&&Date.now()-T0<600000)}}
async function verCheck(){{try{{const v=await (await fetch('ver.json?_='+Date.now(),{{cache:'no-store'}})).json();const k=v.review||v.at;if(VER===null){{VER=k;return}}if(k!==VER){{VER=k;await softRefresh()}}}}catch(e){{}}}}
async function tick(){{clearTimeout(window._pt);if(document.hidden)return;
 await verCheck();
 if(busyNow()||Date.now()-LASTAPI>(Date.now()-LASTACT>600000?300000:60000)){{LASTAPI=Date.now();await poll()}}
 clearTimeout(window._pt);if(!document.hidden)window._pt=setTimeout(tick,busyNow()?10000:30000)}}
function kick(){{clearTimeout(window._pt);window._pt=setTimeout(tick,400)}}
document.addEventListener('visibilitychange',()=>{{if(!document.hidden)kick()}});
async function softRefresh(){{clearTimeout(SRT);
 if([...document.querySelectorAll('dialog')].some(d=>d.open)){{SRT=setTimeout(softRefresh,3000);return}}   // 세팅 창 등이 열려 있으면 닫힌 뒤에
 let doc;try{{const r=await fetch('review.html?_='+Date.now(),{{cache:'no-store'}});if(!r.ok)throw 0;doc=new DOMParser().parseFromString(await r.text(),'text/html')}}catch(e){{SRT=setTimeout(softRefresh,15000);return}}
 const L=document.getElementById('list'),NL=doc.getElementById('list');if(!L||!NL)return;
 const ae=document.activeElement,sel=ae&&ae.tagName==='TEXTAREA'?[ae.selectionStart,ae.selectionEnd]:null;
 const old=new Map();[...L.children].forEach(c=>{{if(c.matches('.card'))old.set(ck(c),c);else c.remove()}});
 const want=[];let chg=0;
 [...NL.children].forEach(n=>{{if(!n.matches('.card')){{want.push(document.importNode(n,true));return}}
  const k=ck(n),h=n.outerHTML,o=old.get(k);
  if(o&&SRC.get(k)===h){{want.push(o);old.delete(k);return}}
  const c=document.importNode(n,true);SRC.set(k,h);bindAll(c);chg++;
  if(o){{old.delete(k);const f=o.querySelector('.fb'),nf=c.querySelector('.fb');
   if(f&&nf&&(f.querySelector('textarea').value.trim()||f.querySelector('.fbf').files.length||f.contains(ae)))nf.replaceWith(f);   // 쓰던 피드백·첨부 파일 그대로
   if(o.dataset.view&&o.dataset.view!==o.dataset.cur&&o.dataset.cur===c.dataset.cur){{const vb=c.querySelector(`.vb[data-v="${{o.dataset.view}}"]`);if(vb)vb.click()}}   // 보던 버전 그대로
   o.remove()}}
  want.push(c)}});
 old.forEach(o=>{{o.remove();chg++}});
 want.forEach((c,i)=>{{if(L.children[i]!==c)L.insertBefore(c,L.children[i]||null)}});
 if(sel&&ae.isConnected&&document.activeElement!==ae){{ae.focus({{preventScroll:true}});try{{ae.setSelectionRange(sel[0],sel[1])}}catch(e){{}}}}
 const tb=document.querySelector('.tabs'),cal=tb.querySelector('.calbtn');tb.querySelectorAll('.tab').forEach(t=>t.remove());cal.after(...[...doc.querySelectorAll('.tabs .tab')].map(t=>document.importNode(t,true)));
 document.querySelector('.ptabs').replaceChildren(...[...doc.querySelectorAll('.ptabs .ptab')].map(t=>document.importNode(t,true)));
 ts=[...document.querySelectorAll('.tab')];ps=[...document.querySelectorAll('.ptab')];bindTabs();
 const sp=document.querySelector('.hd .spend'),nsp=doc.querySelector('.hd .spend');if(sp&&nsp)sp.innerHTML=nsp.innerHTML;
 try{{for(const s of doc.scripts){{const t=s.textContent;let m=/const DAYCNT=(.*);$/m.exec(t);if(m&&typeof DAYCNT==='object'){{const v=JSON.parse(m[1]);Object.keys(DAYCNT).forEach(k=>delete DAYCNT[k]);Object.assign(DAYCNT,v)}}
  m=/(?:const|let) BUILT=([0-9]+),ACCT=(.*),PREF=(.*),IDENT=(.*);$/m.exec(t);if(m){{BUILT=+m[1];ACCT=JSON.parse(m[2]);PREF=JSON.parse(m[3]);IDENT=JSON.parse(m[4])}}}}}}catch(e){{}}
 DONEK.clear();WAITDEP=0;LASTSR=Date.now();sh(P,DD);prog(LAST[0],LAST[1],LAST[2]);
 if(chg){{const t=document.createElement('div');t.className='tnote';t.innerHTML='<b>✓ 새 결과가 화면에 반영됐어요</b>';document.getElementById('tnotes').append(t);setTimeout(()=>t.remove(),5000)}}}}
bindAll(document);tick();
document.addEventListener('click',e=>{{const b=e.target.closest('.rthumb');if(!b)return;e.preventDefault();let d=document.getElementById('refdlg');if(!d){{d=document.createElement('dialog');d.id='refdlg';document.body.append(d);d.addEventListener('click',ev=>{{if(ev.target===d||ev.target.closest('.rx'))d.close()}});d.addEventListener('close',()=>d.innerHTML='')}}
 const v=b.dataset.v,p=b.dataset.p,mv=b.closest('.card')&&b.closest('.card').querySelector('.mv:not([hidden])');
 const ref=v?`<video class="rv" src="${{v}}"${{p?` poster="${{p}}"`:''}} loop playsinline controls autoplay></video>`:`<img src="${{p}}" alt="레퍼런스 원본">`;
 d.innerHTML=`<div class="rw"><figure>레퍼런스 원본${{ref}}</figure></div><div class="rb"><button type="button" class="rx">닫기</button></div>`;d.showModal()}});
document.addEventListener('click',e=>{{const b=e.target.closest('.rsync');if(!b)return;const d=b.closest('dialog');if(!d)return;d.querySelectorAll('video').forEach(v=>{{v.currentTime=0;v.play().catch(()=>{{}})}})}});   // 팝업 안 레퍼런스·복각본을 같은 시점부터
</script>{SPEND_DLG_H}{SPEND_JS_H}{DATECAL_DLG}{DATECAL_JS_H}</body></html>'''
open(R + 'site/review.html', 'w').write(page); print('review', len(rv), 'dates', len(dates))
