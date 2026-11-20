#!/bin/zsh
# site/ → Cloudflare Pages 배포 (daily.sh·worker.sh 공용). 자격증명은 wrangler login 것을 쓴다.
export PATH=/Users/daun/.local/node/bin:/usr/bin:/bin:/usr/sbin:/sbin
export CLOUDFLARE_ACCOUNT_ID=YOUR_CF_ACCOUNT_ID
cd /Users/daun/ad-reference
# 페이지가 새 배포를 알아채고 새로고침 없이 바뀐 부분만 다시 그리게(정적 파일이라 Blob 호출 없음, 2026-10-21)
printf '{"at":%s,"index":%s,"review":%s}' $(date +%s) $(stat -f %m site/index.html 2>/dev/null || echo 0) $(stat -f %m site/review.html 2>/dev/null || echo 0) > site/ver.json
OUT=$(./node_modules/.bin/wrangler pages deploy site --project-name ad-reference --branch main --commit-dirty=true 2>&1)
URL=$(echo "$OUT" | grep -Eo 'https://[a-z0-9.-]+\.pages\.dev' | tail -1)
if [ -z "$URL" ]; then echo "$OUT" | tail -5; exit 1; fi
echo "배포: https://ad-reference.pages.dev  (이번 판: $URL)"
