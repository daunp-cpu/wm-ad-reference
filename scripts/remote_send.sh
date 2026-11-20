#!/bin/zsh
# 팀원 요청을 그 팀원 맥으로 보낸다(2026-11-10 다운: "각자 자기 Claude 로, 맥이 켜질 때까지 기다리기").
# 사용: remote_send.sh <job> <작업폴더 W> <요청자 이름> <팀원 id>
# 다운 맥(허브)이 claude_prep 까지 끝낸 작업폴더 + brief 가 가리키는 파일(레퍼런스·첨부 에셋·이전 버전 폴더)을
# tar 로 묶어 Blob {P}rq/<job>.tar 에 올리고, {P}rq/<id>.json(그 팀원 대기 목록)에 넣는다.
# 결과는 remote_collect.sh 가 {P}rr/<job>.json 을 보고 가져와 검수 페이지에 올린다.
export PATH=/Users/daun/.local/bin:/Users/daun/.local/node/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
R=$(cd "$(dirname "$0")/.." && pwd); cd $R; SITE=$(basename $R)
P=$([ "$SITE" = bh-reference ] && echo bh- || echo "")
J=$1; W=$2; WHO=$3; ID=$4
PY=/Users/daun/meta-ads/.venv/bin/python
Q=$R/data/claude_queue; mkdir -p $Q/remote
T=/tmp/wm-send-$SITE-$J; rm -rf $T; mkdir -p $T
$PY -I - "$W" "$HOME" > $T/list <<'EOF'
import json, os, sys
W, H = sys.argv[1].rstrip('/'), sys.argv[2]
b = json.load(open(W + '/brief.json'))
out = {os.path.relpath(W, H)}
def walk(x):
    if isinstance(x, dict): [walk(v) for v in x.values()]
    elif isinstance(x, list): [walk(v) for v in x]
    elif isinstance(x, str) and x.startswith(H + '/') and os.path.isfile(x) and os.path.getsize(x) < 1.5e9:
        out.add(os.path.relpath(x, H))   # 파일만 — 폴더(root 등)는 통째로 묶지 않음
walk(b)
bw = (b.get('base_work') or '').rstrip('/')
if bw and os.path.isdir(bw): out.add(os.path.relpath(bw, H))   # 수정하기: 이전 버전 폴더
print('\n'.join(sorted(out)))
EOF
tar -C $HOME -cf $T/pack.tar -T $T/list || { echo "꾸러미 묶기 실패"; exit 1; }
echo "꾸러미 $(du -h $T/pack.tar | cut -f1) ($(wc -l < $T/list)개 항목) → $WHO 맥"
node scripts/remote.mjs push "${P}rq/$J.tar" $T/pack.tar || { echo "올리기 실패"; exit 1; }
# 그 팀원 대기 목록에 추가(목록은 허브만 쓴다)
L=$(node scripts/remote.mjs getjson "${P}rq/$ID.json")
L=$($PY -I -c "import json,sys;l=json.loads(sys.argv[1]) or [];j=sys.argv[2];l=l+[j] if j not in l else l;print(json.dumps(l))" "$L" "$J")
node scripts/remote.mjs putjson "${P}rq/$ID.json" "$L"
printf '{"who":"%s","id":"%s","sent":%s}' "$WHO" "$ID" $(date +%s) > $Q/remote/$J.json
node scripts/blob.mjs status "{\"state\":\"working\",\"job\":\"$J\",\"ids\":[],\"step\":\"${WHO}님 맥에서 만들 차례 (맥이 켜져 있으면 곧 시작)\",\"all\":1,\"t0\":$(date +%s),\"exp\":2400}" >/dev/null 2>&1
rm -rf $T
