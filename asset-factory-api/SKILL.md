---
name: asset-factory-api
version: 4
description: "Asset Factory(ComfyUI 워크플로우 기반) 로 게임/일러스트 에셋 생성. 변형 선택 → 호출 → 결과 회수. 모델·LoRA·step·cfg 같은 SD 파라미터는 사용자가 만지지 않는다. SD 서버 직접 호출 절대 금지."
triggers:
  - asset factory
  - asset-factory
  - 에셋 팩토리
  - af workflow
  - 픽셀아트 생성
  - 게임 에셋
  - 스프라이트 생성
  - 일러스트 생성
  - 캐릭터 도트
  - 로고 생성
  - 임시 시뮬
  - 스캐치
  - cherry-pick
  - comfyui 워크플로우
---

# Asset Factory (v4 — ComfyUI 워크플로우 시대)

게임/일러스트 에셋 생성 파이프라인. **`af` CLI 한 줄로 ComfyUI 워크플로우 변형을 호출**한다.

## 🚨 v4 의 패러다임 전환 (이전과 다름)

이전(v3) 멘탈모델은 폐기됐다:

| 항목 | v3 (구) | v4 (지금) |
|---|---|---|
| 백엔드 | A1111 직접 호출 | **ComfyUI 워크플로우 호출** |
| 모델 선택 | 에이전트가 `af catalog models` 보고 결정 | **변형(variant)이 모델을 내장** — 에이전트 관여 X |
| LoRA/weight | 에이전트가 `--lora xxx:0.8` 지정 | 변형 내부에 박혀 있음 |
| step/cfg/sampler | 에이전트가 결정 | 변형 `defaults` 가 알아서 |
| 카테고리 | 약함 | **명시적**: `sprite` / `illustration` / `pixel_bg` / `icon` |
| 결과 형태 | 1장 | **multi-output** (변형마다 다름; e.g. `sprite/pixel_alpha` = 3장) |
| 동적 입력 | 없음 | **PoseExtract / ControlNet chain** 가능 (이미지 업로드) |
| 승인 | 항상 cherry-pick 큐 | `--bypass-approval` 플래그로 우회 가능 |

→ **에이전트의 인지 부담은 줄었고, 핵심 역량은 "카탈로그 탐색 + 변형 선택"** 이다.

## When to use

- 게임 캐릭터 스프라이트, 마케팅 일러스트, 픽셀 배경, UI 아이콘 — 어떤 종류든.
- 사람이 cherry-pick 할 후보 N장이 필요할 때.
- 임시 시뮬/스캐치 1장 — `--bypass-approval` 로 즉시 회수.
- 다른 에이전트의 입력으로 흘릴 chain 중간물.

## When NOT to use

- 비-에셋 1회성 이미지 (예: 슬라이드 1장 mockup) — 이미지 생성 자체가 목표가 아니고
  에셋 파이프라인에 들어갈 필요 없는 거면 다른 도구.
- ComfyUI 직접 두드리기 — 절대 금지. asset-factory 가 입출력·이력·승인을 일관되게 관리한다.

---

## CLI: `af`

설치 위치: `~/.local/bin/af` (NodeJS, deps 없음). 자세한 옵션은 `af --help`.

> **백엔드 분기 (v4.1)**: `workflow` 서브트리(`catalog`, `describe`, `gen`, `upload`)는
> asset-factory 레포의 **Python typer CLI** 로도 동일 동작한다 — `python -m cli workflow ...`
> (PR #18에서 채택). `af workflow ...` 와 결과는 같다. `health` / `list` / `get` /
> `export` / `batch` (A1111 호환) 등 그 외 명령은 당분간 `af` (Node.js) 에만 있다.
> 일반 사용자는 `af` 그대로 쓰면 된다 — 분기는 운영자만 알면 충분.

```bash
# 1. 점검
af health                                 # ComfyUI 연결, registry 로드 상태

# 2. 카탈로그 탐색 (가장 먼저 — 어떤 변형을 쓸지 결정)
af workflow catalog                       # 카테고리 → 변형 트리 + input_labels + aliases
af workflow describe sprite/pixel_alpha   # 단일 변형 상세 (defaults, outputs, 권장 negative)

# 3. 생성 — 텍스트만으로
af workflow gen sprite/pixel_alpha <project> <asset_key> "<prompt>" --wait

# 4. cherry-pick 후보 N장
af workflow gen sprite/pixel_alpha <project> <asset_key> "<prompt>" \
   --candidates 4 --wait

# 5. 동적 입력 (PoseExtract / ControlNet)
af workflow upload ./pose.png                       # 로컬 파일 업로드
af workflow upload --from-asset <asset_id>          # 기존 에셋 → 입력으로 chain
af workflow upload --from-run <run_id> --output pixel_alpha  # 이전 run 의 특정 출력

# 또는 generate 한 번에 (가장 자주 쓰는 패턴)
af workflow gen sprite/pose_extract <project> <asset_key> "<prompt>" \
   --input source_image=@./pose.png \
   --input pose_image=run:<run_id>/pixel_alpha \
   --wait

# 6. Bypass 모드 (사람 승인 우회 — 시뮬/스캐치/chain 중간물)
af workflow gen sprite/pixel_alpha tmp_sim sim_001 "..." \
   --bypass-approval --wait
# → 결과 즉시 다운로드 가능, 승인 큐 거치지 않음. tmp_* project 권장.

# 7. Aliases (의도 기반 단축 — 매핑은 catalog 에 노출됨)
af workflow gen @character <project> <key> "..." --wait   # = sprite/pixel_alpha
af workflow gen @marketing <project> <key> "..." --wait   # = illustration/animagine_hires
af workflow gen @sketch <project> <key> "..." --wait      # = sprite/pixel_alpha + bypass

# 8. 결과 회수
af list <project> [--include-bypassed]
af get <asset_id> -o output.png
af export <project> --manifest               # 승인본만 묶음. bypass 자산 자동 제외.

# 9. dry-run (patch 점검만, ComfyUI 호출 X)
af workflow gen ... --dry-run
# → 어떤 노드에 어떤 값이 패치되는지 PatchReport 만 반환. 라벨 매칭 사전 점검용.
```

**폴링**: `--wait` 빼면 enqueue 후 즉시 종료. 응답의 `run_id` 로 나중에 `af status <run_id>` 또는 `af wait <run_id>`.

---

## 카테고리 결정 트리 (가장 자주 쓰는 매핑)

> 🟢 빠른 cheat-sheet. 정확한 변형 의도/출력 형태/prompt 합성은 **아래 `## 디스커버리
> 메타`** 의 catalog 응답 (`meta.intent` / `meta.output_layout` / `meta.prompt_template`)
> 이 SSOT — 표와 catalog 가 충돌하면 catalog 우선.

| 의도 | 카테고리/변형 | alias |
|---|---|---|
| 게임용 픽셀 캐릭터 (즉시 사용) | `sprite/pixel_alpha` ⭐ | `@character` |
| 게임 캐릭터 디테일 보강 | `sprite/hires` | — |
| 일러스트풍 캐릭터 (배경 알파) | `sprite/rembg_alpha` | — |
| 비교용 (5장 한 번에) | `sprite/full` | — |
| 마케팅·표지 일러스트 | `illustration/animagine_hires` | `@marketing` |
| Pony 스타일 일러스트 | `illustration/pony_hires` | — |
| 픽셀 타일/배경 | `pixel_bg/*` | — |
| UI 아이콘 (flat) | `icon/*` | — |
| 임시 스캐치 1장 | `@sketch` (bypass 자동 적용) | `@sketch` |

**규칙**: 카테고리·변형 직접 지정과 alias 둘 다 OK. 새 alias 등장 여부는 `af workflow catalog` 의 `aliases` 필드로 확인.

---

## 디스커버리 메타 — task → variant 결정

`/api/workflows/catalog` 응답 (`version: 2`) 의 각 변형에 디스커버리 메타가
포함된다. 변형 선택·prompt 합성에 필요한 의사결정 정보의 **SSOT**.

> 출처: [`asset-factory/docs/NEXT.md §1.A`](https://github.com/sunghere/asset-factory/blob/main/docs/NEXT.md) (PR #21 spec) + 구현 PR #30.
> 마이그레이션은 변형 단위로 점진적 — `meta` 가 빈 객체인 변형은 *legacy* (메타 미등록).

### 응답 schema (실 catalog 기준)

```jsonc
// GET /api/workflows/catalog — sprite/pixel_alpha (메타 마이그레이션 완료 변형)
{
  "version": 2,                                 // ← schema bump (legacy 자동 감지 신호)
  "categories": {
    "sprite": {
      "variants": {
        "pixel_alpha": {
          // ─── 기존 호출 메타 (변동 없음) ────────────
          "description": "픽셀 그리드 + 투명배경 (게임 엔진용) ⭐",
          "available": true, "status": "ready", "primary": true,
          "outputs": [...], "defaults": {...},
          "input_labels": [
            {
              "label": "pose_image",
              "required": false,
              "default": "pose_grid_1x3_mini_2.5h_1280x640.png",
              "description": "ControlNet 포즈 가이드. 1×3 그리드 PNG. ...",
              "alternatives": [                  // ← §1.A 신규 (사이드카 yaml)
                "pose_grid_1x3_5h_1280x640.png",
                "pose_grid_1x4_1280x640.png",
                "pose_grid_3x3_1280x896.png"
              ]
            }
          ],

          // ─── 신규 디스커버리 메타 (§1.A) ────────────
          "meta": {
            "intent": "3-pose character sheet (1×3 grid, transparent BG) for 2D game engine import.",
            "use_cases": ["RPG character with idle / walk-side / walk-front 3-pose set", ...],
            "not_for":   ["single character portrait — use illustration/animagine_hires", ...],
            "output_layout": {
              "kind": "pose_grid",               // single | pose_grid | tile_grid | character_sheet
              "rows": 1, "cols": 3,
              "per_cell_size": [426, 640],
              "alpha": true,
              "notes": "..."
            },
            "tags": [                            // list[str], 영문/한국어 혼용 OK
              "pixel-art", "transparent-bg", "pose-sheet", "controlnet-pose",
              "1x3-grid", "rpg-character", "2d-game-asset", "chibi", "illustrious",
              "게임-스프라이트", "픽셀-캐릭터"
            ],
            "prompt_template": {                 // null 이면 §B 미마이그 변형 (legacy)
              "base_positive": "pixel_character_sprite, sprite, sprite sheet, (pixel art:1.5), ...",
              "base_negative": "(worst quality, low quality:1.4), blurry, ...",
              "user_slot": {
                "label": "subject",
                "description": "캐릭터 묘사만 (외형/복장/무기). 스타일·구도·배경 묘사 금지 ...",
                "examples": [
                  "1girl, silver hair twin tails, navy school uniform, holding a notebook",
                  "1boy, brown spiky hair, blue tunic, leather belt with sword",
                  ...
                ],
                "required": true, "min_chars": 8, "max_chars": 400
              },
              "injection_rule": "{base_positive}, {subject}"
            }
          }
        },

        "hires": {
          // 메타 마이그레이션 안 된 변형 (legacy) ─────
          "description": "1920×960 디테일 보강 (흰배경)",
          ...
          "meta": {
            "intent": "",                        // ← 빈 문자열 = legacy
            "use_cases": [], "not_for": [], "tags": [],
            "output_layout": { "kind": "single", "rows": 1, "cols": 1,
                               "per_cell_size": null, "alpha": false, "notes": "" },
            "prompt_template": null              // ← null = §B 미마이그
          }
        }
      }
    }
  }
}
```

### 변형 선택 4-step

1. **catalog 호출** — `af workflow catalog` 또는 `GET /api/workflows/catalog`. `version: 2` 확인.
2. **`meta.intent` 한 줄로 변형 후보 인식**:
   - 비어있으면 (`""`) legacy 변형 — 본문 `description` + `defaults.width/height/pose_image` 로 추론 fallback (Pitfalls #12 휴리스틱)
   - 있으면 *그 한 줄 그대로* 가 변형의 본질
3. **`meta.use_cases` / `meta.not_for` 로 적합성 검증**:
   - `use_cases` 에 task 의도가 매칭되면 OK
   - `not_for` 에 *대체 변형 힌트* 가 박혀있음 (예: `"single view 일러스트 → illustration/* 사용"`) — 잘못 골랐으면 그 힌트 따라 점프
4. **`meta.output_layout` 으로 출력 형태 *확정***:
   - `kind` 가 `single` / `pose_grid` / `tile_grid` / `character_sheet` 중 하나
   - `rows × cols × per_cell_size` 가 *최종 이미지의 그림 구성* — 사용자가 원하는 형태와 일치하는지 *반드시* 셀프체크 (Pitfalls #12 의 사고 사례 — `pose_grid` 인데 single 로 오인하면 학교 복도 씬 같은 결과)

### prompt 합성 — `meta.prompt_template` (§1.B 자동)

서버가 변형의 `meta.prompt_template.base_positive` / `base_negative` 를 **자동으로
합성**한다. 사용자/에이전트는 *캐릭터 묘사만* (`subject`) 넣으면 됨.

#### 두 입력 모드 — `subject` (권장) vs `prompt` (legacy)

`POST /api/workflows/generate` 가 받는 두 입력 필드:

| 필드 | 모드 | 동작 |
|---|---|---|
| `subject` (str, optional) | **subject** | 변형의 `base_positive` + `injection_rule` 로 자동 합성. 사용자는 *캐릭터 묘사만*. |
| `prompt` (str) | **legacy** 또는 자동 | 통째 입력 — 변형의 `base_positive` 무시. 기존 사용자/스크립트 호환. |
| `prompt_mode` (`auto` / `subject` / `legacy`) | 강제 | `auto`(default) — 자동 감지. `subject`/`legacy` — 강제. |

**자동 감지 규칙** (`prompt_mode: auto`, `subject` 미지정, `prompt` 만 있을 때):

1. `prompt` 길이가 `user_slot.max_chars` 초과 → **legacy**
2. `base_positive` 의 첫 4 토큰 (시그니처) 이 `prompt` 에 *이미 있음* → **legacy** (사용자가 통째 작성)
3. 변형에 `prompt_template == null` (legacy 변형) → **legacy** 자동
4. 그 외 → **subject** (기본)

#### `subject` 모드 호출 (권장)

```python
POST /api/workflows/generate
{
  "workflow_category": "sprite",
  "workflow_variant":  "pixel_alpha",
  "subject": "1girl, silver hair twin tails, navy school uniform, holding a notebook",
  "project": "demo", "asset_key": "test_001",
  "candidates_total": 1
}
```

CLI:
```bash
af workflow gen sprite/pixel_alpha demo test_001 --subject "1girl, silver hair twin tails, navy school uniform, holding a notebook" --wait
```

`base_positive` (`pixel_character_sprite, sprite, sprite sheet, ...`) + `, ` + `subject` 가
서버에서 자동 합성. `base_negative` 는 자동 prepend (override 불가).

#### 응답의 `prompt_resolution`

generate 응답에 *항상* `prompt_resolution` 객체 동봉 (spec §B.4 Response):

```jsonc
{
  "run_id": "...",
  "prompt_resolution": {
    "mode": "subject",                // "subject" | "legacy"
    "user_slot": "subject",            // subject 모드면 슬롯명, legacy 면 null
    "user_input": "1girl, silver hair...",   // subject or prompt 원본
    "final_positive": "pixel_character_sprite, sprite, sprite sheet, ..., 1girl, silver hair...",
    "final_negative": "(worst quality, low quality:1.4), blurry, ..."
  },
  ...
}
```

→ **debug 시 `final_positive` 로 ComfyUI 에 실제 보낸 값 확인 가능**. 디자인이
이상하면 여기를 먼저 본다 (subject 가 base_positive 에 묶여서 어떻게 나갔나).

#### subject 입력 가이드

`meta.prompt_template.user_slot` 의 안내 따른다:

- `user_slot.description` — *"캐릭터 묘사만 (외형/복장/무기). 스타일·구도·배경 묘사 금지"*
- `user_slot.examples` — 변형마다 검증된 예시 prompt 들 (그대로 복사 가능)
- `user_slot.min_chars` / `max_chars` — 길이 검증. 위반 시 HTTP 400 + 에러 코드

**스타일/배경/레이아웃 묘사는 base_positive 가 이미 처리** — subject 에 *중복 묘사하지 마라*. (chibi:1.4) 같은 강조도 금지 (ControlNet stick figure 와 충돌).

#### legacy 모드 (기존 사용자/스크립트)

`prompt` 통째 입력은 그대로 동작:
```python
POST /api/workflows/generate
{
  "workflow_variant": "pixel_alpha",
  "prompt": "pixel art, sprite sheet, 1girl, silver hair, ...",   // 통째 입력
  ...
}
```

자동 감지가 *legacy* 로 분기 (시그니처 토큰 매칭). 결과 동일 — 기존 워크플로우 호환.

#### `base_negative` override 금지

사용자 `negative_prompt` 는 변형의 `base_negative` 에 **append 만**. 변형이 박은
필수 negative (예: `floating sword, detached weapon` — sprite/pixel_alpha) 는
*override 불가* 가 안전 정책 (spec §B.3).

### 변형 추천 (자연어 / tag 검색) — §1.C 자동

서버가 **자연어 query** + **tag filter** 두 endpoint 를 노출. catalog 응답을 직접
파싱하지 말고 이걸 호출.

#### `POST /api/workflows/recommend` — 자연어 query (rule-based scoring)

```jsonc
POST /api/workflows/recommend
{
  "query": "RPG 픽셀 캐릭터 정면 측면 뒷면 시트",
  "top": 3,
  "include_unavailable": false   // optional, default false
}

→ 200 OK
{
  "query": "...",
  "candidates": [
    {
      "variant": "sprite/pixel_alpha",
      "score": 0.92,
      "intent": "3-pose character sheet (1×3 grid, transparent BG) for 2D game engine import.",
      "use_cases_hit":   ["RPG character with idle / walk-side / walk-front 3-pose set", ...],
      "tags_hit":        ["rpg-character", "픽셀-캐릭터"],
      "not_for_warnings":[]   // ← 사용자 query 가 이 변형의 not_for 와 매칭되면 경고
    },
    ...
  ],
  "scoring_method": "rule"   // 현재 룰 기반. 미래: "embedding" / "llm"
}
```

CLI: `af workflow recommend "RPG 픽셀 캐릭터 정면 측면 뒷면 시트" --top 3`

**스코어링 (Phase 1 — 룰 기반)**:
- `intent` / `use_cases` / `tags` 에 query 키워드 매칭 → 가산점
- `not_for` 에 query 매칭 → 페널티 + `not_for_warnings` 에 동봉

**한국어/영어 혼용 OK** — `meta.intent` 가 영문, `meta.tags` 에 한국어 들어있는
변형도 정확히 매칭.

#### `GET /api/workflows/search` — tag filter (정확 매칭)

```jsonc
GET /api/workflows/search?tag=transparent-bg&tag=pose-sheet&not=scenery

→ 200 OK
{
  "filters": { "tag": ["transparent-bg", "pose-sheet"], "not": ["scenery"] },
  "matches": [
    { "variant": "sprite/pixel_alpha",
      "intent":  "3-pose character sheet (1×3 grid, ...)",
      "tags_hit":["pose-sheet", "transparent-bg"] }
  ]
}
```

- `?tag=X&tag=Y` — 모든 tag 일치 (AND)
- `?not=Z` — 그 tag 가진 변형 제외 (negative filter)
- 0 매칭이면 `matches: []`

CLI: `af workflow search --tag transparent-bg --tag pose-sheet --not scenery`

#### 둘 중 어느 걸 쓰나?

| 상황 | 추천 endpoint |
|---|---|
| 사용자가 **자연어 task 묘사** (e.g. "게임 캐릭터 도트") | `/recommend` |
| **알려진 tag 조합** 으로 정확 매칭 (e.g. `transparent-bg` + `pose-sheet`) | `/search` |
| **부정 필터** 필요 (e.g. *"pixel-art 인데 pose-sheet 아닌 것"*) | `/search` |
| 후보 *순위* + 점수 + 경고 필요 | `/recommend` |

#### 조합 패턴 (Paperclip Asset Relay 시)

```python
# 1) 자연어로 후보 좁히기
POST /api/workflows/recommend
  → top 3 후보 받음

# 2) `not_for_warnings` 비어있는 첫 후보 채택
candidate = next(c for c in res["candidates"] if not c["not_for_warnings"])

# 3) catalog 의 `meta.output_layout` 으로 형태 최종 검증
# 4) `subject` 모드로 generate 호출
```

### tags — 자유 태그 (closed enum 아님)

`tags` 는 **list[str]**. 변형마다 영문/한국어 혼용 자유. 추천 컨벤션:

| 카테고리 | 자주 쓰는 tag (참고용 — 강제 아님) |
|---|---|
| 출력 형태 | `transparent-bg` / `alpha-pixel` / `alpha-rembg` / `1x3-grid` / `1x4-grid` / `3x3-grid` / `tile-grid` |
| 스타일 | `pixel-art` / `chibi` / `flat` / `anime` |
| 용도 | `rpg-character` / `2d-game-asset` / `marketing` / `tile-map` |
| 모델 | `illustrious` / `pony` / `sdxl-anime` / `sd1.5` |
| 입력 | `controlnet-pose` / `pose-sheet` / `face-detailer` |

새 변형 작성 시 *기존 변형의 tags* 를 보고 동일 어휘 재사용 권장 (검색 매칭 정합성).
어휘 폐쇄형 enum 은 §1.C 머지 시점에 결정 (현재는 자유 list).

### 매니페스트 마이그레이션 진행 상태

**25/25 변형 메타 마이그 완료** (PR #38–#41). 모든 변형이 `meta.intent` / `output_layout` / `tags` / `prompt_template` 노출.

| 카테고리 | 변형 수 | 상태 |
|---|---|---|
| sprite | 10 | ✅ 모두 (pixel_alpha / hires / rembg_alpha / stage1 / full / v37_pixel / v37_full / v36_pro_stage1 / v36_pro_full / pose_extract) |
| illustration | 10 | ✅ 모두 (animagine / pony / hyphoria / anything / meinamix × {hires, stage1}) |
| pixel_bg | 4 | ✅ 모두 (sdxl_stage1 / sdxl_hires / pony_stage1 / pony_hires) |
| icon | 1 | ✅ flat |

`pose_extract` 만 `prompt_template == null` (utility 변형 — pose 추출, prompt 무관).

---

## 동적 입력 (PoseExtract / ControlNet) — 사용법

특정 변형은 사용자 이미지를 입력으로 받는다 (예: `sprite/pose_extract`, ControlNet 변형).
어떤 변형이 어떤 라벨을 받는지는 catalog 응답의 `input_labels` 에 명시된다:

```jsonc
// af workflow describe sprite/pose_extract
{
  "input_labels": [
    { "label": "source_image", "required": true,  "description": "Pose 추출할 원본 이미지" },
    { "label": "pose_image",   "required": false, "default": "pose_grid_1x3_mini_2.5h_1280x640.png" }
  ]
}
```

→ `--input <label>=<source>` 형식으로 박아 넣는다. `<source>` 는 3가지:

| 형식 | 의미 |
|---|---|
| `@./local.png` | 로컬 파일 — 자동 업로드 |
| `<asset_id>` | 기존 에셋 (UUID 직접) |
| `run:<run_id>/<output_label>` | 이전 run 의 특정 출력 (chain 의 표준 형태) |

**chain 의 표준 패턴** (사용자 이미지 → 포즈 추출 → 캐릭터 합성):

```bash
# 1) 포즈 추출
af workflow gen sprite/pose_extract pj_chain step1 "extract pose" \
   --input source_image=@./user_pose.jpg --bypass-approval --wait
# → run_id="run_aaa..."

# 2) 추출된 포즈로 캐릭터 합성
af workflow gen sprite/pixel_alpha pj_chain step2 "knight, blue armor, ..." \
   --input pose_image=run:run_aaa.../pixel_alpha --wait
```

> chain 중간물(`step1`)은 `--bypass-approval` 권장 — 검수 가치가 없는 변환물.

---

## 승인 모드 (`approval_mode`)

| 모드 | 호출 | 용도 |
|---|---|---|
| `manual` (default) | 플래그 없음 | 사람이 cherry-pick UI 에서 승인. 게임 자산·로고 등 *실제로 들어갈* 에셋. |
| `bypass` | `--bypass-approval` | 사람 승인 무의미한 임시물. 시뮬·스캐치·chain 중간물. |
| `auto` (예약) | `--auto-approve` | (서버가 신뢰 점수로 자동 승인 — 향후) |

**Bypass 사용 규칙**:
- project 명을 `tmp_*` 또는 `sim_*` 로 — namespace 격리.
- `af list <project>` 에 안 보임. `--include-bypassed` 로만 노출.
- `af export --manifest` 에 안 묶임 (승인본 아님).
- 보존 기간: `af health` 의 `bypass_retention_days` 참고. 그 후 GC.
- **인증은 동일** — 승인 우회지 인증 우회 아님.

**선택 가이드**:
- 로고 8장 → cherry-pick 의미 있음 → `manual`
- 캐릭터 시뮬 100장 → 검수 무의미 → `bypass`
- chain 중간물 → 항상 `bypass`
- 게임에 들어갈 sprite → `manual`

---

## 프롬프팅 핵심

> 변형이 모델/LoRA/preset 을 박고 있어 **세부 SD 파라미터는 만지지 않는다**. 에이전트가
> 신경쓸 건 prompt 본문과 negative 의 **속성 보호** 뿐.

> 🟢 **모든 변형의 prompt 합성은 서버 자동** (§1.B). 사용자/에이전트는 `subject`
> (캐릭터 묘사만) 입력 — `meta.prompt_template.user_slot.examples` 가 SSOT.
> 아래 §1~§4 cheat-sheet 는 *빠른 reference* (legacy 모드 직접 호출 또는
> 디버깅 시 base_positive 가 어떻게 생긴지 감 잡기 용).

### 1. Prefix는 카테고리 워크플로우가 자동 추가
- `sprite/*`: `pixel art, sprite, three views, ...` 자동 prepend
- 에이전트 입력은 **캐릭터 묘사 본문만**. `pixel art,` 같은 prefix 직접 안 적어도 됨.

### 2. 권장 negative 는 catalog 에서 제공
`af workflow describe <variant>` 의 `recommended_negative_preset` 또는 `defaults.negative_prompt`
가 이미 채워져 있다 (예: `NEG_PIXEL_SPRITE`, `NEG_ILLUSTRATION`). **추가 negative 만**
적기 — preset 위에 덧붙여진다.

### 3. 속성 보호 (캐릭터 일관성)
원치 않는 경쟁 속성을 negative 에 명시. 실버 헤어 유지 시:
```
negative: pink hair, gold hair, brown hair, blonde hair, ...
```
유지율 +20~30%.

### 4. 카테고리별 prompt 템플릿

**sprite (V38)**:
```
1girl, (black hair:1.2), (side ponytail:1.3), long hair,
blue knight armor, (holding silver sword:1.3), sword in right hand,
red cape, fantasy warrior, masterpiece, best quality, very aesthetic
```

**illustration**:
```
1girl, school uniform, sitting in cafe, soft natural lighting,
cinematic composition, masterpiece, best quality, very aesthetic
```

**Pony 변형**: 끝에 `score_X` 필수
```
score_9, score_8_up, score_7_up, score_6_up,
1girl, ...
```

---

## 상세 가이드

### sprite 변형 빠른 표

| 변형 | 출력 수 | 언제 |
|---|---|---|
| `sprite/pixel_alpha` ⭐ | 3 (Stage1·Pixelized·**PixelAlpha**) | **메인** — 게임 엔진 즉시 사용 |
| `sprite/hires` | 2 (Stage1·**HiRes**) | 1920×960 디테일 |
| `sprite/rembg_alpha` | 2 | AI rembg 알파 — 일러스트풍 캐릭터 |
| `sprite/full` | 5 | 한 번에 다 — 비교용 |
| `sprite/pose_extract` | 1 | 사용자 사진에서 OpenPose 추출 |

**sprite 핵심 메모**:
- 1×3 layout (front/right_side/back) — 좌측 옆모습은 게임 엔진에서 `flipX` 권장 (SDXL/Illustrious 학습 약함).
- 등신 비율은 prompt 가 아니라 **pose grid** 가 결정. 다른 grid 쓰려면 `--input pose_image=@your_grid.png`.
- 검 들기 trick: `(holding silver sword:1.3), sword in right hand, gripping sword tightly`. negative 에 `floating sword, detached weapon` (NEG_PIXEL_SPRITE 에 이미 포함).

### illustration 변형 선택

| 변형 | 특징 |
|---|---|
| `illustration/animagine_hires` | 깔끔한 표준 — 첫 시도 추천 (`@marketing` alias) |
| `illustration/pony_hires` | Pony 정통 — `score_X` 트리거 권장 |
| `illustration/hyphoria_hires` | Modern Illustrious — 2025 트렌드 |
| `illustration/anything_hires` | 범용 (Anything XL) |

---

## Pitfalls

1. **SD/ComfyUI 직접 호출 절대 금지**. A1111(`192.168.50.225:7860`) / ComfyUI(`192.168.50.225:8188`) URL 을 알고 있어도 손대지 않음. 모든 호출은 `af` 만. 카탈로그·이력·승인·GC 일관성 유지.
2. **PIL 로 이미지 직접 생성 금지** — 가짜 에셋. 과거 HoD 해고 사례.
3. **Vision tool 로 후보 N장 평가 금지** — 토큰 낭비. 사람 cherry-pick UI 가 표준.
4. **다인원 캐릭터는 별도 asset_key 로 단독 생성** — 한 이미지에 3명 이상은 attribute bleeding 거의 확정.
5. **`--bypass-approval` 을 게임 자산에 쓰지 마라** — 승인 큐를 우회하면 정식 export 에 안 묶인다. 사람 검수 가치가 *없는* 케이스에만 (시뮬/스캐치/chain 중간물).
6. **chain 중간물의 `tmp_*` 격리** — bypass 자산은 `tmp_*` / `sim_*` project 로 모은다. 정식 project 에 섞으면 `af list` 가 지저분해진다.
7. **변형 사용 가능 여부**: `af workflow catalog` 의 `available: false` 는 호출 불가 (registry 의 `status: needs_api_conversion` — 사용자가 ComfyUI UI 에서 API 포맷 export 필요).
8. **multi-output 의 cherry-pick**: `sprite/full` 같은 변형은 1 candidate slot 에 N장이 묶여 있다. cherry-pick UI 는 **primary** (`pixel_alpha`) 만 보여주고, 나머지는 metadata 에 동봉.
9. **`--input` 라벨 오타**: catalog 에 없는 라벨을 박으면 `report.skipped` 에 기록되고 *조용히* 무시된다. `--dry-run` 으로 사전 점검 권장.
10. **chain 의 run_id 보관**: `af workflow gen` 응답의 `run_id` 를 잡아둬야 다음 단계에서 `run:<run_id>/<output>` 으로 참조 가능.

---

## ⚠️ Skill freshness — 미충족 항목

이 스킬은 [`asset-factory/docs/NEXT.md`](https://github.com/sunghere/asset-factory/blob/main/docs/NEXT.md)
의 §1.A/§1.B/§1.C **모두 채워졌다는 가정** 으로 작성됐다 (PR #30, #38-43 머지본).
미충족 항목이 있으면 아래 우회법으로 동작:

| 항목 | 상태 | 비고 |
|---|---|---|
| `--bypass-approval` 플래그 | ✅ 채워짐 (PR #18) | — |
| catalog `input_labels` | ✅ 채워짐 (PR #18) | — |
| `af workflow upload` CLI | ✅ 채워짐 (PR #18, Python `python -m cli workflow upload`) | — |
| `--input <label>=...` 통합 호출 | ✅ 채워짐 (PR #18, Python CLI) | — |
| **§1.A `meta.intent` / `output_layout` / `use_cases` / `not_for` / `tags(list)`** | ✅ 채워짐 (PR #30, #38-41) — 25/25 변형 마이그 완료 | — |
| **§1.A `input_labels.alternatives`** | ✅ 채워짐 (PR #30) | — |
| **catalog `version: 2` bump** | ✅ 채워짐 (PR #30) | — |
| **§1.A `meta.prompt_template`** | ✅ 채워짐 (PR #30, #38-41) — `pose_extract` (utility 변형) 제외 모두 | — |
| **§1.B 서버측 `subject` 자동 주입** (`resolve_prompt`, `WorkflowGenerateRequest.subject`, `prompt_resolution` 응답) | ✅ 채워짐 (PR #42) | `prompt_mode: auto/subject/legacy` 자동 감지 |
| **§1.C `POST /api/workflows/recommend`** (자연어 query + weighted-rule score) | ✅ 채워짐 (PR #43) | `candidates[].score`, `use_cases_hit`, `tags_hit`, `not_for_warnings`, `scoring_method` |
| **§1.C `GET /api/workflows/search`** (tag filter + negative filter) | ✅ 채워짐 (PR #43) | `?tag=X&tag=Y&not=Z` |
| `--dry-run` | ⏳ 미충족 | 직접 enqueue 후 작은 변형 (`sprite/pixel_alpha`, candidates=1) 으로 실 호출. `--input` 라벨 오타는 응답의 `report.skipped` 로 확인 |
| `aliases` (`@character` 등) | ⏳ 미충족 | full path (`sprite/pixel_alpha`) 로 호출 |
| `run:<run_id>/<output>` syntax | ⏳ 부분 충족 | `--input source_image=asset:<id>` 로 chain. 특정 output label 참조 (`run:.../pixel_alpha`) 는 asset_id 직접 룩업 (`af list <project>` → metadata 매칭) |

**갭이 채워질 때마다 이 표에서 한 줄씩 지운다** (skill 유지보수자).

> §1.A/§1.B/§1.C 모두 채워졌으므로 본문에 *임시 우회* 안내 (manual prompt 합성,
> Python catalog 파싱) 는 **제거됨**. 대신 *서버 자동 동작* + *응답 검증* 패턴으로
> 전환됨 (위 `## 디스커버리 메타 — prompt 합성` / `## 디스커버리 메타 — 변형 추천`).

---

## Paperclip 워크플로

페이퍼클립 이슈가 "에셋 N장 만들어줘" 형태일 때:

1. **카탈로그 확인**: `af workflow catalog` → 카테고리·변형 결정. 의도 명확하면 alias (`@character` 등) 사용.
2. **dry-run 으로 사전 점검**: `af workflow gen <variant> ... --dry-run` 으로 패치 결과·라벨 매칭 OK 인지.
3. **본 호출**: `af workflow gen <variant> <project> <asset_key> "<prompt>" --candidates N --wait`.
4. **bypass 결정**: 시뮬/스캐치/chain 중간물이면 `--bypass-approval`. 정식 자산이면 빼고 cherry-pick 큐로.
5. **결과 전달**: 출력의 `cherry-pick URL` 을 이슈 코멘트로. bypass 면 `af get <asset_id>` 결과 직접 첨부.
6. **승인 후**: 필요 시 `af export <project> --manifest`.

---

## Related skills

- (없음 — `stable-diffusion-api` 는 v3 의 흔적. v4 부터 SD 직접 호출은 정책상 금지.)
