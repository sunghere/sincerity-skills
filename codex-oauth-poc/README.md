# Codex OAuth PoC

Paperclip fork에서 신규 어댑터 `codex_oauth_local` 구현 전, **OAuth 토큰으로 `https://chatgpt.com/backend-api/codex/responses`를 직접 호출 가능한지** 검증한 PoC 4종.

## 결과 요약

| PoC | 파일 | 결과 | 핵심 발견 |
|-----|------|------|----------|
| 1. 단순 streaming | `01_text.py` | ✅ | 인증·헤더 형식 확정 |
| 2. Tool call round-trip | `02_tool_call.py` | ✅ | `response.completed.output`이 빈 배열 → SSE 이벤트 누적자 필수 |
| 3. Token refresh | `03_refresh.py` | ✅ | refresh 시 access+refresh 모두 회전 |
| 4. Reasoning encrypted_content | `04_reasoning.py` | ✅ | gpt-5.3-codex만 reasoning item 반환 |

## 확정된 인터페이스

```
POST https://chatgpt.com/backend-api/codex/responses
Headers:
  Authorization: Bearer <access_token>
  chatgpt-account-id: <account_id>
  OpenAI-Beta: responses=v1
  originator: codex_cli_rs
  version: 0.0.0
  Content-Type: application/json
  Accept: text/event-stream

Body:
  model: gpt-5.5 | gpt-5.4 | gpt-5.4-mini | gpt-5.3-codex
  stream: true (REQUIRED — 옵션 아님)
  store: false
  instructions: <system prompt>
  input: [...messages + echoed output items + function_call_output...]
  tools: [...]  // strict: true 미지원
  tool_choice: "auto"
  parallel_tool_calls: true
```

## SSE 이벤트 누적 패턴 (어댑터 구현 시 필수)

```python
output_items = []   # response.output_item.done 누적
text_buf = ""       # response.output_text.delta 누적
final_status = None # response.completed.status

# 다음 turn input에 그대로 echo:
input = [user_message, *output_items, {"type":"function_call_output", ...}]
```

`response.completed.output`은 항상 `[]` 이므로 의존하면 안 됨.

## Token refresh

```
POST https://auth.openai.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
refresh_token=<current>
client_id=app_EMoamEEZ73f0CkXaXp7hrann
```

응답: `access_token` + `refresh_token` (회전됨) + `id_token` + `expires_in`. 새 두 토큰 모두 `~/.codex/auth.json`에 저장 (Codex CLI 호환).

## 허용 모델 (ChatGPT 계정)

검증된 모델:
- `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex`

거부됨 (Platform API key 전용):
- `gpt-5`, `gpt-5-codex`, `gpt-5.2-codex`, `gpt-5.1-codex-max/mini`, `codex-mini-latest`

## 다음 단계

이 PoC를 paperclip fork의 `packages/adapters/codex-oauth-local/`로 이식.

- `src/server/oauth-store.ts`: ~/.codex/auth.json 읽기/쓰기
- `src/server/oauth-refresh.ts`: 토큰 갱신
- `src/server/codex-http.ts`: SSE accumulator + responses 엔드포인트 호출
- `src/server/execute.ts`: paperclip adapter contract (얇게)
- `src/server/parse.ts`: SSE → paperclip event 변환

기존 `packages/adapters/codex-local/`은 **0줄 변경**. fork-friendly.

## 출처

- hermes-agent OAuth 구현: `~/workspace/hermes-agent/hermes_cli/auth.py:1514` (`refresh_codex_oauth_pure`)
- Codex CLI Rust 소스: `~/workspace/codex/codex-rs/login/src/auth/manager.rs:869`
