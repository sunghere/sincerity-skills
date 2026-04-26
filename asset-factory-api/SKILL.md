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

## ⚠️ Skill freshness — 미충족 P0 항목

이 스킬은 [`asset-factory/docs/TODOS_for_SKILL.md`](https://github.com/sunghere/asset-factory/blob/main/docs/TODOS_for_SKILL.md) 의 P0 가
**모두 채워졌다는 가정** 으로 작성됐다. 미충족 항목이 있으면 아래 우회법으로 동작:

| P0 항목 | 미충족 시 우회 |
|---|---|
| `af workflow upload` CLI | `curl -F file=@x.png $AF_URL/api/workflows/inputs` 로 직접 호출 후 응답의 `name` 을 `workflow_params.load_images.<label>` 에 박아 generate 호출 |
| `--bypass-approval` 플래그 | 임시 manual 승인 — 정식 우회 모드 등장까지는 검수 큐를 사용. 또는 `tmp_*` project 로만 격리 운영. |
| catalog `input_labels` | `af workflow describe <variant>` 의 `defaults` 에서 `pose_image` / `source_image` 같은 키를 보고 라벨 추측. 매칭 안 되면 `--dry-run` 의 `report.skipped` 로 확인. |
| `aliases` (`@character` 등) | full path (`sprite/pixel_alpha`) 로 호출. 공식 alias 등장까지 잠시 길게 적기. |
| `--dry-run` | 직접 enqueue 후 작은 변형 (`sprite/pixel_alpha`, candidates=1) 으로 실 호출. |
| `--input <label>=...` 통합 호출 | upload + generate 2-step. `workflow_params` JSON 직접 조립. |
| `run:<run_id>/<output>` syntax | `from-asset` 으로 chain — asset_id 직접 룩업 (`af list <project>` 후 metadata 매칭). |

**갭이 채워질 때마다 이 표에서 한 줄씩 지운다** (skill 유지보수자).

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
