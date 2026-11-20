# 레퍼런스 별표 (2026-11-11 다운 "팀장님이 별표 누르면 내가 보고 복각"). build.py 가 index.html 에 끼워 넣음.
# 카드마다 오른쪽 위 ☆ → 누르면 POST api/bokgak {type:star,id,by,on,meta} → Blob stars.json(팀 공유). 15초마다 다시 받아 다른 사람 별표 알림.
# '⭐ 별표' 탭 = 별표 찍힌 것만. 목록에서 빠진 레퍼런스(실시간 검색 카드·지난 레퍼런스)는 저장해 둔 meta 로 카드를 만들어 붙임 → 바로 복각 가능.
STAR_CHIP = '<button class="chip" data-f="star" aria-pressed="false">⭐ 별표 <small id="starN">0</small></button>'
STAR_CSS = '''<style>.starb{position:absolute;right:8px;top:8px;z-index:5;border:0;border-radius:999px;background:rgba(0,0,0,.55);color:#fff;font-size:18px;line-height:1;padding:6px 9px;cursor:pointer;font-family:inherit}
.starb:hover{background:rgba(0,0,0,.75)}.starb.on{background:#ffc400;color:#3a2a00;font-weight:800;font-size:15px;box-shadow:0 2px 8px rgba(0,0,0,.25)}.starb span{font-size:12px;margin-left:2px}
.c .im .nw{top:44px}.c:has(.starb.on){outline:2px solid #ffc400;outline-offset:-2px}</style>'''
STAR_JS = r'''<script>
(()=>{let STARS={},first=true,busy=false;window.STARS_=STARS;
const E=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]);
const WHO=['화영','다운','도현','근형','형태','다솔'];
function me(){let w='';try{w=localStorage.getItem('bokgak-who')||''}catch(e){}if(WHO.includes(w))return w;w=(prompt('별표는 팀 전체에 이름과 같이 보여요.\n이름을 적어주세요 ('+WHO.join(' / ')+')')||'').trim();if(!WHO.includes(w)){if(w)alert(WHO.join(', ')+' 중 하나로 적어주세요');return''}try{localStorage.setItem('bokgak-who',w)}catch(e){}return w}
function paint(c){const id=c.dataset.id;if(!id)return;const im=c.querySelector('.im');if(!im)return;let b=im.querySelector(':scope > .starb');if(!b){b=document.createElement('button');b.type='button';b.className='starb';im.append(b)}
 const s=STARS[id];b.classList.toggle('on',!!s);b.innerHTML=s?'★<span>'+E(s.by)+'</span>':'☆';b.title=s?s.by+'님 별표 · '+new Date(s.at).toLocaleString('ko-KR')+' (누르면 빼기)':'별표 — 팀 전체에 보여요';b.setAttribute('aria-label',s?s.by+'님 별표, 빼기':'별표 찍기');b.setAttribute('aria-pressed',String(!!s))}
function ghosts(){const G=document.querySelector('.g');if(!G)return;
 Object.entries(STARS).forEach(([id,s])=>{if(G.querySelector(':scope > .c[data-id="'+id+'"]'))return;const m=s.meta||{},img=m.img||m.poster||(m.imgs||[]).slice(-1)[0]||'';
  const t=document.createElement('template');t.innerHTML=`<article class="c" data-id="${E(id)}" data-f="starx" data-s="${E(((m.page||'')+' '+(m.t||'')+' '+s.by).toLowerCase())}"><label class="pick"><input type="checkbox" value="${E(id)}"> 복각</label><div class="im">${img?`<img src="${E(img)}" loading="lazy" referrerpolicy="no-referrer" alt="">`:''}${m.video?`<video class="pv" data-src="${E(m.video)}" muted loop playsinline controls preload="none"></video>`:''}<span class="d">${typeof m.days==='number'?m.days+'일 집행':E(m.days||'별표')}</span></div><div class="b"><div class="st" data-st></div><div class="p">${E(m.page||'레퍼런스')}</div><div class="mt">${m.dur?'영상 '+E(m.dur):'이미지'} · 지금 목록엔 없는 레퍼런스</div><div class="t">${E(m.t||'')}</div></div></article>`;
  const nd=t.content.firstElementChild;G.append(nd);if(!META[id])META[id]={page:m.page||'',t:m.t||'',dur:m.dur||'',days:m.days,poster:m.poster||'',imgs:m.imgs||[],video:m.video||''};try{bPick(nd)}catch(e){}try{bVid(nd)}catch(e){}nd.hidden=CURF!=='star'});
 G.querySelectorAll(':scope > .c[data-f="starx"]').forEach(c=>{if(!STARS[c.dataset.id])c.remove()})}
function paintAll(){ghosts();document.querySelectorAll('.c[data-id]').forEach(paint);const n=document.getElementById('starN');if(n)n.textContent=Object.keys(STARS).length;if(CURF==='star')show('star');try{sync()}catch(e){}}
const PEND={};   // 내가 방금 찍거나 뺀 것 — 서버 목록 반영이 늦어도 1분간은 내 화면 그대로(2026-11-11 '별표가 좀 이따 없어짐' 고침)
function setS(o){o=Object.assign({},o||{});const now=Date.now();Object.entries(PEND).forEach(([id,p])=>{if(now-p.at>60000){delete PEND[id];return}if(p.on)o[id]=o[id]||p.s;else delete o[id]});Object.keys(STARS).forEach(k=>delete STARS[k]);Object.assign(STARS,o)}
function note(s,id){const t=document.createElement('div');t.className='tnote';t.innerHTML='<b>⭐ '+E(s.by)+'님</b>이 별표: <b>'+E(((s.meta||{}).page||'레퍼런스').slice(0,30))+'</b> <a href="#" data-go="star" style="color:#9cf">별표 탭 보기</a>';(document.getElementById('tnotes')||document.body).append(t);setTimeout(()=>t.remove(),12000)}
async function load(){if(document.hidden||busy)return;try{const r=await (await fetch('api/bokgak?stars=1',{cache:'no-store'})).json();if(!r.ok)return;const w=(()=>{try{return localStorage.getItem('bokgak-who')||''}catch(e){return''}})();
 if(!first)Object.entries(r.stars||{}).forEach(([id,s])=>{if(!STARS[id]&&s.by!==w)note(s,id)});first=false;setS(r.stars);paintAll()}catch(e){}}
document.addEventListener('click',async e=>{const g=e.target.closest('[data-go="star"]');if(g){e.preventDefault();ap('star');scrollTo({top:0,behavior:'smooth'});return}
 const b=e.target.closest('.starb');if(!b)return;e.preventDefault();e.stopPropagation();const c=b.closest('.c'),id=c.dataset.id,cur=STARS[id];const by=me();if(!by)return;
 if(cur&&cur.by!==by&&!confirm(cur.by+'님이 찍은 별표예요. 뺄까요?'))return;
 const im=c.querySelector('.im img'),src=im?im.getAttribute('src'):'';const m=Object.assign({},META[id]||{},{page:(META[id]||{}).page||(c.querySelector('.p')||{}).textContent||'',img:/^m\//.test(src)?src:''});if(!m.poster&&src&&!/^m\//.test(src))m.poster=src;
 busy=true;if(cur)delete STARS[id];else STARS[id]={by,at:Date.now(),meta:m};PEND[id]={on:!cur,at:Date.now(),s:STARS[id]||cur};paintAll();
 try{const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'star',id,by,on:!cur,meta:m})})).json();if(!r.ok)throw new Error(r.msg);setS(r.stars)}catch(err){alert('별표 저장 실패: '+err.message);delete PEND[id];if(cur)STARS[id]=cur;else delete STARS[id]}
 busy=false;paintAll()},true);
let mt;new MutationObserver(()=>{clearTimeout(mt);mt=setTimeout(()=>document.querySelectorAll('.c[data-id]').forEach(c=>{if(!c.querySelector('.im > .starb'))paint(c)}),300)}).observe(document.body,{childList:true,subtree:true});
document.querySelectorAll('.c[data-id]').forEach(paint);load();setInterval(load,15000);document.addEventListener('visibilitychange',load);
})();
</script>'''
