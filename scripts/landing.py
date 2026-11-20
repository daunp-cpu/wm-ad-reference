"""랜딩 페이지 읽기 — 복각하기 팝업의 랜딩 목록(data/products.json)과, 고른 랜딩에 맞춘 소재 제작용 상품 정보.
python3 -I landing.py            → sooo.kr 상품 목록 갱신(data/products.json)
from landing import read_landing → {url,title,price,image,images,text}"""
import json, re, html, os, sys, urllib.request, urllib.parse
R = '/Users/daun/ad-reference/'
DEFAULT = 'https://sooo.kr/product/detail.html?product_no=108&cate_no=1&display_group=2'


def _get(u, timeout=40):
    return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=timeout).read().decode('utf-8', 'ignore')


def _meta(h, prop):
    m = re.search(r'<meta (?:property|name)="%s" content="([^"]*)"' % re.escape(prop), h)
    return html.unescape(m.group(1)) if m else ''


def read_landing(url):
    """랜딩 HTML에서 상품명·가격·대표/상세 이미지·본문 텍스트를 뽑는다(없는 건 빈 값)."""
    h = _get(url)
    title = _meta(h, 'og:title') or (re.search(r'<title>(.*?)</title>', h, re.S) or [None, ''])[1]
    title = re.sub(r'\s*-\s*SOOO\s*$', '', html.unescape(title)).strip()
    price = _meta(h, 'product:sale_price:amount') or _meta(h, 'product:price:amount')
    img = _meta(h, 'og:image')
    base = '{0.scheme}://{0.netloc}'.format(urllib.parse.urlparse(url))
    imgs = []
    for s in re.findall(r'<img[^>]+(?:ec-data-src|data-src|src)="([^"]+\.(?:jpg|jpeg|png|webp))"', h, re.I):
        s = urllib.parse.urljoin(base, html.unescape(s))
        if any(k in s for k in ('/web/product/', '/web/upload/', 'detail')) and s not in imgs and s != img: imgs.append(s)
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S | re.I)
    text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', body))).strip()
    i = max(text.find('판매가'), text.find('소비자가'))   # 상품 정보 영역부터
    imgs = [x for x in imgs if '/small/' not in x and '/tiny/' not in x]
    imgs.sort(key=lambda x: 'NNEditor' not in x)   # 상품 상세 이미지 먼저(공통 배너는 뒤로)
    return {'url': url, 'title': title, 'price': price, 'image': img, 'images': imgs[:12], 'text': text[max(i - 300, 0):max(i - 300, 0) + 2500] if i >= 0 else ''}


def products():
    h = _get('https://sooo.kr/product/list.html?cate_no=1')
    nos = list(dict.fromkeys(re.findall(r'product_no=(\d+)', h)))
    out = []
    for no in nos:
        u = f'https://sooo.kr/product/detail.html?product_no={no}&cate_no=1&display_group=2'
        try:
            d = read_landing(u)
            if d['title']: out.append({'no': no, 'url': u, 'title': d['title'], 'price': d['price'], 'image': d['image']})
        except Exception as e: print('상품 읽기 실패', no, str(e)[:80])
    out.sort(key=lambda x: (x['no'] != '108', int(x['no'])))   # 기본(108) 맨 위
    json.dump(out, open(R + 'data/products.json', 'w'), ensure_ascii=False, indent=1)
    print('상품', len(out))


if __name__ == '__main__': products()
