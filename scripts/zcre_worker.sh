#!/bin/zsh
# ZCRE 생성 탭 요청 1건 처리: zcre_worker.sh <job>  (worker.sh 가 띄움)
# 견적(zcre_quote) → Claude 가 견적만(생성 도구 권한 없음) / 승인(zcre_run) → Claude 가 생성 → 결과 site/z/ 배포 / 취소(zcre_cancel)
export PATH=/Users/daun/.local/bin:/Users/daun/.local/node/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
R=/Users/daun/ad-reference; cd $R
J=$1; PY=/Users/daun/meta-ads/.venv/bin/python
TYPE=$($PY -c "import json;print(json.load(open('data/zcre/jobs/$J.json'))['type'])")
echo "===== $(date '+%F %T') ZCRE $TYPE $J ====="
# 🔴 2026-11-11 다운: 요청자 비면 아예 받지 않음 / 팀원 요청은 그 사람 맥에서만(다운 본인 것만 이 맥)
BY=$($PY -I -c "import json;print(json.load(open('data/zcre/jobs/$J.json')).get('by') or '')")
[ -z "$BY" ] && { echo "요청자 없음 → 받지 않음"; exit 0; }
# 팀원이면 보내고 true, 다운이면 false(이 맥에서 처리). 보내기 실패·맥 미등록이면 이 맥에서 만들지 않고 실패 처리(rid 가 있을 때)
send_member() {   # send_member <rid> <q|r> <요청자>
  [ "$3" = "다운" ] && return 1
  local ID=$($PY -I -c "import json,sys;print(json.load(open('/Users/daun/wm-claude/members.json')).get(sys.argv[1],''))" "$3")
  if [ -n "$ID" ] && [ "$(node scripts/remote.mjs getjson team/$ID.json 2>/dev/null)" != null ]; then
    zsh scripts/zcre_remote_send.sh $1 $2 "$3" $ID && return 0
    $PY -I scripts/zcre.py fail $1 "$3님 맥으로 보내지 못했어요. 잠시 뒤 다시 요청해 주세요"; return 0
  fi
  $PY -I scripts/zcre.py fail $1 "$3님 맥이 등록되지 않았어요(팀원 설정 필요). 다운 맥에서는 만들지 않아요"; return 0
}
Z="mcp__claude_ai_ZCRE__query_zcre mcp__claude_ai_ZCRE__prepare_upload ToolSearch Bash Read Write"
if [ "$TYPE" = "zcre_quote" ]; then
  RID=$J; $PY -I scripts/zcre.py new $J; $PY -I scripts/zcre.py prep $RID
  W=$R/data/zcre/$RID
  send_member $RID q "$BY" && exit 0
  perl -e 'alarm shift; exec @ARGV' 900 claude -p --model claude-sonnet-5-5 "단계 1: 견적. $R/scripts/zcre_claude.md 를 끝까지 읽고 그대로 따른다. 요청은 $W/brief.json, 작업폴더 $W. quote.json 을 쓰고 끝낸다. create_generation 은 부르지 않는다." \
    --allowedTools "$Z" --permission-mode acceptEdits --add-dir $W --output-format text > $W/claude_quote.log 2>&1
  $PY -I scripts/zcre.py quoted $RID
elif [ "$TYPE" = "zcre_run" ]; then
  RID=$($PY -I scripts/zcre.py approve $J)
  [ -z "$RID" ] && { echo "승인할 견적 없음"; exit 0; }
  W=$R/data/zcre/$RID; rm -f $W/result.json
  OWN=$($PY -I scripts/zcre.py owner $RID)   # 견적을 만든 사람 맥에서 생성(견적 토큰이 그 사람 계정 것)
  [ -z "$OWN" ] && { $PY -I scripts/zcre.py fail $RID "견적 요청자가 없어 생성하지 않아요"; exit 0; }
  send_member $RID r "$OWN" && exit 0
  perl -e 'alarm shift; exec @ARGV' 3600 claude -p --model claude-sonnet-5-5 "단계 2: 생성. $R/scripts/zcre_claude.md 를 끝까지 읽고 그대로 따른다. 작업폴더 $W (quote.json·approved.json). result.json 을 쓰고 끝낸다." \
    --allowedTools "$Z mcp__claude_ai_ZCRE__create_generation" --permission-mode acceptEdits --add-dir $W --output-format text > $W/claude_run.log 2>&1
  # 결과 파일을 사이트에 올린 다음 '완료'로 보이게(배포 전에 완료 뜨면 빈 화면)
  $PY - $RID <<'E'
import json,sys,os
w='/Users/daun/ad-reference/data/zcre/'+sys.argv[1]+'/'
print('결과', open(w+'result.json').read()[:300] if os.path.exists(w+'result.json') else '없음')
E
  $PY -I scripts/zcre.py ran $RID
  WL=/tmp/ad-reference-worker.lock
  while [ -e $WL ] && [ $(( $(date +%s) - $(stat -f %m $WL) )) -lt 3600 ]; do sleep 10; done
  touch $WL; $PY -I scripts/build_review.py >/dev/null; zsh scripts/deploy.sh | tail -1; rm -f $WL
  $PY -I scripts/zcre.py push
  osascript -e "display notification \"ZCRE 생성이 끝났어요\" with title \"SOOO 소재 제작\"" 2>/dev/null
elif [ "$TYPE" = "zcre_cancel" ]; then
  $PY -I scripts/zcre.py cancel $J
fi
