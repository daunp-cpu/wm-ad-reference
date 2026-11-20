"""대표님 계정 메타 토큰 저장. Graph API 탐색기에서 토큰을 '복사'만 한 뒤 실행 — 클립보드에서 읽어 60일 토큰으로 바꿔
~/.config/ad-reference/meta_ceo.env (권한 600) 에 저장하고 클립보드는 비움. 토큰 값은 출력하지 않음.
사용: python3 -I save_meta_token.py"""
import json, os, subprocess, urllib.request, urllib.parse, urllib.error, datetime
def env(p):
    d = {}
    for l in open(p):
        if '=' in l and not l.startswith('#'): k, v = l.strip().split('=', 1); d[k] = v.strip('"\'')
    return d
E = env('/Users/daun/sooo-meta/.env'); G = 'https://graph.facebook.com/v21.0/'
short = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout.strip()
if 'access_token=' in short: short = urllib.parse.parse_qs(short.split('#', 1)[-1].split('?', 1)[-1]).get('access_token', [''])[0]   # 로그인 완료 주소를 통째로 복사한 경우
if not short.startswith('EAA') or len(short) < 100: raise SystemExit('클립보드에 메타 토큰이 없어요. Graph API 탐색기에서 토큰을 복사한 뒤 다시 실행해 주세요.')
def get(path, **q):
    try: return json.load(urllib.request.urlopen(G + path + '?' + urllib.parse.urlencode(q), timeout=60))
    except urllib.error.HTTPError as e:
        m = json.loads(e.read().decode()).get('error', {}); raise SystemExit('메타 오류: ' + (m.get('error_user_msg') or m.get('message', '')))
r = get('oauth/access_token', grant_type='fb_exchange_token', client_id=E['META_APP_ID'], client_secret=E['META_APP_SECRET'], fb_exchange_token=short)
tok = r['access_token']; exp = (datetime.date.today() + datetime.timedelta(seconds=int(r.get('expires_in', 5184000)))).isoformat()
me = get('me', fields='id,name', access_token=tok)
D = os.path.expanduser('~/.config/ad-reference'); os.makedirs(D, exist_ok=True); P = D + '/meta_ceo.env'
open(P, 'w').write(f'META_ACCESS_TOKEN={tok}\nOWNER={me["name"]}\nEXPIRES={exp}\n'); os.chmod(P, 0o600)
subprocess.run(['pbcopy'], input='', text=True)   # 클립보드 비우기
dd = get('debug_token', input_token=tok, access_token=E['META_APP_ID'] + '|' + E['META_APP_SECRET']).get('data', {})
print('권한:', ', '.join(dd.get('scopes', [])))
if 'ads_read' not in dd.get('scopes', []) and 'ads_management' not in dd.get('scopes', []): raise SystemExit('저장은 했지만 ads_read 권한이 없어서 광고 계정을 볼 수 없어요. 탐색기에서 ads_read 를 추가해 다시 받아주세요.')
acc = get('me/adaccounts', fields='name,account_id,account_status,amount_spent', limit=200, access_token=tok).get('data', [])
print(f'저장 완료 — {me["name"]} 계정, 만료 {exp}')
print(f'볼 수 있는 광고 계정 {len(acc)}개:')
for a in sorted(acc, key=lambda a: -int(a.get('amount_spent') or 0)):
    print(f"  {a['account_id']}  {a['name']}  누적 지출 {int(a.get('amount_spent') or 0):,}{'' if a.get('account_status') == 1 else '  [비활성]'}")
