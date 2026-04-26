---
name: asset-factory-api
version: 3
description: "Asset Factory로 게임 픽셀아트/일러스트/UI 에셋 생성. `af` CLI 한 줄로 A1111 단일/배치 또는 ComfyUI 워크플로우(sprite/illustration/pixel_bg/icon) 호출. SD/jq/curl 직접 사용 금지."
triggers:
  - asset factory
  - asset-factory
  - 에셋 팩토리
  - 픽셀아트 생성
  - 게임 에셋
  - 스프라이트 생성
  - 캐릭터 도트
  - cherry-pick
  - comfyui 워크플로우
  - 일러스트 생성
---

# Asset Factory

게임 픽셀아트 에셋 생성 파이프라인. **`af` CLI로 모든 작업 처리**, 에이전트는 명령 한두 줄만.

## When to use

픽셀아트 캐릭터/스프라이트/UI 아이콘이 필요할 때, 또는 같은 에셋의 여러 후보를 뽑아 사람이 cherry-pick하고 싶을 때.

## When NOT to use

1회성 비픽셀 이미지, 즉시 1장만 보고 싶을 때 → `generate-asset` CLI 직접 사용.

## CLI: `af` (이게 전부다)

설치 위치: `~/.local/bin/af` (NodeJS, deps 없음). 자세한 옵션은 `af --help`.

서버는 두 SD 백엔드를 동시에 들고 있다 — **A1111** (legacy, 단순 픽셀 생성) 와
**ComfyUI** (워크플로우 기반, 다양한 카테고리·multi-output). 명령이 다르다.

```bash
# 1. 점검
af health                              # A1111 + ComfyUI 양쪽 다 보고
af catalog models                      # A1111 모델 목록
af catalog loras                       # A1111 LoRA + 권장 weight
af workflow catalog                    # ComfyUI 카테고리/변형 목록 ⭐

# 2A. A1111 — 단일 픽셀 생성 (가장 단순)
af gen <project> <asset_key> "<prompt>" --size 64 --wait \
       --negative "background, blurry" --model pixelArtDiffusionXL_spriteShaper

# 2B. A1111 — 디자인 배치 (cherry-pick)
af batch <project> <asset_key> \
   --prompts "p1" "p2" --models pixelArtDiffusionXL_spriteShaper \
   --seeds 4 --size 64 --wait

# 2C. ComfyUI — 워크플로우 변형 호출 ⭐ (캐릭터 sprite/일러스트/픽셀배경/아이콘 모두)
af workflow gen sprite/pixel_alpha <project> <asset_key> "<prompt>" \
   --seed 42 --wait
# 변형이 multi-output (예: sprite/full = 5장) 이면 1슬롯에 N장 다 저장됨.
# primary 가 cherry-pick UI에 노출되는 메인 결과.

# 2D. ComfyUI — N개 후보 (cherry-pick)
af workflow gen sprite/pixel_alpha <project> <asset_key> "<prompt>" \
   --seed 100 --candidates 4 --wait

# 3. 결과 가져오기 (백엔드 무관)
af list <project>                      # 에셋 메타 목록
af get <asset_id> -o output.png        # 이미지 다운로드
af export <project> --manifest         # 승인본 일괄 export → ~/workspace/assets/
```

폴링: `--wait` 빼면 enqueue 후 즉시 종료. 나중에 `af status <job_id>` 또는 `af wait <job_id>`.

## 픽셀아트 프롬프트 핵심 (4가지만 기억)

1. **Prefix**: `pixel art, ` 으로 시작
2. **배경**: `transparent background, isolated, no background, clean edges`
3. **Negative 표준**: `background, scenery, blurry, jpeg artifacts, anti-aliased, smooth shading, 3d render, photo, realistic`
4. **속성 보호 (캐릭터 일관성)**: 원치 않는 경쟁 속성을 negative에 명시. 실버 헤어 유지하려면 negative에 `pink hair, gold hair, brown hair, ...` 모두 나열 → 유지율 +20~30%.

## 모델 선택 (A1111)

`af catalog models`로 확인. 픽셀아트 게임 에셋은 **`pixelArtDiffusionXL_spriteShaper` 기본**. 시리즈/브랜드는 한 모델로 통일하고 다양성은 `--seeds`로 확보 (모델 섞으면 한 세트로 안 읽힘).

## ComfyUI 워크플로우 카테고리 — 언제 무엇을

`af workflow catalog` 로 호출 가능한 변형 확인. 4가지 카테고리:

| 카테고리 | 언제 쓰나 | 메인 변형 (primary) | 비고 |
|---|---|---|---|
| **sprite** | 게임 캐릭터 스프라이트 (3뷰 multi-view, ControlNet OpenPose 강제) | `sprite/pixel_alpha` ⭐ | 1280×640 픽셀 + 투명배경. 게임 엔진 즉시 사용 |
| **illustration** | 마케팅·표지·배경 일러스트 (픽셀아트 아님) | `illustration/animagine_hires` | 5종 모델 × stage1/hires |
| **pixel_bg** | 픽셀 타일·배경 | (변환 필요) | C 시리즈, 사용자 export 후 활성 |
| **icon** | 앱 UI 아이콘 (flat) | (변환 필요) | D 시리즈, 사용자 export 후 활성 |

### sprite 변형 빠른 가이드

| 변형 | 출력 수 | 언제 |
|---|---|---|
| `sprite/pixel_alpha` ⭐ | 3 (Stage1·Pixelized·**PixelAlpha**) | **메인 — 게임 엔진용 투명배경 픽셀** |
| `sprite/hires` | 2 (Stage1·**HiRes**) | 1920×960 디테일 보강 |
| `sprite/rembg_alpha` | 2 (Stage1·**RembgAlpha**) | AI rembg 알파 (일러스트풍 캐릭터) |
| `sprite/full` | 5 (위 다 + Pixelized + RembgAlpha) | 한 번에 다 — 비교용 |
| `sprite/v36_pro_*` | 디자인 단계 | ControlNet 없는 자유 layout |

### sprite 핵심 메모

- 1×3 layout (front / right_side / back) — **좌측은 게임 엔진에서 `flipX` 권장** (SDXL/Illustrious가 좌측 옆모습 학습 약함)
- 등신 비율은 prompt가 아니라 **pose grid (stick figure)** 가 결정. `--workflow-params '{"pose_image":"pose_grid_1x3_mini_2.5h_1280x640.png"}'` 로 변경
- 검 들기 trick: `(holding silver sword:1.3), sword in right hand, gripping sword tightly` 동사 묶기. negative 에 `floating sword, detached weapon` 명시 (이미 NEG_PIXEL_SPRITE preset 에 들어있음)

### illustration 모델 선택

| 변형 | 특징 |
|---|---|
| `illustration/animagine_hires` | 깔끔한 표준 — 첫 시도 추천 |
| `illustration/pony_hires` | Pony 정통 — `score_9, score_8_up, score_7_up` 트리거 권장 |
| `illustration/hyphoria_hires` | Modern Illustrious — 2025년 트렌드 |
| `illustration/anything_hires` | 범용 (Anything XL) |
| `illustration/meinamix_hires` | SD1.5 — 빠르고 가벼움 |

### 카테고리별 prompt 템플릿

**sprite (V38)** — 캐릭터 묘사 + 키워드 자동 prepend (워크플로우의 base prompt 가 `pixel art, sprite, three views, ...` 자동 추가)
```
1girl, (black hair:1.2), (side ponytail:1.3), long hair,
blue knight armor, (holding silver sword:1.3), sword in right hand,
red cape, fantasy warrior, masterpiece, best quality, very aesthetic
```

**illustration** — 직접 작성, masterpiece 어휘 끝에
```
1girl, school uniform, sitting in cafe, soft natural lighting,
cinematic composition, masterpiece, best quality, very aesthetic
```

**Pony 변형은 score_X 필수**
```
score_9, score_8_up, score_7_up, score_6_up,
1girl, ...
```

## Pitfalls

1. **에이전트는 SD/ComfyUI 직접 호출 금지** — A1111(`192.168.50.225:7860`) 도, ComfyUI(`192.168.50.225:8188`) 도 직접 안 두드림. 항상 `af` 만. 카탈로그·이력·검증·승인·GC 일관성 유지.
2. **PIL로 이미지 직접 생성 금지** — 가짜 에셋. 과거 HoD 해고 사례.
3. **Vision tool로 후보 N장 평가 금지** — 토큰 낭비. 사람이 cherry-pick UI에서 보는 게 표준.
4. **다인원 캐릭터는 별도 asset_key로 단독 생성** — 한 이미지에 3명 이상은 attribute bleeding 거의 확정.
5. **`--wait` 타임아웃**: A1111 단일 5분, 배치는 task당 ~6초. ComfyUI 워크플로우는 변형마다 다름 (sprite/full = ~60초). `--timeout N` 으로 조정.
6. **`af gen`의 결과가 1024x1024 raw** — A1111 후처리가 단일 경로에 빠져있을 수 있음. ComfyUI 변형(`af workflow gen sprite/pixel_alpha`)은 워크플로우 안에서 픽셀화/알파 처리까지 다 함 — 픽셀 sprite 가 필요하면 ComfyUI 쪽 우선.
7. **`af workflow gen` 변형 상태 확인** — `af workflow catalog | jq '.categories.<cat>.variants.<v>.available'` 가 `false` 면 호출 불가 (V35 C/D 시리즈는 사용자가 ComfyUI UI에서 _api_*.json export 해야 활성).
8. **multi-output 변형의 cherry-pick** — `sprite/full` 같은 5장 변형은 1개 candidate slot에 5장 다 묶임. cherry-pick UI 는 **primary** (`pixel_alpha`) 만 보여주고, 나머지는 metadata `extra_outputs` 로 추적.
9. **ComfyUI input/ 파일** — `--workflow-params` 의 `pose_image` 등 LoadImage 노드가 참조하는 파일은 **ComfyUI 호스트의 `input/` 디렉토리에 미리 있어야 함** (asset-factory가 아니라 ComfyUI 머신 쪽). 새 pose grid 쓰려면 우리 PC 의 `D:\DEV\ComfyUI\input\` 에 먼저 넣기.

## Paperclip 워크플로

페이퍼클립 이슈가 "에셋 N장 만들어줘" 형태일 때:

1. `af catalog models` → 사용할 모델 결정
2. `af batch <project> <asset_key> --prompts ... --models ... --seeds 4 --wait`
3. 출력에 나오는 `cherry-pick URL`을 이슈 코멘트로 사용자에게 전달
4. 사용자 승인 후 필요 시 `af export <project>`

자세한 운영 노하우(BREAK 구문, attribute bleeding 회피 패턴 등)는 `references/prompt-craft.md`. 인프라/엔드포인트 레퍼런스는 `references/api.md`.

## Related skills

- `stable-diffusion-api` — SD 직접 호출 (Asset Factory 우회 예외 상황만)
- `paperclip-api` — 페이퍼클립 이슈/코멘트/승인 API
