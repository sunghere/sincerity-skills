---
name: asset-factory-api
version: 6
description: "Asset Factory(ComfyUI 워크플로우 기반) 로 게임/일러스트 에셋 생성. catalog → recommend → subject 모드 generate. 모델·LoRA·step·cfg 같은 SD 파라미터는 사용자가 만지지 않는다. SD 서버 직접 호출 절대 금지."
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

# Asset Factory (v4 — ComfyUI 워크플로우)

게임/일러스트 에셋 생성 파이프라인. **`af` CLI 한 줄 또는 REST API 호출**로 ComfyUI 워크플로우 변형을 호출한다.

## 🚨 v4 패러다임 (이전과 다름)

| 항목 | v3 (구) | v4 (지금) |
|---|---|---|
| 백엔드 | (구) SD 직접 호출 | **ComfyUI 워크플로우 호출** |
| 모델 선택 | 에이전트가 결정 | **변형(variant)이 모델을 내장** — 에이전트 관여 X |
| LoRA/weight | 에이전트가 `--lora xxx:0.8` 지정 | 변형 내부에 박혀 있음 |
| step/cfg/sampler | 에이전트가 결정 | 변형 `defaults` 가 알아서 |
| prompt 작성 | 에이전트가 통째 작성 | **`subject` (캐릭터 묘사만) 입력 → 서버 자동 합성** (§1.B) |
| 변형 선택 | description 한 줄 보고 추측 | **`/api/workflows/recommend` 자연어 query** (§1.C) |
| 카테고리 | 약함 | **명시적**: `sprite` / `illustration` / `pixel_bg` / `icon` |
| 결과 형태 | 1장 | **multi-output** (변형마다 다름; e.g. `sprite/pixel_alpha` = 3장) |
| 동적 입력 | 없음 | **PoseExtract / ControlNet chain** 가능 |
| 승인 | 항상 cherry-pick | `--bypass-approval` 플래그로 우회 가능 |

## When to use

- 게임/일러스트 에셋(픽셀 캐릭터, 스프라이트 시트, 일러스트, 픽셀 배경, UI 아이콘) 생성 요청
- *"캐릭터 도트로 만들어줘"* / *"마케팅 일러스트 1장"* / *"NPC 스프라이트 시트"* 같은 task
- 사용자 사진에서 포즈 추출 → 캐릭터 합성 chain
- 시뮬레이션·스캐치 같은 임시물 빠른 iteration (bypass 모드)

## When NOT to use

- 일반 텍스트→이미지 (스타일/모델 자유) — 별 도구
- 비-에셋 이미지 처리 (사진 보정, 배경 제거 단독) — 별 도구
- 고해상도 사진 합성, 실사 — Asset Factory 는 *게임/일러스트 에셋* 전용

---

## CLI: `af`

```bash
# 1. 카탈로그 — 사용 가능한 카테고리/변형/입력 라벨 + 디스커버리 메타
af workflow catalog
af workflow describe sprite/pixel_alpha   # 한 변형의 full meta

# 2. 변형 추천 — 자연어 의도로 후보 받기 (§1.C)
af workflow recommend "RPG 픽셀 캐릭터 정면 측면 뒷면 시트" --top 3

# 3. tag 검색 — 정확 tag 매칭
af workflow search --tag transparent-bg --tag pose-sheet --not scenery

# 4. 생성 (subject 모드 — 권장, §1.B)
af workflow gen sprite/pixel_alpha <project> <asset_key> \
   --subject "1girl, silver hair twin tails, school uniform, holding a notebook" \
   --candidates 4 --wait

# 5. 생성 (legacy 모드 — 기존 호환)
af workflow gen sprite/pixel_alpha <project> <asset_key> "<prompt 통째>" \
   --candidates 4 --wait

# 6. 동적 입력 (PoseExtract / ControlNet) — references/dynamic-inputs.md
af workflow upload ./pose.png
af workflow gen sprite/pose_extract pj step1 \
   --input source_image=@./pose.png --bypass-approval --wait

# 7. Bypass 모드 (시뮬·스캐치·chain 중간물)
af workflow gen sprite/pixel_alpha tmp_sim sim_001 \
   --subject "..." --bypass-approval --wait

# 8. 결과 회수
af list <project> [--include-bypassed]
af get <asset_id> -o output.png
af export <project> --manifest               # 승인본만
```

`--wait` 빼면 `run_id` 받고 종료. 나중에 `af status <run_id>` 또는 `af wait <run_id>`.

---

## 의사결정 — 변형 선택 4-step

매 호출 전 다음 4-step 으로 변형 선택. catalog 응답이 SSOT.

1. **`af workflow recommend "<task 자연어>"`** → top 3 후보 + score + `not_for_warnings`. ⚠️ **`score` 만 믿지 마라** — 룰 기반이라 한국어/짧은 query 에서 엉뚱한 후보가 #1 로 올라오는 사고 사례 다수 (예: "픽셀 배경 ..." 에 `sprite/hires` 가 #1, "UI 앱 아이콘 flat" 에 `sprite/stage1` 이 #1). 반드시 step 2~3 의 `meta.intent` + `output_layout` 로 검증.
2. **첫 후보의 `meta.intent` 한 줄 + `use_cases`/`not_for`** 으로 적합성 검증
3. **`meta.output_layout.kind`** (`single` / `pose_grid` / `tile_grid` / `character_sheet`) 확인 — *최종 이미지의 그림 구성* 이 사용자가 원하는 형태인가?
4. **`meta.prompt_template.user_slot.examples`** 1개 복사해 *캐릭터 묘사로 변형* → `--subject` 인자로 호출

조합 패턴:
```
recommend → 후보 → not_for_warnings 비어있는 첫 후보 채택
         → catalog meta.output_layout 형태 검증
         → subject 모드 generate 호출
         → 응답의 prompt_resolution.final_positive 로 실 prompt 확인
```

> 자세한 catalog 응답 schema, recommend/search API 디테일, prompt 합성 모드는
> `buck(file_path="references/catalog-and-meta.md")` (한 파일에 통합).

---

## 카테고리 결정 트리 (cheat-sheet)

> 🟢 빠른 reference. 정확한 의도/형태/prompt 는 `recommend` 응답이 SSOT.

| 의도 | 카테고리/변형 | alias |
|---|---|---|
| 게임용 픽셀 캐릭터 (즉시 사용) | `sprite/pixel_alpha` ⭐ | `@character` |
| 게임 캐릭터 디테일 보강 | `sprite/hires` | — |
| 일러스트풍 캐릭터 (배경 알파) | `sprite/rembg_alpha` | — |
| 비교용 (5장 한 번에) | `sprite/full` | — |
| 마케팅·표지 일러스트 (단일) | `illustration/animagine_hires` | `@marketing` |
| Pony 스타일 일러스트 | `illustration/pony_hires` | — |
| 픽셀 타일/배경 | `pixel_bg/*` | — |
| UI 아이콘 (flat) | `icon/flat` | — |
| 임시 스캐치 1장 | `@sketch` (bypass 자동) | `@sketch` |

> sprite/* 모두 1×3 multi-pose 시트 — 단일 이미지 필요하면 `illustration/*`. 자세한 변형 비교는 `buck(file_path="references/variant-quick-table.md")`.

---

## 승인 모드 (`approval_mode`)

| 모드 | 호출 | 용도 |
|---|---|---|
| `manual` (default) | 플래그 없음 | 사람 cherry-pick 승인. 게임 자산·로고 등 *실제로 들어갈* 에셋 |
| `bypass` | `--bypass-approval` | 사람 승인 무의미한 임시물. 시뮬·스캐치·chain 중간물 |
| `auto` (예약) | `--auto-approve` | (서버가 신뢰 점수로 자동 승인 — 향후) |

**Bypass 사용 규칙**:
- project 명을 `tmp_*` 또는 `sim_*` 로 (namespace 격리)
- `af list <project>` 에 안 보임. `--include-bypassed` 로만 노출
- `af export --manifest` 에 안 묶임 (승인본 아님)
- 보존 기간: `af health` 의 `bypass_retention_days`. 그 후 GC
- **인증은 동일** — 승인 우회지 인증 우회 아님

선택 가이드: 게임 자산 → `manual` / 시뮬 100장 → `bypass` / chain 중간물 → 항상 `bypass`

---

## 동적 입력 / 프롬프트 디테일 / Paperclip 워크플로

본 SKILL 의 핵심은 *변형 선택 + subject 모드 호출* 만 다룬다. 아래는 케이스별 reference:

| 필요 | 파일 |
|---|---|
| catalog 응답 schema 전체 jsonc / recommend·search API 상세 / prompt_template 합성 디테일 / tag 컨벤션 | `buck(file_path="references/catalog-and-meta.md")` |
| 모든 REST endpoint + curl 예제 + OpenAPI | `buck(file_path="references/api.md")` |
| PoseExtract / ControlNet chain (사용자 사진 → 포즈 추출 → 캐릭터 합성) | `buck(file_path="references/dynamic-inputs.md")` |
| 변형별 cheat-sheet (sprite 10종, illustration 10종 비교) | `buck(file_path="references/variant-quick-table.md")` |
| 프롬프트 작성 노하우 (속성 보호, 시리즈 통일, 다인원, legacy 모드) | `buck(file_path="references/prompt-craft.md")` |
| Paperclip 이슈 받았을 때 워크플로 | `buck(file_path="references/paperclip-flow.md")` |

---

## Pitfalls

1. **SD/ComfyUI 직접 호출 절대 금지**. ComfyUI(`192.168.50.225:8188`) URL 알아도 손대지 않음 — 모든 호출은 `af` 만. 카탈로그·이력·승인·GC 일관성 유지. 진단 시 `/api/comfyui/health` / `/api/comfyui/catalog` curl 은 OK (`references/api.md` 참고).
2. **PIL 로 이미지 직접 생성 금지** — 가짜 에셋. 과거 HoD 해고 사례.
3. **Vision tool 로 후보 N장 평가 금지** — 토큰 낭비. 사람 cherry-pick UI 가 표준.
4. **다인원 캐릭터는 별도 asset_key 로 단독 생성** — 한 이미지에 3명 이상은 attribute bleeding 거의 확정.
5. **`--bypass-approval` 을 게임 자산에 쓰지 마라** — 정식 export 에 안 묶임. 시뮬/스캐치/chain 중간물에만.
6. **chain 중간물의 `tmp_*` 격리** — bypass 자산은 `tmp_*` / `sim_*` project 로. 정식 project 에 섞으면 `af list` 가 지저분.
7. **변형 사용 가능 여부**: catalog 의 `available: false` 는 호출 불가 (registry 의 `status: needs_api_conversion`).
8. **multi-output 의 cherry-pick**: `sprite/full` 같은 변형은 1 candidate slot 에 N장. UI 는 **primary** 만 보여주고 나머지는 metadata 동봉.
9. **`--input` 라벨 오타**: catalog 에 없는 라벨 박으면 `report.skipped` 에 기록되고 *조용히* 무시. `--dry-run` 으로 사전 점검 (⏳ 미구현 시 작은 변형 candidates=1 실 호출).
10. **chain 의 `run_id` 보관**: `gen` 응답의 `run_id` 잡아둬야 다음 단계에서 `run:<run_id>/<output>` 참조 가능.
11. **변형별 회귀 격리**: 한 변형이 1~2초만에 fail + `error_message: null` + 빈 `assets` → *다른 변형으로 즉시 회귀 격리*. `sprite/pixel_alpha` 정상 동작이면 서버 OK. 깨진 변형은 PR/이슈로 보고. 진단에 5분 이상 소진 금지.
12. **변형 의도(layout) 무시 금지** — 호출 전 *반드시* `meta.output_layout.kind` 확인. `pose_grid` 인데 단일 일러스트 의도면 결과 안 나옴 (실 사고 사례: `sprite/pixel_alpha` 를 *학교 복도 씬* 1장 의도로 잘못 호출 → 캐릭터 2명 그려진 학교 복도). **회피 휴리스틱**: 변형 호출 전 1초 셀프체크 — *"이 변형이 만드는 최종 이미지 구성이 사용자가 원하는 것과 일치하나? 단일 vs 그리드, 캐릭터 수, 배경 유무?"*
13. **`subject` 모드 가이드** — `meta.prompt_template.user_slot.description` 따른다 (캐릭터 묘사만, 스타일/배경 묘사 금지, `(chibi:1.4)` 같은 가중치 금지). 변형이 박은 base_positive 와 *중복 묘사* 하지 마라 (영향 거의 없고 토큰 낭비).
14. **`base_negative` override 금지** — 사용자 `negative_prompt` 는 *append 만*. 변형이 박은 필수 negative (예: `floating sword, detached weapon` — sprite/pixel_alpha) 는 안전 정책상 override 불가.

---

## 회귀·실패 진단

```
af workflow gen X/Y ... --wait   →  failed_count=1, error_message=null
                                          │
                                          ▼
[1] 다른 변형으로 회귀 격리 (1분, decisive)
    af workflow gen sprite/pixel_alpha tmp_diag diag1 \
        --subject "1girl, ..." --candidates 1 --bypass-approval --wait
    - 성공 → 서버 OK, *해당 변형* 만 깨짐 → 별도 이슈로 보고하고 동작하는 변형으로 진행
    - 실패 → 서버/ComfyUI 연결 의심 → [2]
                                          │
                                          ▼
[2] ComfyUI 까지 prompt 가 도달했나?
    curl -s 'http://192.168.50.225:8188/history?max_items=20' -o /tmp/h.json
    - 있다 → ComfyUI 측 점검 (ckpt? object_info?)
    - 없다 → asset-factory 가 patch/build/dispatch 단계서 조용히 실패
                                          │
                                          ▼
[3] 추가 단서 — `~/workspace/asset-factory/data/server.log` (uvicorn access 만, 백그라운드 task 의 stderr 는 안 잡힘)
    + `curl http://192.168.50.225:8188/object_info` 로 노드 클래스 등록 확인
```

핵심: [1]만으로 *서버 살았는지 / 특정 변형만 깨진 건지* 거의 확정. 회귀 격리 → 보고 → 동작 변형으로 시연 진행. **시연/smoke 가 막히면 안 된다**.

---

## ⚠️ Skill freshness — 미충족 항목

asset-factory NEXT.md §1.A/§1.B/§1.C **모두 채워짐** (PR #30, #38-43 머지본). 미충족은 ⏳ 만:

| 항목 | 상태 | 미충족 시 우회 |
|---|---|---|
| §1.A meta (intent / output_layout / use_cases / not_for / tags) | ✅ 25/25 변형 (PR #30, #38-41) | — |
| §1.A `meta.prompt_template` | ✅ 24/25 (`pose_extract` 제외 — utility) | — |
| §1.A `input_labels.alternatives` | ✅ (PR #30) | — |
| catalog `version: 2` | ✅ (PR #30) | — |
| §1.B 서버 자동 주입 (`subject`, `prompt_resolution`, `prompt_mode: auto/subject/legacy`) | ✅ (PR #42) | — |
| §1.C `POST /api/workflows/recommend` (자연어 + score + warnings) | ✅ (PR #43) | — |
| §1.C `GET /api/workflows/search` (tag + not filter) | ✅ (PR #43) | — |
| `--bypass-approval` / `input_labels` / `af workflow upload` / `--input` 통합 | ✅ (PR #18) | — |
| `--dry-run` | ⏳ 미충족 | 작은 변형 candidates=1 실 호출. 라벨 오타는 `report.skipped` 로 확인 |
| `aliases` (`@character` 등) | ⏳ 미충족 | full path (`sprite/pixel_alpha`) 로 호출 |
| `run:<run_id>/<output>` syntax | ⏳ 부분 충족 | `--input source_image=asset:<id>` 로 chain. 특정 output 참조는 `af list <project>` → metadata 매칭 |

---

## Related skills

- `paperclip-api` — Paperclip 이슈 컨텍스트로 호출될 때 같이 로드
- `aseprite-build` — 생성된 sprite 시트를 Aseprite 에서 후처리 (split, palette 조정)
