#!/bin/zsh
# 팀원 맥이 끝낸 결과를 가져와 검수 페이지에 올린다(2026-11-10). launchd com.daun.<사이트>-remote 가 1분마다.
# 팀원 맥은 {P}rr/<job>.tar(작업폴더 통째) + {P}rr/<job>.json({home,by,ok}) 를 올린다.
export PATH=/Users/daun/.local/bin:/Users/daun/.local/node/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
R=$(cd "$(dirname "$0")/.." && pwd); cd $R; SITE=$(basename $R)
P=$([ "$SITE" = bh-reference ] && echo bh- || echo "")
PY=/Users/daun/meta-ads/.venv/bin/python
Q=$R/data/claude_queue; mkdir -p $Q/remote $Q/doing $Q/done
for f in $Q/remote/*.json(N); do
  J=${f:t:r}
  M=$(node scripts/remote.mjs getjson "${P}rr/$J.json" 2>/dev/null)
  [ -z "$M" -o "$M" = null ] && continue
  echo "===== $(date '+%F %T') 팀원 맥 결과 받기 $J ====="
  ID=$($PY -I -c "import json;print(json.load(open('$f'))['id'])")
  WHO=$($PY -I -c "import json;print(json.load(open('$f'))['who'])")
  MH=$($PY -I -c "import json,sys;print(json.loads(sys.argv[1]).get('home',''))" "$M")
  W=$R/data/claude_work/$J; T=/tmp/wm-coll-$SITE-$J; rm -rf $T; mkdir -p $T
  node scripts/remote.mjs pull "${P}rr/$J.tar" $T/r.tar || { echo "받기 실패 — 다음에 다시"; continue; }
  tar -C $T -xf $T/r.tar || { echo "풀기 실패"; continue; }
  REL=${SITE}/data/claude_work/$J
  [ -d $T/$REL ] || { echo "꾸러미에 작업폴더 없음"; continue; }
  mkdir -p $W; rsync -a $T/$REL/ $W/
  # 팀원 맥 경로 → 이 맥 경로 (result.json 의 img·mp4 등 절대경로)
  [ -f $W/result.json ] && $PY -I - "$W/result.json" "$MH" "$HOME" <<'EOF'
import json, sys
p, a, b = sys.argv[1:4]
def fix(x):
    if isinstance(x, dict): return {k: fix(v) for k, v in x.items()}
    if isinstance(x, list): return [fix(v) for v in x]
    if isinstance(x, str) and a and x.startswith(a + '/'): return b + x[len(a):]
    return x
d = json.load(open(p)); json.dump(fix(d), open(p, 'w'), ensure_ascii=False, indent=1)
EOF
  echo "$WHO 맥에서 완성 → 반영"
  WL=/tmp/$SITE-worker.lock
  while [ -e $WL ] && [ $(( $(date +%s) - $(stat -f %m $WL) )) -lt 3600 ]; do sleep 15; done
  touch $WL
  cp data/review.json data/review.json.bak_claude 2>/dev/null
  if [ -f $W/result.json ]; then $PY -I scripts/claude_finish.py $W/brief.json $W/result.json; else $PY -I scripts/claude_finish.py $W/brief.json 없음; fi
  [ -f $Q/doing/$J.json ] && mv $Q/doing/$J.json $Q/done/$J.json
  $PY -I scripts/build_review.py
  zsh scripts/deploy.sh
  node scripts/blob.mjs done "$J" >/dev/null 2>&1
  node scripts/blob.mjs stdone "$J" >/dev/null 2>&1
  [ $(ls -d /tmp/$SITE-claude-*.lock.d 2>/dev/null | wc -l) -lt 1 ] && [ -z "$(ls $Q/remote/*.json(N) 2>/dev/null | grep -v $J)" ] && node scripts/blob.mjs status '{"state":"idle"}' >/dev/null 2>&1
  rm -f $WL
  # 정리: 꾸러미·결과·대기 목록
  node scripts/remote.mjs del "${P}rq/$J.tar"; node scripts/remote.mjs del "${P}rr/$J.tar"; node scripts/remote.mjs del "${P}rr/$J.json"
  L=$(node scripts/remote.mjs getjson "${P}rq/$ID.json")
  L=$($PY -I -c "import json,sys;l=json.loads(sys.argv[1]) or [];print(json.dumps([x for x in l if x!=sys.argv[2]]))" "$L" "$J")
  node scripts/remote.mjs putjson "${P}rq/$ID.json" "$L"
  rm -f $f; rm -rf $T
  osascript -e "display notification \"${WHO}님 맥에서 만든 복각 소재가 검수 페이지에 올라갔어요\" with title \"광고 레퍼런스\"" 2>/dev/null
done
# ZCRE 탭(견적·생성) 결과도 같이 받는다(2026-11-11)
[ "$SITE" = ad-reference ] && zsh scripts/zcre_collect.sh
