# 검색창 '지금 집행 중' 실시간 결과 칸 (2026-11-11). build.py 가 index.html 에 끼워 넣음.
# 검색어 입력 → 1.2초 멈추거나 Enter → POST api/bokgak {type:libsearch,q,terms} → 맥 작업기(1분 주기)가 메타 광고 라이브러리에서 긁어 Blob ls/<키>.json → GET ?ls=<키> 4초 폴링.
# 카드는 일반 레퍼런스 카드와 같은 모양·같은 복각 체크(META 에 추가) — 바로 복각 가능.
LS_HTML = '''<section id="lsBox" class="lsbox" hidden><div class="lshd"><b>📡 메타 광고 라이브러리 · 지금 집행 중</b><span id="lsMsg" class="mmsg"></span><button type="button" id="lsRe" class="ghost2 sm" hidden>다시 찾기</button></div>
<div class="lg" id="lsG"></div><div class="lsft"><button type="button" id="lsMore" class="ghost2" hidden>더 보기</button></div></section>'''
LS_CSS = '''<style>.lsbox{margin:14px 0 6px;padding:14px;border:2px solid var(--ac);border-radius:14px;background:var(--s)}.lshd{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:12px}.lshd b{font-size:16px}
.lshd .mmsg{color:var(--mu);font-size:13px}.ghost2.sm{padding:4px 12px;font-size:12px}.lg{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}.lg:empty{display:none}.lsft{display:flex;justify-content:center;margin-top:12px}
.lsbox .c .im{aspect-ratio:4/5}.lw{position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,.6);color:#fff;border-radius:6px;padding:1px 7px;font-size:11px;font-weight:700}
.lsbar{height:4px;border-radius:2px;background:var(--ln);overflow:hidden;flex-basis:100%}.lsbar i{display:block;height:100%;background:var(--ac);transition:width .8s}</style>'''
LS_JS = r'''<script>
(()=>{const qi=document.getElementById('qIn'),box=document.getElementById('lsBox'),G=document.getElementById('lsG'),msg=document.getElementById('lsMsg'),re=document.getElementById('lsRe'),more=document.getElementById('lsMore');if(!qi||!box)return;
const E=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
let tok=0,lastQ='',ADS=[],shown=0,tm=null;
function terms(q){const t=[q];if(!/\s/.test(q)){(SYN[q]||[]).filter(w=>w.length>=2&&!/%/.test(w)&&w!==q).slice(0,4).forEach(w=>t.push(w));[' 이벤트',' 할인',' 선물'].forEach(s=>t.length<8&&t.push(q+s))}return t}
function card(a){const img=a.poster||(a.imgs&&a.imgs.length?a.imgs[a.imgs.length-1]:'');
 return `<article class="c" data-id="${E(a.id)}" data-f="live"><label class="pick"><input type="checkbox" value="${E(a.id)}"> 복각</label><div class="im">${img?`<img src="${E(img)}" loading="lazy" referrerpolicy="no-referrer" alt="">`:''}${a.video?`<video class="pv" data-src="${E(a.video)}" muted loop playsinline controls preload="none"></video>`:''}<span class="d">${a.days!=null?a.days+'일째 집행':'집행 중'}</span>${a.main?'':a.hit?'<span class="lw">비슷한 말</span>':'<span class="lw">문구엔 검색어 없음</span>'}</div>
<div class="b"><div class="st" data-st></div><div class="p">${E(a.page||'광고')}</div><div class="mt">${E(a.start||'')} 시작 · ${a.dur?'영상 '+E(a.dur):'이미지'}${a.multi>1?' · 광고 '+a.multi+'개':''}${a.low?' · 노출 적음':''}</div><div class="t">${E((a.text||'').replace(/^[\s\S]*?\n광고\n/,''))}</div><a class="l" href="https://www.facebook.com/ads/library/?id=${E(a.id)}" target="_blank" rel="noopener">광고 라이브러리에서 보기 ↗</a></div></article>`}
function render(n){const part=ADS.slice(shown,shown+n);if(!part.length)return;const t=document.createElement('template');t.innerHTML=part.map(card).join('');const nodes=[...t.content.children];G.append(...nodes);shown+=part.length;
 part.forEach(a=>{META[a.id]={page:a.page||'광고',t:(a.text||'').slice(0,600),dur:a.dur||'',days:a.days,poster:a.poster||'',imgs:a.imgs||[],video:a.video||''}});
 nodes.forEach(nd=>{try{bPick(nd)}catch(e){}try{bVid(nd)}catch(e){}});try{sync()}catch(e){}more.hidden=shown>=ADS.length;more.textContent='더 보기 ('+(ADS.length-shown)+'개 남음)'}
more.onclick=()=>render(60);
async function start(q,force){const my=++tok;lastQ=q;ADS=[];shown=0;G.innerHTML='';more.hidden=true;re.hidden=true;box.hidden=false;msg.textContent='메타에 요청 보내는 중…';
 let key;try{const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'libsearch',q,terms:terms(q),force:!!force})})).json();if(!r.ok)throw new Error(r.msg);key=r.key}catch(e){if(my===tok)msg.textContent='요청 실패: '+e.message;re.hidden=false;return}
 const t0=Date.now();
 while(my===tok&&Date.now()-t0<7*60e3){let d=null;try{d=(await (await fetch('api/bokgak?ls='+key,{cache:'no-store'})).json()).ls}catch(e){}
  if(my!==tok)return;const s=Math.round((Date.now()-t0)/1000);
  if(d&&d.state==='done'){ADS=d.ads||[];const ago=Math.round((Date.now()-d.at)/60000);msg.innerHTML=`<b style="color:var(--ac)">${ADS.length}개</b> 찾음 (문구에 검색어 있는 것 ${d.hit||0}개 먼저) · 검색어 ${(d.qs||[q]).map(E).join(', ')} · ${ago<1?'방금':ago+'분 전'} 수집`;re.hidden=false;render(60);if(!ADS.length)msg.textContent='지금 집행 중인 광고를 못 찾았어요 — 다른 말로 쳐보세요';return}
  if(d&&d.state==='fail'){msg.textContent='수집 실패 — 다시 찾기를 눌러주세요';re.hidden=false;return}
  msg.innerHTML=(d&&d.state==='running'?`메타 광고 라이브러리에서 긁는 중… ${s}초 (검색어 ${(d.terms||[]).length}개 · 보통 1~2분)`:`요청 접수 — 맥이 1분 안에 시작해요… ${s}초`)+'<span class="lsbar"><i style="width:'+Math.min(95,s/1.5)+'%"></i></span>';
  await new Promise(r=>setTimeout(r,4000))}
 if(my===tok){msg.textContent='시간이 너무 걸려요 — 다운 맥이 꺼져 있을 수 있어요. 다시 찾기를 눌러주세요';re.hidden=false}}
re.onclick=()=>{const q=qi.value.trim();if(q)start(q,true)};
function go(now){clearTimeout(tm);const q=qi.value.trim();if(!q){tok++;box.hidden=true;lastQ='';return}if(q===lastQ||q.length<2)return;tm=setTimeout(()=>start(q),now?0:1200)}
qi.addEventListener('input',()=>go(false));qi.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();lastQ='';go(true)}});
})();
</script>'''
