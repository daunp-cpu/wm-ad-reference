#!/bin/zsh
# 매일 아침 레퍼런스 갱신: 광고 라이브러리 수집 → 대행 계정 집계 → 페이지 생성 → Vercel 배포
# 주소: https://your-site.vercel.app 
export PATH=/Users/daun/.local/node/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/daun/ad-reference
echo "===== $(date '+%F %T') ====="
note(){ osascript -e "display notification \"$1\" with title \"광고 레퍼런스\"" 2>/dev/null }
# 11/5: 맥이 깨어난 직후엔 인터넷이 아직 안 붙어 있음 → 최대 5분 기다렸다 시작
for i in $(seq 1 30); do curl -s -m 5 -o /dev/null https://www.facebook.com && break; echo "인터넷 대기 $i"; sleep 10; done
node scripts/scrape-library.mjs || { note "광고 라이브러리 수집 실패(어제 목록 유지)"; }
python3 -I scripts/agency.py 2>logs/agency_err.log; rc=$?; cat logs/agency_err.log
python3 -I scripts/agency_video.py   # 고효율 영상 재생 주소(매일 만료돼서 다시)
grep -q CEO_TOKEN_EXPIRING logs/agency_err.log && note "대표님 계정 메타 토큰이 곧 만료돼요 — Claude에게 새로 받자고 말해주세요"
if [ $rc -eq 3 ]; then note "메타 토큰 만료 — 대행 계정 집계는 어제 데이터로 유지"; fi
/Users/daun/meta-ads/.venv/bin/python -I scripts/landing.py || note "자사몰 상품 목록 갱신 실패(어제 목록 사용)"
/Users/daun/meta-ads/.venv/bin/python -I scripts/drive_index.py || note "구글 드라이브 에셋 목록 갱신 실패 — 구글 로그인 만료일 수 있어요(Claude에게 재로그인 요청)"
python3 scripts/build.py || { note "페이지 생성 실패"; exit 1; }
python3 scripts/build_review.py || note "검수 페이지 생성 실패"
zsh scripts/deploy.sh || { note "배포 실패"; exit 1; }
echo "완료"
