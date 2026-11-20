#!/bin/zsh
# site/ → Vercel 배포 후 your-site.vercel.app 에 연결 (daily.sh·worker.sh 공용)
export PATH=/Users/daun/.local/node/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/daun/ad-reference
# 페이지가 새 배포를 알아채고 새로고침 없이 바뀐 부분만 다시 그리게(정적 파일이라 Blob 호출 없음, 2026-10-21)
printf '{"at":%s,"index":%s,"review":%s}' $(date +%s) $(stat -f %m site/index.html 2>/dev/null || echo 0) $(stat -f %m site/review.html 2>/dev/null || echo 0) > site/ver.json
TOKEN=$(cat ~/.vercel-token)
# 2026-11-04 속도: claude_kit(5.2GB·4.8만 파일, 사이트와 무관)를 .vercelignore 로 빼서 파일 3.5천 개 → 압축 없이 올리면 바뀐 파일만 올라감.
# 실패하면 예전 방식(--archive=tgz, 전체 압축 업로드)으로 한 번 더.
URL=$(vercel deploy --prod --yes --token "$TOKEN" --scope wm-aa1b 2>/dev/null | grep -Eo 'https://ad-reference-[a-z0-9]+-wm-aa1b\.vercel\.app' | head -1)
[ -z "$URL" ] && URL=$(vercel deploy --prod --yes --archive=tgz --token "$TOKEN" --scope wm-aa1b 2>/dev/null | grep -Eo 'https://ad-reference-[a-z0-9]+-wm-aa1b\.vercel\.app' | head -1)
[ -z "$URL" ] && URL=$(vercel ls ad-reference --token "$TOKEN" --scope wm-aa1b 2>/dev/null | grep -Eo 'https://ad-reference-[a-z0-9]+-wm-aa1b\.vercel\.app' | head -1)
[ -z "$URL" ] && exit 1
vercel alias set "$URL" your-site.vercel.app --token "$TOKEN" --scope wm-aa1b >/dev/null 2>&1
echo "배포: https://your-site.vercel.app  (이번 판: $URL)"
