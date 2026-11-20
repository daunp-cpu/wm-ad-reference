#!/bin/zsh
# 3분마다: 레퍼런스 페이지 요청 처리. 🔴 복각·다시 복각·수정·'추가하고 바로 복각'은 Gemini 로 만들지 않고 Claude 대기열(data/claude_queue)로
# → scripts/claude_worker.sh 가 Claude Code 로 직접 편집(2026-10-21 다운 지시). 세팅·ON/OFF·대표버전·삭제·레퍼런스 등록은 여기서 바로.
export PATH=/Users/daun/.local/node/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/daun/ad-reference
LOCK=/tmp/ad-reference-worker.lock
[ -e $LOCK ] && [ $(( $(date +%s) - $(stat -f %m $LOCK) )) -lt 3600 ] && exit 0
touch $LOCK; trap "rm -f $LOCK" EXIT
JOBS=$(node scripts/blob.mjs jobs 2>/dev/null) || exit 0
[ -z "$JOBS" -o "$JOBS" = "[]" ] && exit 0
echo "===== $(date '+%F %T') 복각 요청 ====="
PY=/Users/daun/meta-ads/.venv/bin/python
Q=data/claude_queue; mkdir -p $Q/doing $Q/done
# Claude 대기열에 이미 넣은 요청(진행 중·끝남 포함)은 다시 집지 않는다 — 안 그러면 3분마다 헛배포
printf '%s' "$JOBS" | $PY -c "import sys,json,os;[(open('/tmp/adref_job_%s.json'%j['job'],'w').write(json.dumps(j,ensure_ascii=False)), print(j['job'])) for j in json.load(sys.stdin) if not any(os.path.exists('$Q/%s%s.json'%(d,j['job'])) for d in ('','doing/','done/'))]" > /tmp/adref_jobs.txt
[ -s /tmp/adref_jobs.txt ] || exit 0
N=0; ADDED=; DID=; CL=
while read -r J; do
  TYPE=$($PY -c "import json;print(json.load(open('/tmp/adref_job_$J.json')).get('type','bokgak'))")
  if [ "$TYPE" = "setup" -o "$TYPE" = "status" ]; then
    node scripts/blob.mjs status "{\"state\":\"working\",\"job\":\"$J\",\"ids\":[]}"
    $PY -I scripts/setup_ad.py /tmp/adref_job_$J.json; RC=$?; DID=1
    [ $RC -eq 75 ] && echo "메타 호출 한도 — 다음 회차에 다시" || node scripts/blob.mjs done "$J"
  elif [ "$TYPE" = "addref" ]; then
    node scripts/blob.mjs status "{\"state\":\"working\",\"job\":\"$J\",\"ids\":[]}"
    $PY -I scripts/addref.py /tmp/adref_job_$J.json && ADDED=1
    if [ -f /tmp/adref_follow_$J.json ]; then   # '추가하고 바로 복각' → Claude 대기열(끝나면 claude_worker 가 done 처리)
      $PY -c "import json;j=json.load(open('/tmp/adref_follow_$J.json'));j['type']='bokgak';j['job']='$J';json.dump(j,open('$Q/$J.json','w'),ensure_ascii=False)"; rm -f /tmp/adref_follow_$J.json; CL=1
    else node scripts/blob.mjs done "$J"; fi
  elif [ "$TYPE" = "revise" ]; then   # 수정하기 → Claude 직접
    cp /tmp/adref_job_$J.json $Q/$J.json; CL=1
  elif [ "$TYPE" = "select" -o "$TYPE" = "delete" ]; then
    node scripts/blob.mjs status "{\"state\":\"working\",\"job\":\"$J\",\"ids\":[]}"
    $PY -I scripts/revise.py /tmp/adref_job_$J.json; node scripts/blob.mjs done "$J"; DID=1
  elif [ "$TYPE" = "delref" ]; then
    node scripts/blob.mjs status "{\"state\":\"working\",\"job\":\"$J\",\"ids\":[]}"
    $PY -I scripts/delref.py /tmp/adref_job_$J.json && ADDED=1; node scripts/blob.mjs done "$J"; DID=1
  elif [[ "$TYPE" == zcre_* ]]; then   # ZCRE 생성 탭(견적·승인·취소) → 따로 띄워 바로 처리(작업기를 붙잡지 않음)
    mkdir -p data/zcre/jobs; cp /tmp/adref_job_$J.json data/zcre/jobs/$J.json; node scripts/blob.mjs done "$J"
    nohup zsh scripts/zcre_worker.sh $J >> logs/zcre.log 2>&1 &
  elif [ "$TYPE" = "slacksync" ]; then   # 소재공유방 새로고침 버튼(2026-11-12) → 따로 띄워 바로(slack_sync.sh 가 자체 잠금·새 글 있을 때만 배포)
    node scripts/blob.mjs done "$J"
    nohup zsh scripts/slack_sync.sh >> logs/slack_sync.log 2>&1 &
  elif [ "$TYPE" = "libsearch" ]; then   # 검색창 실시간 수집(2026-11-11) → 따로 띄워 바로(작업기 안 붙잡음, 배포 없음)
    cp /tmp/adref_job_$J.json data/libsearch/jobs/$J.json; node scripts/blob.mjs done "$J"
    nohup zsh scripts/libsearch.sh $J >> logs/libsearch.log 2>&1 &
  elif [ "$TYPE" = "retry" ]; then   # 실패 카드 다시 복각 → Claude 직접
    cp /tmp/adref_job_$J.json $Q/$J.json; CL=1
  else   # 복각하기 → Claude 직접(Gemini 자동 복각 bokgak.py 는 쓰지 않음)
    cp /tmp/adref_job_$J.json $Q/$J.json; CL=1
  fi
  N=$((N+1)); rm -f /tmp/adref_job_$J.json
done < /tmp/adref_jobs.txt
[ -n "$CL" ] && { echo "Claude 대기열에 넣음 — claude_worker 가 바로 직접 편집"; launchctl kickstart gui/$(id -u)/com.daun.$(basename $(pwd))-claude >/dev/null 2>&1; }
[ -z "$DID" -a -z "$ADDED" ] && exit 0
[ -n "$ADDED" ] && $PY -I scripts/build.py
$PY -I scripts/build_review.py
zsh scripts/deploy.sh
node scripts/blob.mjs status '{"state":"idle"}'
D=$(TZ=Asia/Seoul date +%F)
[ -n "$ADDED" ] && osascript -e "display notification \"레퍼런스 페이지가 갱신됐어요\" with title \"광고 레퍼런스\"" 2>/dev/null
