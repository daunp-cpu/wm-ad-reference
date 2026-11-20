"""복각 소재를 만들며 실제로 호출한 AI 비용만 적어 둔다(data/cost.json).

이 사이트로 만든 소재에 든 돈만 센다 — 다른 데서 쓴 Gemini 요금은 포함하지 않는다.
단가는 2026-10 기준 공개가(Google 공식 가격표가 바뀌면 RATE 만 고치면 된다).
"""
import json, os, datetime, fcntl

USD = 1400          # 환율(원). 정산용이 아니라 눈대중용이라 고정값을 쓴다.
RATE = {
    # 이미지: 장당. 입력 레퍼런스 이미지도 따로 과금된다.
    'nano-banana-pro-preview': {'out_img': 0.134, 'in_img': 0.067},
    # 텍스트·분석: 100만 토큰당
    'gemini-3.1-pro-preview': {'in_tok': 2.0 / 1e6, 'out_tok': 12.0 / 1e6},
    # 영상: 1초당(720p, 소리 없음)
    'veo-3.1-fast-generate-001': {'sec': 0.08},
    # ZCRE: 크레딧당. 2026-10-26 다운 충전 59,400원 / 8,000크레딧 = 7.425원
    'zcre': {'credit': 59400 / 8000 / 1400},
}


CUR = {'date': None, 'no': None}   # 지금 만들고 있는 소재(bokgak.py 가 채운다) — 소재별 금액용


def _path(root):
    return os.path.join(root, 'data/cost.json')


def log(root, model, **kw):
    """호출 한 건 기록. kw: out_img/in_img/in_tok/out_tok/sec 중 해당하는 것."""
    r = RATE.get(model) or RATE.get(model.split(':')[0], {})   # 'zcre:<모델>' 은 zcre 단가
    usd = sum(r.get(k, 0) * v for k, v in kw.items())
    row = dict(t=datetime.datetime.now().isoformat(timespec='seconds'), model=model, usd=round(usd, 6), **kw)
    if CUR.get('date') and CUR.get('no'): row['date'], row['no'] = CUR['date'], CUR['no']
    p = _path(root)
    # 복각이 동시에 여러 개 돌아서(2026-10-26) 잠금을 잡고 읽고 쓴다 — 안 그러면 기록이 서로 덮인다
    with open(p + '.lock', 'w') as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try: rows = json.load(open(p))
        except Exception: rows = []
        rows.append(row)
        tmp = p + '.tmp'
        json.dump(rows, open(tmp, 'w'), ensure_ascii=False)
        os.replace(tmp, p)
    return usd


def total(root):
    """(총 원화, 호출 수, 첫 기록일) — 기록이 없으면 (0, 0, None)."""
    try: rows = json.load(open(_path(root)))
    except Exception: return 0, 0, None
    if not rows: return 0, 0, None
    return round(sum(x.get('usd', 0) for x in rows) * USD), len(rows), rows[0]['t'][:10]


def seed(root):
    """기록을 심기 전에 만든 소재는 호출 이력이 없다 → review.json 으로 건당 추정해 한 번만 넣는다.
    추정 근거: 소재 1건 = 기획(gemini 1회) + 이미지 생성(버전 수만큼) + 레퍼런스·제품 입력 이미지 3장,
    영상이면 veo 8초와 키프레임 2장이 더 붙는다."""
    p = _path(root)
    try: rows = json.load(open(p))
    except Exception: rows = []
    if any(x.get('est') for x in rows): return 0          # 이미 심었다
    try: rv = json.load(open(os.path.join(root, 'data/review.json')))
    except Exception: return 0
    r_img, r_txt, r_veo = RATE['nano-banana-pro-preview'], RATE['gemini-3.1-pro-preview'], RATE['veo-3.1-fast-generate-001']
    plan = 8000 * r_txt['in_tok'] + 1500 * r_txt['out_tok']
    add = []
    for x in rv:
        nver = max(1, len(x.get('versions') or []) or 1)
        vid = str(x.get('img') or '').endswith('.mp4') or bool(x.get('video')) or x.get('ref_kind') == '영상'
        usd = plan + nver * (r_img['out_img'] + 3 * r_img['in_img'])
        if vid: usd += 8 * r_veo['sec'] + 2 * (r_img['out_img'] + r_img['in_img'])
        add.append(dict(t=(x.get('date') or '') + 'T' + (x.get('made') or '00:00') + ':00',
                        model='(추정)', usd=round(usd, 6), est=True, date=x.get('date'), no=x.get('no')))
    if not add: return 0
    rows = add + rows
    rows.sort(key=lambda r: r['t'])
    tmp = p + '.tmp'; json.dump(rows, open(tmp, 'w'), ensure_ascii=False); os.replace(tmp, p)
    return len(add)


def est_count(root):
    try: return sum(1 for x in json.load(open(_path(root))) if x.get('est'))
    except Exception: return 0


def by_day(root):
    """{'2026-10-19': 1550, ...} 날짜별 합계(원). 달력에 뿌린다."""
    try: rows = json.load(open(_path(root)))
    except Exception: return {}
    out = {}
    for x in rows:
        d = (x.get('date') or x.get('t', '')[:10])[:10]
        if len(d) == 10: out[d] = out.get(d, 0) + x.get('usd', 0) * USD
    return {k: round(v) for k, v in sorted(out.items())}


def by_item(root):
    """{'2026-10-19/001': 1550, ...} 소재별 합계(원). 검수 카드에 작게 띄운다."""
    try: rows = json.load(open(_path(root)))
    except Exception: return {}
    out = {}
    for x in rows:
        if x.get('date') and x.get('no'):
            k = f"{x['date']}/{x['no']}"
            out[k] = out.get(k, 0) + x.get('usd', 0) * USD
    return {k: round(v) for k, v in out.items()}


def month_total(root, ym=None):
    """이번 달(또는 ym='2026-10')만 합산 — (원, 건수, 추정건수). 기록은 지우지 않고 표시만 달마다 새로 센다."""
    ym = ym or datetime.date.today().strftime('%Y-%m')
    try: rows = json.load(open(_path(root)))
    except Exception: return 0, 0, 0
    sel = [x for x in rows if (x.get('date') or x.get('t', ''))[:7] == ym]
    return round(sum(x.get('usd', 0) for x in sel) * USD), len(sel), sum(1 for x in sel if x.get('est'))


if __name__ == '__main__':
    # ZCRE 사용 기록(복각 Claude 가 생성 끝나고 부름): python cost.py zcre <사이트폴더> <실사용 크레딧> <ZCRE 모델> [날짜 번호]
    import sys
    a = sys.argv[1:]
    if len(a) >= 4 and a[0] == 'zcre':
        if len(a) >= 6: CUR['date'], CUR['no'] = a[4], a[5]
        print(round(log(a[1], 'zcre:' + a[3], credit=float(a[2])) * USD), '원 기록 (' + a[3] + ')')
