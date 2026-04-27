# Catalog & Discovery 메타 — Reference

> SKILL.md 본문은 *변형 선택 4-step* 만 다룬다. 이 파일은 catalog 응답 schema 전체,
> recommend/search API 디테일, prompt_template 합성 모드 (§1.B), tag 컨벤션을 다룬다.
>
> 출처: [`asset-factory/docs/NEXT.md §1.A/§1.B/§1.C`](https://github.com/sunghere/asset-factory/blob/main/docs/NEXT.md) (PR #21 spec) + 구현 PR #30/#38-43 머지본.

---

## 1. Catalog 응답 schema (`GET /api/workflows/catalog`)

```jsonc
// 25/25 변형 모두 메타 마이그 완료 (sprite 10 + illustration 10 + pixel_bg 4 + icon 1)
{
  "version": 2,                                 // ← schema bump (legacy 자동 감지 신호)
  "categories": {
    "sprite": {
      "description": "...",
      "primary_variant": "pixel_alpha",
      "variants": {
        "pixel_alpha": {
          // ─── 호출 메타 (변동 없음) ────────────────
          "description": "픽셀 그리드 + 투명배경 (게임 엔진용) ⭐",
          "available": true, "status": "ready", "primary": true,
          "file": "sprite/...api_pixel_alpha.json",
          "outputs": [
            { "label": "stage1", "primary": false },
            { "label": "pixelized", "primary": false },
            { "label": "pixel_alpha", "primary": true }
          ],
          "defaults": { "steps": 30, "cfg": 6.5, "sampler": "dpmpp_2m", ... },
          "input_labels": [
            {
              "label": "pose_image",
              "required": false,
              "default": "pose_grid_1x3_mini_2.5h_1280x640.png",
              "description": "ControlNet 포즈 가이드. 1×3 그리드 PNG. ...",
              "alternatives": [                  // ← §1.A 신규
                "pose_grid_1x3_5h_1280x640.png",
                "pose_grid_1x4_1280x640.png",
                "pose_grid_3x3_1280x896.png"
              ]
            }
          ],

          // ─── 디스커버리 메타 (§1.A) ────────────────
          "meta": {
            "intent": "3-pose character sheet (1×3 grid, transparent BG) for 2D game engine import.",
            "use_cases": [
              "RPG character with idle / walk-side / walk-front 3-pose set",
              "Top-down RPG sprite atlas seed (one row of poses, alpha-cut)",
              "Card-game character sprite with consistent design across 3 angles"
            ],
            "not_for":   [
              "single character portrait — use illustration/animagine_hires",
              "scene/background — use pixel_bg/*",
              "logo or app icon — use icon/flat",
              "character with varying scale/age/outfit between cells"
            ],
            "output_layout": {
              "kind": "pose_grid",               // single | pose_grid | tile_grid | character_sheet
              "rows": 1, "cols": 3,
              "per_cell_size": [426, 640],
              "alpha": true,
              "notes": "Output is a single 1280×640 PNG with alpha. ..."
            },
            "tags": [                            // list[str], 영문/한국어 혼용 OK
              "pixel-art", "transparent-bg", "pose-sheet", "controlnet-pose",
              "1x3-grid", "rpg-character", "2d-game-asset", "chibi", "illustrious",
              "게임-스프라이트", "픽셀-캐릭터"
            ],
            "prompt_template": {                 // null 이면 §B 미마이그 변형 (utility)
              "base_positive": "pixel_character_sprite, sprite, sprite sheet, (pixel art:1.5), white background, 1x3 pose grid layout, ...",
              "base_negative": "(worst quality, low quality:1.4), blurry, ..., floating sword, detached weapon, ...",
              "user_slot": {
                "label": "subject",
                "description": "캐릭터 묘사만 (외형/복장/무기). 스타일·구도·배경 묘사 금지 ...",
                "examples": [
                  "1girl, silver hair twin tails, navy school uniform, holding a notebook",
                  "1boy, brown spiky hair, blue tunic, leather belt with sword",
                  "1girl, (black hair:1.2), (side ponytail:1.3), long hair, blue knight armor, (holding silver sword:1.3), ..."
                ],
                "required": true, "min_chars": 8, "max_chars": 400
              },
              "injection_rule": "{base_positive}, {subject}"
            }
          }
        },

        "pose_extract": {
          // utility 변형 (pose 추출, prompt 무관) — prompt_template == null
          "meta": {
            "intent": "Utility: extract OpenPose stick figure from a source image.",
            ...
            "prompt_template": null              // ← null = §B 합성 안 함 (legacy 자동)
          }
        }
      }
    }
  }
}
```

### `meta` 필드 의미

| 필드 | 타입 | 의미 |
|---|---|---|
| `intent` | str | **한 줄** 변형의 본질. 변형 인식·디스플레이 |
| `use_cases` | str[] | 적합 시나리오 (긍정 매칭 신호 — recommend score) |
| `not_for` | str[] | 부적합 + 대체 변형 힌트 (오선택 방지 — `not_for_warnings`) |
| `output_layout.kind` | enum | `single` / `pose_grid` / `tile_grid` / `character_sheet` |
| `output_layout.rows`/`cols` | int | grid 차원 (kind ≠ single 시) |
| `output_layout.per_cell_size` | [int,int] | 각 셀의 픽셀 크기 |
| `output_layout.alpha` | bool | 알파 채널 여부 |
| `output_layout.notes` | str | 자유 서술 (split 방법 등) |
| `tags` | str[] | 검색용 태그 (`/search` 매칭) |
| `prompt_template.base_positive` | str | §1.B subject 합성 시 prepend |
| `prompt_template.base_negative` | str | §1.B 자동 prepend (override 불가) |
| `prompt_template.user_slot` | object | 사용자 입력 슬롯 (label/description/examples/required/min_chars/max_chars) |
| `prompt_template.injection_rule` | str | `{base_positive}, {subject}` 같은 합성 템플릿 |
| `input_labels.<label>.description` | str | 입력 라벨 사용자 안내 |
| `input_labels.<label>.alternatives` | str[] | 같은 라벨에 대체 가능한 입력 파일들 |

---

## 2. Prompt 합성 — §1.B subject-injection (자동)

서버가 `meta.prompt_template.base_positive` / `base_negative` 를 **자동 합성**한다. 사용자/에이전트는 *캐릭터 묘사만* (`subject`) 넣으면 됨.

### 두 입력 모드

| 필드 | 모드 | 동작 |
|---|---|---|
| `subject` (str, optional) | **subject** | 변형의 `base_positive` + `injection_rule` 로 자동 합성 |
| `prompt` (str) | **legacy** 또는 자동 | 통째 입력 — `base_positive` 무시 |
| `prompt_mode` (`auto`/`subject`/`legacy`) | 강제 | `auto`(default) — 자동 감지 |

### 자동 감지 규칙 (`prompt_mode: auto` 기준)

1. `subject` 명시됨 → **subject** (강제)
2. `prompt_mode: legacy` → **legacy** (강제)
3. 변형에 `prompt_template == null` (utility) → **legacy** (자동)
4. `prompt` 길이 > `user_slot.max_chars` → **legacy** (사용자 통째 작성 추정)
5. `base_positive` 의 시그니처 토큰 (첫 4 토큰) 이 `prompt` 에 *이미 있음* → **legacy**
6. 그 외 → **subject** (기본)

### `subject` 모드 호출 (권장)

```jsonc
POST /api/workflows/generate
Headers: x-api-key: <API_KEY>, Content-Type: application/json
{
  "workflow_category": "sprite",
  "workflow_variant":  "pixel_alpha",
  "subject": "1girl, silver hair twin tails, navy school uniform, holding a notebook",
  "project": "demo", "asset_key": "test_001",
  "candidates_total": 1,
  "approval_mode": "manual"   // 또는 "bypass"
}
```

CLI: `af workflow gen sprite/pixel_alpha demo test_001 --subject "..." --wait`

### `prompt_resolution` 응답

generate 응답에 *항상* 동봉:

```jsonc
{
  "run_id": "...",
  "prompt_resolution": {
    "mode": "subject",                                          // "subject" | "legacy"
    "user_slot": "subject",                                      // legacy 면 null
    "user_input": "1girl, silver hair...",                       // subject or prompt 원본
    "final_positive": "pixel_character_sprite, sprite, ..., 1girl, silver hair...",
    "final_negative": "(worst quality, low quality:1.4), ..."
  },
  ...
}
```

→ **debug 시 `final_positive` 로 ComfyUI 에 실제 보낸 값 확인 가능**. 디자인 이상하면 여기 먼저 본다.

### `subject` 입력 가이드

`meta.prompt_template.user_slot` 따른다:

- `description` — *"캐릭터 묘사만 (외형/복장/무기). 스타일·구도·배경 묘사 금지"*
- `examples` — 변형마다 검증된 예시 (그대로 복사 가능)
- `min_chars` / `max_chars` — 위반 시 HTTP 400 + 에러 코드

**규칙**:
- 스타일/배경/레이아웃 묘사는 `base_positive` 가 처리 — `subject` 에 *중복 묘사 금지*
- `(chibi:1.4)` 같은 chibi 가중치 강조 금지 (ControlNet stick figure 와 충돌)
- 검 든 캐릭터: `(holding silver sword:1.3), sword in right hand, gripping sword tightly` 동사 묶기 권장

### `base_negative` override 금지

사용자 `negative_prompt` 는 `base_negative` 에 **append 만**. 필수 negative (예: `floating sword, detached weapon` — sprite/pixel_alpha) 는 *override 불가* 가 안전 정책 (spec §B.3).

---

## 3. 변형 추천 — §1.C recommend / search

### `POST /api/workflows/recommend` — 자연어 query

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
      "not_for_warnings":[]   // 사용자 query 가 not_for 와 매칭되면 경고
    },
    ...
  ],
  "scoring_method": "rule"   // 현재 룰 기반. 미래: "embedding" / "llm"
}
```

CLI: `af workflow recommend "RPG 픽셀 캐릭터 정면 측면 뒷면 시트" --top 3`

**스코어링 (Phase 1 — 룰 기반)**:
- `intent` / `use_cases` / `tags` 에 query 키워드 매칭 → 가산점
- `not_for` 에 query 매칭 → 페널티 + `not_for_warnings` 동봉

**한국어/영어 혼용 OK** — `meta.intent` 영문, `meta.tags` 한국어 혼용된 변형도 정확 매칭.

### `GET /api/workflows/search` — tag filter

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

### 둘 중 어느 걸 쓰나?

| 상황 | endpoint |
|---|---|
| 사용자 **자연어 task 묘사** (e.g. "게임 캐릭터 도트") | `/recommend` |
| **알려진 tag 조합** 정확 매칭 | `/search` |
| **부정 필터** 필요 ("pixel-art 인데 pose-sheet 아닌 것") | `/search` |
| 후보 *순위* + 점수 + 경고 필요 | `/recommend` |

### 조합 패턴 (Paperclip Asset Relay 등)

```python
# 1) 자연어로 후보 좁히기
res = POST /api/workflows/recommend  → top 3

# 2) not_for_warnings 비어있는 첫 후보 채택
candidate = next(c for c in res["candidates"] if not c["not_for_warnings"])

# 3) catalog 의 meta.output_layout 으로 형태 최종 검증
# 4) subject 모드로 generate 호출
```

---

## 4. tags — 자유 태그 (closed enum 아님)

`tags` 는 **list[str]**. 변형마다 영문/한국어 혼용 자유. 추천 컨벤션:

| 카테고리 | 자주 쓰는 tag (참고 — 강제 아님) |
|---|---|
| 출력 형태 | `transparent-bg` / `alpha-pixel` / `alpha-rembg` / `1x3-grid` / `1x4-grid` / `3x3-grid` / `tile-grid` |
| 스타일 | `pixel-art` / `chibi` / `flat` / `anime` |
| 용도 | `rpg-character` / `2d-game-asset` / `marketing` / `tile-map` |
| 모델 | `illustrious` / `pony` / `sdxl-anime` / `sd1.5` |
| 입력 | `controlnet-pose` / `pose-sheet` / `face-detailer` |

새 변형 작성 시 *기존 변형의 tags* 보고 동일 어휘 재사용 권장 (검색 매칭 정합성). 어휘 폐쇄형 enum 은 미래 결정 (현재는 자유 list).

---

## 5. 매니페스트 마이그레이션 진행 상태

**25/25 변형 메타 마이그 완료** (PR #30, #38-41).

| 카테고리 | 변형 수 | 상태 |
|---|---|---|
| sprite | 10 | ✅ pixel_alpha / hires / rembg_alpha / stage1 / full / v37_pixel / v37_full / v36_pro_stage1 / v36_pro_full / pose_extract |
| illustration | 10 | ✅ animagine / pony / hyphoria / anything / meinamix × {hires, stage1} |
| pixel_bg | 4 | ✅ sdxl_stage1 / sdxl_hires / pony_stage1 / pony_hires |
| icon | 1 | ✅ flat |

`pose_extract` 만 `prompt_template == null` (utility 변형 — pose 추출, prompt 무관).
