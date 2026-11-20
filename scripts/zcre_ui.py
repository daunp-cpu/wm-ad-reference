"""레퍼런스 페이지 'ZCRE 생성' 탭(화면). build.py 가 불러 씀.
요청: 견적 받기(무료) → 맥의 Claude 가 ZCRE 견적 → 페이지에 크레딧 표시 → '승인하고 생성'을 눌러야만 크레딧 사용 → 결과 갤러리."""
import json, os
R = '/Users/daun/ad-reference/'
MODELS = json.load(open(R + 'data/zcre/models.json')) if os.path.exists(R + 'data/zcre/models.json') else []
FIRST = ['nano-banana-pro', 'gpt-image-2', 'seedream-v5-pro', 'midjourney-v8.2', 'seedance-2.5', 'veo-3.1', 'kling-3', 'veo-3.1-fast', 'elevenlabs-v4']   # 자주 쓸 모델 먼저
# 모델 설명·용도 묶음(ZCRE 가 설명을 안 줘서 일반 정보로 정리 — 확실치 않은 건 '정보 적음')
G_ORDER = {'image': ['이미지 제작 추천', '가상 인물 사진 추천', '편집·보정', '그 밖의 이미지 모델'],
           'video': ['영상 제작 추천', '가상 인물 영상 추천', '편집·보정·번역', '그 밖의 영상 모델'],
           'audio': ['나레이션·음성 추천', '편집', '그 밖의 오디오 모델']}
INFO = {   # model: (묶음, 짧은 설명, 자세한 설명)
 'nano-banana-pro': ('이미지 제작 추천', '제품 합성·한글 글자 최강', 'Google Gemini 3 Pro 이미지. 참조 사진 여러 장(제품·인물·배경)을 섞어 한 장으로 만드는 데 가장 강하고, 한글 문구도 잘 씀. 광고 이미지·상세페이지 컷 1순위.'),
 'gpt-image-2': ('이미지 제작 추천', '지시를 꼼꼼히 따름·글자 강함', 'OpenAI 이미지 모델. 긴 지시(배치·문구·스타일)를 정확히 따르고 글자 표현이 좋음. 인포그래픽·카드형 소재에 좋음.'),
 'nano-banana-2': ('이미지 제작 추천', '빠르고 싼 시안용', 'Nano Banana 일반 버전. Pro 보다 싸고 빨라 시안·배경 여러 장 뽑을 때. 9:16 1장 9크레딧(10/23 견적).'),
 'seedream-v5-pro': ('가상 인물 사진 추천', '사실적인 인물·고해상도', 'ByteDance Seedream. 피부·머릿결이 사실적인 가상 모델 사진, 고해상도 화보컷에 좋음.'),
 'midjourney-v8.2': ('가상 인물 사진 추천', '감성·무드 화보', 'Midjourney. 분위기·조명이 예쁜 화보·무드컷. 다만 참조 제품을 그대로 지키는 건 약함 → 제품 없는 컷에.'),
 'wan-2.7-image-pro': ('가상 인물 사진 추천', '사실적 인물(상위)', 'Alibaba Wan 이미지 상위 버전. 사실적인 인물 사진.'),
 'nano-banana-2.1': ('그 밖의 이미지 모델', 'Nano Banana 2 개선판', 'Nano Banana 2 의 새 버전(차이 정보 적음).'),
 'gpt-image-2.5-flare': ('그 밖의 이미지 모델', 'GPT Image 2.5 변형', 'OpenAI GPT Image 2.5 계열 변형. flare/sunburst 차이는 정보 적음 — 한 번 비교해 보고 고르세요.'),
 'gpt-image-2.5-sunburst': ('그 밖의 이미지 모델', 'GPT Image 2.5 변형', 'OpenAI GPT Image 2.5 계열 변형. flare/sunburst 차이는 정보 적음.'),
 'wan-2.7-image': ('그 밖의 이미지 모델', 'Wan 이미지 기본', 'Alibaba Wan 이미지 기본 버전.'),
 'grok-imagine-image': ('그 밖의 이미지 모델', 'xAI Grok 이미지', 'xAI Grok 이미지 생성. 정보 적음.'),
 'wand-vega-image-1.0-pro': ('그 밖의 이미지 모델', 'Vega 이미지(정보 적음)', 'Vega 이미지 pro. 제공사·특징 정보 적음.'),
 'wand-vega-image-1.0-flash': ('그 밖의 이미지 모델', 'Vega 이미지 빠른판', 'Vega 이미지 flash. 정보 적음.'),
 'wand-vega-image-1.0-lite': ('그 밖의 이미지 모델', 'Vega 이미지 경량', 'Vega 이미지 lite. 정보 적음.'),
 'topaz-upscale-image': ('편집·보정', '화질 올리기', 'Topaz 업스케일. 작은·흐린 이미지를 선명하게 키움.'),
 'bria-background-remove': ('편집·보정', '누끼(배경 제거)', 'Bria 배경 제거. 제품·인물 누끼.'),
 'bria-expand': ('편집·보정', '비율 바꾸며 바깥 채우기', 'Bria 확장. 1:1 → 9:16 처럼 비율을 바꿀 때 잘린 바깥을 자연스럽게 채움.'),
 'veo-3.1': ('영상 제작 추천', '사실감 최상·소리까지', 'Google Veo 3.1. 화질·움직임 사실감이 가장 좋고 효과음·대사 소리까지 만듦. 비쌈.'),
 'seedance-2.5': ('영상 제작 추천', '카메라 무빙·가성비, 480p 미리보기', 'ByteDance Seedance 2.5. 카메라 움직임·컷 전환이 좋고 가성비. 프롬프트에 "드래프트"라고 쓰면 싼 480p 미리보기 먼저 → 마음에 들면 1080p.'),
 'veo-3.1-fast': ('영상 제작 추천', 'Veo 싸고 빠른판', 'Veo 3.1 fast. 품질 조금 낮고 더 쌈. 제품 없는 연출컷(물방울·꽃 등)에 충분.'),
 'kling-3': ('가상 인물 영상 추천', '인물 표정·동작 자연스러움', 'Kling 3. 사람 얼굴·손·몸 움직임이 자연스러워 가상 모델 리뷰·사용컷에 좋음.'),
 'kling-3-motion-control': ('가상 인물 영상 추천', '레퍼런스 동작 그대로 옮기기', 'Kling 3 모션 컨트롤. 레퍼런스 영상의 동작을 인물 사진에 그대로 입힘(레퍼런스 따라하기 복각에 유용).'),
 'minimax-h3': ('가상 인물 영상 추천', '역동적인 움직임', 'MiniMax(Hailuo). 움직임이 크고 역동적인 인물 영상.'),
 'seedance-2': ('그 밖의 영상 모델', 'Seedance 이전판', 'Seedance 2. 2.5 이전 버전.'),
 'seedance-2-fast': ('그 밖의 영상 모델', 'Seedance 2 빠른판', 'Seedance 2 fast.'),
 'seedance-2-mini': ('그 밖의 영상 모델', 'Seedance 2 경량', 'Seedance 2 mini. 싸고 짧은 컷.'),
 'wan-3.0': ('그 밖의 영상 모델', 'Wan 영상 기본', 'Alibaba Wan 영상. 저렴한 편.'),
 'wan-3.0-prime': ('그 밖의 영상 모델', 'Wan 영상 상위', 'Wan 3.0 상위 버전.'),
 'grok-imagine-video': ('그 밖의 영상 모델', 'xAI Grok 영상', 'xAI Grok 영상. 정보 적음.'),
 'grok-imagine-video-1.5': ('그 밖의 영상 모델', 'Grok 영상 1.5', 'Grok 영상 1.5. 정보 적음.'),
 'grok-imagine-video-1.5-lite': ('그 밖의 영상 모델', 'Grok 영상 경량', 'Grok 영상 1.5 lite. 정보 적음.'),
 'gemini-omni-flash': ('그 밖의 영상 모델', 'Google Gemini 계열(정보 적음)', 'Google Gemini 계열 영상. 정보 적음.'),
 'vega-1.5-pro': ('그 밖의 영상 모델', 'Vega 영상(정보 적음)', 'Vega 영상 pro. 정보 적음.'),
 'happy-horse-1': ('그 밖의 영상 모델', '정보 적음', '정보 적음.'),
 'happy-horse-1.1': ('그 밖의 영상 모델', '정보 적음', '정보 적음.'),
 'jiujitsu': ('그 밖의 영상 모델', '정보 적음', '정보 적음.'),
 'topaz-upscale-video': ('편집·보정·번역', '영상 화질 올리기', 'Topaz 영상 업스케일(기본).'),
 'topaz-upscale-video-precision': ('편집·보정·번역', '화질 올리기(원본 충실)', 'Topaz 업스케일 정밀 — 원본을 최대한 그대로.'),
 'topaz-upscale-video-generative': ('편집·보정·번역', '화질 올리기(디테일 생성)', 'Topaz 업스케일 생성형 — 없는 디테일을 그려 넣음(얼굴·글자 변할 수 있음).'),
 'topaz-upscale-video-creative': ('편집·보정·번역', '화질 올리기(창의적)', 'Topaz 업스케일 크리에이티브 — 가장 많이 바뀜.'),
 'topaz-interpolate-video': ('편집·보정·번역', '프레임 늘려 부드럽게', 'Topaz 프레임 보간 — 끊기는 영상을 60fps 처럼 부드럽게.'),
 'bytedance-upscale-video': ('편집·보정·번역', '영상 화질 올리기', 'ByteDance 업스케일.'),
 'bytedance-interpolate-video': ('편집·보정·번역', '프레임 늘려 부드럽게', 'ByteDance 프레임 보간.'),
 'heygen-video-translate-speed': ('편집·보정·번역', '다른 언어로 더빙(빠름)', 'HeyGen 영상 번역 — 영상 속 말을 일본어·영어 등으로 더빙+립싱크. 빠름.'),
 'heygen-video-translate-precision': ('편집·보정·번역', '다른 언어로 더빙(정확)', 'HeyGen 번역 정밀 — 번역·립싱크 더 정확, 초당 크레딧 2배.'),
 'elevenlabs-v4': ('나레이션·음성 추천', '자연스러운 한국어 나레이션', 'ElevenLabs v4. 감정 있는 자연스러운 나레이션·성우 목소리.'),
 'elevenlabs-v4-turbo': ('나레이션·음성 추천', 'ElevenLabs 빠른판', 'ElevenLabs v4 turbo. 조금 싸고 빠름.'),
 'seed-audio-1.0': ('그 밖의 오디오 모델', 'ByteDance 음성', 'ByteDance 음성 생성(MP3, 최대 120초). 참조 목소리 최대 3개.'),
 'bytedance-audio-separation': ('편집', '목소리·배경음 분리', '영상·음원에서 목소리/배경음(/효과음) 분리. 레퍼런스 BGM 만 빼낼 때.'),
}
def _info(m):
    g, short, long = INFO.get(m['model_name'], (G_ORDER[m['media']][-1], '정보 적음', '정보 적음.'))
    return {'model_name': m['model_name'], 'media': m['media'], 'group': g, 'short': short, 'desc': long}
ML = [_info(m) for m in MODELS]
ML.sort(key=lambda m: (G_ORDER[m['media']].index(m['group']) if m['group'] in G_ORDER[m['media']] else 9, FIRST.index(m['model_name']) if m['model_name'] in FIRST else 99, m['model_name']))
GORD = json.dumps(G_ORDER, ensure_ascii=False)

ZCRE_HTML = '''<style>
.hdr{display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.zbtn{display:flex;flex-direction:column;align-items:flex-start;gap:2px;min-width:260px;padding:12px 20px;border:0;border-radius:16px;cursor:pointer;font:inherit;color:#fff;text-align:left;background:linear-gradient(135deg,#7b2ff7,#f107a3);box-shadow:0 6px 18px rgba(123,47,247,.35);transition:transform .15s,box-shadow .15s}
.zbtn b{font-size:17px;letter-spacing:-.2px}.zbtn small{font-size:12px;opacity:.9}.zbtn:hover{transform:translateY(-1px);box-shadow:0 8px 22px rgba(123,47,247,.45)}
.zbtn[aria-pressed=true]{outline:3px solid #fff;outline-offset:-6px}.zbtn[aria-pressed=true] b::after{content:'  · 닫기'}
@media(max-width:700px){.hdr{align-items:stretch;width:100%}.zbtn{min-width:0}}
.zc{border:1px solid var(--ln);background:var(--s);border-radius:14px;padding:16px;margin:0 0 18px}.zc[hidden]{display:none!important}
.zh{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.zh b{font-size:18px}.zbal{font-weight:800;color:var(--ac)}
.zn{color:var(--mu);font-size:13px;margin:6px 0 12px}.zdesc{margin:-2px 0 0;font-size:13px;background:#f6f0ff;color:#4b2a86;border-radius:8px;padding:8px 10px}
.zf{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.zf label{display:flex;flex-direction:column;gap:4px;font-size:13px;font-weight:700}.zf .zw{grid-column:1/-1}
.zf select,.zf input,.zf textarea{font:inherit;font-size:14px;padding:8px 10px;border:1px solid var(--ln);border-radius:8px;background:var(--bg,#fff);color:var(--fg)}
.zf .ck{flex-direction:row;align-items:center;font-weight:600}.zgo{grid-column:1/-1;display:flex;gap:10px;align-items:center}
.zgo button,.zi button{border:0;border-radius:999px;padding:9px 18px;font:inherit;font-weight:800;cursor:pointer;background:var(--ac);color:#fff}.zi button.sec{background:transparent;color:var(--mu);border:1px solid var(--ln)}
.zl{display:flex;flex-direction:column;gap:10px;margin-top:16px}.zi{border:1px solid var(--ln);border-radius:12px;padding:12px;background:var(--bg,#fff)}
.zi .t{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13px;color:var(--mu)}.zi .t b{color:var(--fg)}.zi .p{margin:6px 0;font-size:14px;white-space:pre-wrap;word-break:break-word}
.zst{font-weight:800;border-radius:999px;padding:1px 9px;font-size:12px;background:#eef;color:#3b5bdb}.zst.done{background:#e6f6ea;color:#1b7a36}.zst.failed,.zst.price_up{background:#fdecec;color:#c62828}.zst.quoted{background:#fff4dc;color:#a35b00}
.zrv{font-size:13px;background:var(--s);border-radius:8px;padding:8px 10px;white-space:pre-wrap;margin:6px 0}.zbt{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
.zg{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.zg figure{margin:0;display:flex;flex-direction:column;gap:4px;font-size:12px}.zg img,.zg video{max-width:260px;max-height:360px;border-radius:8px;background:#000}.zg a{font-weight:700;color:var(--ac)}
@media(max-width:700px){.zf{grid-template-columns:1fr}}
</style>
<section class="zc" id="zcre" hidden>
<div class="zh"><b>ZCRE 생성</b><span class="zbal" id="zBal">잔액 확인 중…</span></div>
<p class="zn">모델·프롬프트를 넣고 <b>견적 받기</b>(무료) → 크레딧 견적이 뜨면 <b>승인하고 생성</b>을 눌러야만 크레딧이 나가요. 이 맥의 Claude 가 대신 실행해서 시작까지 1분쯤, 영상은 몇 분 더 걸려요. 견적은 5분 지나면 승인할 때 다시 받아요(더 비싸지면 멈추고 다시 물어봐요).</p>
<form class="zf" id="zForm">
<label>담당자<select id="zWho"><option value="">이름 고르기</option><option>화영</option><option>다운</option><option>도현</option><option>근형</option><option>형태</option><option>다솔</option></select></label>
<label>종류<select id="zMedia"><option value="image">이미지</option><option value="video">영상</option><option value="audio">오디오</option></select></label>
<label>모델<select id="zModel"></select></label>
<p class="zdesc zw" id="zDesc"></p>
<label class="zw">프롬프트<textarea id="zPrompt" rows="4" placeholder="만들 장면·문구를 자세히. 제품은 참조 사진을 꼭 넣어주세요(AI 가 제품 모양을 바꿀 수 있어요)"></textarea></label>
<label class="zw">옵션<input id="zOpt" placeholder="예) 9:16, 5초, 1080p, 2장 — 모델이 지원하는 것만 적용돼요"></label>
<label class="zw">참조 파일 (최대 5개 · 이미지·영상·오디오)<input type="file" id="zFiles" multiple accept="image/jpeg,image/png,image/webp,video/*,audio/*"></label>
<label class="zw ck"><input type="checkbox" id="zUseSel"> 지금 고른 레퍼런스 카드 <b id="zSelN">0</b>개 대표 이미지를 참조로 쓰기</label>
<div class="zgo"><button type="submit" id="zGo">견적 받기 (무료)</button><span id="zMsg" class="zn" style="margin:0"></span></div>
</form>
<div class="zl" id="zList"></div>
</section>
<script type="application/json" id="zmodels">__MODELS__</script>'''.replace('__MODELS__', json.dumps(ML, ensure_ascii=False).replace('</', '<\\/'))

ZCRE_JS = r'''<script>
(()=>{const $=id=>document.getElementById(id),ZM=JSON.parse($('zmodels').textContent),ST={quoting:'견적 받는 중',quoted:'견적 나옴 · 승인 대기',running:'생성 중',done:'완료',failed:'실패',cancelled:'취소됨',price_up:'견적 올라서 멈춤'};
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let ZLOCAL=[],ZT=null,ZLAST=null;
function fill(){const m=$('zMedia').value,gs=[...new Set(ZM.filter(x=>x.media===m).map(x=>x.group))];
 $('zModel').innerHTML=gs.map(g=>`<optgroup label="${esc(g.includes('추천')?'★ '+g:g)}">${ZM.filter(x=>x.media===m&&x.group===g).map(x=>`<option value="${esc(x.model_name)}">${esc(x.model_name)} — ${esc(x.short)}</option>`).join('')}</optgroup>`).join('');desc()}
function desc(){const x=ZM.find(y=>y.model_name===$('zModel').value);$('zDesc').innerHTML=x?`<b>${esc(x.group)}</b> · ${esc(x.desc)}`:''}
$('zMedia').onchange=fill;$('zModel').onchange=desc;fill();
try{const w=localStorage.getItem('bokgak-who');if(w)$('zWho').value=w}catch(e){}
const selN=()=>{try{return typeof sel!=='undefined'?sel.size:0}catch(e){return 0}};
function render(z){ZLAST=z;$('zSelN').textContent=selN();
 if(z&&z.balance!=null)$('zBal').textContent=`잔액 ${(+z.balance).toLocaleString()} 크레딧 · 이번 달 사용 ${(+z.month_used||0).toLocaleString()}${z.balance_at?' · '+z.balance_at+' 기준':''}`;else if(z)$('zBal').textContent='잔액은 첫 견적 때 확인돼요';
 const items=((z&&z.items)||[]);const have=new Set(items.map(x=>x.rid));ZLOCAL=ZLOCAL.filter(x=>!have.has(x.job)&&Date.now()-x.t<15*60e3);
 const loc=ZLOCAL.map(x=>`<div class="zi"><div class="t"><span class="zst">요청 접수됨</span><b>${esc(x.model)}</b>${esc(x.by)} · 1분 안에 Claude 가 견적 시작</div><div class="p">${esc(x.prompt)}</div></div>`).join('');
 $('zList').innerHTML=loc+items.map(x=>{const st=x.state;let b='';
  if(st==='quoted'||st==='price_up'){const c=st==='price_up'?x.new_credits:x.credits;b=`<div class="zrv">${esc(x.review||'')}</div>${x.err?`<div class="zn" style="color:#c62828">${esc(x.err)}</div>`:''}<div class="zbt"><button type="button" data-run="${esc(x.rid)}" data-c="${esc(c)}">승인하고 생성 · 최대 ${esc(c)} 크레딧</button><button type="button" class="sec" data-cx="${esc(x.rid)}">취소</button></div><div class="zn">승인 전엔 크레딧이 나가지 않아요</div>`}
  else if(st==='done')b=`<div class="zg">${(x.files||[]).map((f,i)=>`<figure>${f.media==='video'?`<video src="${esc(f.url)}" controls playsinline preload="metadata"></video>`:f.media==='audio'?`<audio src="${esc(f.url)}" controls></audio>`:`<img src="${esc(f.url)}" alt="결과 ${i+1}" loading="lazy">`}<a href="${esc(f.url)}" download>받기</a></figure>`).join('')}</div>`
  else if(st==='failed')b=`<div class="zn" style="color:#c62828">${esc(x.err||'')}</div>`;
  else if(st==='running')b='<div class="zn">ZCRE 에서 만드는 중이에요. 끝나면 여기 결과가 떠요(영상은 몇 분).</div>';
  return `<div class="zi"><div class="t"><span class="zst ${esc(st)}">${esc(ST[st]||st)}</span><b>${esc(x.model)}</b>${esc(x.by||'')} · ${esc(x.at||'')}${x.nref?` · 참조 ${x.nref}개`:''}${st==='done'&&x.used!=null?` · ${esc(x.used)} 크레딧 사용`:''}${st==='quoted'&&x.credits!=null?` · 견적 ${esc(x.credits)} 크레딧`:''}</div>${x.prompt?`<div class="p">${esc(x.prompt)}${x.opts?`\n<small>옵션: ${esc(x.opts)}</small>`:''}</div>`:''}${b}</div>`}).join('')||(loc?'':'<div class="zn">아직 요청이 없어요.</div>');
}
async function poll(){clearTimeout(ZT);if($('zcre').hidden)return;let busy=ZLOCAL.length>0;
 try{const r=await (await fetch('api/bokgak?zcre=1',{cache:'no-store'})).json();render(r.zcre);busy=busy||((r.zcre&&r.zcre.items)||[]).some(x=>['quoting','running'].includes(x.state))}catch(e){}
 ZT=setTimeout(poll,busy?4000:20000)}
window.zOpen=()=>{render(ZLAST);poll()};
$('zOpenBtn').onclick=()=>{const on=$('zcre').hidden;document.querySelectorAll('.bar .chip').forEach(c=>c.setAttribute('aria-pressed',String(!on&&c.dataset.f==='all')));document.querySelectorAll('.sub').forEach(d=>d.hidden=true);
 $('zOpenBtn').setAttribute('aria-pressed',String(on));show(on?'zcre':'all');if(on)$('zcre').scrollIntoView({behavior:'smooth',block:'start'})};
document.querySelectorAll('.bar .chip').forEach(c=>c.addEventListener('click',()=>$('zOpenBtn').setAttribute('aria-pressed','false')));
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!$('zcre').hidden)poll()});
$('zForm').onsubmit=async e=>{e.preventDefault();const m=$('zMsg'),b=$('zGo'),by=$('zWho').value,prompt=$('zPrompt').value.trim(),fs=[...$('zFiles').files].slice(0,5);
 const refs=$('zUseSel').checked?[...(typeof sel!=='undefined'?sel:[])].slice(0,5):[];
 if(!by){m.textContent='담당자를 골라주세요';return}if(!prompt&&!fs.length&&!refs.length){m.textContent='프롬프트나 참조 파일을 넣어주세요';return}
 b.disabled=true;try{localStorage.setItem('bokgak-who',by)}catch(e){}
 try{const assets=[];for(const [k,f] of fs.entries()){if(f.size>30*1024*1024)throw new Error((k+1)+'번 파일이 30MB 넘어요');assets.push(await upFile(f,p=>m.textContent=`파일 올리는 중… ${k+1}/${fs.length} (${p}%)`))}
  const body={type:'zcre_quote',by,model:$('zModel').value,media:$('zMedia').value,prompt,opts:$('zOpt').value.trim(),refs,assets};
  const r=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})).json();if(!r.ok)throw new Error(r.msg);
  ZLOCAL.unshift({job:r.job,by,model:body.model,prompt,t:Date.now()});m.textContent='견적 요청했어요 (무료) — 1~2분 안에 아래에 크레딧이 떠요';$('zFiles').value='';render(ZLAST);poll()}
 catch(err){m.textContent='실패: '+err.message}b.disabled=false};
$('zList').addEventListener('click',async e=>{const r=e.target.closest('[data-run]'),c=e.target.closest('[data-cx]');if(!r&&!c)return;
 const by=$('zWho').value;
 if(r&&!confirm(`최대 ${r.dataset.c} 크레딧을 써서 생성할까요?\n(견적이 5분 지났으면 다시 받고, 더 비싸지면 멈춰요)`))return;
 const t=r||c;t.disabled=true;t.textContent=r?'승인 보냄 · 곧 시작':'취소 중…';
 try{const x=await (await fetch('api/bokgak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:r?'zcre_run':'zcre_cancel',rid:(r||c).dataset[r?'run':'cx'],by})})).json();if(!x.ok)throw new Error(x.msg);poll()}catch(err){t.textContent='실패: '+err.message}});
})();
</script>'''
