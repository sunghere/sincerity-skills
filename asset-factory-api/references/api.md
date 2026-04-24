# Asset Factory API 레퍼런스 (REST 직접 호출)

> 일반 사용은 `af` CLI로 충분. 이 문서는 디버깅·통합·`af`에 없는 엔드포인트가 필요할 때만 본다.

## 서버 정보

- **Base URL**: `http://localhost:8000` (페이퍼클립 에이전트는 같은 Mac mini 동작)
  - LAN: `http://192.168.50.250:8000` (Mac mini IP, `AF_HOST=0.0.0.0 ./run-dev.sh restart` 필요)
  - Tailscale: `http://yoons-macmini.tailbff496.ts.net:8000` 또는 `http://100.72.190.122:8000`
- **API Key**: `.env`의 `API_KEY` (있으면 변경 계열에 `x-api-key` 헤더 필수)
- **백엔드 SD**: `192.168.50.225:7860` (Asset Factory가 알아서 호출)
- **Web UI**: `/app/`, **Cherry-pick UI**: `/cherry-pick?batch=<id>`
- **데이터**: `~/workspace/asset-factory/data/` (DB, 후보 이미지)
- **Export 기본**: `~/workspace/assets/<project>/<category>/<asset_key>.png`

## 엔드포인트 빠른 참조

| 용도 | Method · Path | `af` 대응 |
|------|---------------|-----------|
| 헬스 / SD 연결 | `GET /api/health`, `/api/health/sd` | `af health` |
| 모델/LoRA 카탈로그 | `GET /api/sd/catalog/{models,loras}` | `af catalog [models\|loras]` |
| 단일 생성 | `POST /api/generate` 🔑 | `af gen` |
| 스펙 파일 배치 | `POST /api/generate/batch` 🔑 | (스펙 파일 필요) |
| 디자인 배치 (cherry-pick) | `POST /api/mcp/design_asset` 🔑 ⭐ | `af batch` |
| 잡 상태 polling | `GET /api/jobs/{job_id}` | `af status`, `af wait` |
| 최근 잡 타임라인 | `GET /api/jobs/recent?limit=10` | — |
| SSE 이벤트 스트림 | `GET /api/events` | — |
| 에셋 목록/요약 | `GET /api/assets`, `/api/assets/summary` | `af list` |
| 에셋 단건/이미지 | `GET /api/assets/{id}/{detail,image}` | `af get` |
| 후보 슬롯 목록 | `GET /api/assets/{id}/candidates` | — |
| 후보 → 메인 승격 | `POST /api/assets/approve-from-candidate` 🔑 | (cherry-pick UI) |
| 재생성 | `POST /api/assets/{id}/regenerate` 🔑 | — |
| 검증 | `POST /api/validate/{id}`, `/api/validate/all` 🔑 | — |
| 실패 일괄 재처리 | `POST /api/batch/{revalidate,regenerate}-failed` 🔑 | — |
| 디렉토리 → DB 동기화 | `POST /api/projects/scan` 🔑 | — |
| 승인본 export | `POST /api/export` 🔑, `GET /api/export/manifest` | `af export` |
| GC 상태/즉시실행 | `GET /api/system/gc/status`, `POST /api/system/gc/run` 🔑 | — |

🔑 = API Key 필요, ⭐ = 가장 자주 쓰는 진입점

## 단일 생성 요청 스키마 (`POST /api/generate`)

```json
{
  "project": "wooridul-factory",
  "asset_key": "kitten_idle",
  "category": "character",          // default "sprite"
  "prompt": "pixel art, cute kitten, transparent background",
  "negative_prompt": "background, blurry",
  "model_name": "pixelArtDiffusionXL_spriteShaper",   // optional
  "width": null, "height": null,                       // 비워두면 모델별 기본
  "steps": 20, "cfg": 7.0, "sampler": "DPM++ 2M",
  "expected_size": 64,              // 최종 픽셀아트 크기
  "max_colors": 32,
  "max_retries": 3
}
```

응답: `{"job_id": "..."}`

## 디자인 배치 요청 스키마 (`POST /api/mcp/design_asset`)

```json
{
  "project": "wooridul-factory",
  "asset_key": "warrior_idle",
  "category": "character",
  "prompts": ["pixel art warrior, sword and shield, idle pose"],
  "models": ["pixelArtDiffusionXL_spriteShaper"],
  "loras": [
    [{"name": "pixel-art-xl-v1.1", "weight": 0.7}]
  ],
  "seeds_per_combo": 4,
  "common": {
    "steps": 28, "cfg": 7.0, "sampler": "DPM++ 2M",
    "expected_size": 64, "max_colors": 32, "max_retries": 3,
    "negative_prompt": "background, blurry"
  }
}
```

응답: `{"batch_id": "btc_...", "job_id": "...", "expanded_count": N, "estimated_eta_seconds": N*6}`

⚠️ **`loras`는 2차원 배열**: 바깥 리스트가 "곱집합 한 칸", 안 리스트가 그 칸에 동시 적용할 LoRA들. 단일 LoRA도 `[[{"name":"...","weight":0.7}]]`.

## 잡 폴링

`GET /api/jobs/{job_id}` 응답:
```json
{
  "id": "...", "job_type": "generate_single",
  "status": "pending|running|completed|failed",
  "total_count": 1, "completed_count": 0, "failed_count": 0,
  "error_message": null,
  "created_at": "...", "updated_at": "..."
}
```

폴링 규칙:
- 첫 polling 5초 후, 이후 3~5초 간격
- 단일: 30초~2분, 배치: task당 ~6초
- `status == "failed"`면 `error_message` 보고
- timeout: 단일 5분, 배치 (task_count × 15초) 권장

## SD 에러 분류

`task.last_error.code`:
- `timeout`, `oom`, `unreachable`, `sd_server_error`, `sd_client_error`
- `oom` / `sd_client_error`는 즉시 failed (재시도 안 함)
- 나머지는 task-level 지수 백오프(2^n + 25% 지터)

## API Pitfalls

1. **`spec_id`는 서버측 `specs/*.json` 파일명** — 임의 파일명 보내면 404
2. **API Key 누락 401**, 다른 회사 키 403 — `.env`에 키 없으면 헤더 빠져도 OK
3. **batch_id ≠ job_id** — cherry-pick UI는 `batch_id`, polling은 `job_id`
4. **`completed_count == total_count`인데 status=running** — 워커가 마지막 task 마무리 중, 한 번 더 polling
5. **`expected_size`는 SD 생성 해상도가 아닌 최종 픽셀아트 크기** — width/height는 비워두고 expected_size만
6. **picking 직후 polling = 0초** — 첫 polling은 최소 5초 대기
7. **재생성은 metadata 보존** — `regenerate`는 기존 prompt/cfg 그대로. 프롬프트 변경하려면 새 generate
8. **GC가 후보 지움** — 선택된 후보도 GC 대상. 메인 승격 후 24h 내 export로 백업
9. **단일 생성 후처리 누락 가능성** — `af gen`이 1024x1024 raw 그대로 떨어뜨릴 수 있음. validation_status=fail 시 `af get` 후 수동 처리 또는 `af batch` 경로 사용 (배치엔 후처리 파이프라인 적용됨)
