# Asset Factory API 레퍼런스

> 일반 사용은 `af` CLI 또는 `references/catalog-and-meta.md` 의 메타 사용 패턴으로 충분.
> 이 문서는 모든 REST endpoint 의 **호출 디테일** + curl 예제 + 응답 형식을 다룬다.
>
> ⚠️ 모델·LoRA·step·cfg 수동 지정은 지원하지 않는다 (변형이 내장). 본 문서는 ComfyUI 워크플로우 호출 인터페이스만 다룬다.

---

## 서버 정보

- **Base URL**: `http://localhost:47823` (Asset Factory 운영 메인 — loopback. `af` CLI default)
  - LAN 다른 기기에서 호출: 운영 호스트의 LAN IP — DHCP 로 가변하므로 *항상 동일 IP 보장 안 됨*. 운영 서버는 `0.0.0.0:47823` 으로 binding 되어 있어 어떤 IP 든 받음. 안 닿으면 `ipconfig getifaddr en0` 로 현재 IP 재확인.
  - 원격 / 영구 고정: Tailscale `http://100.72.190.122:47823` 또는 `http://yoons-macmini.tailbff496.ts.net:47823`. Tailscale IP 는 DHCP 영향 받지 않음.
  - **테스트 인스턴스**: `http://localhost:8000` (`run-dev.sh` 의 `AF_PORT=8000` override 시) — 운영 DB / 큐 와 분리.
- **API Key**: `.env` 의 `API_KEY`. 변경 계열에 `x-api-key` 헤더 필수. 인증은 항상 살아있음 — bypass 모드도 인증은 우회 안 함.
- **백엔드**: ComfyUI (Asset Factory 가 알아서 호출. 직접 두드리면 안 됨.)
- **Web UI**: `/app/`, **Cherry-pick UI**: `/app/cherry-pick/<batch_id>` (canonical deep-link)
  - 호환 진입점: `/cherry-pick?batch_id=<batch_id>` 또는 `/cherry-pick?run=<job_id>` (server 가 batch_id 룩업 후 redirect — sunghere/asset-factory#64)
- **데이터**: `~/workspace/asset-factory/data/`
- **Export 기본**: `~/workspace/assets/<project>/<category>/<asset_key>.png`
- **OpenAPI**: `GET /openapi.json` (FastAPI 자동 생성)

---

## 엔드포인트 빠른 참조

| 용도 | Method · Path | `af` 대응 |
|---|---|---|
| 헬스 / ComfyUI 연결 | `GET /api/health` | `af health` |
| ComfyUI 단독 헬스 + 큐 상태 ⭐ | `GET /api/comfyui/health` | — |
| ComfyUI 모델/LoRA/VAE/ControlNet/Workflow 카탈로그 ⭐ | `GET /api/comfyui/catalog` | — |
| ComfyUI 큐 (running/pending) | `GET /api/comfyui/queue` | — |
| **워크플로우 카탈로그** | `GET /api/workflows/catalog` | `af workflow catalog` |
| 워크플로우 상세 | `GET /api/workflows/catalog` (variant 필터링) | `af workflow describe <cat>/<v>` |
| **변형 추천 (자연어)** ⭐ | `POST /api/workflows/recommend` | `af workflow recommend` |
| **변형 검색 (tag filter)** | `GET /api/workflows/search` | `af workflow search` |
| **동적 입력 업로드** (멀티파트) | `POST /api/workflows/inputs` 🔑 | `af workflow upload` |
| 동적 입력 (기존 에셋) | `POST /api/workflows/inputs/from-asset` 🔑 | `af workflow upload --from-asset` |
| **생성** | `POST /api/workflows/generate` 🔑 ⭐ | `af workflow gen` |
| 잡/run 상태 polling | `GET /api/runs/{run_id}/status` | `af status`, `af wait` |
| SSE 이벤트 스트림 | `GET /api/events` | — |
| 에셋 목록 | `GET /api/assets` (project 필터) | `af list` |
| 에셋 단건/이미지 | `GET /api/assets/{id}/{detail,image}` | `af get` |
| 후보 → 메인 승격 | `POST /api/assets/approve-from-candidate` 🔑 | (cherry-pick UI) |
| Bypass 자산 목록 | `GET /api/assets?include_bypassed=true` | `af list --include-bypassed` |
| 승인본 export | `POST /api/export` 🔑, `GET /api/export/manifest` | `af export` |
| GC 상태 / 즉시실행 | `GET /api/system/gc/status`, `POST /api/system/gc/run` 🔑 | — |

🔑 = API Key 필요, ⭐ = 가장 자주 쓰는 진입점

---

## `GET /api/workflows/catalog`

ComfyUI 레지스트리 카탈로그. **catalog 응답 schema 전체는 `references/catalog-and-meta.md` 의 §1 참고.**

```bash
curl http://localhost:47823/api/workflows/catalog | jq '.version, .categories | keys'
# → 2
# → ["icon", "illustration", "pixel_bg", "sprite"]
```

**`version: 2`** (PR #30) — schema bump 후 `meta` 필드 노출. 기존 클라이언트는 `meta` 무시하면 동작 동일.

**`available: false`** 인 변형은 `status: "needs_api_conversion"` — ComfyUI UI 에서 API 포맷 export 가 안 된 상태. 호출하면 400.

---

## `POST /api/workflows/recommend` — §1.C 자연어 추천

```bash
curl -X POST http://localhost:47823/api/workflows/recommend \
  -H "Content-Type: application/json" \
  -d '{"query": "RPG 픽셀 캐릭터 정면 측면 뒷면 시트", "top": 3}'
```

응답 schema 는 `references/catalog-and-meta.md` 의 §3 참고.

핵심:
- `candidates[].score` (0.0 ~ 1.0)
- `candidates[].not_for_warnings` — 사용자 query 가 변형의 not_for 와 매칭되면 경고
- `scoring_method: "rule"` (현재 룰 기반)

---

## `GET /api/workflows/search` — §1.C tag filter

```bash
curl "http://localhost:47823/api/workflows/search?tag=transparent-bg&tag=pose-sheet&not=scenery"
```

응답:
```jsonc
{
  "filters": { "tag": ["transparent-bg", "pose-sheet"], "not": ["scenery"] },
  "matches": [
    { "variant": "sprite/pixel_alpha", "intent": "...", "tags_hit": ["pose-sheet", "transparent-bg"] }
  ]
}
```

- `?tag=X&tag=Y` — 모든 tag 일치 (AND)
- `?not=Z` — 그 tag 가진 변형 제외
- 0 매칭이면 `matches: []`

---

## `POST /api/workflows/inputs` — 동적 이미지 업로드 (멀티파트)

PoseExtract / ControlNet 변형이 받을 사용자 이미지를 ComfyUI `input/<subfolder>/` 로 업로드.

```bash
curl -F "file=@./pose.png" \
     -F "subfolder=asset-factory" \
     -H "x-api-key: $AF_API_KEY" \
     http://localhost:47823/api/workflows/inputs
```

응답:
```jsonc
{ "name": "pose_a1b2.png", "subfolder": "asset-factory" }
```

→ `name` 을 generate 의 `workflow_params.load_images.<label>` 에 박는다.

**보안 자동**:
- content-type whitelist (PNG/JPEG/WEBP) — 415
- `MAX_INPUT_BYTES` 상한 (env-var override) — 413
- 이미지 정화 (polyglot strip, 메타 정화, DecompressionBomb 캐치)
- path traversal / 비-whitelist 문자 정규화

---

## `POST /api/workflows/inputs/from-asset` — 기존 asset → input

```bash
curl -X POST http://localhost:47823/api/workflows/inputs/from-asset \
  -H "x-api-key: $AF_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"asset_id": "uuid-...", "subfolder": "asset-factory"}'
```

PoseExtract 결과 → 다른 워크플로우의 ControlNet 입력. 1차에선 chain 자동화 안 함 — 사용자가 명시적으로 asset_id 전달.

---

## `POST /api/workflows/generate` — 메인 호출 ⭐

§1.B subject-injection (PR #42) 후 두 모드:

### 모드 1: subject (권장)

```bash
curl -X POST http://localhost:47823/api/workflows/generate \
  -H "x-api-key: $AF_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_category": "sprite",
    "workflow_variant":  "pixel_alpha",
    "subject":           "1girl, silver hair twin tails, school uniform, holding a notebook",
    "project":           "demo",
    "asset_key":         "test_001",
    "candidates_total":  4,
    "approval_mode":     "manual"
  }'
```

서버가 `meta.prompt_template.base_positive` + `, ` + `subject` 자동 합성. `base_negative` 자동 prepend.

### 모드 2: legacy (호환성)

```bash
curl -X POST http://localhost:47823/api/workflows/generate \
  -d '{
    "workflow_variant": "pixel_alpha",
    "prompt":           "pixel art, sprite sheet, 1girl, silver hair, ...",
    "negative_prompt":  "...",
    "project": "demo", "asset_key": "test_001"
  }'
```

`prompt` 통째 입력 — `base_positive` 무시. 자동 감지가 *legacy* 로 분기.

### `prompt_mode` 강제

| 값 | 동작 |
|---|---|
| `auto` (default) | 자동 감지 (subject 명시 / template null / 길이 휴리스틱 / 시그니처 토큰 매칭) |
| `subject` | 강제 subject 모드 (subject 또는 prompt 둘 중 하나 필수) |
| `legacy` | 강제 legacy 모드 (prompt 통째) |

### 응답 — `prompt_resolution` 동봉

```jsonc
{
  "run_id": "...",
  "task_ids": ["..."],
  "prompt_resolution": {
    "mode": "subject",                     // "subject" | "legacy"
    "user_slot": "subject",                 // legacy 면 null
    "user_input": "1girl, silver hair...",
    "final_positive": "pixel_character_sprite, sprite, ..., 1girl, silver hair...",
    "final_negative": "(worst quality, low quality:1.4), ..."
  },
  "approval_mode": "manual",
  ...
}
```

→ debug 시 `final_positive` 로 ComfyUI 에 실제 보낸 값 확인.

### 동적 입력 (`workflow_params.load_images`)

```jsonc
{
  "workflow_variant": "pose_extract",
  "subject": "extract pose",
  "workflow_params": {
    "load_images": {
      "source_image": "pose_a1b2.png"   // /inputs 응답의 name
    }
  },
  ...
}
```

또는 chain 시 (이전 run 결과 참조):
```jsonc
"load_images": {
  "pose_image": { "run_id": "run_xxx", "output_label": "pixel_alpha" }
}
```

---

## `GET /api/runs/{run_id}/status` — 상태 polling

```bash
curl http://localhost:47823/api/runs/run_xxx/status | jq
```

응답:
```jsonc
{
  "run_id": "run_xxx",
  "status": "completed",   // queued | running | completed | failed | completed_with_errors
  "progress": { "completed": 4, "total": 4 },
  "assets": [
    {
      "asset_id": "uuid-...",
      "candidate_index": 0,
      "label": "pixel_alpha",
      "image_path": "..."
    },
    ...
  ],
  "batch_id": "btc_xxxxxxxxxxxxxxxx",          // cherry-pick UI 가 후보를 묶는 키
  "cherry_pick_url": "/app/cherry-pick/btc_xxxxxxxxxxxxxxxx",   // manual 모드만, bypass 면 null. SSOT — 직접 합성 금지.
  "error_message": null,
  "first_task_prompt_resolution": { ... }   // 첫 task 의 prompt_resolution (디버깅)
}
```

**`completed_with_errors` + `error_message: null` + 빈 `assets`** — 변형 회귀. SKILL.md 본문의 회귀·실패 진단 섹션 참고.

---

## `POST /api/assets/approve-from-candidate` — 후보 승격

cherry-pick UI 에서 자동 호출. CLI 없음 (UI 표준).

```bash
curl -X POST http://localhost:47823/api/assets/approve-from-candidate \
  -H "x-api-key: $AF_API_KEY" \
  -d '{"candidate_id": "uuid-..."}'
```

→ 후보가 메인 자산으로 승격. `af list` 에 노출.

---

## `POST /api/export` — 승인본 묶음

```bash
curl -X POST http://localhost:47823/api/export \
  -H "x-api-key: $AF_API_KEY" \
  -d '{"project": "proj_demo", "format": "manifest"}'

# 응답 예
{
  "export_id": "...",
  "manifest_path": "~/workspace/assets/proj_demo/manifest.json",
  "asset_count": 12
}
```

manifest.json 에 asset_id, prompt_resolution.final_positive, seed, label, image_path 박힘 — 재현 가능.

> **bypass 자산 자동 제외** — 정식 export 에 안 묶임.

---

## `GET /api/system/gc/status` — GC 상태

```bash
curl http://localhost:47823/api/system/gc/status | jq
```

응답:
```jsonc
{
  "bypass_retention_days": 7,
  "next_run_at": "...",
  "last_run_summary": { "deleted_assets": 42, "freed_mb": 1234 }
}
```

bypass 자산은 `bypass_retention_days` 후 자동 GC. `tmp_*` / `sim_*` project 는 격리되어 정식 자산과 섞이지 않음.

---

## ComfyUI 카탈로그 / 헬스 / 큐

ComfyUI 가 1차 데이터 소스. Catalog/System 화면 + 진단용.
`af` 대응 명령은 없음 — 운영자가 curl 로 직접 진단할 때 사용.

### `GET /api/comfyui/health` — ComfyUI 단독 헬스 + 큐

```bash
curl -s http://localhost:47823/api/comfyui/health | jq
```

응답:
```jsonc
{
  "ok": true,
  "host": "http://192.168.50.225:8188",
  "fetched_at": "2026-04-29T01:30:00Z",
  "comfyui_version": "0.19.3",
  "python_version": "3.10.11",
  "device_count": 1,
  "device_names": ["cuda:0 NVIDIA GeForce RTX 4080 SUPER"],
  "queue": {"running": 0, "pending": 0},
  "workflows_available": 25
}
```

**실패 시** (timeout/예외 — 항상 200 + `ok: false`):
```jsonc
{"ok": false, "host": "...", "fetched_at": "...", "error": "timeout: ComfyUI did not respond within 5.0s"}
```

응답이 항상 200 + 본문 `ok` 필드로 분기 — 프론트 배너가 status code 분기 안 타게.
timeout 기본 5초 (`COMFYUI_HEALTH_TIMEOUT_SECONDS` env override).

### `GET /api/comfyui/catalog` — 모델/LoRA/VAE/ControlNet/Workflow 합본

```bash
curl -s http://localhost:47823/api/comfyui/catalog | jq '{
  checkpoints: (.checkpoints | length),
  loras: (.loras | length),
  vaes: (.vaes | length),
  controlnets: (.controlnets | length),
  upscalers: (.upscalers | length),
  workflows: (.workflows | length),
  fetched_at, stale
}'
```

응답:
```jsonc
{
  "fetched_at": "2026-04-29T01:30:00Z",
  "stale": false,
  "checkpoints": [
    {"name": "AnythingXL_xl.safetensors", "family": "sdxl", "used_by_workflows": ["illustration:anything_hires", ...]}
  ],
  "loras": [{"name": "Pixel_Resin_x16.safetensors", "used_by_workflows": [...]}],
  "vaes": [{"name": "xlVAEC_g102.safetensors", "used_by_workflows": []}],
  "controlnets": [{"name": "control-lora-openposeXL2-rank256.safetensors", "used_by_workflows": []}],
  "upscalers": [],
  "workflows": [
    {
      "id": "sprite:pixel_alpha",
      "category": "sprite",
      "label": "...",
      "variants": 1,
      "uses_models": ["AnythingXL_xl.safetensors"],
      "uses_loras": ["pixel-art-xl-v1.1.safetensors"]
    }
  ]
}
```

**캐시**: 60초 in-memory (`COMFYUI_CATALOG_TTL_SECONDS` env override). 응답 1.94MB
원본을 ComfyUI 에서 가져와 변환 → 두 번째 호출은 < 100ms.

**실패 시 (캐시 있음)**: 마지막 성공 페이로드 + `stale: true` + `error` 첨부.
**실패 시 (캐시 없음)**: `{"ok": false, "error": "...", "host": "...", "fetched_at": "..."}`.

`family` 필드: checkpoint name 으로 추론 (`xl` 토큰 → `sdxl`, `pony` 토큰 → `pony`,
나머지 → `unknown`). `used_by_workflows` 는 변형 api.json 의 정적 분석 결과 —
동적 patch 는 추적 불가 (PLAN_comfyui_catalog.md §8 위험 항목).

### `GET /api/comfyui/queue` — running list + pending count

```bash
curl -s http://localhost:47823/api/comfyui/queue | jq
```

응답:
```jsonc
{
  "ok": true,
  "running": [{"prompt_id": "abc-123", "number": 0}],
  "pending": 2,
  "host": "http://192.168.50.225:8188",
  "fetched_at": "..."
}
```

5초 timeout (`COMFYUI_QUEUE_TIMEOUT_SECONDS`). 항상 200 + `ok` 분기.

---

## OpenAPI

전체 spec:
```bash
curl http://localhost:47823/openapi.json | jq '.paths | keys'
```

→ FastAPI 자동 생성. 본 문서가 stale 하면 OpenAPI 가 SSOT.

---

## Skill freshness — 미충족 항목 우회

⏳ 미충족 항목 (SKILL.md 본문 참고) 별 우회:

| 미충족 | 우회 |
|---|---|
| `--dry-run` | 작은 변형 (`sprite/pixel_alpha`, candidates=1) 실 호출. 라벨 오타는 응답의 `report.skipped` 로 확인 |
| `aliases` (`@character` 등) | full path (`sprite/pixel_alpha`) 로 호출. catalog 응답에 `aliases` 키 등장 시 채워짐 |
| `run:<run_id>/<output>` syntax | `--input source_image=asset:<id>` 로 chain. 특정 output label 참조는 asset_id 직접 룩업 (`af list <project>` → metadata 매칭) |
