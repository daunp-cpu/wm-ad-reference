# 소재공유방 새로고침 버튼 (2026-11-12 다운: "슬랙 동기화 하루 한 번으로, 필요하면 버튼으로").
# 탭 안내문(#lede) 안의 버튼 → POST api/bokgak {type:slacksync,by} → 맥 작업기(1분)가 slack_sync.sh 실행 → 새 글 있으면 사이트 다시 만들고 배포(페이지는 ver.json 으로 자동 반영).
SS_BTN = '<button type="button" class="ssbtn" data-ss="1">🔄 소재공유방 새로고침</button>'
SS_CSS = '<style>.ssbtn{margin-left:8px;border:1px solid #bbb;border-radius:999px;background:#fff;padding:3px 11px;font:inherit;font-size:12px;cursor:pointer}.ssbtn:hover{background:#f3f3f3}.ssbtn[disabled]{opacity:.55;cursor:default}</style>'
SS_JS = r'''<script>
(()=>{const WHO=['화영','다운','도현','근형','형태'];let last=0;
document.addEventListener('click',async e=>{const b=e.target.closest('.ssbtn');if(!b)return;e.preventDefault();
 if(Date.now()-last<180000){b.textContent='⏳ 방금 요청했어요 — 2~3분 뒤 자동 반영';return}
 let w='';try{w=localStorage.getItem('bokgak-who')||''}catch(x){}
 if(!WHO.includes(w)){w=(prompt('이름을 적어주세요 ('+WHO.join(' / ')+')')||'').trim();if(!WHO.includes(w))return;try{localStorage.setItem('bokgak-who',w)}catch(x){}}
 b.disabled=true;b.textContent='요청 중…';
 try{const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:'slacksync',by:w})})).json();if(!r.ok)throw new Error(r.msg||'실패');last=Date.now();b.textContent='✅ 요청됨 — 새 글이 있으면 2~3분 뒤 자동 반영'}
 catch(x){b.textContent='요청 실패: '+x.message}
 b.disabled=false;setTimeout(()=>{if(b.isConnected)b.textContent='🔄 소재공유방 새로고침'},20000)})})();
</script>'''
