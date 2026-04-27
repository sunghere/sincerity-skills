# 변형별 빠른 비교표 — Reference

> SKILL.md 본문에서 분리. 변형들 차이를 *깊이* 비교할 때만 본다.
> 정확한 의도/출력 형태는 `recommend` / `describe` 응답이 SSOT.

---

## sprite 카테고리 (10 변형)

| 변형 | 출력 수 | 1×3 layout | 알파 | 해상도 | 언제 |
|---|---|---|---|---|---|
| `pixel_alpha` ⭐ | 3 (Stage1·Pixelized·**PixelAlpha**) | ✅ | ✅ | 1280×640 | **메인** — 게임 엔진 즉시 사용 |
| `hires` | 2 (Stage1·**HiRes**) | ✅ | ❌ | 1920×960 | 디테일 보강 (마케팅·홍보) |
| `rembg_alpha` | 2 | ✅ | ✅ (AI rembg) | 1280×640 | 일러스트풍 캐릭터 (반투명 디테일 보존) |
| `stage1` | 1 | ✅ | ❌ | 1280×640 | 빠른 디자인 탐색 (raw, 흰배경) |
| `full` | 5 | ✅ | (변형마다) | 1280×640 | 한 번에 다 — 비교용 |
| `v37_pixel` | 1 | ✅ | ❌ | 1280×640 | [V37] alpha 단계 우회, 픽셀 정렬만 |
| `v37_full` | 3 | ✅ | (변형마다) | 1280×640 | [V37] Stage1 + HiRes + Pixelized |
| `v36_pro_stage1` | 1 | ❌ (free layout) | ❌ | 1024×1024 | [V36 Pro] 컨셉 디자인 탐색 (ControlNet 없음) |
| `v36_pro_full` | 3 | ❌ (free layout) | (변형마다) | 1024×1024 | [V36 Pro] 컨셉 풀 파이프라인 |
| `pose_extract` | 1 | — | — | (입력 따름) | **utility**: 사용자 사진 → OpenPose stick figure |

### sprite 핵심 메모

- **1×3 layout** (front / right_side / back) — 좌측 옆모습은 게임 엔진에서 `flipX` 권장 (SDXL/Illustrious 학습 약함).
- **등신 비율** 은 prompt 가 아니라 **pose grid** 가 결정. 다른 grid 쓰려면 `--input pose_image=<alternative>`.
- **검 들기 trick**: `(holding silver sword:1.3), sword in right hand, gripping sword tightly`. negative 에 `floating sword, detached weapon` (NEG_PIXEL_SPRITE 에 이미 포함).
- V36 Pro 만 ControlNet 없음 → free layout 가능.
- `pose_extract` 는 prompt 무관 — `prompt_template == null`. 사용자 이미지만 받음.

---

## illustration 카테고리 (10 변형)

| 변형 | 모델 | 1×3 layout | 해상도 | 특징 |
|---|---|---|---|---|
| `animagine_hires` ⭐ | Animagine XL | ❌ (단일) | 1024×1024 → 1.5x | **메인** — 깔끔한 표준 (`@marketing` alias) |
| `animagine_stage1` | Animagine XL | ❌ (단일) | 1024×1024 | base 단계 (빠른 iteration) |
| `pony_hires` | Prefect Pony XL | ❌ (단일) | 1024×1024 → 1.5x | Pony 정통 (`score_X` 자동) |
| `pony_stage1` | Prefect Pony XL | ❌ (단일) | 1024×1024 | Pony base |
| `hyphoria_hires` | Hyphoria | ❌ (단일) | 1024×1024 → 1.5x | Modern Illustrious (2025 트렌드) |
| `hyphoria_stage1` | Hyphoria | ❌ (단일) | 1024×1024 | Hyphoria base |
| `anything_hires` | AnythingXL | ❌ (단일) | 1024×1024 → 1.5x | 범용 (style 자유도 큼) |
| `anything_stage1` | AnythingXL | ❌ (단일) | 1024×1024 | Anything base |
| `meinamix_hires` | MeinaMix | ❌ (단일) | 512×768 → 1.5x | SD1.5 — VRAM 제한 환경 |
| `meinamix_stage1` | MeinaMix | ❌ (단일) | 512×768 | SD1.5 base |

### illustration 핵심 메모

- **모두 단일 이미지** — sprite 와 다름 (sprite/* 는 1×3 시트).
- **Pony 변형** 은 `score_9, score_8_up, score_7_up` 자동 prepend (`base_positive` 가 처리). 사용자가 직접 박을 필요 없음.
- **stage1** 은 빠른 prompt 검증용. 마음에 들면 `_hires` 로 같은 seed 재호출.
- 모델별 트리거 차이는 `meta.prompt_template.base_positive` 에 박힘 — 구체 내용은 `af workflow describe <variant>` 또는 `references/catalog-and-meta.md` 참고.

---

## pixel_bg 카테고리 (4 변형)

| 변형 | 모델 | 해상도 | 특징 |
|---|---|---|---|
| `sdxl_stage1` | PixelDiffusionXL | 1024×1024 | 일반 픽셀 배경 prototyping |
| `sdxl_hires` | PixelDiffusionXL | 1024 → 1.5x | 일반 픽셀 배경 + refine |
| `pony_stage1` | RDXL Pony Pixel + Fnaf LoRA | 1024×1024 | Fnaf-style / horror / dark 환경 |
| `pony_hires` | RDXL Pony Pixel + Fnaf LoRA | 1024 → 1.5x | Fnaf-style horror + refine (마케팅 quality) |

### pixel_bg 핵심 메모

- 단일 이미지, *환경/타일/배경* 전용 (캐릭터 없음).
- Pony 변형은 `score_X` 자동 + Fnaf trained_words (`pixel art`, `game assets`, `overworld`) 자동 prepend.
- 단순 환경/숲/마을 → SDXL. 호러/공포/Fnaf 컨셉 → Pony.

---

## icon 카테고리 (1 변형)

| 변형 | 출력 수 | 알파 | 해상도 | 언제 |
|---|---|---|---|---|
| `flat` | 2 (raw·**alpha**) | ✅ | 1024×1024 | UI 아이콘 (flat/vector style) |

---

## 변형 선택 의사결정 cheat-sheet

> 정확한 매칭은 `af workflow recommend "<task>"` 사용.
> 이 표는 *친숙한 카테고리* 를 빠르게 찾기 위한 reference.

```
사용자 의도                        →  카테고리          →  변형
──────────────────────────────────────────────────────────────────────
"게임 캐릭터 도트"                  →  sprite           →  pixel_alpha ⭐
"게임 캐릭터 마케팅 컷"             →  sprite           →  hires (흰배경) 또는 rembg_alpha (알파)
"3방향 캐릭터 시트 한 번에"         →  sprite           →  full (5장 비교용)
"단일 일러스트 (캐릭터 1장)"        →  illustration     →  animagine_hires 또는 hyphoria_hires
"Pony 스타일 / score_X 표현"       →  illustration     →  pony_hires
"고정밀 SDXL 일러스트"              →  illustration     →  hyphoria_hires (Modern) 또는 anything_hires (범용)
"VRAM 제한 / 빠른 iteration"        →  illustration     →  meinamix_hires (SD1.5)
"픽셀 배경 / 타일 / 환경"           →  pixel_bg         →  sdxl_hires (일반) 또는 pony_hires (호러)
"UI 아이콘 (앱·게임)"               →  icon             →  flat
"포즈 추출 (사용자 사진 → 레퍼런스)" →  sprite           →  pose_extract (utility)
"빠른 design 탐색 (cherry-pick 전)"  →  *               →  *_stage1 변형 (빠름)
"임시 시뮬·스캐치"                   →  *               →  --bypass-approval + tmp_* project
```

---

## related/sibling 활용 (catalog `meta` 안에 명시 안 됨 — 변형별 description 참고)

V36 → V37 → V38 흐름:
- V36 Pro = 컨셉 디자인 탐색 (free layout, ControlNet 없음)
- V37 = ControlNet 추가, 픽셀 정렬만 (alpha 없음)
- V38 = 메인 라인업 (alpha 추가)

탐색 단계: V36 → V37 → V38. 운영은 V38 (`pixel_alpha`/`hires`/`rembg_alpha`).
