#!/bin/zsh
# 검색창 실시간 수집 1건 (2026-11-11). worker.sh 가 libsearch 요청을 data/libsearch/jobs/<job>.json 으로 옮기고 이걸 띄움.
# → Blob ls/<키>.json 을 running → done(광고 목록)으로. 페이지가 GET api/bokgak?ls=<키> 로 받아 그림.
export PATH=/Users/daun/.local/node/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/daun/ad-reference
J=$1; F=data/libsearch/jobs/$J.json; [ -f $F ] || exit 1
PY=/Users/daun/meta-ads/.venv/bin/python
K=$($PY -I -c "import json,sys;print(json.load(open(sys.argv[1]))['key'])" $F)
Q=$($PY -I -c "import json,sys;print(json.load(open(sys.argv[1]))['q'])" $F)
TERMS=("${(@f)$($PY -I -c "import json,sys;[print(t) for t in json.load(open(sys.argv[1])).get('terms') or [json.load(open(sys.argv[1]))['q']]]" $F)}")
O=data/libsearch/$K.json; T=$(mktemp /tmp/ls.XXXX)
echo "===== $(date '+%F %T') 실시간 검색: $Q (${#TERMS}개 검색어) ====="
printf '{"state":"running","q":%s,"terms":%s,"req":%s,"at":%s}' "$($PY -I -c 'import json,sys;print(json.dumps(sys.argv[1],ensure_ascii=False))' "$Q")" "$($PY -I -c 'import json,sys;print(json.dumps(sys.argv[1:],ensure_ascii=False))' "${TERMS[@]}")" "$(date +%s)000" "$(date +%s)000" > $T
node scripts/blob.mjs putjson ls/$K.json $T >/dev/null
if perl -e 'alarm shift; exec @ARGV' 360 node scripts/libsearch.mjs $O "${TERMS[@]}"; then
  node scripts/blob.mjs putjson ls/$K.json $O >/dev/null && echo "올림: $(grep -o '"n":[0-9]*' $O | head -1)"
else
  printf '{"state":"fail","q":%s,"at":%s}' "$($PY -I -c 'import json,sys;print(json.dumps(sys.argv[1],ensure_ascii=False))' "$Q")" "$(date +%s)000" > $T; node scripts/blob.mjs putjson ls/$K.json $T >/dev/null; echo "실패"
fi
rm -f $T; mv $F data/libsearch/jobs/done_$J.json 2>/dev/null
