# build_review.py 에 넣을 누적 금액 달력 UI. f-string 밖에서 조립해 중괄호 충돌을 피한다.
SPEND_CSS = """
.hd{flex-wrap:wrap}
.spend{flex-basis:100%;color:#0f766e;font-size:15px;font-weight:800;margin:6px 0 0;background:#e3f3f0;border:2px solid #0f766e;border-radius:10px;padding:10px 14px;cursor:pointer;text-align:left;font-family:inherit}
.spend:hover{background:#d3ebe7}
.spend small{color:#3c6f69;font-weight:600;font-size:12px}
#spendDlg{border:0;border-radius:16px;padding:0;max-width:420px;width:calc(100vw - 32px);box-shadow:0 20px 60px rgba(0,0,0,.3)}
#spendDlg::backdrop{background:rgba(0,0,0,.4)}
.sw{background:var(--s);color:var(--fg);padding:16px}
.sh{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.sh b{font-size:16px}
.sh button{border:0;background:var(--acs);color:var(--ac);border-radius:8px;padding:5px 10px;cursor:pointer;font-weight:700}
.stabs{display:flex;gap:6px;margin-bottom:10px}
.stabs button{flex:1;border:1px solid var(--ln);background:var(--s);color:var(--mu);border-radius:8px;padding:6px;cursor:pointer;font-weight:700;font-size:13px}
.stabs button.on{background:var(--ac);color:#fff;border-color:var(--ac)}
.snav{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-weight:700}
.snav button{border:1px solid var(--ln);background:var(--s);color:var(--fg);border-radius:8px;width:32px;height:32px;cursor:pointer;font-size:16px}
.snav button:disabled{opacity:.3;cursor:default}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:2px}
.cal .dow{text-align:center;font-size:11px;color:var(--mu);padding:2px 0}
.cal .cell{min-height:46px;border-radius:6px;padding:3px 4px;font-size:11px;background:var(--bg)}
.cal .cell.has{background:var(--acs);color:var(--ac);font-weight:700}
.cal .cell.out{opacity:.25}
.cal .cell .n{font-size:10px;opacity:.7;display:block}
.rows{display:flex;flex-direction:column;gap:4px}
.rows .r{display:flex;justify-content:space-between;padding:7px 10px;border-radius:8px;background:var(--bg);font-size:13px}
.rows .r b{font-variant-numeric:tabular-nums}
.sfoot{margin-top:12px;padding-top:10px;border-top:1px solid var(--ln);display:flex;justify-content:space-between;font-size:13px}
.sfoot b{font-size:15px}
.snote{margin-top:8px;font-size:11px;color:var(--mu);line-height:1.5}
"""

SPEND_DLG = """<dialog id="spendDlg"><div class="sw">
<div class="sh"><b>복각 소재 사용 금액</b><button type="button" id="sclose">닫기</button></div>
<div class="stabs"><button type="button" data-v="day" class="on">일별</button><button type="button" data-v="week">주별</button><button type="button" data-v="month">월별</button></div>
<div class="snav"><button type="button" id="sprev">&lsaquo;</button><span id="slabel"></span><button type="button" id="snext">&rsaquo;</button></div>
<div id="sbody"></div>
<div class="sfoot"><span id="sfl">기간 합계</span><b id="stotal"></b></div>
<p class="snote" id="snote"></p>
</div></dialog>"""

SPEND_JS = """
const SPD=__SPENDD__, SEST=__SEST__;
(function(){
 const btn=document.querySelector('.spend'), dlg=document.getElementById('spendDlg');
 if(!btn||!dlg)return;
 const W=(n)=>n.toLocaleString('ko-KR')+'원';
 const days=Object.keys(SPD).sort();
 let view='day', cur=days.length?new Date(days[days.length-1]+'T00:00:00'):new Date();
 const body=document.getElementById('sbody'), label=document.getElementById('slabel');
 const total=document.getElementById('stotal'), prev=document.getElementById('sprev'), next=document.getElementById('snext');
 const mk=(t,c,h)=>{const e=document.createElement(t);if(c)e.className=c;if(h!==undefined)e.innerHTML=h;return e};
 function weekKey(d){const t=new Date(d);const day=(t.getDay()+6)%7;t.setDate(t.getDate()-day);return t.toISOString().slice(0,10)}
 function render(){
  body.textContent=''; let sum=0;
  document.querySelectorAll('.stabs button').forEach(b=>b.classList.toggle('on',b.dataset.v===view));
  if(view==='day'){
   const y=cur.getFullYear(), m=cur.getMonth();
   label.textContent=y+'년 '+(m+1)+'월';
   const cal=mk('div','cal');
   ['월','화','수','목','금','토','일'].forEach(d=>cal.appendChild(mk('div','dow',d)));
   const first=new Date(y,m,1), lead=(first.getDay()+6)%7, last=new Date(y,m+1,0).getDate();
   for(let i=0;i<lead;i++)cal.appendChild(mk('div','cell out',''));
   for(let d=1;d<=last;d++){
    const key=y+'-'+String(m+1).padStart(2,'0')+'-'+String(d).padStart(2,'0');
    const v=SPD[key]||0; if(v)sum+=v;
    cal.appendChild(mk('div','cell'+(v?' has':''), d+(v?'<span class="n">'+v.toLocaleString('ko-KR')+'</span>':'')));
   }
   body.appendChild(cal);
   prev.disabled=next.disabled=false;
  }else if(view==='week'){
   label.textContent='주별';
   const g={}; days.forEach(d=>{const k=weekKey(d); g[k]=(g[k]||0)+SPD[d]});
   const rows=mk('div','rows');
   Object.keys(g).sort().reverse().forEach(k=>{
    const e=new Date(k); e.setDate(e.getDate()+6);
    rows.appendChild(mk('div','r','<span>'+k.slice(5).replace('-','/')+' ~ '+e.toISOString().slice(5,10).replace('-','/')+'</span><b>'+W(g[k])+'</b>'));
    sum+=g[k];
   });
   body.appendChild(rows); prev.disabled=next.disabled=true;
  }else{
   label.textContent='월별';
   const g={}; days.forEach(d=>{const k=d.slice(0,7); g[k]=(g[k]||0)+SPD[d]});
   const rows=mk('div','rows');
   Object.keys(g).sort().reverse().forEach(k=>{
    rows.appendChild(mk('div','r','<span>'+k.slice(0,4)+'년 '+(+k.slice(5))+'월</span><b>'+W(g[k])+'</b>'));
    sum+=g[k];
   });
   body.appendChild(rows); prev.disabled=next.disabled=true;
  }
  document.getElementById('sfl').textContent = view==='day' ? '이 달 합계' : '전체 합계';
  total.textContent=W(sum);
  const all=days.reduce((a,d)=>a+SPD[d],0);
  document.getElementById('snote').textContent =
   '실제 호출한 AI 비용입니다(이미지 생성·기획·영상). 전체 누적 '+W(all)
   + (SEST? ' · 기록을 심기 전 '+SEST+'건은 건당 추정값입니다.' : '');
 }
 btn.onclick=()=>{render();dlg.showModal()};
 document.getElementById('sclose').onclick=()=>dlg.close();
 dlg.onclick=e=>{if(e.target===dlg)dlg.close()};
 document.querySelectorAll('.stabs button').forEach(b=>b.onclick=()=>{view=b.dataset.v;render()});
 prev.onclick=()=>{cur.setMonth(cur.getMonth()-1);render()};
 next.onclick=()=>{cur.setMonth(cur.getMonth()+1);render()};
})();
"""

# ── 날짜 달력(제작한 날만 숫자 표시, 누르면 그 날 소재만 보기)
DATECAL_CSS = """
.calbtn{border:1px solid var(--ln);background:var(--s);color:var(--fg);border-radius:999px;padding:7px 13px;font-weight:700;cursor:pointer;font-size:14px}
.calbtn:hover{border-color:var(--ac);color:var(--ac)}
#dateDlg{border:0;border-radius:16px;padding:0;max-width:400px;width:calc(100vw - 32px);box-shadow:0 20px 60px rgba(0,0,0,.3)}
#dateDlg::backdrop{background:rgba(0,0,0,.4)}
#dateDlg .dcell{min-height:44px;border-radius:8px;padding:3px 0;font-size:12px;background:var(--bg);color:var(--mu);text-align:center;border:0;font-family:inherit}
#dateDlg .dcell.has{background:var(--acs);color:var(--ac);font-weight:800;cursor:pointer;border:1px solid var(--ac)}
#dateDlg .dcell.has:hover{filter:brightness(.96)}
#dateDlg .dcell.on{background:var(--ac);color:#fff}
#dateDlg .dcell .cnt{display:block;font-size:12px;font-weight:800;color:#b45309}
#dateDlg .dcell.on .cnt{color:#ffd54a}
#dateDlg .dcell.blank{background:transparent}
#dateDlg .sat{color:#2f6fd0}#dateDlg .sun{color:#c62828}
"""

DATECAL_DLG = """<dialog id="dateDlg"><div class="sw">
<div class="sh"><b id="dtitle">날짜 고르기</b><button type="button" id="dclose">닫기</button></div>
<div class="snav"><button type="button" id="dprev">&lsaquo;</button><span id="dlabel"></span><button type="button" id="dnext">&rsaquo;</button></div>
<div id="dbody"></div>
<p class="snote">숫자가 있는 날만 소재를 만든 날이에요. 눌러서 그 날 소재만 볼 수 있어요.</p>
</div></dialog>"""

DATECAL_JS = """
const DAYCNT=__DAYCNT__;
(function(){
 const dlg=document.getElementById('dateDlg'), btn=document.querySelector('.calbtn');
 if(!dlg||!btn)return;
 const body=document.getElementById('dbody'), label=document.getElementById('dlabel');
 let cur=new Date();
 function render(){
  const who=(typeof P!=='undefined'?P:''), cnt=DAYCNT[who]||{};
  const ds=Object.keys(cnt).sort();
  if(ds.length&&!render.moved){ cur=new Date(ds[ds.length-1]+'T00:00:00'); render.moved=1 }
  const y=cur.getFullYear(), m=cur.getMonth();
  label.textContent=y+'년 '+(m+1)+'월';
  document.getElementById('dtitle').textContent=who?who+'님이 만든 날':'날짜 고르기';
  body.textContent='';
  const cal=document.createElement('div'); cal.className='cal';
  ['월','화','수','목','금','토','일'].forEach((d,i)=>{
   const e=document.createElement('div'); e.className='dow'+(i===5?' sat':i===6?' sun':''); e.textContent=d; cal.appendChild(e)});
  const lead=(new Date(y,m,1).getDay()+6)%7, last=new Date(y,m+1,0).getDate();
  for(let i=0;i<lead;i++){const e=document.createElement('div'); e.className='dcell blank'; cal.appendChild(e)}
  for(let d=1;d<=last;d++){
   const key=y+'-'+String(m+1).padStart(2,'0')+'-'+String(d).padStart(2,'0'), n=cnt[key]||0;
   const dow=(new Date(y,m,d).getDay()+6)%7;
   const e=document.createElement('button'); e.type='button';
   e.className='dcell'+(n?' has':'')+(typeof DD!=='undefined'&&DD===key?' on':'')+(dow===5?' sat':dow===6?' sun':'');
   e.innerHTML=d+(n?'<span class="cnt">'+n+'</span>':'');
   if(n)e.onclick=()=>{sh(who,key);dlg.close()};
   cal.appendChild(e);
  }
  body.appendChild(cal);
 }
 btn.onclick=()=>{render.moved=0;render();dlg.showModal()};
 document.getElementById('dclose').onclick=()=>dlg.close();
 dlg.onclick=e=>{if(e.target===dlg)dlg.close()};
 document.getElementById('dprev').onclick=()=>{cur.setMonth(cur.getMonth()-1);render.moved=1;render()};
 document.getElementById('dnext').onclick=()=>{cur.setMonth(cur.getMonth()+1);render.moved=1;render()};
})();
"""
