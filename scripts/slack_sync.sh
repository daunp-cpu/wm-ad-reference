#!/bin/zsh
# 하루 1번(아침 8시) + 페이지 새로고침 버튼(worker.sh slacksync)으로 #소재공유방 새 글을 가져와 레퍼런스 페이지에 반영 → 배포. 새 글 없으면 아무것도 안 함. (2026-11-12 5분→하루 1번, 다운)
# 슬랙은 claude.ai 슬랙 커넥터로만 읽히므로 Claude(Haiku)를 잠깐 띄워 읽기만 시킨다(2026-10-21 다운: "소재공유방에서 5분에 한번씩 끌고 오라구").
export PATH=/Users/daun/.local/bin:/Users/daun/.local/node/bin:/usr/bin:/bin:/usr/sbin:/sbin
R=/Users/daun/ad-reference; cd $R
LOCK=/tmp/ad-reference-slack.lock
[ -e $LOCK ] && [ $(( $(date +%s) - $(stat -f %m $LOCK) )) -lt 1500 ] && exit 0
touch $LOCK; trap "rm -f $LOCK" EXIT
PY=/Users/daun/meta-ads/.venv/bin/python
LAST=$($PY -c "import json;m=json.load(open('data/slack/messages.json'));print(max(x['ts'] for x in m))")
OUT=$R/data/slack/new_$(date +%Y%m%d%H%M%S).json; rm -f $OUT
P="슬랙 채널 YOUR_SLACK_CHANNEL_ID 을 slack_read_channel 로 읽어라(oldest=$LAST, limit=100, response_format=detailed). 결과에 'Thread: N replies' 가 있는 메시지는 slack_read_thread(channel_id=YOUR_SLACK_CHANNEL_ID, message_ts=그 메시지 TS)로 답글도 읽어라.
읽은 결과 문자열들을 고치지 말고 그대로 이어 붙여서, Write 도구로 $OUT 에 JSON {\"messages\": \"<이어 붙인 원문>\"} 형식으로 저장해라(줄바꿈·따옴표는 JSON 이스케이프). 새 메시지가 하나도 없으면 파일을 만들지 말고 '없음'만 출력해라. 다른 일은 하지 마라."
perl -e 'alarm shift; exec @ARGV' 600 claude -p "$P" --model haiku --allowedTools "mcp__claude_ai_Slack__slack_read_channel mcp__claude_ai_Slack__slack_read_thread Write" --add-dir $R/data/slack --output-format text > /tmp/ad-reference-slack.log 2>&1
[ -s $OUT ] || exit 0
echo "===== $(date '+%F %T') 소재공유방 새 글 ====="
N0=$($PY -c "import json;print(len(json.load(open('data/slack_refs.json'))))")
$PY -I scripts/slack_parse.py $OUT || exit 0
$PY -I scripts/slack_import.py | tail -20
# $PY -I scripts/slack_files.py | tail -5   # 파일만 올린 글 — 브라우저 다운로드가 아직 안 돼서 잠시 끔(10/21)
N1=$($PY -c "import json;print(len(json.load(open('data/slack_refs.json'))))")
[ "$N1" = "$N0" ] && { echo "새 카드 없음"; exit 0; }
# 사이트 다시 만들기(작업기와 겹치지 않게)
WL=/tmp/ad-reference-worker.lock
while [ -e $WL ] && [ $(( $(date +%s) - $(stat -f %m $WL) )) -lt 3600 ]; do sleep 15; done
touch $WL; $PY -I scripts/build.py | tail -1; zsh scripts/deploy.sh | tail -1; rm -f $WL
osascript -e "display notification \"소재공유방 새 레퍼런스 $((N1-N0))개가 올라왔어요\" with title \"광고 레퍼런스\"" 2>/dev/null
