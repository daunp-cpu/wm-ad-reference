"""소재공유방 레퍼런스에 후킹 포인트·응용 아이디어·태그·흐름 분류 붙이기(Gemini Flash, 이미 한 건 건너뜀).
팀원 메모에 있는 말은 원문 그대로 쓰고, 없을 때만 AI 제안(표시 붙음)."""
import json, os, sys, base64, urllib.request, urllib.error, time
R = '/Users/daun/ad-reference/'; KEY = open(os.path.expanduser('~/.config/gemini/key')).read().strip()
refs = json.load(open(R + 'data/slack_refs.json')); msgs = {m['ts']: m for m in json.load(open(R + 'data/slack/messages.json'))}
FORCE = '--all' in sys.argv


def gem(parts, model='gemini-flash-latest'):
    body = {'contents': [{'parts': parts}], 'generationConfig': {'temperature': 0.2, 'responseMimeType': 'application/json'}}
    rq = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', data=json.dumps(body).encode(),
                                headers={'x-goog-api-key': KEY, 'Content-Type': 'application/json'}, method='POST')
    for k in range(3):
        try: return json.loads(json.loads(urllib.request.urlopen(rq, timeout=120).read())['candidates'][0]['content']['parts'][0]['text'])
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and k < 2: time.sleep(15); continue
            raise RuntimeError(f'HTTP {e.code}: {e.read().decode()[:200]}')


n = 0
for x in refs:
    if x.get('hook') is not None and not FORCE: continue
    m = msgs.get(x['ts'], {}); th = m.get('thread') or []
    prompt = f"""팀 슬랙 #소재공유방에 팀원이 공유한 광고 레퍼런스를 정리한다. SOOO(탈모 증상 완화 샴푸) 소재 기획에 쓸 것이다.
팀원 메모(원문): {x.get('note') or '(없음)'}
스레드 답글: {' / '.join(th) or '(없음)'}
인스타 계정: {x.get('account')} · 형식: {'영상 ' + x['dur'] if x['kind'] == 'video' else '이미지'}
원문 캡션: {(x.get('caption') or '')[:500]}
첨부 = 대표 이미지.
규칙: 팀원 메모에 있는 말은 고치지 말고 그대로 옮긴다(맞춤법도 그대로). 메모가 'A > B' 처럼 후킹 장면과 적용·전개를 같이 쓰면 앞은 hook, 뒤는 idea.
메모에 응용(적용) 내용이 없으면 idea 는 SOOO 탈모샴푸에 이 형식을 어떻게 쓸지 한 줄 제안하고 idea_ai=true. 메모가 비었으면 hook 도 영상/캡션을 보고 한 줄로 쓰고 hook_ai=true.
JSON만: {{"hook":"","hook_ai":false,"idea":"","idea_ai":false,"tags":["3~7개, 짧게(예: 젊은층, 실사 UGC, 후킹, 고민, B&A, 정보성, 자막, AI, 밈, 가격)"],"flow":"형식 · 흐름을 → 로(예: 실사 UGC · '이거 ~ 아니에요' 후킹 → 원인 설명 → 전후 비교 → 댓글 유도)"}}"""
    parts = [{'inline_data': {'mime_type': 'image/jpeg', 'data': base64.b64encode(open(R + f"site/m/L{x['id']}.jpg", 'rb').read()).decode()}}, {'text': prompt}]
    try:
        o = gem(parts); o = o[0] if isinstance(o, list) else o
        x.update(hook=o.get('hook', ''), hook_ai=bool(o.get('hook_ai')), idea=o.get('idea', ''), idea_ai=bool(o.get('idea_ai')), tags=o.get('tags', [])[:7], flow=o.get('flow', ''), thread=th)
        n += 1; print('정리', x['id'], x['hook'][:30], '|', x['idea'][:30], flush=True)
    except Exception as e: print('실패', x['id'], str(e)[:120], flush=True)
    json.dump(refs, open(R + 'data/slack_refs.json', 'w'), ensure_ascii=False, indent=1)
print('정리 완료', n)
