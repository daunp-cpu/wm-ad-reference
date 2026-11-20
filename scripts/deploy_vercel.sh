#!/bin/zsh
# site/ → Vercel 배포 후 your-site.vercel.app 에 연결 (daily.sh·worker.sh 공용)
export PATH=/Users/daun/.local/node/bin:/usr/bin:/bin:/usr/sbin:/sbin
cd /Users/daun/ad-reference
# 페이지가 새 배포를 알아채고 새로고침 없이 바뀐 부분만 다시 그리게(정적 파일이라 Blob 호출 없음, 2026-10-21)
printf '{"at":%s,"index":%s,"review":%s}' $(date +%s) $(stat -f %m site/index.html 2>/dev/null || echo 0) $(stat -f %m site/review.html 2>/dev/null || echo 0) > site/ver.json
TOKEN=$(cat ~/.vercel-token)
URL=$(vercel deploy --prod --yes --archive=tgz --token "$TOKEN" --scope wm-aa1b 2>/dev/null | grep -Eo 'https://ad-reference-[a-z0-9]+-wm-aa1b\.vercel\.app' | head -1)
[ -z "$URL" ] && URL=$(vercel ls ad-reference --token "$TOKEN" --scope wm-aa1b 2>/dev/null | grep -Eo 'https://ad-reference-[a-z0-9]+-wm-aa1b\.vercel\.app' | head -1)
[ -z "$URL" ] && exit 1
vercel alias set "$URL" your-site.vercel.app --token "$TOKEN" --scope wm-aa1b >/dev/null 2>&1
echo "배포: https://your-site.vercel.app  (이번 판: $URL)"
