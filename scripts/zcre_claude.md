# ZCRE 생성 탭 — Claude 지시서

레퍼런스 페이지 'ZCRE 생성' 탭의 요청 1건을 ZCRE 커넥터 도구로 처리한다. 단계는 프롬프트 맨 앞에 적힌 것 하나만 한다.

## 공통 규칙
- ZCRE 도구는 `mcp__claude_ai_ZCRE__*`. 안 보이면 ToolSearch 로 `zcre` 검색해 불러온다. `query_zcre` 인자는 항상 `{query:{action:...}}`.
- **서명 URL·quote_token 은 화면 출력·로그·답변에 쓰지 않는다.** 파일(JSON)에만 쓴다.
- model_name 은 brief/quote 에 있는 그대로. 모델 ID 를 지어내지 않는다.
- 실패·시간 초과 시 자동으로 다시 생성하지 않는다. 같은 idempotency_key 로 status 를 먼저 확인한다.
- 사용자 프롬프트의 뜻을 바꾸지 않는다. 옵션(비율·길이·해상도·장수 등)은 모델 스키마의 해당 필드에 넣는다. 스키마에 없는 옵션은 review 에 "적용 못 함"으로 적는다.
- 결과 JSON 은 작업폴더(brief.work)에 Write 로 쓴다.

## 단계 1: 견적 (quote) — **create_generation 은 절대 부르지 않는다(이 단계엔 권한도 없다)**
1. `brief.json` 을 읽는다. (model_name, media, prompt, opts, files[], idempotency_key, work)
2. `query_zcre {query:{action:'model', model_name}}` 로 최신 입력 스키마를 확인한다.
3. 참조 파일(files)이 있으면 하나씩 `prepare_upload` (model_name, media_type, content_type, filename, size_bytes 를 brief 값 그대로) → 응답의 client_transfer 지시대로 Bash `curl` 로 원본(path)을 전송 → `query_zcre {action:'upload', upload_id}` 로 ready·source 확인. 모델이 받지 않는 형식·크기·비율이면 그 파일은 빼고 review 에 이유를 적는다.
4. 스키마대로 `input` 을 만든다. 업로드한 파일은 스키마 설명대로 해당 필드 + `input_assets`(같은 field·index, upload 의 source)로 연결한다. role 은 brief.files[].role 참고.
5. `query_zcre {action:'quote', model_name, idempotency_key, input}` (영상 드래프트는 요청에 '드래프트'가 있을 때만 generation_stage=draft).
6. `query_zcre {action:'balance'}` 로 잔액.
7. `work/quote.json` 에 쓴다:
   - 성공(can_submit=true): `{"ok":true,"model_name":..,"generation_stage":..(없으면 생략),"idempotency_key":..,"input":{..견적에 쓴 그대로..},"quote_token":"..","credits":견적 최대 크레딧(숫자),"review":"한국어 3~6줄: 최종 프롬프트·옵션·첨부 번호/역할·적용 못 한 옵션","expires_at":"ISO 시각(응답에 있으면, 없으면 지금+5분)","balance":잔액숫자}`
   - 실패: `{"ok":false,"reason":"한국어로 이유(사용자가 고칠 수 있게)","balance":잔액}`

## 단계 2: 생성 (run) — 사용자가 페이지에서 견적을 보고 '승인하고 생성'을 눌렀다
1. `work/quote.json`, `work/approved.json`(credits_max) 을 읽는다.
2. 지금이 expires_at 30초 전보다 늦으면, **같은 model_name·generation_stage·input·idempotency_key** 로 quote 를 다시 받는다.
   - 새 견적 크레딧 > credits_max → 생성하지 말고 `work/result.json` = `{"ok":false,"reason":"price_up","credits":새견적}` 쓰고 끝.
   - already_submitted=true → 반환된 request_id 로 3번의 상태 확인부터.
3. `create_generation` (같은 model_name·generation_stage·input·idempotency_key + 그 견적의 quote_token).
4. `query_zcre {action:'status', request_id, wait_seconds:10}` 를 끝날 때까지 반복(대기 중 새 생성 금지). 영상은 수 분~20분 걸릴 수 있다.
5. 성공: `query_zcre {action:'outputs', request_id}` → 결과마다 Bash `curl -sL -o work/out/<n>.<ext> "<original_delivery_url>"` (URL 을 echo 하지 말 것). delivery_url 이 original 과 다르면 재생용으로 `work/out/<n>_view.<ext>` 도 받는다. 받은 파일 크기가 0 이 아닌지 확인.
6. `query_zcre {action:'balance'}`.
7. `work/result.json`:
   - 성공: `{"ok":true,"request_id":..,"credits_used":정산 크레딧(응답에 있으면, 없으면 견적값),"balance":..,"files":[{"path":"원본 경로","view_path":"재생용 경로(없으면 생략)","media":"image|video|audio"}]}`
   - 실패: `{"ok":false,"reason":"한국어 이유 + 정산(환불) 상태","request_id":..,"balance":..}`
