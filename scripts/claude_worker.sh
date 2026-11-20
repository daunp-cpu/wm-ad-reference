#!/bin/zsh
# 2분마다: Claude 대기열(data/claude_queue/*.json)에서 요청 하나를 꺼내 Claude Code 가 직접 복각·수정 → 검수 페이지 반영 → 배포 → 알림.
# 작업기(worker.sh)는 복각·다시 복각·수정 요청을 Gemini 로 만들지 않고 여기 대기열에 넣기만 한다(2026-10-21 다운 지시).
export PATH=/Users/daun/.local/bin:/Users/daun/.local/node/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
R=$(cd "$(dirname "$0")/.." && pwd); cd $R
SITE=$(basename $R)
Q=$R/data/claude_queue; mkdir -p $Q/doing $Q/done
# launchd 는 이 스크립트가 돌고 있으면 또 띄우지 않음 → 인자 없이 불리면 '분배기'로만 동작:
# 대기 요청 수만큼(최대 $MAXJ) 작업을 따로 띄우고 바로 끝남. 그래서 요청이 들어오면 앞 작업이 안 끝났어도 바로 시작.
# 동시 제작 한도: 사이트마다 5개(두 사이트 합쳐 10개 = 맥 코어 수, 2026-10-26 다운 "올릴 수 있는 만큼")
MAXJ=5
if [ "$1" != run ]; then
  mkdir -p $Q/hold; for H in $(find $Q/hold -name "*.json" -mmin +5 2>/dev/null); do mv $H $Q/$(basename $H); done
  for n in $(seq $MAXJ); do
    [ -n "$(ls $Q | grep '\.json$')" ] || break
    nohup zsh $0 run >> $R/logs/claude_worker.log 2>&1 &
    sleep 3
  done
  exit 0
fi
# 동시에 최대 $MAXJ건(빈 자리 하나를 잡음). 요청은 mv 로 집어서 두 작업기가 같은 걸 잡지 않음
LOCK=
for n in $(seq $MAXJ); do L=/tmp/$SITE-claude-$n.lock
  if [ -e $L ] && [ $(( $(date +%s) - $(stat -f %m $L) )) -lt 9000 ]; then continue; fi
  rm -f $L; rmdir $L.d 2>/dev/null   # 오래된 잠금(비정상 종료) 정리
  if mkdir $L.d 2>/dev/null; then touch $L; LOCK=$L; break; fi
done
[ -z "$LOCK" ] && exit 0
trap "rm -f $LOCK; rmdir $LOCK.d 2>/dev/null" EXIT
J=
for B in $(ls -tr $Q | grep '\.json$' | sed 's/\.json$//'); do if mv $Q/$B.json $Q/doing/$B.json 2>/dev/null; then J=$B; break; fi; done
[ -z "$J" ] && exit 0
PY=/Users/daun/meta-ads/.venv/bin/python
W=$R/data/claude_work/$J; mkdir -p $W/out
echo "===== $(date '+%F %T') Claude 직접 복각 $J ====="
$PY -I scripts/claude_prep.py $Q/doing/$J.json $W || { echo "준비 실패"; }
# 2026-11-10 다운: 팀원 요청은 그 팀원 맥의 Claude(본인 계정)로 — 등록된 팀원이면 꾸러미로 보내고 끝(맥이 켜질 때까지 기다림).
# 팀원 맥 등록 = Blob team/<id>.json (팀원 setup 이 씀). 이름→id 는 ~/wm-claude/members.json. 보내기 실패하면 이 맥에서 직접.
WHO=$($PY -I -c "import json;print(json.load(open('$W/brief.json')).get('by') or '다운')" 2>/dev/null)
RID=$($PY -I -c "import json,sys;print(json.load(open('/Users/daun/wm-claude/members.json')).get(sys.argv[1],''))" "$WHO" 2>/dev/null)
# 🔴 2026-11-11 다운: "팀원 요청이 내 컴퓨터로 도는 것 무조건 차단" → 다운 본인 요청만 이 맥에서 만든다.
#   팀원(다운이 아닌 모든 요청자)은 보내기 성공해야만 진행. 미등록·맥 미등록·보내기 실패면 이 맥에서 만들지 않고 hold 에 두었다가 5분 뒤 다시 시도.
if [ "$WHO" != "다운" ]; then
  if [ -n "$RID" ] && [ "$(node scripts/remote.mjs getjson team/$RID.json 2>/dev/null)" != null ]; then
    zsh scripts/remote_send.sh $J $W "$WHO" $RID && { echo "→ ${WHO}님 맥으로 보냄"; exit 0; }
    echo "원격 보내기 실패 → 이 맥에서 만들지 않음, 5분 뒤 재시도"
  else
    echo "요청자 '$WHO' 맥이 등록 안 됨(members.json·team 등록 확인) → 이 맥에서 만들지 않음, 대기"
  fi
  mkdir -p $Q/hold; mv $Q/doing/$J.json $Q/hold/$J.json; exit 0
fi
date +%s > $W/t0
node scripts/blob.mjs status "{\"state\":\"working\",\"job\":\"$J\",\"ids\":[],\"step\":\"Claude 가 직접 편집 중\",\"all\":1,\"t0\":$(cat $W/t0),\"exp\":2400}" >/dev/null 2>&1
# 2026-11-10 다운: "복각 사이트 = 채팅의 너를 그대로 복사한 것. 같은 모델·같은 메모리·같은 도구로, 필요한 리소스 다 끌고 와서 채팅 퀄리티로"
# → 모델 고정(Opus 5.5), 도구 제한 없음, 메모리는 채팅 메모리 폴더 공유(~/.claude/projects/-Users-daun-*-reference/memory → -Users-daun/memory 링크),
#   수정하기는 이전 버전을 만든 대화를 이어서(--resume … --fork-session) 앞 맥락을 기억한 채로 고침.
PROMPT="광고 레퍼런스 복각 요청 1건을 네가 직접 만든다. 이 요청은 다운이 채팅으로 너에게 직접 시키는 것과 똑같다 — 팀원(요청자: brief.json 의 by)이 다운 계정 대신 이 사이트로 너를 쓰는 것이니, 채팅에서 다운에게 해주는 것과 같은 퀄리티로 만든다.
1) 먼저 메모리 MEMORY.md 를 읽고, 이 요청과 관련된 메모(복각·SOOO/BH 광고주·영상/이미지 편집·제품 사진·BGM·자막·색감 등)를 전부 열어 그 피드백을 지킨다.
2) $R/scripts/claude_bokgak.md 를 끝까지 읽고 따른다. 요청 정보는 $W/brief.json, 작업폴더는 $W (결과물은 $W/out).
3) 채팅에서처럼 필요한 리소스는 뭐든 직접 찾아 가져온다(로컬·드라이브·랜딩페이지·노션·웹·ZCRE 등, 지시서의 비용 한도 안에서). 막히면 다른 방법을 찾고, 그래도 안 되는 것만 note 에 적는다.
4) 검수 바퀴(서브에이전트 리뷰어·나란히 비교·확대 검사)는 돌리지 않는다(2026-11-11 다운: 내가 직접 검수한다, 용량 절약). 한 번에 제대로 만들어 바로 올린다. 퀄리티가 먼저. 스스로 아는 문제가 남으면 summary 맨 앞에 '⚠ 확인 필요: <무엇이 왜>'를 적는다.
5) 이번 요청·피드백에서 새로 배운 것(반복될 실수·다운/팀원 취향)은 메모리 규칙대로 메모에 저장해 다음 요청에 쓴다.
다 만들고 검수한 뒤 $W/result.json 을 지시서 형식대로 쓰고 끝낸다. 사이트 기록·배포·메타 광고는 건드리지 않는다."
SID=$(uuidgen | tr A-Z a-z); RES=()
# 수정하기: 이전 버전을 만든 대화가 있으면 그 대화를 이어서(분기) — 채팅에서 v1→v2 하듯 앞 맥락을 기억
BW=$($PY -I -c "import json;print(json.load(open('$W/brief.json')).get('base_work') or '')" 2>/dev/null)
if [ -n "$BW" ] && [ -f "$BW/session_id" ]; then
  OS=$(cat "$BW/session_id")
  if ls ~/.claude/projects/*/$OS.jsonl >/dev/null 2>&1; then RES=(--resume $OS --fork-session); PROMPT="[같은 소재 수정 요청 — 앞에서 네가 만든 버전에 대한 새 피드백] $PROMPT"; echo "이전 대화 이어서: $OS"; fi
fi
echo $SID > $W/session_id
# 최대 2시간 — 넘으면 멈추고 실패 카드로
perl -e 'alarm shift; exec @ARGV' 7200 claude -p "$PROMPT" --model claude-sonnet-5-5 --effort high "${RES[@]}" --session-id $SID --permission-mode bypassPermissions \
  --add-dir $W --add-dir /Users/daun/Downloads --add-dir /Users/daun/Movies --add-dir /Users/daun/ad-reference --add-dir /Users/daun/bh-reference --add-dir /Users/daun/.claude/projects/-Users-daun/memory --output-format text > $W/claude.log 2>&1
echo "Claude 종료 코드 $?"; tail -5 $W/claude.log
# 사이트 기록 반영(작업기와 겹치지 않게 작업기 잠금을 잡고)
WL=/tmp/$SITE-worker.lock
while [ -e $WL ] && [ $(( $(date +%s) - $(stat -f %m $WL) )) -lt 3600 ]; do sleep 15; done
touch $WL
cp data/review.json data/review.json.bak_claude 2>/dev/null
$PY -I scripts/claude_finish.py $W/brief.json $W/result.json
mv $Q/doing/$J.json $Q/done/$J.json
$PY -I scripts/build_review.py
zsh scripts/deploy.sh
# 배포가 끝난 다음에 '완료' 표시 → 검수 페이지가 자동 새로고침할 때 새 결과가 바로 보임
node scripts/blob.mjs done "$J" >/dev/null 2>&1
node scripts/blob.mjs stdone "$J" >/dev/null 2>&1
# 다른 Claude 작업이 아직 돌고 있으면 전체 상태는 그대로 둔다(남의 진행 막대를 지우지 않게)
[ $(ls -d /tmp/$SITE-claude-*.lock.d 2>/dev/null | wc -l) -le 1 ] && node scripts/blob.mjs status '{"state":"idle"}' >/dev/null 2>&1
rm -f $WL
ls $Q/*.json >/dev/null 2>&1 && launchctl kickstart gui/$(id -u)/com.daun.$SITE-claude >/dev/null 2>&1
D=$(TZ=Asia/Seoul date +%F)
URL=$([ "$SITE" = bh-reference ] && echo https://wm-bh-reference.vercel.app || echo https://your-site.vercel.app)
osascript -e "display notification \"Claude 가 직접 만든 복각 소재가 검수 페이지에 올라갔어요\" with title \"광고 레퍼런스\"" 2>/dev/null
# open "$URL/review.html?d=$D"   # 11/10 다운: 작업 중 화면에 뜨지 않게 — 알림만
