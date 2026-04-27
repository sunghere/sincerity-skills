# 프롬프트 작성 노하우 — Reference

> §1.B (PR #42) 머지 후 *서버가 자동으로 base_positive / base_negative 합성*. 사용자/에이전트는 `subject` (캐릭터 묘사만) 입력하면 됨.
>
> 이 파일은 **subject 작성 디테일** + **legacy 모드 호출 시 직접 작성** + **시리즈 통일성/속성 보호/다인원 같은 까다로운 케이스** 노하우 모음.
>
> SKILL.md 본문의 변형 선택 4-step + Pitfalls 만으로 충분한 일반 케이스에는 안 본다.

---

## 1. `subject` 입력 가이드 (subject 모드 — 권장)

### 1.1 어떻게 쓰나

`meta.prompt_template.user_slot.examples` 1개 복사 → 변형 → `--subject` 인자.

```bash
# catalog 의 examples 보기
af workflow describe sprite/pixel_alpha
# → user_slot.examples: ["1girl, silver hair...", "1boy, brown spiky hair...", ...]

# 그대로 변형
af workflow gen sprite/pixel_alpha proj test \
   --subject "1girl, (black hair:1.2), long hair, blue knight armor, (holding silver sword:1.3), red cape, fantasy warrior" \
   --wait
```

### 1.2 규칙

- **캐릭터 묘사만** — 외형 (성별/머리/눈/체형) + 복장 + 무기 + 액션 + 표정
- **금지** — 스타일 (`pixel art`), 구도 (`full body`), 배경 (`white background`), 레이아웃 (`1x3 grid`). 이 모두 `base_positive` 가 처리.
- **금지** — `(chibi:1.4)` 같은 chibi 가중치 강조. ControlNet stick figure 가 등신 결정 → 충돌.
- **금지** — `<lora:xxx:0.7>` syntax. 워크플로우 JSON 의 LoRA 노드와 이중 로드.

### 1.3 Pony 변형 — score 자동

`illustration/pony_*`, `pixel_bg/pony_*` 변형은 `base_positive` 에 `score_9, score_8_up, score_7_up` 자동 prepend. **사용자가 직접 박을 필요 없음** (legacy 모드에서만 필요).

### 1.4 검 들기 trick

검 든 캐릭터 호출 시 동사 묶기:

```
(holding silver sword:1.3), sword in right hand, gripping sword tightly
```

`base_negative` 에 `floating sword, detached weapon, levitating sword, weapon hovering` 등 8개 이미 박혀있어도 prompt 가 약하면 검 떠다님.

---

## 2. 속성 보호 (시리즈 통일성)

### 2.1 머리 색 유지

같은 캐릭터를 N장 뽑을 때, 머리 색이 변하면 시리즈 통일성 깨짐.

```bash
# subject 에 명시
--subject "1girl, (silver hair:1.3), long hair, ..."

# negative 에 경쟁 색 명시 — 유지율 +20~30%
--negative-prompt "pink hair, gold hair, brown hair, blonde hair, red hair, green hair, blue hair"
```

→ `negative_prompt` 는 `base_negative` 에 *append* 됨 (override 아님).

### 2.2 시리즈에서 캐릭터 일관성

```bash
# seed 고정 + candidates=1 반복
SEED=42
for pose in idle walk run attack; do
  af workflow gen sprite/pixel_alpha proj_series ${pose} \
     --subject "1girl, silver hair twin tails, school uniform, ${pose}" \
     --seed $SEED --candidates 1 --wait
done
```

> 매번 다른 seed 면 미세 변화 누적 → 캐릭터 다른 사람으로 보임. seed 고정 + subject 만 미세 조정.

### 2.3 LoRA 트리거가 약할 때

`base_positive` 의 LoRA 트리거 (e.g. `pixel_character_sprite`) 가 약해 보이면 — **prompt 에서 강화하지 마라**. 트리거가 강도가 정해져 있고 (워크플로우 JSON 의 노드), prompt 에 중복 적어도 효과 거의 없음.

→ 강화 필요하면 워크플로우 JSON 의 LoRA 노드 strength 변경 (asset-factory 개발자 PR 단위).

---

## 3. legacy 모드 (직접 prompt 작성)

`prompt_template == null` 인 utility 변형 (`pose_extract`) 또는 `prompt_mode: legacy` 강제 시.

### 3.1 sprite/* (V38 legacy)

```
1girl, (black hair:1.2), (side ponytail:1.3), long hair,
blue knight armor, (holding silver sword:1.3), sword in right hand,
red cape, fantasy warrior, masterpiece, best quality, very aesthetic
```

자동 prepend 되던 `pixel_character_sprite, sprite, sprite sheet, ...` 가 빠지므로 직접 박아야 함.

### 3.2 illustration/* (단일)

```
1girl, school uniform, sitting in cafe, soft natural lighting,
cinematic composition, masterpiece, best quality, very aesthetic
```

### 3.3 Pony 변형 (legacy)

끝 또는 처음에 `score_X` 필수:

```
score_9, score_8_up, score_7_up, score_6_up,
1girl, ...
```

> subject 모드면 자동 prepend 됨. legacy 만 직접 박음.

---

## 4. 까다로운 케이스

### 4.1 다인원 캐릭터 (3명 이상)

**한 이미지에 3명 이상 — attribute bleeding 거의 확정**. 머리색·복장·무기 섞임.

→ 별도 `asset_key` 로 단독 생성:

```bash
for char in alice bob charlie; do
  af workflow gen illustration/animagine_hires proj_party char_${char} \
     --subject "<character ${char} 묘사>" \
     --candidates 4 --wait
done
# → 후처리에서 합성 (별 도구)
```

### 4.2 시리즈 배경 통일

같은 환경의 다른 시간대 / 시점 N장:

```bash
# 환경 묘사를 base 로 박고 *변화 부분만* subject 에서 변경
SEED=100
for time in dawn noon dusk night; do
  af workflow gen pixel_bg/sdxl_hires proj_env env_${time} \
     --subject "fantasy castle courtyard, ${time} lighting, ..." \
     --seed $SEED --candidates 1 --wait
done
```

### 4.3 표정/포즈만 변경 (캐릭터 동일)

`pose_image` alternatives 활용:

```bash
# pose_grid_1x4 로 4-pose 시트 (idle/walk/attack/hurt)
af workflow gen sprite/pixel_alpha proj_anim warrior_4pose \
   --subject "1boy, knight, ..." \
   --input pose_image=pose_grid_1x4_1280x640.png \
   --wait
```

→ 캐릭터 prompt 는 동일, layout 만 변경.

---

## 5. 모델 선택 가이드 (illustration 카테고리)

| 변형 | 강점 | 약점 |
|---|---|---|
| `animagine_hires` | 깔끔한 표준 anime | 스타일 자유도 보통 |
| `pony_hires` | Pony 정통, score 표현 풍부 | NSFW 학습 강함 (의도 안 했어도) |
| `hyphoria_hires` | Modern Illustrious 2025 트렌드 | 새 모델 — 안정성 검증 중 |
| `anything_hires` | 범용 (가장 무난) | 특색 부족 |
| `meinamix_hires` | SD1.5 — VRAM 적음 | 해상도 낮음 (512×768) |

→ 마케팅·홍보 = `animagine_hires` (`@marketing` alias). 특수 스타일 의도 = pony/hyphoria. VRAM 제약 = meinamix.

---

## 6. catalog 응답이 SSOT — 이 문서 stale 우려 시

본 파일의 변형별 디테일 (LoRA 트리거, 자동 prepend, base_positive/negative 등) 은 catalog `meta.prompt_template` 이 SSOT. 차이 발견 시:

```bash
af workflow describe sprite/pixel_alpha   # → prompt_template 전체
```

이 응답이 본 파일과 충돌하면 응답이 우선. 본 파일 갱신 PR 부탁.
