# Asset Factory API 레퍼런스 (v4 — ComfyUI 워크플로우)

> 일반 사용은 `af` CLI 로 충분. 이 문서는 디버깅·CLI 미구현 기능·스킬 freshness 표의 우회법이 필요할 때만 본다.
>
> ⚠️ v4 부터 A1111 직접 호출 / 모델·LoRA·step·cfg 수동 지정은 **폐기**. 이 문서는 ComfyUI 워크플로우 호출 인터페이스만 다룬다.

## 서버 정보

- **Base URL**: `http://localhost:8000` (Paperclip 에이전트는 같은 Mac mini 동작)
  - LAN: `http://192.168.50.250:8000` (Mac mini IP, `AF_HOST=0.0.0.0 ./run-dev.sh restart`)
  - Tailscale: `http://yoons-macmini.tailbff496.ts.net:8000` 또는 `http://100.72.190.122:8000`
- **API Key**: `.env` 의 `API_KEY`. 변경 계열에 `x-api-key` 헤더 필수. 인증은 항상 살아있음 — bypass 모드도 인증은 우회 안 함.
- **백엔드**: ComfyUI (Asset Factory 가 알아서 호출. 직접 두드리면 안 됨.)
- **Web UI**: `/app/`, **Cherry-pick UI**: `/cherry-pick?run=<run_id>`
- **데이터**: `~/workspace/asset-factory/data/`
- **Export 기본**: `~/workspace/assets/<project>/<category>/<asset_key>.png`

## 엔드포인트 빠른 참조

| 용도 | Method · Path | `af` 대응 |
|------|---------------|-----------|
| 헬스 / ComfyUI 연결 | `GET /api/health` | `af health` |
| **워크플로우 카탈로그** | `GET /api/workflows/catalog` | `af workflow catalog` |
| 워크플로우 상세 | `GET /api/workflows/catalog` (variant 필터링) | `af workflow describe <cat>/<v>` |
| **동적 입력 업로드** (멀티파트) | `POST /api/workflows/inputs` 🔑 | `af workflow upload` *(P0 미구현 시 curl)* |
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

## `GET /api/workflows/catalog`

ComfyUI 레지스트리 카탈로그 — 카테고리·변형·출력·기본값을 그대로 노출.

```jsonc
{
  "version": 1,
  "categories": {
    "sprite": {
      "description": "게임용 픽셀 캐릭터 스프라이트 ...",
      "primary_variant": "pixel_alpha",
      "variants": {
        "pixel_alpha": {
          "description": "픽셀 그리드 + 투명배경 (게임 엔진용) ⭐",
          "available": true,
          "status": "ok",
          "primary": true,
          "file": "sprite/Sprite_Illustrious_PoseGuided_Alpha_V38_api_pixel_alpha.json",
          "has_file": true,
          "outputs": [
            { "label": "stage1",     "primary": false },
            { "label": "pixelized",  "primary": false },
            { "label": "pixel_alpha","primary": true  }
          ],
          "defaults": {
            "steps": 30, "cfg": 6.5,
            "sampler": "dpmpp_2m", "scheduler": "karras",
            "width": 1280, "height": 640,
            "pose_image": "pose_grid_1x3_mini_2.5h_1280x640.png"
          },
          // ↓ P0-2 채워지면 명시적으로 노출되는 필드 (현재는 defaults 에서 추측)
          "input_labels": [
            { "label": "pose_image", "required": false,
              "default": "pose_grid_1x3_mini_2.5h_1280x640.png" }
          ]
        }
      }
    }
  },
  // ↓ P0/P2 alias 등장 시 노출
  "aliases": {
    "@character": { "category": "sprite",       "variant": "pixel_alpha" },
    "@marketing": { "category": "illustration", "variant": "animagine_hires" },
    "@sketch":    { "category": "sprite",       "variant": "pixel_alpha", "approval_mode": "bypass" }
  }
}
```

**`available: false`** 인 변형은 `status: "needs_api_conversion"` — ComfyUI UI 에서 API 포맷 export 가 안 된 상태. 호출하면 400.

## `POST /api/workflows/inputs` — 동적 이미지 업로드 (멀티파트)

PoseExtract / ControlNet 변형이 받을 사용자 이미지를 ComfyUI `input/<subfolder>/` 로 업로드.

```bash
curl -F "file=@./pose.png" \
     -F "subfolder=asset-factory" \
     -H "x-api-key: $AF_API_KEY" \
     http://localhost:8000/api/workflows/inputs
```

응답:
```json
{ "name": "asset-factory_<sha256[:12]>_pose.png" }
```

이 `name` 을 `POST /api/workflows/generate` 의 `workflow_params.load_images.<label>` 에 박는다.

**가드**:
- Content-type: `image/png` / `image/jpeg` / `image/webp` 만
- 크기: 20MB (`MAX_INPUT_BYTES`) 초과 시 413
- PIL `Image.load()` 로 픽셀 디코딩 + 재인코딩 → polyglot/EXIF/ICC 정화
- DecompressionBombError 캐치 → 픽셀폭탄 입력도 400
- subfolder 정규화 (path traversal 차단), 비었거나 위반이면 `asset-factory` 로

## `POST /api/workflows/inputs/from-asset` — 기존 에셋을 입력으로

```bash
curl -X POST -H "Content-Type: application/json" -H "x-api-key: $AF_API_KEY" \
  -d '{"asset_id": "ast_..."}' \
  http://localhost:8000/api/workflows/inputs/from-asset
```

응답: `{ "name": "asset-factory_..._<asset>.png" }`

> P1-6 채워지면 `{ "run_id": "...", "output_label": "pixel_alpha" }` 도 받게 됨 — 그때까지는 `asset_id` 로만.

## `POST /api/workflows/generate` ⭐ — 메인 진입점

```jsonc
{
  "category": "sprite",
  "variant":  "pixel_alpha",
  "project":  "wooridul-factory",
  "asset_key": "warrior_idle",

  "prompt": "1girl, blue knight armor, holding silver sword, masterpiece, ...",
  "negative_prompt": "",  // 비우면 변형의 recommended preset (NEG_PIXEL_SPRITE 등) 사용

  // 동적 입력 — POST /api/workflows/inputs 응답의 name 을 박음
  "workflow_params": {
    "load_images": {
      "pose_image":   "asset-factory_abc123_pose.png",
      "source_image": "asset-factory_def456_user.png"
    },
    // KSampler stage 별 override (드물게 사용)
    "ksampler_overrides": {
      "hires|refine": { "steps": 8, "cfg": 4.0 }
    }
  },

  "seed": 42,                  // omit → random
  "candidates": 4,             // cherry-pick 후보 수 (default 1)

  "approval_mode": "manual",   // "manual" (default) | "bypass" — P0-1 채워지면 활성
  "dry_run": false             // P2-9 채워지면 활성 — patch 결과만 반환
}
```

응답 (즉시):
```jsonc
{
  "run_id": "run_01H...",
  "status": "queued",
  "expected_outputs": [
    { "label": "stage1",      "asset_id": null },
    { "label": "pixelized",   "asset_id": null },
    { "label": "pixel_alpha", "asset_id": null }   // primary
  ],
  "poll_url": "/api/runs/run_01H.../status",
  "estimated_duration_sec": 35
}
```

폴링이 끝나면 `expected_outputs[].asset_id` 가 채워지고 `status: "completed"` 로.

## 폴링

`GET /api/runs/{run_id}/status` — `POST /api/workflows/generate` 의 응답 스키마와 동일 형태가 채워져 돌아온다.

규칙:
- 첫 polling 5초 후, 이후 3~5초 간격
- 변형별 소요 시간: `sprite/pixel_alpha` ~35s, `sprite/full` ~60s, `illustration/animagine_hires` ~25s
- `status == "failed"` 면 `error_message` 보고
- 타임아웃 권장: `expected_duration_sec × 3` (안전마진)

## 에러 분류

| HTTP | 의미 | 흔한 원인 |
|---|---|---|
| 400 | 입력 검증 실패 | unknown variant, malformed `workflow_params`, polyglot/픽셀폭탄 입력 |
| 401 | API key 누락 | 변경 계열인데 `x-api-key` 헤더 없음 |
| 403 | 권한 없음 | 다른 프로젝트 에셋 접근 |
| 404 | 자원 없음 | unknown asset_id, run_id |
| 413 | 너무 큰 입력 | 20MB 초과 |
| 415 | 미지원 포맷 | content-type 또는 PIL 검출 포맷이 PNG/JPEG/WEBP 아님 |
| 422 | 워크플로우 불가 | 변형이 `needs_api_conversion` |
| 500 | 백엔드 장애 | ComfyUI 미연결, GPU OOM |

## API Pitfalls

1. **카탈로그·런타임 일치 검증**: catalog 응답의 `available: false` / `status: needs_api_conversion` 인 변형은 generate 시 422. 호출 전 catalog 확인 권장.
2. **`workflow_params.load_images` 라벨 오타**: catalog 의 `input_labels`(또는 `defaults`) 에 없는 라벨은 silent skip — 결과는 나오지만 의도와 다른 이미지. `dry_run` (P2-9) 또는 결과 검수.
3. **`run_id` ≠ `asset_id`**: 한 run 이 multi-output 이면 `expected_outputs[].asset_id` 가 N개. cherry-pick UI 와 polling 은 `run_id` 기준, 다운로드는 `asset_id` 기준.
4. **`completed_count == total_count` 인데 status=running**: 워커가 마지막 마무리 중. 한 번 더 polling.
5. **`approval_mode: "bypass"` 의 namespace**: bypass 자산은 `af list <project>` 에 안 보임. `--include-bypassed` 또는 API 의 `?include_bypassed=true` 로만 노출. `tmp_*`/`sim_*` project 명 권장.
6. **`from-asset` 의 권한**: 호출자가 접근권 없는 asset_id 면 403. 같은 회사 asset 만.
7. **polyglot 차단**: `Image.load()` 실패 → 400. 정상 PNG 가 거부되면 EXIF 손상 의심 — `pngcrush` 로 재인코딩 후 재시도.
8. **GC 와 bypass**: bypass 자산은 일반 candidate 보다 짧은 retention. `health.bypass_retention_days` (P1-7) 확인 후 export 또는 승격 타이밍 잡기.
9. **registry.yml 수정 후 캐시**: `workflow_registry` 는 프로세스 시작시 1회 로드. yaml 만지면 `./run-dev.sh restart` 필요.
10. **A1111 잔존 엔드포인트**: 혹시 `/api/sd/*` / `/api/generate` (single) / `/api/mcp/design_asset` 같은 경로가 살아있어도 **사용 금지**. P2-8 후 deprecation 헤더로 드러남.

## 스킬 freshness — P0 미구현 시 우회

| P0 | 대응 우회 |
|---|---|
| `af workflow upload` 미구현 | 위 멀티파트 curl 로 `/api/workflows/inputs` 직접 호출 → 응답의 `name` 을 generate 의 `workflow_params.load_images.<label>` 에 박기 |
| `--bypass-approval` 미구현 | manual 승인으로 운영. `tmp_*` project 격리. |
| catalog `input_labels` 미노출 | catalog 응답의 `defaults` 에서 `pose_image` / `source_image` 키 보고 라벨 추측. 매칭 실패 시 dry_run. |

자세한 우회법은 `SKILL.md` 의 "Skill freshness" 표 참고.
