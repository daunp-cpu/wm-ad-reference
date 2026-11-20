#!/bin/zsh
# 사이트를 어디에 올릴지 바꾸기: zsh scripts/use_host.sh vercel | cf
# 저장소 도우미(blob.mjs)·배포(deploy.sh)·작업기 알림 주소를 한 번에 바꾼다. 페이지·서버 코드는 둘 다 들어 있어서 그대로.
cd /Users/daun/ad-reference
case "$1" in
  vercel) cp scripts/blob_vercel.mjs scripts/blob.mjs; cp scripts/deploy_vercel.sh scripts/deploy.sh; U=https://your-site.vercel.app ;;
  cf)     cp scripts/blob_cf.mjs scripts/blob.mjs;     cp scripts/deploy_cf.sh scripts/deploy.sh;     U=https://ad-reference.pages.dev ;;
  *) echo "사용: zsh scripts/use_host.sh vercel|cf"; exit 1 ;;
esac
sed -i '' -E "s#https://(wm-ad-reference\.vercel\.app|ad-reference\.pages\.dev)#$U#g" scripts/worker.sh scripts/daily.sh
echo "$1 로 바꿈 → $U"
