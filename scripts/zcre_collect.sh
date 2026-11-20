#!/bin/zsh
# 팀원 맥이 끝낸 ZCRE 견적·생성 결과를 가져와 반영(remote_collect.sh 가 1분마다 부름). 2026-11-11
export PATH=/Users/daun/.local/bin:/Users/daun/.local/node/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
R=/Users/daun/ad-reference; cd $R
PY=/Users/daun/meta-ads/.venv/bin/python
for f in $R/data/zcre/remote/*.json(N); do
  J=${f:t:r}; RID=${J%.*}; ST=${J##*.}
  M=$(node scripts/remote.mjs getjson "zrr/$J.json" 2>/dev/null)
  [ -z "$M" -o "$M" = null ] && continue
  echo "===== $(date '+%F %T') ZCRE 팀원 맥 결과 받기 $J ====="
  ID=$($PY -I -c "import json;print(json.load(open('$f'))['id'])"); WHO=$($PY -I -c "import json;print(json.load(open('$f'))['who'])")
  MH=$($PY -I -c "import json,sys;print(json.loads(sys.argv[1]).get('home',''))" "$M")
  T=/tmp/wm-zcoll-$J; rm -rf $T; mkdir -p $T
  node scripts/remote.mjs pull "zrr/$J.tar" $T/r.tar || { echo "받기 실패 — 다음에 다시"; continue; }
  tar -C $T -xf $T/r.tar || { echo "풀기 실패"; continue; }
  REL=ad-reference/data/zcre/$RID; W=$R/data/zcre/$RID
  [ -d $T/$REL ] || { echo "꾸러미에 작업폴더 없음"; continue; }
  mkdir -p $W; rsync -a --exclude brief.json --exclude approved.json --exclude 'in/' $T/$REL/ $W/
  for j in $W/quote.json $W/result.json; do [ -f $j ] && $PY -I - "$j" "$MH" "$HOME" <<'EOF'
import json, sys
p, a, b = sys.argv[1:4]
def fix(x):
    if isinstance(x, dict): return {k: fix(v) for k, v in x.items()}
    if isinstance(x, list): return [fix(v) for v in x]
    if isinstance(x, str) and a and x.startswith(a + '/'): return b + x[len(a):]
    return x
json.dump(fix(json.load(open(p))), open(p, 'w'), ensure_ascii=False, indent=1)
EOF
  done
  if [ "$ST" = q ]; then
    $PY -I scripts/zcre.py quoted $RID
  else
    $PY -I scripts/zcre.py ran $RID
    WL=/tmp/ad-reference-worker.lock
    while [ -e $WL ] && [ $(( $(date +%s) - $(stat -f %m $WL) )) -lt 3600 ]; do sleep 10; done
    touch $WL; $PY -I scripts/build_review.py >/dev/null; zsh scripts/deploy.sh | tail -1; rm -f $WL
    $PY -I scripts/zcre.py push
    osascript -e "display notification \"${WHO}님 맥에서 ZCRE 생성이 끝났어요\" with title \"SOOO 소재 제작\"" 2>/dev/null
  fi
  node scripts/remote.mjs del "zrq/$J.tar"; node scripts/remote.mjs del "zrr/$J.tar"; node scripts/remote.mjs del "zrr/$J.json"
  L=$(node scripts/remote.mjs getjson "zrq/$ID.json")
  L=$($PY -I -c "import json,sys;l=json.loads(sys.argv[1]) or [];print(json.dumps([x for x in l if x!=sys.argv[2]]))" "$L" "$J")
  node scripts/remote.mjs putjson "zrq/$ID.json" "$L"
  rm -f $f; rm -rf $T
done
