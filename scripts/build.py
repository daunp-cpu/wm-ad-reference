"""data/*.json → site/index.html(광고 라이브러리 레퍼런스) + site/agency.html(대행 계정 고효율). 이미지는 site/m/ 에 저장."""
import sys; sys.path.insert(0, '/Users/daun/ad-reference/scripts'); from zcre_ui import ZCRE_HTML, ZCRE_JS
from slacksync_ui import SS_BTN, SS_CSS, SS_JS   # 소재공유방 새로고침 버튼(2026-11-12)
import json,os,re,datetime,hashlib,urllib.request,html
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
R='/Users/daun/ad-reference/'; M=R+'site/m/'; os.makedirs(M,exist_ok=True)
today=datetime.date.today(); TS=datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
cfg=json.load(open(R+'config.json')); QC={q['q']:q for q in cfg['queries']}
def fetch(url,key):
    out=M+key+'.jpg'
    if os.path.exists(out): return key
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.facebook.com/'})
        data=urllib.request.urlopen(req,timeout=40).read(); tmp=out+'.tmp'; open(tmp,'wb').write(data)
        im=Image.open(tmp).convert('RGB'); im.thumbnail((480,600)); im.save(out,quality=78); os.remove(tmp); return key
    except Exception: return None
def secs(d):
    if not d: return None
    m,s=d.split(':'); return int(m)*60+int(s)
esc=lambda s: html.escape(s or '')
# ---------- 광고 라이브러리 ----------
raw=json.load(open(R+'data/library-raw.json'))
_cl=lambda v: v.encode('utf-8','surrogatepass').decode('utf-8','ignore') if isinstance(v,str) else v
for c in raw:   # 잘린 이모지(짝 없는 서로게이트) 제거
    for k in ('text','page'):
        if k in c: c[k]=_cl(c[k])
seen=json.load(open(R+'data/seen.json')) if os.path.exists(R+'data/seen.json') else {}
best={}; QS={}   # 광고 id → 걸린 키워드 전부
for c in raw:
    if c['low'] or not c.get('start'): continue
    q=QC.get(c['q'],{}); must=q.get('must')
    if must and not any(m in c['text'] for m in must): continue
    days=(today-datetime.date.fromisoformat(c['start'])).days
    if days<cfg.get('min_days',14): continue
    c['days']=days; c['group']=q.get('group','')
    QS.setdefault(c['id'],[])
    if c['q'] not in QS[c['id']]: QS[c['id']].append(c['q'])
    if c['id'] not in best or best[c['id']]['rank']>c['rank']: best[c['id']]=c
uniq={}
for c in sorted(best.values(),key=lambda x:-x['days']):
    t=re.sub(r'\s+',' ',c['text']).strip(' /'); k=t[:60]
    if k in uniq: continue
    c['t']=t; uniq[k]=c
# 2026-11-10 다운: 올영 포스터 등 더 다양하게 → 키워드마다 상위 per_query 개는 꼭 넣고, 나머지는 오래 집행된 순으로 채움
_all=sorted(uniq.values(),key=lambda x:(-x['days'],x['rank']));_pq=cfg.get('per_query',6);_pick=[];_ids=set();_byq={}
for c in _all: _byq.setdefault(c['q'],[]).append(c)
for q_,cs in _byq.items():
    for c in cs[:_pq]: _pick.append(c);_ids.add(c['id'])
for c in _all:
    if len(_pick)>=cfg.get('max_cards',300): break
    if c['id'] not in _ids: _pick.append(c);_ids.add(c['id'])
lib=sorted(_pick,key=lambda x:(-x['days'],x['rank']))[:max(cfg.get('max_cards',300),len(_byq)*_pq)]
for c in lib: seen.setdefault(c['id'],today.isoformat()); c['new']=seen[c['id']]==today.isoformat()
json.dump(seen,open(R+'data/seen.json','w'))
def libimg(c):
    url=c['poster'] or (c['imgs'][1] if len(c['imgs'])>1 else (c['imgs'][0] if c['imgs'] else None))
    # 카드 안 첫 이미지는 보통 페이지 프로필 → 가장 큰 쪽(뒤쪽)을 우선
    if c['imgs'] and not c['poster']: url=c['imgs'][-1] if len(c['imgs'])>1 else c['imgs'][0]
    return fetch(url,'L'+c['id']) if url else None
with ThreadPoolExecutor(12) as ex: keys=list(ex.map(libimg,lib))
for c,k in zip(lib,keys): c['img']=k
# ---------- 대행 계정 ----------
ag=json.load(open(R+'data/agency.json')) if os.path.exists(R+'data/agency.json') else []
# 같은 브랜드가 광고계정 여러 개로 쪼개져 있어 읽기 힘들다 → 브랜드 하나로 묶는다(원본 계정명은 data/agency.json 에 그대로 남음)
BRAND=[('셀라딕스',('셀라딕스',)),('마미케어',('마미케어','mommycare')),('성분에디터',('성분에디터',)),
       ('FnL',('fnl','에프앤엘')),('칸디데',('칸디데','candide')),('프롬랩',('from labs','fromlabs')),
       ('이삼오구_비피젠',('비피젠',)),('이삼오구_히든',('히든',)),('오브휴',('오브휴','ofhue')),
       ('베러데이',('betterday',)),('SOOO',('sooo',)),('라라스윗',('라라스윗','lalasweet'))]
def brand(n):
    low=n.lower()
    for b,keys in BRAND:
        if any(k in low for k in keys): return b
    return n
for x in ag: x['acct']=brand(x['acct'])
merged={}
for x in ag:
    k=x.get('video_id') or (x.get('img') or '').split('?')[0] or x['id']
    if k in merged:
        m=merged[k]; m['spend']+=x['spend']; m['pur']+=x['pur']; m['val']+=x['val']; m['days']=max(m['days'],x['days'])
        if x['first'] and (not m['first'] or x['first']<m['first']): m['first']=x['first']
        if x['last'] and (not m['last'] or x['last']>m['last']): m['last']=x['last']
        if x.get('status')=='ACTIVE': m['status']='ACTIVE'
    else: merged[k]=dict(x)
ag=sorted(merged.values(),key=lambda x:(-x['days'],-x['spend']))
with ThreadPoolExecutor(12) as ex: keys=list(ex.map(lambda x: fetch(x['img'],'A'+x['id']) if x.get('img') else None,ag))
for x,k in zip(ag,keys): x['imgk']=k; x['roas']=x['val']/x['spend'] if x['spend'] else 0
def fmt_ag(x):
    n=x['name'].lower()
    if 'gif' in n: return 'GIF'
    if any(s in n for s in ('image','img','이미지')): return '이미지'
    if x.get('vlen'): return '영상 %d초'%x['vlen']
    if x.get('video_id'): return '영상'
    return '이미지'
CSS='''<style>
.uprev{display:flex;flex-wrap:wrap;gap:6px}.uprev:empty{display:none}.uprev figure{margin:0;width:84px;position:relative}.uprev img,.uprev video{width:84px;height:110px;object-fit:cover;border-radius:6px;display:block;background:#000}.uprev b{position:absolute;top:3px;left:3px;background:#000;color:#ffd54a;border-radius:4px;padding:0 5px;font-size:12px}.uprev .udoc{display:flex;align-items:center;justify-content:center;width:84px;height:110px;border-radius:6px;background:var(--acs,#eef);color:var(--ac);font-size:12px;font-weight:800;text-align:center}.uprev figcaption{font-size:10.5px;color:var(--mu);overflow:hidden;white-space:nowrap}
.hk{border:2px solid var(--ac);border-left-width:5px;border-radius:10px;padding:8px 10px;background:var(--acs,rgba(59,91,219,.07));font-size:13px;line-height:1.55}.hk p{margin:0 0 4px}.hk p:last-child{margin:0}.hk b{color:var(--ac)}.hk i,.more i{color:var(--mu);font-style:normal;font-size:12px}
.tgs{display:flex;flex-wrap:wrap;gap:4px}.tgs span{background:var(--acs,#e8edff);color:var(--ac);border-radius:6px;padding:1px 7px;font-size:12px;font-weight:700}
.more{font-size:12.5px;color:var(--mu)}.more summary{cursor:pointer;font-weight:700;color:var(--fg)}.more p{margin:6px 0 0;line-height:1.5}.more b{color:var(--fg)}
.taken{position:absolute;inset:0;z-index:3;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;background:rgba(20,18,32,.62);color:#fff;text-align:center;pointer-events:none}
.taken b{font-size:28px;font-weight:900;line-height:1.1}.taken span{font-size:20px;font-weight:800}.taken small{font-size:13px;opacity:.85}.taken.ing{background:rgba(92,58,190,.62)}.taken.ing span{animation:blk 1.2s infinite alternate}.taken.live{background:rgba(22,122,74,.66)}
@keyframes blk{to{opacity:.45}}@media (prefers-reduced-motion:reduce){.taken.ing span{animation:none}}
.who{font:inherit;font-size:14px;padding:8px 10px;border:2px solid #c62828;border-radius:8px}.cxs{border:1px solid #c62828;color:#c62828;background:#fff;border-radius:999px;padding:0 8px;font-size:11px;font-weight:800;cursor:pointer}.pick{z-index:4!important}
.im{position:relative}.im video.pv{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#000;opacity:0;transition:opacity .2s}.im video.pv.on{opacity:1}
.addc{border:2px dashed var(--ac);background:var(--s);color:var(--ac);border-radius:10px;min-height:320px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;cursor:pointer;font:inherit}.addc b{font-size:56px;line-height:1}.addc span{font-weight:800}.addc small{color:var(--mu)}
.addc:hover{background:var(--acs,rgba(59,91,219,.08))}.pendc{border:2px dashed var(--ln);border-radius:10px;min-height:320px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;color:var(--mu);text-align:center;padding:12px}
dialog{border:0;border-radius:14px;padding:0;width:min(520px,calc(100vw - 32px));background:var(--s);color:var(--fg)}dialog::backdrop{background:rgba(0,0,0,.45)}
.md{padding:18px 20px;display:flex;flex-direction:column;gap:10px}.md h3{margin:0}.md label{display:flex;flex-direction:column;gap:4px;font-size:13px;font-weight:700}.md small{color:var(--mu);font-weight:400}
.md input:not([type=radio]),.md select,.md textarea{font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--ln);border-radius:8px;background:var(--bg);color:var(--fg)}
.seg{display:flex;gap:8px}.seg label{flex-direction:row;align-items:center;gap:6px;border:1px solid var(--ln);border-radius:999px;padding:6px 14px;cursor:pointer}.seg label:has(input:checked){border-color:var(--ac);color:var(--ac)}
.aprev img,.aprev video{max-width:100%;max-height:260px;border-radius:8px;display:block}.mrow{display:flex;align-items:center;gap:8px;justify-content:flex-end}.mmsg{flex:1;font-size:12.5px;color:var(--mu);margin:0}
.pri{border:0;border-radius:999px;padding:9px 18px;font-weight:800;background:var(--ac);color:#fff;cursor:pointer}.pri:disabled{opacity:.5}.ghost2{border:1px solid var(--ln);background:var(--s);color:var(--fg);border-radius:999px;padding:9px 16px;cursor:pointer}
.linfo{display:flex;gap:10px;align-items:center;font-size:13px;background:var(--bg);border-radius:8px;padding:8px}.linfo img{width:56px;height:56px;object-fit:cover;border-radius:6px}.linfo:empty{display:none}
:root{--bg:#f3f4f7;--s:#fff;--fg:#16171d;--mu:#5d6070;--ln:#dcdee6;--ac:#3a5bd9;--acs:#e6ebfc;--ok:#167a4a;--oks:#dff3e8;--new:#d12f5a}
@media (prefers-color-scheme:dark){:root{--bg:#121318;--s:#1b1d24;--fg:#e8e9ef;--mu:#9a9db0;--ln:#2c2f3a;--ac:#8ea6ff;--acs:#232a45;--ok:#5fd39a;--oks:#173226;--new:#ff7096}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,"Apple SD Gothic Neo","Pretendard",sans-serif}
.w{max-width:1280px;margin:0 auto;padding:28px max(16px,env(safe-area-inset-left)) 64px}
h1{margin:0;font-size:28px}nav{display:flex;gap:14px;margin:6px 0 4px}nav a{color:var(--ac);font-weight:700;text-decoration:none}
.lede{color:var(--mu);margin:6px 0 16px;max-width:75ch}.bar{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 18px}.sub{display:flex;flex-wrap:wrap;gap:6px;margin:-8px 0 18px;padding:10px 12px;background:var(--s);border:1px solid var(--ln);border-radius:12px}.chip.sm{padding:3px 10px;font-size:13px}.chip small{opacity:.65;font-weight:500}[hidden]{display:none!important}
.chip{border:1px solid var(--ln);background:var(--s);color:var(--fg);border-radius:999px;padding:6px 12px;font-weight:600;cursor:pointer}
.chip[aria-pressed=true]{background:var(--ac);color:var(--s);border-color:var(--ac)}
.g{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.delref{float:right;border:1px solid var(--ln);background:var(--s);color:var(--mu);border-radius:999px;padding:1px 8px;font-size:11px;cursor:pointer;margin-left:6px}
.delref:hover{border-color:#c62828;color:#c62828}
.c{background:var(--s);border:1px solid var(--ln);border-radius:10px;overflow:hidden;display:flex;flex-direction:column;min-width:0}
.c .im{aspect-ratio:4/5;background:#0c0d10;display:flex;align-items:center;justify-content:center;position:relative}
.c img{width:100%;height:100%;object-fit:contain}.b{padding:10px 12px;display:flex;flex-direction:column;gap:6px;font-size:13px;min-width:0}
.d{position:absolute;top:8px;left:8px;background:var(--s);color:var(--fg);font-weight:800;border-radius:6px;padding:1px 7px;font-size:13px}
.nw{position:absolute;top:8px;right:8px;background:var(--new);color:#fff;font-weight:800;border-radius:6px;padding:1px 7px;font-size:12px}
.p{font-weight:800;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.mt{color:var(--mu);font-variant-numeric:tabular-nums}
.t{color:var(--fg);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.tg{display:flex;flex-wrap:wrap;gap:4px}.tg span{background:var(--acs);color:var(--ac);border-radius:4px;padding:1px 6px;font-weight:700;font-size:11.5px}
.tg .e{background:var(--oks);color:var(--ok)}a.l{color:var(--ac);font-weight:700;text-decoration:none;margin-top:auto}
.c{position:relative}.hd{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.jump{background:var(--ac);color:#fff;font-weight:800;border-radius:999px;padding:9px 18px;text-decoration:none}.pick{position:absolute;z-index:2;bottom:auto;top:40px;left:8px;background:var(--s);border-radius:6px;padding:2px 8px;font-weight:800;font-size:12.5px;display:flex;gap:5px;align-items:center;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.25)}
.pick input{width:16px;height:16px;accent-color:var(--ac);margin:0}.c.sel{outline:3px solid var(--ac);outline-offset:-3px}
.st:empty{display:none}.st{align-self:flex-start;font-weight:800;font-size:12px;border-radius:5px;padding:1px 8px}
.st.ing{background:#fff1d6;color:#9a5b00}.st.done{background:var(--acs);color:var(--ac)}.st.live{background:var(--oks);color:var(--ok)}.st.fail{background:#fde2e6;color:var(--new)}
.dock{position:fixed;left:50%;transform:translateX(-50%);bottom:max(16px,env(safe-area-inset-bottom));background:var(--fg);color:var(--bg);border-radius:999px;padding:8px 8px 8px 18px;display:flex;gap:10px;align-items:center;box-shadow:0 6px 24px rgba(0,0,0,.3);z-index:9;max-width:calc(100vw - 32px);flex-wrap:wrap}
.dock button{border:0;border-radius:999px;padding:8px 16px;font-weight:800;cursor:pointer;background:var(--ac);color:#fff}.dock .ghost{background:transparent;color:var(--bg);border:1px solid currentColor}
.dock .mu2{opacity:.7;font-size:13px}.tnotes{position:fixed;top:84px;right:16px;display:flex;flex-direction:column;gap:8px;z-index:50;max-width:min(380px,calc(100vw - 32px))}.tnote{background:#1f2433;color:#fff;border-radius:12px;padding:12px 16px;font-size:14px;box-shadow:0 8px 24px rgba(0,0,0,.25);animation:tn .3s}@keyframes tn{from{transform:translateY(-8px);opacity:0}}.tnote b{color:#ffd54a}.tnote b:first-child{color:#fff}.livebar{background:#fff4d6;border:1px solid #f0c24a;color:#5a4300;border-radius:10px;padding:8px 14px;font-size:14px;margin:0 0 12px}.livebar a{color:#5c3abe;font-weight:800;margin-left:6px}.toast{position:fixed;top:16px;left:50%;transform:translateX(-50%);background:var(--ok);color:#fff;font-weight:700;border-radius:10px;padding:10px 16px;z-index:10}
</style>'''
JS='''<script>
const QA=(R,s)=>[...(R.matches&&R.matches(s)?[R]:[]),...R.querySelectorAll(s)];
document.addEventListener('click',e=>{const v=e.target.closest&&e.target.closest('video');if(!v||!v.muted)return;v.muted=false;v.classList.add('on');setTimeout(()=>v.play().catch(()=>{}),0)},true);   // 영상 누르면 소리 켜고 재생
document.addEventListener('volumechange',e=>{const v=e.target;if(v.tagName==='VIDEO'&&!v.muted)document.querySelectorAll('video').forEach(o=>{if(o!==v)o.muted=true})},true);   // 소리는 한 번에 하나만
const cs=[...document.querySelectorAll('.bar .chip')],ss=[...document.querySelectorAll('.sub .chip')];
const bDel=R=>QA(R,'.delref').forEach(b=>b.onclick=async e=>{e.preventDefault();e.stopPropagation();
 if(!confirm('이 레퍼런스를 삭제할까요? 올린 파일도 같이 지워져요.'))return;
 let by='';try{by=localStorage.getItem('bokgak-who')||''}catch(e){}
 b.disabled=true;b.textContent='삭제 중…';
 try{const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'delref',id:b.dataset.id,by})})).json();
  if(!r.ok)throw new Error(r.msg);
  const c=b.closest('.c');if(c){c.style.opacity=.4;c.querySelectorAll('input').forEach(i=>i.disabled=true)}
  b.textContent='삭제 요청됨 · 곧 빠져요';if(typeof addLocal==='function')addLocal({job:r.job,type:'delref'})}
 catch(err){alert('삭제 실패: '+err.message);b.disabled=false;b.textContent='삭제'}});bDel(document);
let CURF='all';function show(f){CURF=f;{const Z=document.getElementById('zcre');if(Z){Z.hidden=f!=='zcre';const G=document.querySelector('.g');if(G)G.hidden=f==='zcre';if(f==='zcre'&&window.zOpen)window.zOpen()}}{const L=document.getElementById('lede'),T=document.getElementById('ledes');if(L&&T){const t=JSON.parse(T.textContent);if(!L.dataset.all)L.dataset.all=L.innerHTML;const g=f==='agency'||f.startsWith('ag_')?'agency':f==='slack'||f.startsWith('s_')?'slack':f==='zcre'?'zcre':'';L.innerHTML=g?t[g]:L.dataset.all}}
const Q=qparse();let qn=0;document.querySelectorAll('.g .c').forEach(c=>{const t=c.dataset.f.split(' ');c.hidden=!((f==='star'?!!(window.STARS_&&STARS_[c.dataset.id]):f==='all'?(Q?true:!(t.includes('slack')||t.includes('agency')||t.includes('starx'))):t.includes(f))&&qok(c,Q));if(!c.hidden)qn++});
{const AB=document.getElementById('addBtn');if(AB)AB.style.display=(Q||f==='star')?'none':''}const N=document.getElementById('qN');if(N)N.textContent=Q?(qn?qn+'개 찾음'+(f==='all'?'':' (이 탭 안에서)'):'찾는 레퍼런스가 없어요 — 다른 말로 쳐보세요'):''}
// 전체 = 집행순 레퍼런스(소재공유방은 자기 탭에서만). 검색 중 '전체'는 소재공유방·대행 계정까지 다 찾음
// 검색(2026-11-11): 띄어쓰기로 나눈 단어 전부 들어간 카드(AND), 단어마다 비슷한 말도 같이(OR). 카드 data-s = 문구+이미지 속 글씨
const SYN={'쿨링':['시원','냉감','아이스','청량','쿨링'],'시원':['쿨링','냉감','청량'],'추석':['명절','한가위','추석'],'명절':['추석','한가위','설날','명절'],'설날':['명절','새해','설 선물','설날'],
 '프로모션':['할인','세일','특가','sale','이벤트','증정','1+1','쿠폰','최저가','블프','블랙프라이데이','한정','% 할인','%할인'],'할인':['세일','특가','sale','% off','최저가'],'세일':['할인','특가','sale'],'특가':['할인','세일','sale','최저가'],'이벤트':['증정','event','추첨','쿠폰'],
 '블프':['블랙프라이데이','black friday','블프'],'블랙프라이데이':['블프','black friday'],'샴푸':['shampoo','샴푸'],'탈모':['두피','모발','머리카락','빠짐','hair'],'두피':['탈모','scalp','두피'],
 '여름':['썸머','summer','쿨링','자외선'],'겨울':['윈터','winter','보습','건조'],'선물':['기프트','gift','선물세트'],'후기':['리뷰','review','별점','내돈내산'],'리뷰':['후기','review','별점'],'1+1':['1+1','원플원','1 + 1'],'올영':['올리브영','olive young','oliveyoung'],'올리브영':['올영','olive young']};
function qparse(){const v=((document.getElementById('qIn')||{}).value||'').trim().toLowerCase();if(!v)return null;return v.split(/\\s+/).map(w=>[w].concat(SYN[w]||[]))}
function qok(c,Q){if(!Q)return true;const s=c.dataset.s;if(s===undefined)return false;return Q.every(g=>g.some(w=>s.includes(w)))}
{const qi=document.getElementById('qIn');if(qi){let tm;qi.addEventListener('input',()=>{clearTimeout(tm);tm=setTimeout(()=>show(CURF),150)});qi.addEventListener('keydown',e=>{if(e.key==='Escape'){qi.value='';show(CURF)}})}}
function ap(f){cs.forEach(c=>c.setAttribute('aria-pressed',String(c.dataset.f===f)));document.querySelectorAll('.sub').forEach(d=>d.hidden=d.dataset.g!==f);ss.forEach(x=>x.setAttribute('aria-pressed','false'));show(f)}
cs.forEach(c=>c.onclick=()=>ap(c.dataset.f));
ss.forEach(x=>x.onclick=()=>{const on=x.getAttribute('aria-pressed')!=='true';ss.forEach(y=>y.setAttribute('aria-pressed','false'));x.setAttribute('aria-pressed',String(on));show(on?x.dataset.q:x.parentNode.dataset.g)});</script>'''
BOKGAK_JS='''<script>
const LS='bokgak-sel';let sel=new Set();try{sel=new Set(JSON.parse(localStorage.getItem(LS)||'[]'))}catch(e){}
const dock=document.querySelector('.dock'),cnt=document.getElementById('cnt'),cost=document.getElementById('cost');
function sync(){document.querySelectorAll('.pick input').forEach(i=>{i.checked=sel.has(i.value);i.closest('.c').classList.toggle('sel',i.checked)});
dock.hidden=!sel.size;cnt.textContent=sel.size+'개 선택';const jc=document.getElementById('jc');jc.hidden=!sel.size;jc.textContent=sel.size+'개 선택';const nv=[...sel].filter(id=>META[id]&&META[id].dur).length,won=(sel.size-nv)*250+nv*6500;cost.textContent='약 '+won.toLocaleString()+'원'+(nv?' (영상 '+nv+'개 포함)':'');try{localStorage.setItem(LS,JSON.stringify([...sel]))}catch(e){}}
const AGAIN=new Set();   // 이미 누가 만든 레퍼런스를 확인하고 다시 고른 것
const bPick=R=>QA(R,'.pick input').forEach(i=>i.onchange=()=>{const c=i.closest('.c'),tb=c.dataset.takenBy;
 if(i.checked&&tb){const [who,k]=tb.split('|');if(!confirm(who+'님이 '+(k==='ing'?'지금 만들고 있는':'이미 만든')+' 레퍼런스예요.\\n그래도 내 버전으로 만들까요?')){i.checked=false;return}AGAIN.add(i.value)}
 if(!i.checked)AGAIN.delete(i.value);i.checked?sel.add(i.value):sel.delete(i.value);sync()});bPick(document);
document.getElementById('clr').onclick=()=>{sel.clear();sync()};

// 팀원 제작 알림: 다른 사람이 복각을 시작하면 오른쪽 위 알림(내가 누른 건 제외), 첫 로딩 때 진행 중인 건 알림 없이 띠로만
let SEENJ=null;
function teamNotice(pend,mine){const jobs=pend.filter(p=>p.type==='bokgak'&&p.items&&p.items.length);
 if(SEENJ===null){SEENJ=new Set(jobs.map(p=>p.job))}else jobs.forEach(p=>{if(SEENJ.has(p.job))return;SEENJ.add(p.job);if(mine.has(p.job))return;
  const nm=(p.items[0].page||'레퍼런스').slice(0,30)+(p.items.length>1?' 외 '+(p.items.length-1)+'개':'');
  const t=document.createElement('div');t.className='tnote';t.innerHTML='<b>🔔 '+(p.by||'팀원')+'님</b>이 <b>'+nm.replace(/</g,'&lt;')+'</b> 소재 제작을 시작했어요';document.getElementById('tnotes').append(t);setTimeout(()=>t.remove(),9000)});
 const lv=document.getElementById('livebar');if(!lv)return;
 lv.innerHTML=jobs.length?'<b>지금 제작 중</b> — '+jobs.map(p=>(p.by||'팀원')+': '+(p.items[0].page||'레퍼런스').slice(0,24).replace(/</g,'&lt;')+(p.items.length>1?' 외 '+(p.items.length-1)+'개':'')).join(' · ')+' <a href="review.html">진행 상황 보기 →</a>':'';lv.hidden=!jobs.length}
function toast(m){const t=document.createElement('div');t.className='toast';t.textContent=m;document.body.append(t);setTimeout(()=>t.remove(),4000)}
const LBL={ing:'복각중',done:'완료',live:'완료 · 세팅됨',fail:'복각 실패'};
function mark(id,k,d,by,job){const c=document.querySelector('.c[data-id="'+id+'"]');if(!c)return;const el=c.querySelector('[data-st]');
 el.className='st '+k;el.textContent=k==='ing'?'복각중'+(by?' · '+by:''):(k==='fail'?LBL.fail:(d?d+' ':'')+(by?by+' ':'')+LBL[k]);
 if(k==='ing'&&job){const x=document.createElement('button');x.type='button';x.className='cxs';x.textContent='취소';x.dataset.job=job;el.append(' ',x)}
 const taken=k==='ing'||k==='done'||k==='live',inp=c.querySelector('.pick input');
 let ov=c.querySelector('.taken');if(taken){if(!ov){ov=document.createElement('div');ov.className='taken';c.querySelector('.im').append(ov)}   // 카드 사진 위 큰 표시
  ov.className='taken '+k;ov.innerHTML=`<b>${by?by+'님':'팀원'}</b><span>${k==='ing'?'제작중…':k==='live'?'제작완료 · 세팅완료':'제작완료'}</span>${d&&k!=='ing'?'<small>'+d+'</small>':''}`}else if(ov)ov.remove();if(inp){inp.disabled=false;c.dataset.takenBy=taken?((by||'팀원')+'|'+k):'';c.querySelector('.pick').title=taken?'이미 만든 레퍼런스예요 — 체크하면 내 버전으로 다시 만들 수 있어요':''}}
document.addEventListener('click',async e=>{const b=e.target.closest('.cxs');if(!b)return;e.preventDefault();if(!confirm('이 복각 요청을 취소할까요?\\n이미 만들고 있는 소재는 그것까지만 끝나요.'))return;b.disabled=true;b.textContent='취소 중…';
 try{const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'cancel',job:b.dataset.job})})).json();if(!r.ok)throw new Error(r.msg);b.textContent='취소됨';LOCAL=LOCAL.filter(l=>l.job!==b.dataset.job);setTimeout(kick,1500)}catch(err){b.textContent='실패';b.disabled=false}});
let REQ={};try{REQ=JSON.parse(localStorage.getItem('bokgak-req')||'{}')}catch(e){}
let LOCAL=[],ACTIVE=false,RST=null;   // LOCAL = 이 탭에서 방금 보낸 요청(서버 목록에 뜨기 전에도 바로 표시), RST = refstatus.json(검수 쪽 배포 때만 다시 받음)
function jt(j){const m=/^([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2})-([0-9]{2})-([0-9]{2})-([0-9]{3})Z$/.exec(j||'');return m?Date.parse(m[1]+'T'+m[2]+':'+m[3]+':'+m[4]+'.'+m[5]+'Z'):0}
function mergeL(pend){const have=new Set(pend.map(p=>p.job));LOCAL=LOCAL.filter(l=>Date.now()-l.at<(have.has(l.job)?20000:360000));return pend.concat(LOCAL.filter(l=>!have.has(l.job)))}
function addLocal(o){o.at=Date.now();LOCAL.push(o);kick()}
async function refresh(){let st={},pend=[],cur=null;
 if(!RST)try{RST=await (await fetch('refstatus.json?'+Date.now(),{cache:'no-store'})).json()}catch(e){}st=RST||{};
 try{const r=await (await fetch('api/bokgak')).json();pend=r.pending||[];cur=r.status}catch(e){return}
 pend=mergeL(pend);ACTIVE=pend.length>0||!!(cur&&cur.state==='working');
 teamNotice(pend,new Set(Object.keys(REQ)));
 document.getElementById('addPend').innerHTML=pend.filter(p=>p.type==='addref').map(p=>`<div class="pendc"><b>${(p.name||'레퍼런스').replace(/</g,'&lt;')}</b><span>${p.kind==='video'?'영상':'이미지'} 추가 중… (3~5분)</span></div>`).join('');
 const busy=new Map();pend.forEach(p=>{(REQ[p.job]||[]).forEach(id=>busy.set(id,p));(p.items||[]).forEach(it=>busy.set(String(it.id),p))});if(cur&&cur.state==='working')(cur.ids||[]).forEach(id=>{if(!busy.has(id))busy.set(id,{job:cur.job})});
 Object.keys(REQ).forEach(j=>{if(!pend.some(p=>p.job===j)&&!(cur&&cur.state==='working'&&cur.job===j)&&Date.now()-jt(j)>30000)delete REQ[j]});try{localStorage.setItem('bokgak-req',JSON.stringify(REQ))}catch(e){}
 document.querySelectorAll('.c[data-id]').forEach(c=>{const id=c.dataset.id,o=st[id]||{},s=typeof o==='string'?o:o.s,d=o.d;
  const by=o.by||'';if(busy.has(id)){const p=busy.get(id);mark(id,'ing',null,p.by,p.job)}else if(s==='세팅완료')mark(id,'live',d,by);else if(s==='제작완료')mark(id,'done',d,by);else{if(s==='실패')mark(id,'fail');else{const e=c.querySelector('[data-st]');e.className='st';e.textContent=''}const inp=c.querySelector('.pick input');if(inp)inp.disabled=false}});}
const lDlg=document.getElementById('lDlg'),lSel=document.getElementById('lSel');
function fillB(se,after){se.innerHTML=Object.keys(BRANDS).map(k=>`<option value="${k}">${BRANDS[k].label}</option>`).join('');try{const b=localStorage.getItem('bokgak-brand');if(b&&BRANDS[b])se.value=b}catch(e){}
 se.onchange=()=>{curB=se.value;PRODUCTS=BRANDS[curB].landings||[];try{localStorage.setItem('bokgak-brand',curB)}catch(e){};after&&after()};curB=se.value;PRODUCTS=BRANDS[curB].landings||[]}   // 2026-11-10 브랜드(SOOO·FnL·칸디데) 고르기
function saveL(u){const mine=myL().filter(x=>x!==u);mine.unshift(u);try{localStorage.setItem('my-landings'+(curB==='SOOO'?'':'-'+curB),JSON.stringify(mine.slice(0,10)))}catch(e){}}
function askL(se,prev){const u=(prompt('랜딩 링크를 붙여넣어 주세요 (https:// 로 시작)')||'').trim();if(!/^https:[/][/][^ ]{4,}$/.test(u)){if(u)alert('https:// 로 시작하는 링크를 넣어주세요');se.value=prev;return false}
 let o=[...se.options].find(x=>x.value===u);if(!o){o=new Option(u.length>70?u.slice(0,70)+'…':u,u);se.add(o,se.options.length-1)}se.value=u;saveL(u);return true}   // 랜딩 입력은 이 목록 하나뿐 — '＋ 직접 링크 입력' 고르면 링크 받아 목록에 넣고 선택
function myL(){try{return JSON.parse(localStorage.getItem('my-landings'+(curB==='SOOO'?'':'-'+curB))||'[]')}catch(e){return[]}}
function fillL(){const mine=myL();lSel.innerHTML=PRODUCTS.map((p,i)=>`<option value="${p.url}">${i?'':'[기본] '}${BRANDS[curB].shop||'자사몰'} · ${p.title.split('|').pop().trim()}${p.price?' · '+(+p.price).toLocaleString()+'원':''}</option>`).join('')
 +(mine.length?'<optgroup label="직접 넣었던 링크">'+mine.map(u=>`<option value="${u.replace(/"/g,'&quot;')}">${u.length>70?u.slice(0,70)+'…':u}</option>`).join('')+'</optgroup>':'')+'<option value="__new">＋ 직접 링크 입력</option>';
 if(!PRODUCTS.length&&curB==='SOOO')lSel.insertAdjacentHTML('afterbegin','<option value="https://sooo.kr/product/detail.html?product_no=108&cate_no=1&display_group=2">[기본] 자사몰 · 스칼프처 샴푸 1+1</option>');lSel.selectedIndex=0;showL()}
let lPrev='';function showL(){if(lSel.value==='__new')askL(lSel,lPrev);lPrev=lSel.value;const nw=false;const p=PRODUCTS.find(x=>x.url===lSel.value);
 document.getElementById('lInfo').innerHTML=p?`<img src="${p.image}" alt=""><div><b>${p.title.split('|').pop().trim()}</b><br>${p.price?(+p.price).toLocaleString()+'원 · ':''}${p===PRODUCTS[0]?'기본 랜딩 ('+BRANDS[curB].label+' 근거·제품 사진 그대로)':'이 상품 상세페이지를 읽고 그 상품으로 만들어요'}</div>`:(nw?'':'<div>이 링크의 상품 정보를 읽고 그 상품으로 만들어요</div>');
 const nv=[...sel].filter(id=>META[id]&&META[id].dur).length;document.getElementById('lGo').textContent=sel.size+'개 복각하기';document.getElementById('lMsg').textContent='예상 비용 약 '+((sel.size-nv)*250+nv*6500).toLocaleString()+'원'+(nv?' · 영상 '+nv+'개는 드라이브 에셋으로 편집한 영상으로 나와요(레퍼런스 장면을 나노바나나+Veo 로 재현, 1편 약 6,500원)':'')}
lSel.onchange=showL;
document.getElementById('go').onclick=()=>{if(!sel.size)return;document.getElementById('who').value='';uFiles.value='';document.getElementById('uPrev').innerHTML='';document.getElementById('uNote').value='';document.getElementById('lCmd').value='';fillB(document.getElementById('bSel'),fillL);fillL();document.getElementById('lMsg').textContent='';lDlg.showModal()};
const uFiles=document.getElementById('uFiles');
uFiles.onchange=()=>{const fs=[...uFiles.files].slice(0,10),pv=document.getElementById('uPrev');if(uFiles.files.length>10)alert('에셋은 10개까지만 올릴 수 있어요(앞의 10개만 씀)');
 pv.innerHTML=fs.map((f,i)=>{const u=URL.createObjectURL(f);return `<figure><b>${i+1}</b>${f.type.startsWith('video')?`<video src="${u}" muted autoplay loop playsinline></video>`:f.type.startsWith('image')?`<img src="${u}" alt="">`:`<span class="udoc">📄 ${(f.name.split('.').pop()||'').toUpperCase()}<br>기획안·문서</span>`}<figcaption>${f.name.replace(/</g,'&lt;').slice(0,18)}</figcaption></figure>`}).join('')};
async function upFile(f,msg){   // 2.5MB 조각으로 올리기(서버 한 번에 받는 크기 제한)
 const up=(self.crypto&&crypto.randomUUID?crypto.randomUUID().replace(/-/g,''):Date.now().toString(36)+Math.random().toString(36).slice(2)).slice(0,24),CH=2.5*1024*1024,n=Math.max(1,Math.ceil(f.size/CH));
 for(let i=0;i<n;i++){msg(Math.round(i/n*100));const data=await new Promise((ok,no)=>{const fr=new FileReader();fr.onload=()=>ok(fr.result.split(',')[1]);fr.onerror=no;fr.readAsDataURL(f.slice(i*CH,(i+1)*CH))});
  const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'chunk',up,i,data})})).json();if(!r.ok)throw new Error(r.msg)}
 return {up,n,ext:(f.name.split('.').pop()||'').toLowerCase(),kind:f.type.startsWith('video')?'video':f.type.startsWith('image')?'image':(f.type.startsWith('audio')||/\.(mp3|wav|m4a|aac)$/i.test(f.name))?'audio':'doc',name:f.name.slice(0,60)}}
document.getElementById('lGo').onclick=async e=>{e.preventDefault();const ids=[...sel];let landing=lSel.value;const m=document.getElementById('lMsg');const by=document.getElementById('who').value;
 if(!by){m.textContent='이름을 골라주세요';document.getElementById('who').focus();return}try{localStorage.setItem('bokgak-who',by)}catch(e){}
 if(!landing||landing==='__new'){m.textContent='랜딩 페이지를 골라주세요';return}
 const b=e.target;b.disabled=true;b.textContent='요청 중…';
 const assets=[];try{const fs=[...uFiles.files].slice(0,10);
  for(const [k,f] of fs.entries()){if(f.size>150*1024*1024)throw new Error((k+1)+'번 파일이 150MB 넘어요');assets.push(await upFile(f,p=>m.textContent=`에셋 올리는 중… ${k+1}/${fs.length} (${p}%)`))}}
 catch(err){m.textContent='에셋 올리기 실패: '+err.message;b.disabled=false;b.textContent=ids.length+'개 복각하기';return}
 try{const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({by,brand:curB,landing,assets,asset_note:document.getElementById('uNote').value.trim(),command:document.getElementById('lCmd').value.trim(),items:ids.map(id=>({id,...META[id],...(AGAIN.has(id)?{again:true}:{})}))})})).json();
  if(!r.ok)throw new Error(r.msg);REQ[r.job]=ids;addLocal({job:r.job,type:'bokgak',by,items:ids.map(id=>({id,page:(META[id]||{}).page||''}))});localStorage.setItem('bokgak-req',JSON.stringify(REQ));ids.forEach(id=>mark(id,'ing'));sel.clear();sync();b.textContent='검수 페이지로 이동…';const kd=new Date(Date.now()+9*3600e3).toISOString().slice(0,10);setTimeout(()=>location.href='review.html?p='+encodeURIComponent(by)+'&d='+kd+'&just='+r.job,600)}
 catch(err){m.textContent='요청 실패: '+err.message;b.disabled=false;b.textContent=ids.length+'개 복각하기'}};
const addDlg=document.getElementById('addDlg'),aFile=document.getElementById('aFile');
function fillAL(){const ls=document.getElementById('aLSel');ls.innerHTML=PRODUCTS.map((p,i)=>`<option value="${p.url}">${i?'':'[기본] '}${p.title.split('|').pop().trim()}${p.price?' · '+(+p.price).toLocaleString()+'원':''}</option>`).join('')||'<option value="">[기본] 자사몰 대표 상품</option>';ls.insertAdjacentHTML('beforeend','<option value="__new">＋ 직접 링크 입력</option>');ls.selectedIndex=0;ls.dataset.prev=ls.value;ls.onchange=()=>{if(ls.value==='__new')askL(ls,ls.dataset.prev);ls.dataset.prev=ls.value}}
document.getElementById('addBtn').onclick=()=>{fillB(document.getElementById('aBSel'),fillAL);fillAL();document.getElementById('aCmd').value='';document.getElementById('aWho').value='';document.getElementById('aMsg').textContent='';addDlg.showModal()};
document.querySelectorAll('input[name=ak]').forEach(r=>r.onchange=()=>{aFile.accept=r.value==='video'?'video/*':'image/*';aFile.value='';document.getElementById('aPrev').innerHTML=''});
const raFiles=document.getElementById('raFiles');
raFiles.onchange=()=>{const fs=[...raFiles.files].slice(0,10);document.getElementById('raPrev').innerHTML=fs.map((f,i)=>{const u=URL.createObjectURL(f);return `<figure><b>${i+1}</b>${f.type.startsWith('video')?`<video src="${u}" muted autoplay loop playsinline></video>`:f.type.startsWith('image')?`<img src="${u}" alt="">`:`<span class="udoc">📄 ${(f.name.split('.').pop()||'').toUpperCase()}<br>기획안·문서</span>`}<figcaption>${f.name.replace(/</g,'&lt;').slice(0,18)}</figcaption></figure>`}).join('')};
aFile.onchange=()=>{const f=aFile.files[0],pv=document.getElementById('aPrev');pv.innerHTML='';if(!f)return;const u=URL.createObjectURL(f);
 pv.innerHTML=f.type.startsWith('video')?`<video src="${u}" muted autoplay loop playsinline></video>`:`<img src="${u}" alt="">`;const nm=document.getElementById('aNm');if(!nm.value)nm.value=f.name.replace(/\.[^.]+$/,'')};
document.getElementById('aGoB').onclick=()=>{window._GO=true;document.getElementById('aGo').click()};
document.getElementById('aGo').onclick=async e=>{e.preventDefault();const go=!!window._GO;window._GO=false;const f=aFile.files[0],m=document.getElementById('aMsg'),b=e.target,by=document.getElementById('aWho').value;if(!by){m.textContent='이름을 골라주세요';return}if(!f){m.textContent='파일을 골라주세요';return}
 const kind=document.querySelector('input[name=ak]:checked').value,ext=(f.name.split('.').pop()||'').toLowerCase();
 if(kind==='image'&&!f.type.startsWith('image')||kind==='video'&&!f.type.startsWith('video')){m.textContent=kind==='image'?'이미지 파일을 골라주세요':'영상 파일을 골라주세요';return}
 if(f.size>150*1024*1024){m.textContent='150MB 이하 파일만 올릴 수 있어요';return}
 b.disabled=true;const up=(self.crypto&&crypto.randomUUID?crypto.randomUUID().replace(/-/g,''):Date.now().toString(36)+Math.random().toString(36).slice(2)).slice(0,24),CH=2.5*1024*1024,n=Math.ceil(f.size/CH);
 try{for(let i=0;i<n;i++){m.textContent=`올리는 중… ${Math.round(i/n*100)}%`;const data=await new Promise((ok,no)=>{const fr=new FileReader();fr.onload=()=>ok(fr.result.split(',')[1]);fr.onerror=no;fr.readAsDataURL(f.slice(i*CH,(i+1)*CH))});
   const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'chunk',up,i,data})})).json();if(!r.ok)throw new Error(r.msg)}
  const assets=[];for(const [k,af] of [...raFiles.files].slice(0,10).entries()){if(af.size>150*1024*1024)throw new Error('에셋 '+(k+1)+'번이 150MB 넘어요');assets.push(await upFile(af,p=>m.textContent=`에셋 올리는 중… ${k+1}/${Math.min(10,raFiles.files.length)} (${p}%)`))}
  const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'addref',by,go,brand:curB,landing:go?(document.getElementById('aLSel').value==='__new'?'':document.getElementById('aLSel').value):'',command:go?document.getElementById('aCmd').value.trim():'',assets,asset_note:document.getElementById('raNote').value.trim(),up,n,kind,ext,name:document.getElementById('aNm').value,memo:document.getElementById('aMemo').value,src:document.getElementById('aSrc').value})})).json();if(!r.ok)throw new Error(r.msg);addLocal({job:r.job,type:'addref',by,name:document.getElementById('aNm').value,kind,go});
  if(go){const kd=new Date(Date.now()+9*3600e3).toISOString().slice(0,10);try{localStorage.setItem('bokgak-who',by)}catch(e){}location.href='review.html?p='+encodeURIComponent(by)+'&d='+kd+'&just='+r.job;return}
  addDlg.close();['aNm','aMemo','aSrc','raNote'].forEach(id=>document.getElementById(id).value='');raFiles.value='';document.getElementById('raPrev').innerHTML='';aFile.value='';document.getElementById('aPrev').innerHTML='';toast('올렸어요! 3~5분 안에 카드로 붙어요 (새로고침 안 해도 자동으로 떠요)')}
 catch(err){m.textContent='실패: '+err.message}b.disabled=false};
const io=new IntersectionObserver(es=>es.forEach(e=>{const v=e.target;if(e.isIntersecting){if(!v.src)v.src=v.dataset.src;v.play().then(()=>v.classList.add('on')).catch(()=>{})}else v.pause()}),{rootMargin:'100px'});
const bVid=R=>QA(R,'video.pv').forEach(v=>{v.onerror=()=>v.remove();io.observe(v)});bVid(document);   // 영상 주소가 만료됐으면 사진 그대로
// ── 새로고침 없이 반영(2026-10-21) ──
// api 확인: 진행 중이면 10초, 없으면 60초(10분 넘게 손 안 대면 5분), 탭 숨기면 멈춤. 배포 확인은 ver.json(정적·Blob 안 씀) 30초.
// 레퍼런스 페이지가 다시 배포되면(직접 추가·삭제) 카드만 추가·제거, 검수 쪽이 배포되면 태그(refstatus.json)만 다시.
let VER=null,LASTAPI=0,LASTACT=Date.now(),SRT=0;
['pointerdown','keydown','scroll','mousemove'].forEach(e=>addEventListener(e,()=>{LASTACT=Date.now()},{passive:true}));
function busyNow(){return ACTIVE||LOCAL.length>0||Object.keys(REQ).length>0}
async function verCheck(){try{const v=await (await fetch('ver.json?_='+Date.now(),{cache:'no-store'})).json();if(VER===null){VER=v;return}
 if(v.review!==VER.review){RST=null;LASTAPI=0}if(v.index!==VER.index)softRefresh();VER=v}catch(e){}}
async function tick(){clearTimeout(window._pt);if(document.hidden)return;
 await verCheck();
 if(busyNow()||!RST||Date.now()-LASTAPI>(Date.now()-LASTACT>600000?300000:60000)){LASTAPI=Date.now();await refresh()}
 clearTimeout(window._pt);if(!document.hidden)window._pt=setTimeout(tick,busyNow()?10000:30000)}
function kick(){clearTimeout(window._pt);window._pt=setTimeout(tick,400)}
document.addEventListener('visibilitychange',()=>{if(!document.hidden)kick()});
async function softRefresh(){clearTimeout(SRT);
 if([...document.querySelectorAll('dialog')].some(d=>d.open)){SRT=setTimeout(softRefresh,3000);return}
 let doc;try{const r=await fetch('index.html?_='+Date.now(),{cache:'no-store'});if(!r.ok)throw 0;doc=new DOMParser().parseFromString(await r.text(),'text/html')}catch(e){SRT=setTimeout(softRefresh,20000);return}
 const G=document.querySelector('.g'),NG=doc.querySelector('.g');if(!G||!NG)return;
 try{const cm=doc.getElementById('cmeta');if(cm)Object.assign(META,JSON.parse(cm.textContent))}catch(e){}
 const cur=new Map([...G.querySelectorAll(':scope > article.c[data-id]')].map(c=>[c.dataset.id,c])),nids=new Set();let add=0,del=0,next=null;
 const list=[...NG.querySelectorAll(':scope > article.c[data-id]')];
 for(let i=list.length-1;i>=0;i--){const n=list[i],id=n.dataset.id;nids.add(id);const o=cur.get(id);if(o){next=o;continue}
  const c=document.importNode(n,true);G.insertBefore(c,next);bPick(c);bVid(c);if(typeof bDel==='function')bDel(c);next=c;add++}
 cur.forEach((o,id)=>{if(!nids.has(id)){o.remove();del++}});
 show(CURF);sync();RST=null;LASTAPI=0;kick();
 if(add||del)toast(add?'새 레퍼런스 '+add+'개가 카드로 붙었어요':'삭제한 레퍼런스를 뺐어요')}
show('all');sync();tick();
</script>'''
NAV='<nav><a href="index.html">광고 라이브러리 레퍼런스</a><a href="agency.html">대행 계정 고효율 소재</a><a href="review.html">복각 소재 검수</a></nav>'
# 직접 추가한 레퍼런스(맨 앞) · 복각하기 팝업 랜딩 목록
CUSTOM=json.load(open(R+'data/custom_refs.json')) if os.path.exists(R+'data/custom_refs.json') else []
PRODUCTS=json.load(open(R+'data/products.json')) if os.path.exists(R+'data/products.json') else []
_BR=json.load(open(R+'data/brands.json')) if os.path.exists(R+'data/brands.json') else {'SOOO':{'label':'SOOO'}}   # 2026-11-10 브랜드별 랜딩
BRANDS_UI={k:{'label':v.get('label',k),'shop':v.get('shop',''),'landings':[dict(url=l['url'],title=l['title'],price=l.get('price',''),image=l.get('image','')) for l in (v.get('landings') if isinstance(v.get('landings'),list) else [])]} for k,v in _BR.items()}
ccards=[]
for x in CUSTOM:
    k='이미지' if x['kind']=='image' else '영상 %s'%x.get('dur','')
    ccards.append(f'''<article class="c" data-id="{x['id']}" data-f="custom {'img' if x['kind']=='image' else 'vid'}"><label class="pick"><input type="checkbox" value="{x['id']}"> 복각</label><div class="im"><img src="m/L{x['id']}.jpg" loading="lazy" alt="">{f'<video class="pv" data-src="m/L{x["id"]}.mp4" muted loop playsinline controls preload="none"></video>' if x['kind']=='video' else ''}<span class="d">직접 추가</span></div>
<div class="b"><div class="st" data-st></div><div class="p">{esc(x['name'])}<button type="button" class="delref" data-id="{x['id']}" title="이 레퍼런스 삭제">삭제</button></div><div class="m">{esc(x['added'])} 추가</div><div class="tg"><span>{k}</span><span class="e">직접 추가</span>{f'<span>참고 파일 {len(x["assets"])}개</span>' if x.get('assets') else ''}</div><div class="t">{esc(x.get('memo',''))}</div>
{f'<a class="l" href="{esc(x["src"])}" target="_blank" rel="noopener">원본 보기 ↗</a>' if x.get('src') else ''}</div></article>''')
# 슬랙 #소재공유방 (scripts/slack_import.py 가 data/slack_refs.json 생성)
AGTXT='<b>고효율 기준</b> · 데이터 기간: <b>전체 기간</b>(최근 30·60일이 아니라 메타가 주는 최대 약 3년, 집행 종료·중지된 광고 포함) · 광고마다 그 기간 <b>누적 성과</b>로 판단 · ① 지출 5만원 이상(칸디데 30만·FnL 10만, 달러 계정 $40) ② ROAS가 <b>그 광고계정 평균 ROAS 이상</b> ③ 구매 수가 <b>계정 안 광고들의 중앙값 이상</b>(최소 5건) · 구매·매출은 메타 기준(기본 기여: 클릭 7일·조회 1일), FnL·협업광고는 공유 항목 구매 · 큰 계정은 매출 큰 순 150개까지 · 정렬: 실제 지출이 난 날 수가 많은 순 · 매일 아침 갱신'
AGNOTE='<p class="lede" style="margin-top:-8px">'+AGTXT+'</p>'
SLACK=json.load(open(R+'data/slack_refs.json')) if os.path.exists(R+'data/slack_refs.json') else []
SLACK=[x for x in SLACK if os.path.exists(M+f"L{x['id']}.jpg")]
for x in SLACK: x['account']=re.sub(r' on Instagram.*$','',x.get('account',''),flags=re.S).strip()[:40]
SWHO=['화영','다운','도현','근형','형태','다솔']
scards=[]
for x in SLACK:
    who=x['by'] if x['by'] in SWHO else '기타'; vid=x['kind']=='video' and os.path.exists(M+f"L{x['id']}.mp4")
    scards.append(f'''<article class="c" data-id="{x['id']}" data-f="slack s_{who}"><label class="pick"><input type="checkbox" value="{x['id']}"> 복각</label><div class="im"><img src="m/L{x['id']}.jpg" loading="lazy" alt="">{f'<video class="pv" data-src="m/L{x["id"]}.mp4" muted loop playsinline controls preload="none"></video>' if vid else ''}<span class="d">소재공유방</span></div>
<div class="b"><div class="st" data-st></div><div class="p">{esc(x['account'] or '인스타 소재')}</div><div class="m">{esc(x['by'])} 공유 · {esc(x['at'][5:16])}</div><div class="tg"><span>{'영상 '+x['dur'] if vid else '이미지'}</span>{f'<span>♥ {esc(x["likes"])}</span>' if x.get('likes') else ''}<span class="e">소재공유방</span></div>
{f'<div class="tgs">'+''.join(f'<span>{esc(t)}</span>' for t in x.get('tags',[]))+'</div>' if x.get('tags') else ''}
<div class="hk"><p><b>【후킹 포인트】</b> {esc(x.get('hook') or x.get('note',''))}{' <i>(AI 정리)</i>' if x.get('hook_ai') else ''}</p>{f'<p><b>【응용 아이디어】</b> {esc(x["idea"])}{" <i>(AI 제안)</i>" if x.get("idea_ai") else ""}</p>' if x.get('idea') else ''}</div>
<details class="more"><summary>자세히</summary>{f'<p><b>【분류】</b> <i>(AI 정리)</i> {esc(x["flow"])}</p>' if x.get('flow') else ''}{'<p><b>【스레드 답글】</b><br>'+'<br>'.join(esc(t) for t in x['thread'])+'</p>' if x.get('thread') else ''}
<p><b>【출처】</b> 슬랙 #소재공유방 · {esc(x['by'])} · {esc(x['at'][5:10].replace('-','/'))}{' · 반응 '+esc(x['react']) if x.get('react') else ''}</p>{f'<p><b>【원문 캡션】</b> {esc(x["caption"])}</p>' if x.get('caption') else ''}</details>
<a class="l" href="{esc(x['link'])}" target="_blank" rel="noopener">인스타 원본 ↗</a></div></article>''')
acards=[]; AGACC=[]; tok=lambda x: re.sub(r'\s+','_',x)
for x in ag:
    if not x.get('imgk'): continue
    if x['acct'] not in AGACC: AGACC.append(x['acct'])
    fm=fmt_ag(x); vid=bool(x.get('vsrc')); mult=x['roas']/x['acct_roas'] if x.get('acct_roas') else 0
    acards.append(f'''<article class="c" data-id="{x['id']}" data-f="agency ag_{tok(x['acct'])}"><label class="pick"><input type="checkbox" value="{x['id']}"> 복각</label><div class="im"><img src="m/{x['imgk']}.jpg" loading="lazy" alt="">{f'<video class="pv" data-src="{esc(x["vsrc"])}" muted loop playsinline controls preload="none"></video>' if vid else ''}<span class="d">{x['days']}일 집행</span></div>
<div class="b"><div class="st" data-st></div><div class="p">{esc(x['acct'])}</div><div class="m" style="word-break:break-all">{esc(x['name'][:60])}</div><div class="m">ROAS {x['roas']:.2f} (계정 평균 ×{mult:.1f}) · 구매 {x['pur']:,.0f}</div>
<div class="tg"><span>{fm}</span><span class="e">대행 고효율</span>{'<span>집행 중</span>' if x.get('status')=='ACTIVE' else ''}</div><div class="t">{esc(x.get('body',''))}</div></div></article>''')
AMETA={x['id']:dict(page=x['acct']+' 고효율 광고',t=('실제 성과: ROAS %.2f, 구매 %d, %d일 집행 / 광고명: %s / 본문: %s'%(x['roas'],x['pur'],x['days'],x['name'],x.get('body','')))[:600],dur=('0:%02d'%min(59,int(x['vlen'])) if x.get('vlen') else ('0:10' if x.get('vsrc') else '')),days=x['days'],poster=x.get('img') or '',imgs=[],video=x.get('vsrc') or '') for x in ag if x.get('imgk')}
CMETA={x['id']:dict(page=x['name'],t=x.get('memo',''),dur=x.get('dur',''),days='직접 추가',poster='',imgs=[]) for x in CUSTOM}
CMETA.update(AMETA)
CMETA.update({x['id']:dict(page=x['account'] or '인스타 소재',t=('팀원 후킹 포인트: '+(x.get('hook') or x.get('note',''))+' / 응용 아이디어(이 방향으로 복각): '+x.get('idea','')+' / 원문 캡션: '+x.get('caption',''))[:600],dur=x['dur'] if x['kind']=='video' else '',days='소재공유방',poster='',imgs=[],video='') for x in SLACK})
# index
HAIR_KW={'샴푸','탈모','두피'}; tok=lambda x: re.sub(r'\s+','_',x)
LBL={q['q']:(q.get('label') or q['q']) for q in cfg['queries']}
cards=[]
for c in lib:
    d=secs(c['dur']); kind='이미지' if not c['dur'] else '영상 %s'%c['dur']
    easy=(not c['dur']) or (d is not None and d<=20)
    qs=QS.get(c['id'],[c['q']]); gs=[]
    for k in qs:
        g=QC.get(k,{}).get('group','')
        if g and g not in gs: gs.append(g)
        if k in HAIR_KW and '헤어·두피·탈모' not in gs: gs.append('헤어·두피·탈모')
    c['gs']=gs; c['qs']=qs
    f=['easy' if easy else '', 'new' if c['new'] else '', 'img' if not c['dur'] else 'vid']+['g_'+tok(g) for g in gs]+['q_'+tok(k) for k in qs]
    page=esc(c['t'].split(' 광고 ')[0][:40])
    cards.append(f'''<article class="c" data-id="{c['id']}" data-f="{' '.join(x for x in f if x)}"><label class="pick"><input type="checkbox" value="{c['id']}"> 복각</label><div class="im">{f'<img src="m/{c["img"]}.jpg" loading="lazy" alt="">' if c['img'] else ''}{f'<video class="pv" data-src="{esc(c["video"])}" muted loop playsinline controls preload="none"></video>' if c.get('video') and c['dur'] else ''}<span class="d">{c['days']}일째</span>{'<span class="nw">NEW</span>' if c['new'] else ''}</div>
<div class="b"><div class="st" data-st></div><div class="p">{page}</div><div class="mt">{c['start']} 시작 · 노출순 {c['rank']}위({esc(c['q'])}){' · 광고 %d개'%c['multi'] if c['multi']>1 else ''}</div>
<div class="tg"><span>{kind}</span>{'<span class="e">쉬움</span>' if easy else ''}{''.join(f'<span>{esc(LBL.get(k,k))}</span>' for k in c['qs'][:3])}</div><div class="t">{esc(c['t'][len(page):][:220])}</div>
<a class="l" href="https://www.facebook.com/ads/library/?id={c['id']}" target="_blank" rel="noopener">원본 보기 ↗</a></div></article>''')
GO=[]
for q in cfg['queries']:
    g=q.get('group','')
    if g and g not in GO: GO.append(g)
from collections import Counter
gc=Counter(g for c in lib for g in c['gs']); qc=Counter(k for c in lib for k in c['qs'])
LEDES_J=json.dumps(dict(zcre='ZCRE 로 이미지·영상·오디오를 바로 만들어요. 견적(무료)을 보고 승인해야만 크레딧을 써요. 결과는 여기 쌓이고 받을 수 있어요.',agency=AGTXT+f' · 마지막 갱신 {TS} · {len(acards)}건',slack=f'슬랙 #소재공유방에 공유된 링크(인스타·메타 광고 라이브러리)를 하루 한 번(아침) 자동으로 가져오고, 바로 보려면 새로고침 버튼을 누르세요. 링크 하나가 카드 하나 · {len(SLACK)}건 '+SS_BTN),ensure_ascii=False).replace('</','<\\/')
SUB=('<div class="sub" data-g="agency" hidden>'+''.join(f'<button class="chip sm" data-q="ag_{esc(tok(a))}" aria-pressed="false">{esc(a)} <small>{sum(1 for x in ag if x["acct"]==a and x.get("imgk"))}</small></button>' for a in AGACC)+'</div>' if acards else '')+('<div class="sub" data-g="slack" hidden>'+''.join(f'<button class="chip sm" data-q="s_{w}" aria-pressed="false">{w} <small>{n}</small></button>' for w in SWHO+['기타'] for n in [sum(1 for x in SLACK if (x['by'] if x['by'] in SWHO else '기타')==w)] if n)+'</div>' if SLACK else '')+''.join(f'<div class="sub" data-g="g_{esc(tok(g))}" hidden>'+''.join(f'<button class="chip sm" data-q="q_{esc(tok(q["q"]))}" aria-pressed="false">{esc(LBL[q["q"]])} <small>{qc[q["q"]]}</small></button>' for q in cfg['queries'] if q.get('group')==g and qc[q['q']])+'</div>' for g in GO)
CMETA_J=json.dumps(CMETA,ensure_ascii=False).replace('</','<\\/')
idx=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SOOO 소재 제작</title>{CSS}</head><body><div class="w">
<div class="tnotes" id="tnotes" aria-live="polite"></div><div class="hd"><h1>SOOO 소재 제작</h1><div class="hdr"><a class="jump" href="review.html">복각 소재 검수 →<span id="jc" hidden style="display:inline-block;margin-left:8px;min-width:22px;padding:0 7px;border-radius:999px;background:#fff;color:#3b5bdb;font-size:13px;line-height:22px;text-align:center">0</span></a><button type="button" class="zbtn" id="zOpenBtn" aria-pressed="false"><b>✦ ZCRE 로 바로 만들기</b><small>이미지·영상·오디오 생성 · 견적 보고 승인</small></button></div></div>{NAV}<script type="application/json" id="ledes">{LEDES_J}</script><p class="lede" id="lede">메타 광고 라이브러리에서 매일 아침 다시 수집합니다. 지금 게재 중이고 노출이 적지 않은 광고만, 오래 게재된 순서로 보여줍니다(성과는 공개되지 않아 게재 기간·노출 순위로 추정). 마지막 갱신 {TS} · {len(lib)}건 · 오늘 새로 발견 {sum(c['new'] for c in lib)}건</p>
<div class="livebar" id="livebar" hidden></div><div class="bar"><button class="chip" data-f="all" aria-pressed="true">전체</button>{f'<button class="chip" data-f="slack" aria-pressed="false">소재공유방 <small>{len(SLACK)}</small></button>' if SLACK else ''}{f'<button class="chip" data-f="agency" aria-pressed="false">대행 계정 고효율 <small>{len(acards)}</small></button>' if acards else ''}<button class="chip" data-f="easy" aria-pressed="false">쉬움(이미지·20초 이하)</button><button class="chip" data-f="new" aria-pressed="false">오늘 새로 발견</button><button class="chip" data-f="img" aria-pressed="false">이미지만</button>{''.join(f'<button class="chip" data-f="g_{esc(tok(g))}" aria-pressed="false">{esc(g)} <small>{gc[g]}</small></button>' for g in GO if gc[g] and g not in ('카테고리','레퍼런스 브랜드'))}</div>{SUB}
{ZCRE_HTML}<div class="g"><button type="button" class="addc" id="addBtn"><b>＋</b><span>레퍼런스 직접 추가</span><small>이미지·영상을 올리면 카드로 붙어요</small></button><div id="addPend" style="display:contents"></div>{''.join(ccards)}{''.join(scards)}{''.join(acards)}{''.join(cards)}</div></div>
<dialog id="addDlg"><form method="dialog" class="md"><h3>레퍼런스 직접 추가</h3>
<label>이름 <small style="color:#c62828">(필수)</small><select id="aWho" class="who"><option value="">이름 선택</option><option>화영</option><option>다운</option><option>도현</option><option>근형</option><option>형태</option><option>다솔</option></select></label>
<div class="seg" role="radiogroup" aria-label="종류"><label><input type="radio" name="ak" value="image" checked> 이미지</label><label><input type="radio" name="ak" value="video"> 영상</label></div>
<label>파일<input type="file" id="aFile" accept="image/*"></label><div id="aPrev" class="aprev"></div>
<label>이름 <small>(브랜드·소재 이름, 카드 제목)</small><input id="aNm" placeholder="예) 바이브랩 7초 영상"></label>
<label>메모 <small>(선택 · 왜 골랐는지, 따라 할 포인트)</small><textarea id="aMemo" rows="3" placeholder="예) 첫 1초 가격 박스가 크게 튀어나오는 연출"></textarea></label>
<label>원본 링크 <small>(선택)</small><input id="aSrc" placeholder="https://"></label>
<label>참고 파일 <small>(선택 · 이 레퍼런스로 복각할 때 같이 쓸 에셋 사진·영상, 기획안 PDF·워드·PPT 등 최대 10개)</small><input type="file" id="raFiles" multiple accept="image/*,video/*,audio/*,.mp3,.wav,.m4a,.aac,.pdf,.txt,.md,.doc,.docx,.rtf,.pptx"></label><div id="raPrev" class="uprev"></div>
<label>참고 파일 메모 <small>(선택)</small><textarea id="raNote" rows="2" placeholder="예) 1번 영상을 첫 컷에, 제품은 2번 사진으로"></textarea></label>
<label>브랜드 <small>(바로 복각할 때 · 어느 업체 소재인지)</small><select id="aBSel"></select></label>
<label>랜딩 페이지 <small>(바로 복각할 때 · 목록에 없으면 맨 아래 '＋ 직접 링크 입력')</small><select id="aLSel"></select></label>
<label>명령어 입력 <small>(선택 · 바로 복각할 때 Claude 가 편집하며 그대로 따라요)</small><textarea id="aCmd" rows="3" placeholder="예) 첫 컷은 1번 영상, 가격은 '개당 2만원'으로"></textarea></label>
<div class="mrow"><span id="aMsg" class="mmsg"></span><button value="cancel" class="ghost2">취소</button><button id="aGo" class="ghost2" value="ok">추가만 하기</button><button id="aGoB" class="pri" type="button">추가하고 바로 복각하기</button></div></form></dialog>
<dialog id="lDlg"><form method="dialog" class="md"><h3>복각 설정</h3><p class="mmsg">고른 랜딩 상품에 맞춰 소재를 만들고, 세팅할 때 이 링크에 UTM이 붙어요.</p>
<label>이름 <small style="color:#c62828">(필수 · 누가 만드는지)</small><select id="who" class="who"><option value="">이름 선택</option><option>화영</option><option>다운</option><option>도현</option><option>근형</option><option>형태</option><option>다솔</option></select></label>
<label>브랜드 <small>(어느 업체 소재인지 — 랜딩 목록·근거·세팅 계정이 여기에 맞춰져요)</small><select id="bSel"></select></label>
<label>랜딩 페이지 <small>(목록에 없으면 맨 아래 '＋ 직접 링크 입력')</small><select id="lSel"></select></label>
<div id="lInfo" class="linfo"></div>
<label>명령어 입력 <small>(선택 · Claude 가 편집할 때 그대로 따라요)</small><textarea id="lCmd" rows="3" placeholder="예) 가격은 '개당 2만원 · 최대 70%'로, 자막은 주아체, 제품은 꼭 3번 사진으로"></textarea></label>
<label>참고 파일 <small>(선택 · 에셋 사진·영상, 기획안 PDF·워드·PPT 등 최대 10개 — 에셋은 먼저 쓰고 기획안은 그대로 따라요)</small><input type="file" id="uFiles" multiple accept="image/*,video/*,audio/*,.mp3,.wav,.m4a,.aac,.pdf,.txt,.md,.doc,.docx,.rtf,.pptx"></label><div id="uPrev" class="uprev"></div>
<label>참고 파일 메모 <small>(선택 · 어떻게 쓸지)</small><textarea id="uNote" rows="2" placeholder="예) 2번 영상은 첫 컷에, 제품은 꼭 3번 사진으로"></textarea></label>
<div class="mrow"><span id="lMsg" class="mmsg"></span><button value="cancel" class="ghost2">취소</button><button id="lGo" class="pri" value="ok">복각하기</button></div></form></dialog>
<div class="dock" hidden><span id="cnt">0개 선택</span><span class="mu2" id="cost"></span><button id="clr" class="ghost">선택 해제</button><button id="go">복각하기</button></div>
<script type="application/json" id="cmeta">{CMETA_J}</script><script>let PRODUCTS={json.dumps([dict(url=p['url'],title=p['title'],price=p['price'],image=p['image']) for p in PRODUCTS],ensure_ascii=False)},CMETA=JSON.parse(document.getElementById('cmeta').textContent);const META={json.dumps({c['id']:dict(page=c['t'].split(' 광고 ')[0][:40],t=c['t'][:600],dur=c['dur'],days=c['days'],poster=c.get('poster',''),imgs=c.get('imgs',[]),video=c.get('video','') if c['dur'] else '') for c in lib},ensure_ascii=False)};Object.assign(META,CMETA);const BRANDS={json.dumps(BRANDS_UI,ensure_ascii=False)};BRANDS.SOOO.landings=PRODUCTS;let curB="SOOO";</script>{JS}{BOKGAK_JS}{ZCRE_JS}</body></html>'''
# ---------- 검색 (2026-11-11 다운 "샴푸·쿨링·프로모션·추석 아무거나 치면 관련 레퍼런스") ----------
# 카드마다 data-s = 광고 문구·계정·키워드·메모 + 이미지에 박힌 글씨(macOS Vision OCR, data/ocr.json 캐시, bin/ocr)
import subprocess
OCRF=R+'data/ocr.json'; OCR=json.load(open(OCRF)) if os.path.exists(OCRF) else {}
SRC={}   # 카드 id → (이미지 파일명, 글자)
for x in CUSTOM: SRC[x['id']]=(f"L{x['id']}.jpg",' '.join([x.get('name',''),x.get('memo',''),'직접 추가']))
for x in SLACK: SRC[x['id']]=(f"L{x['id']}.jpg",' '.join([x.get('account',''),x.get('note',''),x.get('caption','') or '',x.get('by',''),'소재공유방']))
for x in ag: SRC[x['id']]=((x['imgk']+'.jpg') if x.get('imgk') else '',' '.join([x.get('acct',''),x.get('name',''),x.get('body','') or '']))
for c in lib: SRC[c['id']]=((c['img']+'.jpg') if c.get('img') else '',' '.join([c.get('t',''),' '.join(LBL.get(k,k) for k in c.get('qs',[])),' '.join(c.get('gs',[]))]))
_need=sorted({f for f,_ in SRC.values() if f and f not in OCR and os.path.exists(M+f)})
if _need and os.path.exists(R+'bin/ocr'):
    def _ocr(ch):
        try: return subprocess.run([R+'bin/ocr']+[M+f for f in ch],capture_output=True,text=True,timeout=600).stdout
        except Exception: return ''
    with ThreadPoolExecutor(6) as ex:
        for out in ex.map(_ocr,[_need[i:i+30] for i in range(0,len(_need),30)]):
            for ln in out.splitlines():
                try: o=json.loads(ln); OCR[o['f']]=o['t'][:400]
                except Exception: pass
    for f in _need: OCR.setdefault(f,'')   # 글씨 없는 이미지도 다시 안 읽게
    json.dump(OCR,open(OCRF,'w'),ensure_ascii=False)
def _s(i):
    f,t=SRC.get(i,('',''))
    return re.sub(r'\s+',' ',(t[:500]+' '+OCR.get(f,'')).lower()).strip()
idx=re.sub(r'<article class="c" data-id="([^"]+)"',lambda m: m.group(0)+f' data-s="{esc(_s(m.group(1)))}"',idx)
SRCH_HTML='<div class="srch"><input id="qIn" type="search" placeholder="🔍 검색 — 샴푸, 쿨링, 프로모션, 추석, 1+1 …" autocomplete="off" aria-label="레퍼런스 검색"><span id="qN" class="mmsg"></span></div>'
SRCH_CSS='<style>.srch{display:flex;align-items:center;gap:10px;margin:14px 0 -2px}.srch input{flex:1;max-width:560px;font:inherit;font-size:16px;padding:11px 16px;border:2px solid var(--ln);border-radius:999px;background:var(--s);color:var(--fg)}.srch input:focus{outline:none;border-color:var(--ac)}.srch .mmsg{font-weight:700;color:var(--ac)}</style>'
from libsearch_ui import LS_HTML, LS_CSS, LS_JS   # 검색창 '지금 집행 중' 실시간 칸(2026-11-11)
idx=idx.replace('<div class="livebar"',SRCH_HTML+LS_HTML+'<div class="livebar"',1).replace('</head>',SRCH_CSS+LS_CSS+'</head>',1)
from star_ui import STAR_CHIP, STAR_CSS, STAR_JS   # 별표(2026-11-11)
idx=idx.replace('<button class="chip" data-f="all" aria-pressed="true">전체</button>','<button class="chip" data-f="all" aria-pressed="true">전체</button>'+STAR_CHIP,1).replace('</head>',STAR_CSS+SS_CSS+'</head>',1)
idx=idx[:idx.rindex('</body>')]+LS_JS+STAR_JS+SS_JS+idx[idx.rindex('</body>'):]
open(R+'site/index.html','w').write(idx)
# agency
cards=[]
for x in ag:
    fm=fmt_ag(x); easy=fm in ('GIF','이미지') or (x.get('vlen') and x['vlen']<=20)
    mult=x['roas']/x['acct_roas'] if x.get('acct_roas') else 0
    st='집행 중' if x.get('status')=='ACTIVE' else '종료/중지'
    cards.append(f'''<article class="c" data-f="{'easy' if easy else ''} a_{esc(x['acct'])}"><div class="im">{f'<img src="m/{x["imgk"]}.jpg" loading="lazy" alt="">' if x.get('imgk') else ''}{f'<video class="pv on" src="{esc(x["vsrc"])}" poster="m/{x["imgk"]}.jpg" playsinline controls preload="none"></video>' if x.get('vsrc') else ''}<span class="d">{x['days']}일 집행</span></div>
<div class="b"><div class="p">{esc(x['acct'])}</div><div class="mt" style="word-break:break-all">{esc(x['name'])}</div><div class="mt">{x['first'] or '-'} ~ {x['last'] or '-'} · {st}</div>
<div class="mt">지출 {x['spend']:,.0f}원 · 구매 {x['pur']:,.0f} · ROAS {x['roas']:.2f} (계정 평균 ×{mult:.1f})</div>
<div class="tg"><span>{fm}</span>{'<span class="e">쉬움</span>' if easy else ''}</div><div class="t">{esc(x.get('body',''))}</div></div></article>''')
accs=sorted({x['acct'] for x in ag})
agh=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>대행 계정 고효율 소재 (매일 갱신)</title>{CSS}</head><body><div class="w">
<h1>대행 계정 고효율 소재</h1>{NAV}<p class="lede">대행 메타 계정(대표님 포트폴리오 전체 + 칸디데·FnL·오브휴·SOOO)의 실제 성과 기준. 같은 소재는 합침. 마지막 갱신 {TS} · {len(ag)}건</p>{AGNOTE}
<div class="bar"><button class="chip" data-f="all" aria-pressed="true">전체</button><button class="chip" data-f="easy" aria-pressed="false">쉬움(이미지·GIF·20초 이하)</button>{''.join(f'<button class="chip" data-f="a_{esc(a)}" aria-pressed="false">{esc(a)}</button>' for a in accs)}</div>
<div class="g">{''.join(cards)}</div></div>{JS}</body></html>'''
open(R+'site/agency.html','w').write(agh)
print('library',len(lib),'agency',len(ag))
# 안 쓰는 이미지 정리
used={f'{c["img"]}.jpg' for c in lib if c.get('img')}|{f'{x["imgk"]}.jpg' for x in ag if x.get('imgk')}|{f'L{x["id"]}.jpg' for x in CUSTOM}|{f'L{x["id"]}.{e}' for x in SLACK for e in ('jpg','mp4')}|{f'L{x["id"]}.mp4' for x in CUSTOM if x['kind']=='video'}   # 직접 추가 카드 사진은 지우지 않음
from PIL import Image as _I
for x in CUSTOM:   # 혹시 지워졌으면 원본에서 다시
    q=M+f'L{x["id"]}.jpg'
    if not os.path.exists(q):
        srcs=[R+f'data/ref_{x["id"]}.jpg',R+f'data/custom/{x["id"]}_f0.jpg']
        for sp in srcs:
            if os.path.exists(sp): im=_I.open(sp).convert('RGB'); im.thumbnail((480,600)); im.save(q,quality=80); break
try:   # 별표 찍힌 레퍼런스 썸네일은 목록에서 빠져도 남김(별표 탭에서 보이게)
    _st=json.loads(subprocess.run(['node',R+'scripts/remote.mjs','getjson','stars.json'],capture_output=True,text=True,timeout=60,cwd=R).stdout or 'null') or {}
    used|={os.path.basename((v.get('meta') or {}).get('img') or '') for v in _st.values()}|{f'L{k}.jpg' for k in _st}|{f'A{k}.jpg' for k in _st}
except Exception as e: print('별표 목록 못 받음(썸네일 정리는 그대로)',e)
for f in os.listdir(M):
    if f not in used: os.remove(M+f)
