// 아이디·비밀번호(기본 인증)로 페이지 보호 — 대행 계정 성과가 들어 있음
// 비밀번호에 한글이 있어 브라우저가 UTF-8 로 보낸다. atob 결과를 바이트로 되돌려 디코딩한다.
// 비밀번호는 환경변수 SITE_PASSES(쉼표 구분)로 설정한다.
export const config = { matcher: '/(.*)' };
const USER = 'Marketing';
const PASSES = [...(process.env.SITE_PASSES||'').split(',').filter(Boolean)];
export default function middleware(req) {
  const h = req.headers.get('authorization') || '';
  if (h.startsWith('Basic ')) {
    try {
      const raw = atob(h.slice(6));
      const txt = new TextDecoder().decode(Uint8Array.from(raw, c => c.charCodeAt(0)));
      const i = txt.indexOf(':');
      if (txt.slice(0, i) === USER && PASSES.includes(txt.slice(i + 1))) return;
    } catch (e) {}
  }
  return new Response('로그인이 필요합니다', { status: 401, headers: { 'WWW-Authenticate': 'Basic realm="sooo-bokgak", charset="UTF-8"' } });
}
