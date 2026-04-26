# HANDOFF: SD 워크플로우 → asset-factory 통합

**작성일**: 2026-04-26
**작성자**: 이전 세션 (Claude/Cowork)
**다음 작업 대상**: `D:\DEV\asset-factory\` 서버 코드 + `D:\DEV\sincerity-skills\asset-factory-api\` skill 확장

---

## 0. 한 페이지 요약 (TL;DR)

이전 세션에서 **ComfyUI 워크플로우 4개 카테고리 × 다양한 변형**을 만들었음. 이제 이걸 `asset-factory` 서버에 통합해서 `af` CLI로 LLM이 호출 가능하게 만드는 단계.

**완성된 자산** (모두 `D:\DEV\ComfyUI\comfyuiImage_v34\`):
- V38 Sprite + Alpha (게임 캐릭터 도트, **메인 결과물**) ⭐
- V37 Sprite + ControlNet OpenPose
- V37 PoseExtract (기존 이미지에서 OpenPose 추출)
- V36 Sprite Pro (캐릭터 디자인 베이스)
- V36 B 시리즈 5종 (애니메 일러스트, 모델별)
- V35 C 시리즈 2종 (픽셀 배경/타일)
- V35 D 시리즈 1종 (앱 UI 아이콘)

각각 **UI format + API format JSON** 모두 갖춤. asset-factory가 호출할 때는 API JSON 사용.

**다음 작업의 핵심 결정**: 새 skill `sd-generator`를 만들 것인가, 기존 `asset-factory-api` 확장할 것인가? → **기존 확장 권장**. 이유는 §6에 자세히.

---

## 1. 현재 상태 (전 세션에서 결론 난 것들)

### 1.1 메인 캐릭터 디자인 (V38 default prompt)
```
1girl, (black hair:1.2), (side ponytail:1.3), long hair,
hair tied at side, medium height ponytail,
blue knight armor, (holding silver sword:1.3), sword in right hand,
gripping sword tightly, red cape, fantasy warrior,
masterpiece, best quality, very aesthetic
```

### 1.2 V37/V38 sprite 워크플로우 핵심 설정
- **베이스**: `hyphoria_v002.safetensors` (Illustrious)
- **LoRA**: `pixel_character_sprite_illustrious` (0.7) + `pixelart_up` (0.4)
- **ControlNet**: `control-lora-openposeXL2-rank256.safetensors` (strength 0.85)
- **Sampler**: dpmpp_2m / karras, CFG 6.5, 30 steps
- **Resolution**: 1280×640 (1×3 layout: front / right_side / back)
- **등신**: 2.5 (mini SD chibi) — `pose_grid_1x3_mini_2.5h_1280x640.png`
- **Pixelize**: 8x downscale → upscale (160×80 → 1280×640 nearest)
- **Color Alpha**: WAS_Remove_Background, mode=`foreground`, threshold=245, tolerance=5

### 1.3 V38의 5종 출력 (api_full 기준)
1. `*_Stage1` — raw 1280×640 (흰배경)
2. `*_HiRes` — 1920×960 디테일 보강 (흰배경)
3. `*_Pixelized` — 8x 픽셀 그리드 정렬 (흰배경)
4. `*_PixelAlpha` ⭐ — 픽셀 그리드 + 투명배경 (게임 엔진용)
5. `*_RembgAlpha` — AI rembg 알파 (일러스트용)

### 1.4 검증 완료된 결과
- ✅ 캐릭터 비율 2.5등신 (ControlNet stick figure 강제)
- ✅ 4뷰 일관성 (좌측은 게임 엔진에서 flipX 권장)
- ✅ 흑발 사이드 포니테일
- ✅ 검 들기 (떠다니는 문제 해결)
- ✅ 흰배경 alpha 처리
- ✅ 픽셀 그리드 정렬

---

## 2. 핵심 자산 위치

### 2.1 ComfyUI 워크플로우
```
D:\DEV\ComfyUI\comfyuiImage_v34\
├── (sprite) Sprite_Illustrious_PoseGuided_Alpha_V38.json + api 5종 ⭐
├── (sprite) Sprite_Illustrious_PoseGuided_V37.json + api 4종
├── (sprite) PoseExtract_V37.json + api
├── (sprite design) Sprite_Illustrious_Pro_V36.json + api 4종
├── (illustration) B1_AnimagineXL_HiRes_V36.json + api 2종
├── (illustration) B2_PrefectPony_HiRes_V36.json + api 2종
├── (illustration) B4_Hyphoria_HiRes_V36.json + api 2종
├── (illustration) B5_AnythingXL_HiRes_V36.json + api 2종
├── (illustration) B6_MeinaMix_HiRes_V36.json + api 2종
├── (pixel_bg) C1_PixelDiffusionXL_V35.json
├── (pixel_bg) C2_RDXLPixelArt_V35.json
├── (icon) D1_AppIcon_V35.json
├── pose_grid_1x3_*.png (4개: 5h/3.5h/3h/2.5h)
├── pose_grid_1x4_*.png (5개, 미사용)
├── pose_grid_3x3/4x2/5x2_*.png (3개, 미사용)
└── generate_*.py (5개: pose_grid + v35/v36/v37/v38)
```

### 2.2 사용자 직접 저장본 (수동 보존, 건드리지 말 것)
```
D:\DEV\ComfyUI\user\default\workflows\
├── Sprite_Illustrious_Pro_V36.1.json     ← 사용자 36.1
├── Sprite_Illustrious_PoseGuided_V37.json
└── pixel_art\ (사용자 자체 워크플로우 13개, 별개 라인)
```

### 2.3 ComfyUI input/ (LoadImage 노드 참조)
```
D:\DEV\ComfyUI\input\
└── pose_grid_1x3_*.png 등 (already copied)
```

### 2.4 sd-catalog (메타데이터)
```
D:\DEV\sincerity-skills\sd-catalog\
└── sd_catalog.yml + detail/ (22개 모델)
```

### 2.5 asset-factory (다음 작업 대상)
```
D:\DEV\asset-factory\
└── 분석 필요 (서버 코드)
```

### 2.6 기존 skill (확장 후보)
```
D:\DEV\sincerity-skills\asset-factory-api\
└── SKILL.md (af CLI 가이드, 이미 작성됨)
```

---

## 3. 카테고리별 워크플로우 매핑 표

| Category | 변형 | 워크플로우 파일 (API) | Use case |
|---|---|---|---|
| **sprite** | pixel_alpha ⭐ | `Sprite_Illustrious_PoseGuided_Alpha_V38_api_pixel_alpha.json` | 게임 sprite (투명 픽셀) |
| sprite | full | `..._Alpha_V38_api_full.json` | 5종 동시 출력 |
| sprite | hires | `..._Alpha_V38_api_hires.json` | 1920×960 디테일 |
| sprite | rembg_alpha | `..._Alpha_V38_api_rembg_alpha.json` | AI 알파 |
| sprite | stage1 | `..._V37_api_stage1.json` | 빠른 디자인 탐색 |
| sprite (디자인) | base | `Sprite_Illustrious_Pro_V36_api_*.json` | 캐릭터 컨셉 |
| sprite extract | pose | `PoseExtract_V37_api.json` | 이미지→OpenPose |
| **illustration** | animagine | `B1_AnimagineXL_HiRes_V36_api_hires.json` | 깔끔한 표준 |
| illustration | pony | `B2_PrefectPony_HiRes_V36_api_hires.json` | Pony 정통 (score_9 트리거) |
| illustration | hyphoria | `B4_Hyphoria_HiRes_V36_api_hires.json` | Modern Illustrious |
| illustration | anything | `B5_AnythingXL_HiRes_V36_api_hires.json` | 범용 |
| illustration | meinamix | `B6_MeinaMix_HiRes_V36_api_hires.json` | SD1.5 빠름 |
| **pixel_bg** | sdxl | `C1_PixelDiffusionXL_V35.json` | SDXL 기반 |
| pixel_bg | pony | `C2_RDXLPixelArt_V35.json` | Pony + Fnaf style |
| **icon** | flat | `D1_AppIcon_V35.json` | flat/벡터 |

---

## 4. V38 API JSON 동적 수정 가이드

asset-factory가 LLM의 요청을 받아 API JSON을 patch할 때 알아야 할 노드 ID 매핑.

V38 api_full의 주요 노드 ID:

| Node ID | 종류 | 수정 필드 | 예시 |
|---|---|---|---|
| `2` | CheckpointLoader | `ckpt_name` | "hyphoria_v002.safetensors" |
| `3` | LoRA #1 (sprite) | `strength_model`, `strength_clip` | 0.7 |
| `4` | LoRA #2 (pixelart_up) | `strength_model`, `strength_clip` | 0.4 |
| `5` | **Positive Prompt** | **`text`** | (캐릭터 디자인) |
| `6` | Negative Prompt | `text` | (NEG_PIXEL_SPRITE) |
| `7` | LoadImage (pose grid) | `image` | "pose_grid_1x3_mini_2.5h_1280x640.png" |
| `8` | ControlNetLoader | `control_net_name` | "control-lora-openposeXL2-rank256.safetensors" |
| `9` | ControlNetApply | `strength` | 0.85 |
| `10` | EmptyLatentImage | `width`, `height` | 1280, 640 |
| `11` | KSampler #1 | **`seed`**, `steps`, `cfg` | 동적 |

⚠️ **주의**: 각 워크플로우 변형(stage1/hires/pixel_alpha 등)마다 노드 ID가 다를 수 있음. asset-factory는 워크플로우 로드 후 `class_type` 검색으로 동적 매칭하는 게 안전. 패치 시 ID 하드코딩 비추천.

권장 patch 함수 시그니처:
```python
def patch_workflow(api_json: dict, *, prompt: str, seed: int,
                   pose_image: str | None = None,
                   controlnet_strength: float | None = None) -> dict:
    for nid, node in api_json.items():
        ct = node.get("class_type")
        if ct == "CLIPTextEncode" and is_positive(node):
            node["inputs"]["text"] = prompt
        elif ct == "KSampler":
            node["inputs"]["seed"] = seed
        elif ct == "LoadImage" and pose_image:
            node["inputs"]["image"] = pose_image
        elif ct == "ControlNetApply" and controlnet_strength:
            node["inputs"]["strength"] = controlnet_strength
    return api_json
```

---

## 5. 핵심 결정 사항 (왜 이렇게 했는지 — 다음 작업자가 모를 수 있는 함정)

### 5.1 WAS_Remove_Background의 mode 라벨이 직관 반대 ⚠️
```python
# 코드 분석 (was-ns/WAS_Node_Suite.py)
if mode == 'background':
    grayscale_image = ImageOps.invert(grayscale_image)
    threshold = 255 - threshold
```
실제 동작:
- `mode="background"` → 캐릭터(어두운 부분)를 alpha 처리 ❌ (라벨과 반대)
- `mode="foreground"` → 흰배경을 alpha 처리 ✅ (정답)

**threshold=245, tolerance=5, mode=foreground**가 검증된 default.

### 5.2 ControlNet stick figure만 등신 결정
chibi prompt (`(chibi:1.4)` 등) 강하게 넣으면 캐릭터 비율 깨짐(과적용). prompt에는 `chibi, sd character` 정도 가벼운 힌트만, 비율은 stick figure y좌표(`generate_pose_grid.py`의 `head_ratio`)로 통제.

### 5.3 1×3 layout (4뷰가 아닌 3뷰)
SDXL/Illustrious는 좌측 옆모습 학습 약함. 4뷰 시도 시 좌측이 자주 우측처럼 그려짐. → 3뷰만 생성하고 게임 엔진에서 `flipX`. 캐릭터 일관성 100% (정확한 좌우대칭).

### 5.4 검 떠다니는 문제 (multi-view 일러스트의 고질적 이슈)
"silver sword" 단독 명시는 별개 오브젝트로 인식됨. **`(holding silver sword:1.3), sword in right hand, gripping sword tightly`**로 동사 묶기 + negative에 `floating sword, detached weapon` 등 8개 키워드 박아서 해결.

### 5.5 prompt 단순화 (chibi 키워드 과적용 사례)
초기에 `(chibi:1.4), (super deformed:1.2), big head, small body, (3 head tall body:1.3)` 등 7개 박았다가 결과 깨짐. 현재는 `chibi, sd character, full body` 정도만.

### 5.6 V36 Sprite vs V37/V38
- V36 Sprite: 캐릭터 컨셉 디자인 단계 (자유로운 layout)
- V37 Sprite: + ControlNet OpenPose (3뷰 강제)
- V38 Sprite: + Alpha 추출 (게임 엔진용)
- 사용자가 "용도별로 만들어둔 것"이라 V36도 보존 (deprecated 아님)

### 5.7 사용자 36.1 보존본
`D:\DEV\ComfyUI\user\default\workflows\Sprite_Illustrious_Pro_V36.1.json`은 사용자가 V36에서 직접 변형한 버전. 절대 건드리지 말 것.

---

## 6. 다음 작업 — 두 가지 트랙

### Track A: asset-factory 서버 통합 (메인)

**목표**: `af gen` CLI에 우리가 만든 새 워크플로우 타입 추가.

**해야 할 일**:
1. `D:\DEV\asset-factory\` 코드 분석
   - 기존 SD 호출 흐름 (어느 endpoint가 ComfyUI 호출하나)
   - 워크플로우 타입 분기 로직 (이미 있으면 확장, 없으면 추가)
   - sd_catalog 로딩 위치 (`SD_CATALOG_PATH` 환경변수)
2. 새 endpoint 또는 기존 확장
   ```
   POST /api/sd/generate
   body: {
     "category": "sprite|illustration|pixel_bg|icon",
     "variant": "pixel_alpha|hires|...",
     "style": "animagine|pony|...",   // illustration만
     "head_ratio": 2.5,                // sprite만
     "prompt": "...",                  // 자연어 또는 SD prompt
     "seed": 12345,
     "negative": null                  // override 옵션
   }
   ```
3. 워크플로우 로딩 + patch
   - `D:\DEV\ComfyUI\comfyuiImage_v34\`에서 적절한 API JSON 로드
   - 또는 별도 위치(`asset-factory/workflows/`)에 복사 후 import
   - patch_workflow() 호출 (§4 참조)
4. ComfyUI `/prompt` POST + 폴링 + 결과 다운로드
5. validation_status 처리 (5종 출력 중 어느 게 메인인지 결정)

**우선순위**:
- sprite (V38 pixel_alpha) ← 즉시 가치
- illustration (B 시리즈) ← 마케팅/디자인 자산
- pixel_bg (C 시리즈)
- icon (D 시리즈)

### Track B: asset-factory-api skill 확장 (선택)

**목표**: `af` CLI에 새 옵션 추가 + SKILL.md 갱신.

`af` CLI 옵션 추가 예시:
```bash
af gen <project> <asset_key> "prompt" \
    --category sprite \
    --variant pixel_alpha \
    --head-ratio 2.5

af gen <project> <asset_key> "prompt" \
    --category illustration \
    --style hyphoria

af catalog workflows  # 카테고리/변형 목록 노출
```

SKILL.md에 추가할 섹션:
- "When to use sprite vs illustration vs pixel_bg vs icon"
- 카테고리별 prompt 템플릿
- multi-view sprite의 좌우 flip 가이드

---

## 7. 권장 진행 순서

1. **§2.5 asset-factory 코드 1시간 분석** — 어디까지 만들어졌는지, sd_catalog 어떻게 쓰는지 파악
2. **`af catalog models` 실행** — 현재 어떤 모델/워크플로우 노출되는지
3. **Track A 1번 워크플로우 통합** — V38 sprite pixel_alpha 하나만 먼저 (validation으로)
4. 통합 성공 → 나머지 카테고리 확장
5. Track B (skill 확장)는 마지막

**환경변수 메모**: `SD_CATALOG_PATH=D:\DEV\sincerity-skills\sd-catalog\sd_catalog.yml` 또는 변환된 단일 파일

---

## 8. 미해결/추가 고려 사항

- **B 시리즈 V37/V38화**: 가능. 일러스트에 alpha 추가하면 마케팅 자산으로 유용. (rembg만 추가하면 됨)
- **C/D 시리즈 V36/V37화**: 가능. 픽셀 배경에 HiRes 추가, 아이콘에 alpha 추가.
- **Chroma key 방식**: 흰배경 alpha 실패 시 fallback. prompt에서 `white background` → `solid magenta background` + magenta를 alpha로.
- **LayerDiffuse**: 가장 깔끔한 alpha 생성. 별도 모델(layer_xl_transparent_attn.safetensors) 필요.
- **IPAdapter 재투입**: 캐릭터 일관성 더 강하게 잡으려면. V34 Advanced에 이미 사용 사례 있음.
- **Detailer (FaceDetailer)**: 작은 얼굴 디테일 보강. V34 Detailer가 참고 자료.

---

## 9. 환경/스택 메모

- **사용자**: Kotlin 백엔드 8년차
- **GPU**: RTX 4080 Super 16GB VRAM
- **ComfyUI**: `D:\DEV\ComfyUI\` (master 브랜치)
- **ComfyUI 패키지** (확인됨): comfyui-impact-pack, comfyui-kjnodes, ComfyUI-Manager, comfyui_controlnet_aux, comfyui_ipadapter_plus, was-ns
- **rembg 패키지**: 사용자가 ComfyUI Manager로 자동 설치 (확인 안됨, 없으면 V38 rembg_alpha 안 됨)
- **모델 파일**: D:\DEV\ComfyUI\models\ (catalog yml 참조)

---

## 10. 빠른 시작 (다음 작업자용)

```bash
# 1. ComfyUI 켜기 (이미 켜져 있을 가능성 높음)
cd D:\DEV\ComfyUI
python main.py
# → http://localhost:8188

# 2. asset-factory 헬스 체크
af health
# → SD 연결 OK인지 확인

# 3. 현재 노출된 모델/워크플로우
af catalog models
af catalog loras

# 4. 우리가 만든 V38 워크플로우 직접 호출 (asset-factory 거치지 않고 검증)
python -c "
import requests, json, uuid
with open(r'D:\DEV\ComfyUI\comfyuiImage_v34\Sprite_Illustrious_PoseGuided_Alpha_V38_api_pixel_alpha.json') as f:
    wf = json.load(f)
res = requests.post('http://localhost:8188/prompt',
    json={'prompt': wf, 'client_id': str(uuid.uuid4())})
print(res.json())
"
# → ComfyUI/output/에 PNG 생성됨

# 5. asset-factory 코드 분석 시작
cd D:\DEV\asset-factory
# (코드 구조 파악 후 새 endpoint 추가)
```

---

## 11. 참고 — 직전 세션의 진화 흐름 (요약)

V35 (모델 분리) → V36 (HiRes 옵션 + B/C/D 시리즈) → V36.1 (사용자 변형) → V37 (ControlNet OpenPose, 1×3 layout, chibi 비율) → V38 (alpha 추출, WAS bg 노드 fix).

각 버전별 핵심 변경:
- V35: 카테고리별 모델 분리 (sprite/illust/pixel_bg/icon)
- V36: HiRes 그룹 추가 (mute toggle), API format 일괄 생성
- V36.1: 사용자 직접 변형 (보존)
- V37: ControlNet OpenPose, 1×3 chibi grid, prompt 단순화, 검 떠다님 fix
- V38: 색상 알파 + AI rembg 알파, WAS 노드 mode/threshold/이름 fix

generator 스크립트들이 V37→V38로 import 의존하므로 **`generate_v37_workflows.py` 절대 삭제 금지**.

---

이 인계서로 다음 작업자가 1~2시간 내 풀 컨텍스트 따라잡고 작업 시작 가능. 추가 질문은 user에게 확인.
