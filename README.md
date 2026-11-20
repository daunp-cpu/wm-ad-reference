# wm-ad-reference

광고 레퍼런스 수집 · 복각 자동화 사이트의 코드입니다. (Vercel 배포 + 로컬 작업기)

## 구성
- `api/`, `functions/`, `middleware.js` : Vercel/Cloudflare 서버 함수, 기본 인증
- `scripts/` : 페이지 빌드(`build.py`, `build_review.py`), 복각·수정·세팅 작업기(`bokgak.py`, `revise.py`, `setup_ad.py`), 수집(`agency.py`, `libsearch.mjs`), 배포 스크립트
- `scripts/claude_bokgak.md`, `CLAUDE.md` : 작업기 Claude 지시서
- `claude_kit/` : 작업기가 쓰는 보조 도구
- `config.example.json` : 수집 키워드 설정 예시

## 내 환경에 맞추려면
이 저장소에는 비밀번호·토큰·계정 ID를 넣지 않았습니다. `YOUR_...` 로 된 값은 본인 값으로 바꾸세요.
- 사이트 비밀번호 : 환경변수 `SITE_PASSES` (쉼표 구분), 아이디는 `middleware.js` 의 `USER`
- Meta 광고 계정, 구글 드라이브 폴더, 슬랙 채널, Cloudflare KV ID 등은 `scripts/` 와 `wrangler.toml` 에서 치환
- 토큰류는 코드 밖(`~/.config/...`, 환경변수)에서 읽습니다.
- 데이터(`data/`), 빌드 결과(`site/`)는 포함하지 않았습니다. `scripts/build.py` 로 생성됩니다.
