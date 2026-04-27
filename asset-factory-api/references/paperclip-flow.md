# Paperclip 워크플로 — Reference

> SKILL.md 본문에서 분리. Paperclip 이슈 받아 에셋 생성 task 진행 시 본다.

---

## 표준 흐름

페이퍼클립 이슈가 *"에셋 N장 만들어줘"* / *"NPC 시트 5종"* / *"게임 로고 8개 시안"* 형태일 때:

### 1. 의도 파싱 + 변형 추천

```bash
# 자연어 task 그대로 recommend 에 넘기기
af workflow recommend "<이슈에서 추출한 자연어 task>" --top 3

# 또는 tag 조합이 명확하면 search
af workflow search --tag transparent-bg --tag pose-sheet
```

→ top 3 후보 + score + `not_for_warnings` 받음.

### 2. 후보 검증

`not_for_warnings` 비어있는 첫 후보 채택. catalog 의 `meta.output_layout` 으로 *최종 이미지 형태* (`single`/`pose_grid`/`tile_grid`/`character_sheet`) 가 사용자 의도와 일치하는지 확인.

```bash
af workflow describe sprite/pixel_alpha   # full meta 한 번 확인
```

### 3. 본 호출 (subject 모드 권장)

```bash
af workflow gen <variant> <project> <asset_key> \
   --subject "<캐릭터 묘사만 — 외형/복장/무기>" \
   --candidates N --wait
```

- `subject` 는 catalog `meta.prompt_template.user_slot.examples` 1개를 참고해 *변형*
- `<project>` 는 Paperclip 이슈 ID 또는 `proj_<short>` 컨벤션
- `<asset_key>` 는 의미 있는 식별자 (e.g. `npc_warrior_silver`)
- `--candidates 4` 가 cherry-pick 시 좋은 비교 분량 (1·2 는 부족, 8 은 검수 피로)

### 4. 승인 모드 결정

| 케이스 | 모드 | 명령 |
|---|---|---|
| 게임에 들어갈 정식 자산 | `manual` | (플래그 없음) — cherry-pick 큐 |
| 시뮬·스캐치·chain 중간물 | `bypass` | `--bypass-approval` |
| 다인원 / 시리즈 통일성 / 로고 등 *디자인 판단 필요* | `manual` | 사람 검수 가치 명확 |

> 원칙: 검수 가치 *없으면* bypass, *있으면* manual.

### 5. 결과 전달

```bash
# manual 모드 — Web UI cherry-pick 안내 코멘트
af status <job_id>   # 잡 상태 + completed_count 확인
# → 후보 이미지는 Web UI (/cherry-pick) 에서 사용자가 직접 선택
# → Paperclip 이슈 코멘트로 안내 ("후보 N장 준비됨 — http://...:47823/cherry-pick 에서 선택 부탁")

# bypass 모드 — 결과 직접 첨부
af get <asset_id> -o output.png
# → 파일 직접 업로드
```

### 6. 승인 후 (manual 모드)

```bash
af export <project> --manifest   # 승인본만 묶음 (bypass 자동 제외)
```

→ ZIP/디렉토리로 사용자 전달. manifest.json 에 asset_id, prompt_resolution.final_positive, seed 등 메타데이터 동봉.

---

## 케이스별 가이드

### 케이스 A: NPC 캐릭터 시트 5종

```bash
# 의도: RPG NPC 캐릭터 5명 (서로 다른 직업) 의 1×3 sprite sheet
for npc in warrior mage rogue priest archer; do
  af workflow gen sprite/pixel_alpha proj_rpg_npc npc_${npc} \
     --subject "<직업별 캐릭터 묘사>" \
     --candidates 4 --wait
done
# → cherry-pick 큐에 5 × 4 = 20 candidate slot 등장
# → 사람이 NPC 별 1장씩 골라서 5장 승인
```

**주의**: 다인원 시도하지 마라 — 한 이미지에 3명 이상은 attribute bleeding. 별도 `asset_key` 로 단독 생성.

### 케이스 B: 마케팅 일러스트 1장 (단일)

```bash
af workflow gen illustration/animagine_hires proj_mkt cover_001 \
   --subject "1girl, school uniform, sitting in cafe, soft natural lighting" \
   --candidates 4 --wait
```

→ sprite 가 아닌 illustration 사용. 단일 이미지 + 흰배경 아닌 풍부한 배경.

### 케이스 C: 사용자 사진 → 캐릭터 합성 chain

```bash
# 1) 포즈 추출
af workflow gen sprite/pose_extract tmp_chain step1 \
   --subject "extract pose" \
   --input source_image=@./user_pose.jpg \
   --bypass-approval --wait
# → job_id="..." (응답에서 capture). chain 입력은 asset_id 로 우회 (`run:<id>` syntax 미구현)

# 2) 추출된 포즈로 캐릭터 합성
af workflow gen sprite/pixel_alpha proj_user_chain final \
   --subject "knight, blue armor, holding sword" \
   --input pose_image=run:run_xxx.../pixel_alpha \
   --candidates 4 --wait
```

> chain 중간물 (`step1`) 은 `tmp_*` project + `--bypass-approval`. 정식 자산 (`step2`) 만 cherry-pick 큐로.

### 케이스 D: 시뮬레이션 100장 (검수 무의미)

```bash
# bypass 모드 + 큰 candidates_total
for i in {1..100}; do
  af workflow gen sprite/pixel_alpha sim_${BATCH} sim_${i} \
     --subject "..." --bypass-approval --candidates 1 --wait
done
# → cherry-pick 큐 안 거침. 결과 즉시 회수 가능.
# → bypass_retention_days 후 GC 됨 (자동 정리)
```

### 케이스 E: 로고 8장 시안 (사람 디자인 판단 필요)

```bash
af workflow gen icon/flat proj_logo logo_v1 \
   --subject "<브랜드 컨셉>" \
   --candidates 8 --wait
# → manual 모드 — 8장 cherry-pick UI 에서 1-2장 선별
```

> 로고는 디자인 판단 가치 큼 → bypass 금지.

---

## 사용자 응대 패턴

### 의도 파악 단계

이슈 본문에서 다음 정보 추출:
1. **카테고리 의도** (캐릭터 / 일러스트 / 배경 / 아이콘)
2. **출력 형태** (단일 / 시트 / 다수)
3. **스타일 키워드** (픽셀 / Pony / 마케팅 / 호러 등)
4. **수량** (몇 장? 시뮬인가 정식인가)
5. **chain 의도** (사용자 사진/asset 입력 있나)

→ 이걸 자연어로 `recommend` 에 넘김.

### 모호한 의도일 때

`af workflow recommend` 의 top 3 + 각 후보의 `not_for_warnings` 보여주고 사용자에게 *"이거 맞아?"* 한 번 확인. 잘못된 변형으로 100장 뽑고 재생성하는 것보다 1분 확인이 효율적.

### 결과 전달 후

`prompt_resolution.final_positive` 를 코멘트에 한 줄 박아두면, 사용자가 *"이 prompt 살짝 바꿔줘"* 라 할 때 정확히 어디가 base_positive 고 어디가 subject 인지 추적 가능.

---

## Pitfalls (Paperclip 컨텍스트 전용)

1. **이슈 본문 그대로 prompt 박지 마라** — 사용자가 한국어로 "검 든 기사 그려줘" 라 했어도 `subject` 는 영문 + SD 토큰 컨벤션 (`1boy, knight, blue armor, holding sword`). catalog `examples` 참고.
2. **`asset_key` 는 의미 있게** — `npc_warrior_silver_v2` 같은 식별자. `test_001` 같은 generic name 은 시리즈 추적 안 됨.
3. **시리즈 통일성** — 같은 캐릭터 다른 포즈 N장이면 `seed` 고정 + `--candidates 1` 반복. 매번 다른 seed 면 캐릭터 일관성 깨짐.
4. **`tmp_*` project 격리** — bypass 자산을 정식 project 에 섞지 마라. `af list <project>` 가 지저분해짐 + manifest export 시 혼란.
5. **이슈 close 전에 export** — `af export <project> --manifest` 로 승인본 묶음 + manifest.json 첨부 → 이슈 close. manifest 에 prompt/seed 박혀있어 재현 가능.
