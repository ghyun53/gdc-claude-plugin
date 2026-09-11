# 건의 본문 HTML 대응 — 길이 검증·조회 평문화

| 속성 | 값 |
|------|-----|
| 유형 | fix |
| 영역 | server/gdc_mcp |
| 날짜 | 2026-09-11 |
| 상태 | done |
| 관련 | gdc-service PR #199 (GDC #606) |

## 요청 내용

gdc-service에서 건의 본문·댓글이 서식 있는 입력으로 바뀌면서 `Suggestion.content`에 HTML이 저장된다. MCP 도구가 이를 평문으로 가정하고 있어 두 곳이 어긋난다.

- `_validate_suggestion_content`가 길이를 **태그까지 포함해** 재므로, 서식 있는 본문이 2000자 제한에 억울하게 걸린다.
- `get_suggestion`이 `content`를 그대로 돌려줘 터미널에 `<p>`·`<strong>` 같은 태그가 노출된다.
- `_suggestion_title`이 본문 첫 줄로 제목을 만들 때 `<p>제목</p>` 같은 태그 섞인 문자열을 쓴다.

## 배경

화면 편집기가 붙은 뒤에도 MCP `submit_suggestion`은 평문을 보낸다(에이전트가 쓰는 본문은 평문이다). 서버는 평문을 그대로 저장하고 화면이 표시 직전에 문단 HTML로 올리므로 제출 경로는 바꿀 필요가 없다. 반대 방향, 즉 **화면에서 쓴 HTML 본문을 MCP로 읽을 때**와 **HTML이 섞여 들어올 때의 길이 판정**만 맞추면 된다.

레포에 이미 `doc_utils.is_html` / `html_to_text`가 있어 `list_task_comments`가 같은 방식으로 댓글 HTML을 평문화한다. 같은 헬퍼를 재사용한다.

## 작업 결과

- [x] `_validate_suggestion_content` — HTML이면 `html_to_text`로 벗긴 글자 수로 최소 5자·최대 2000자를 판정(저장은 원문 그대로)
- [x] `_suggestion_title` — 제목 자동 생성 시 태그를 벗긴 본문의 첫 줄을 쓴다
- [x] `get_suggestion` — `content`를 `html_to_text`로 평문화해 반환 (`list_task_comments`와 같은 방식)
- [x] 테스트 3건 추가 (HTML 본문 길이 판정 2건, HTML 제목 자동 생성 1건) — 233 passed
- [x] `plugin.json` 0.9.0 → 0.9.1, 안내서 사이트 버전 표기 2곳 동기화

## 참고 사항

- 도구 수 변화 없음(34종 유지) — 동작만 바뀌어 README 도구표는 그대로다.
- 평문 제출 경로는 무변경이다. 서버가 평문을 그대로 저장하고 화면이 표시 시점에 문단으로 올린다.
