"""Slack #소재공유방 읽기 결과(slack_read_channel 저장 파일) → data/slack/messages.json 에 합치기(ts 기준 중복 제거).
사용: python3 -I slack_parse.py 결과파일 [결과파일...]"""
import json, re, sys, os
R = '/Users/daun/ad-reference/'; OUT = R + 'data/slack/messages.json'
have = {m['ts']: m for m in (json.load(open(OUT)) if os.path.exists(OUT) else [])}
for p in sys.argv[1:]:
    s = json.load(open(p))['messages']
    for b in re.split(r'\n?=== Message from ', s)[1:]:
        m = re.match(r'(.+?) <([^>]*)> \((U\w+)[^)]*\) at (\S+ \S+) KST ===\s*\nMessage TS: (\S+)\n(.*)', b, re.S)   # 외부 사용자는 (U.., external: 회사)
        if not m: continue
        name, mail, uid, at, ts, body = m.groups()
        files = re.findall(r'(\S+) \(ID: (F\w+), ([\w/.+-]+), ([\d.]+ \w+)\)', body)
        links = re.findall(r'<(https?://[^|>]+)', body)
        text = re.split(r'\n<https?://|\nFiles:|\nReactions:|\nThread', body)[0].strip()
        text = re.sub(r'<(https?://[^|>]+)\|[^>]*>', r'\1', text)
        react = re.search(r'Reactions: (.*)', body)
        old = have.get(ts, {})
        have[ts] = dict(old, name=name, uid=uid, at=at, ts=ts, text=text, links=links, react=react.group(1) if react else '',
                        files=[dict(name=f[0], id=f[1], mime=f[2], size=f[3]) for f in files])
out = sorted(have.values(), key=lambda x: x['ts'], reverse=True)
os.makedirs(R + 'data/slack', exist_ok=True); json.dump(out, open(OUT, 'w'), ensure_ascii=False, indent=1)
print('메시지', len(out), '기간', out[-1]['at'], '~', out[0]['at'])
