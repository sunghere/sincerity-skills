# 프롬프트 노하우 (v4 — ComfyUI 워크플로우 시대)

> SKILL.md 본문은 핵심만 다룬다. 이 파일은 까다로운 케이스 (다인원·속성 보호·시리즈 통일 등) 대응용.
>
> ⚠️ v4 의 변화: 모델·LoRA·step·cfg 같은 SD 파라미터는 **에이전트가 만지지 않는다**. 변형(variant) 이 다 박고 있다. 이 문서는 **prompt 본문 작성** 노하우만 다룬다.

## 1. 카테고리별 prompt 문법 (변형이 자동 처리하는 것 vs 에이전트가 적는 것)

### sprite/* (V38 / V37 라인업)
- 워크플로우가 자동 prepend: `pixel art, sprite, three views, ...`
- 등신·layout 은 **pose grid 가 결정** (prompt 영향 X)
- 에이전트가 적는 본문: 캐릭터 묘사 + 의상 + 장비 + 표정/포즈 의도

```
1girl, (black hair:1.2), (side ponytail:1.3), long hair,
blue knight armor, (holding silver sword:1.3), sword in right hand,
red cape, fantasy warrior, masterpiece, best quality, very aesthetic
```

### illustration/animagine_hires
- 자연어 OK. 끝에 `masterpiece, best quality, very aesthetic`
- pixel-art 키워드 절대 X (이건 일러스트 카테고리)

```
1girl, school uniform, sitting in cafe, soft natural lighting,
cinematic composition, masterpiece, best quality, very aesthetic
```

### illustration/pony_hires (Pony 정통)
- **`score_X` 트리거 필수** — 빠지면 출력 품질 급락
```
score_9, score_8_up, score_7_up, score_6_up,
1girl, ...
```

### illustration/hyphoria_hires (Modern Illustrious)
- 2025 트렌드. Pony 처럼 score 토큰 안 써도 됨. 자연어 + masterpiece 끝.

> 변형별 권장 negative 는 **catalog 의 `recommended_negative_preset` 또는 `defaults.negative_prompt`** 가 알아서. 에이전트는 추가 negative (속성 보호) 만 적는다.

## 2. 다인원 / 영역 분리 — v4 의 우회법

A1111 의 `BREAK` 토큰은 **ComfyUI 워크플로우에선 그대로 동작 안 함** (CLIP encoding 단이 다름). v4 에서 다인원은 다음 4단계로:

| Level | 방법 | 적용 |
|-------|------|------|
| 1 | 본문에 명시적 위치·가중치 (`leftmost girl: ...`) | 2인 이하 약한 효과 — 한계 명확 |
| 2 | 인원 축소 (3→2, 별도 1샷) | 안정성 ↑ |
| 3 | **단독 생성 + 사용자 측 합성** ⭐ | 가장 확실. 캐릭터 100% 보존. **3인 이상 무조건 이것** |
| 4 | Regional Prompter / ControlNet 변형 | 변형 추가 시 가능 (현재 미제공) |

**Level 3 워크플로**:
1. 캐릭터 A 단독 생성 (`asset_key=char_a`, `--bypass-approval` 권장 — 합성 전 임시물)
2. 캐릭터 B 단독 생성 (`asset_key=char_b`)
3. 사용자가 게임 엔진/디자인 도구에서 합성. PIL 같은 코드 합성은 에이전트가 직접 X (가짜 에셋 사례).

## 3. 속성 보호 — 경쟁 속성 차단 (v3 와 동일, v4 도 유효)

원하는 속성을 지키려면 대체 속성을 모두 negative 로 명시.

| 지키려는 속성 | Negative 에 추가할 것 |
|--------------|---------------------|
| 실버/플래티넘 헤어 | `pink hair, gold hair, brown hair, red hair, blue hair, green hair, purple hair, orange hair` |
| 긴 머리 | `short hair, bob, buzz cut, pixie cut` |
| 특정 눈색 (예: 청록) | 청록 외 모든 눈색 명시 |
| 동양인 얼굴 | `western face, european features` |
| 좌측 옆모습 보존 | (sprite 한정) — pose grid 의 좌측 칸 fix. 게임 엔진에서 `flipX` 권장 |

평범한 `low quality, bad anatomy` 만 적을 때 대비 유지율 +20~30%.

> 주의: catalog 의 권장 negative preset (`NEG_PIXEL_SPRITE` 등) 위에 **덧붙여진다** — 중복 작성 금지.

## 4. 시리즈/브랜드 통일

> v3 에선 "모델 1개 고정 + seed 변주" 가 규칙이었지만, v4 에선 변형 자체가 모델을 박고 있어서 **변형 1개 고정** 으로 자동 충족된다.

올바른 패턴:
- 한 시리즈는 **변형 1개로 통일** (예: 모든 캐릭터를 `sprite/pixel_alpha` 로)
- 다양성은 prompt 변주 + `seed` 변주 (`--candidates 4` 또는 4번 호출)
- alias (`@character`) 사용 시 자동으로 통일

잘못된 패턴:
- 같은 시리즈 안에서 `sprite/pixel_alpha` 와 `illustration/animagine_hires` 섞기 → 사용자 피드백 "통일감 없음" 보장
- `sprite/full` 의 5개 출력을 다른 캐릭터로 골라잡기 — 같은 1 candidate 의 변형들이라 **같은 캐릭터** 여야 의미

## 5. 사용자 사진 → 포즈/스타일 ControlNet (v4 신규)

PR #14 의 동적 입력으로 가능해진 패턴.

### A. 사용자 사진의 포즈만 추출 → 캐릭터 합성
```bash
# 1) 포즈 추출 (chain 중간물 — bypass)
af workflow gen sprite/pose_extract pj_chain step1 "extract pose only" \
   --input source_image=@./user_photo.jpg \
   --bypass-approval --wait

# 2) 추출된 포즈 grid 로 캐릭터 합성
af workflow gen sprite/pixel_alpha pj_chain step2 \
   "1girl, blue knight armor, holding sword, masterpiece, ..." \
   --input pose_image=run:<step1_run_id>/pixel_alpha \
   --wait
```

### B. 사용자가 직접 그린 pose grid 사용
```bash
af workflow gen sprite/pixel_alpha pj character_a "..." \
   --input pose_image=@./custom_pose_grid.png \
   --wait
```

> 프롬프트는 ControlNet 의 conditioning 위에서 작동. 포즈가 강하게 박힐수록 prompt 의 "pose" 관련 단어 (예: `standing`, `running`) 는 영향 약해짐.

## 6. 배경 투명화

워크플로우가 알아서 처리:
- `sprite/pixel_alpha`: stage1 → pixelize → alpha 까지 워크플로우 내부에서 완성
- `sprite/rembg_alpha`: AI rembg 노드로 일러스트풍 알파

워크플로우 안에서 안 되는 변형이면 (예: 일부 illustration 변형) **재생성 권장**:
- prompt: `transparent background, isolated on transparent, no background, clean edges`
- negative: `background, scenery, color fill, gradient background`

> v3 의 `floodfill-bg-remove` 는 ComfyUI 변형이 자체 처리하므로 **거의 호출할 일 없음**. 비상용으로만.

## 7. 가짜 에셋 판정 (재차 강조)

에이전트가 PIL 로 사각형 합성해 "생성 완료" 보고하는 패턴 방지.

1. **파일 크기**: 32×32 PNG ≥ 1KB 정상, <500B 강력 의심
2. **색상 수**: PIL `Image.getcolors(65536)` ≤ 10개 + 단색 면적 큼 → 의심
3. **확정**: vision tool 로 "ComfyUI 생성인가 PIL 합성인가" 판정

> 워크플로우 호출은 시간이 걸린다 (~30s+). 5초 만에 결과가 나왔다면 가짜.

## 8. 결과는 사람이 본다

vision tool 로 후보 N장 일일이 평가하지 말 것 — 토큰 낭비.

- **manual 모드**: `cherry-pick URL` 한 줄 사용자에게 전달, 종료. 사람이 평가.
- **bypass 모드**: 결과 N장의 `asset_id` 와 함께 미리보기 1~2장만 첨부. 평가는 사용자.

예외: OCR / 색상 측정 / 픽셀 카운트처럼 **정량 검증** 이 필요한 경우만.

## 9. v3 → v4 마이그레이션 가이드 (이전 prompt 자산이 있을 때)

v3 시절 작성된 prompt 자산을 v4 에서 재사용하려면:

| v3 요소 | v4 처리 |
|---------|---------|
| `BREAK` 구문 | 제거. Level 3 (단독 생성) 으로 분리. |
| 모델명 (`pixelArtDiffusionXL_spriteShaper` 등) | 제거. 변형 (`sprite/pixel_alpha`) 으로 대체. |
| LoRA 명시 (`<lora:pixel-art-xl-v1.1:0.7>`) | 제거. 변형이 LoRA 박고 있음. |
| `score_9, score_8_up, ...` | Pony 변형 (`illustration/pony_hires`) 사용 시만 유지. |
| `expected_size: 64`, `max_colors: 32` | 제거. 변형 출력이 곧 최종. |
| `negative_prompt`: `low quality, bad anatomy` 만 | catalog preset 사용 + 속성 보호만 추가. |
| 캐릭터 묘사 본문 | 그대로 사용 가능 — 가장 가치 있는 자산. |

> **요약**: prompt 본문 (캐릭터 묘사) 만 가져가고 SD 파라미터·모델·LoRA·script 토큰은 다 버린다.
