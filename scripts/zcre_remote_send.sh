#!/bin/zsh
# ZCRE 견적·생성을 그 사람 맥으로 보낸다(2026-11-11 다운: "팀원 요청이 다운 맥에서 돌면 안 됨").
# 사용: zcre_remote_send.sh <rid> <q|r> <요청자 이름> <팀원 id>   (q=견적, r=승인 후 생성)
export PATH=/Users/daun/.local/bin:/Users/daun/.local/node/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
R=/Users/daun/ad-reference; cd $R
RID=$1; ST=$2; WHO=$3; ID=$4; J=$RID.$ST
PY=/Users/daun/meta-ads/.venv/bin/python
mkdir -p data/zcre/remote
T=/tmp/wm-zsend-$J; rm -rf $T; mkdir -p $T
tar -C $HOME -cf $T/pack.tar ad-reference/data/zcre/$RID || { echo "꾸러미 묶기 실패"; exit 1; }
node scripts/remote.mjs push "zrq/$J.tar" $T/pack.tar || { echo "올리기 실패"; exit 1; }
L=$(node scripts/remote.mjs getjson "zrq/$ID.json")
L=$($PY -I -c "import json,sys;l=json.loads(sys.argv[1]) or [];j=sys.argv[2];l=l+[j] if j not in l else l;print(json.dumps(l))" "$L" "$J")
node scripts/remote.mjs putjson "zrq/$ID.json" "$L" || exit 1
printf '{"who":"%s","id":"%s","rid":"%s","stage":"%s","sent":%s}' "$WHO" "$ID" "$RID" "$ST" $(date +%s) > data/zcre/remote/$J.json
rm -rf $T; echo "→ ${WHO}님 맥으로 보냄 ($J)"
