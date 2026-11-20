// 2026-10-20 사이트를 다시 Vercel(Pro)로 옮김 → 예전 Cloudflare 주소로 오면 새 주소로 넘김. 되돌리려면 _middleware.js.bak-261020 로 복구.
export async function onRequest({ request }) {
  const u = new URL(request.url);
  return Response.redirect('https://your-site.vercel.app' + u.pathname + u.search, 302);
}
