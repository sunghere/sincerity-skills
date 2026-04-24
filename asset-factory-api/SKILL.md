---
name: asset-factory-api
version: 2
description: "Asset Factory로 게임 픽셀아트 에셋 생성. `af` CLI 한 줄로 단일/배치 생성·폴링·다운로드. SD/jq/curl 직접 사용 금지."
triggers:
  - asset factory
  - asset-factory
  - 에셋 팩토리
  - 픽셀아트 생성
  - 게임 에셋
  - 스프라이트 생성
  - cherry-pick
---

# Asset Factory

게임 픽셀아트 에셋 생성 파이프라인. **`af` CLI로 모든 작업 처리**, 에이전트는 명령 한두 줄만.

## When to use

픽셀아트 캐릭터/스프라이트/UI 아이콘이 필요할 때, 또는 같은 에셋의 여러 후보를 뽑아 사람이 cherry-pick하고 싶을 때.

## When NOT to use

1회성 비픽셀 이미지, 즉시 1장만 보고 싶을 때 → `generate-asset` CLI 직접 사용.

## CLI: `af` (이게 전부다)

설치 위치: `~/.local/bin/af` (NodeJS, deps 없음). 자세한 옵션은 `af --help`.

```bash
# 1. 점검
af health                              # 서버 + SD 연결 OK인지
af catalog models                      # 사용 가능한 모델
af catalog loras                       # LoRA + 권장 weight

# 2. 단일 생성 (가장 자주 씀)
af gen <project> <asset_key> "<prompt>" --size 64 --wait \
       --negative "background, blurry" --model pixelArtDiffusionXL_spriteShaper

# 3. 디자인 배치 — 여러 후보, 사람이 cherry-pick
af batch <project> <asset_key> \
   --prompts "p1" "p2" --models pixelArtDiffusionXL_spriteShaper \
   --seeds 4 --size 64 --wait
# 끝에 cherry-pick URL이 출력됨 — 사용자에게 그대로 전달

# 4. 결과 가져오기
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

## 모델 선택

`af catalog models`로 확인. 픽셀아트 게임 에셋은 **`pixelArtDiffusionXL_spriteShaper` 기본**. 시리즈/브랜드는 한 모델로 통일하고 다양성은 `--seeds`로 확보 (모델 섞으면 한 세트로 안 읽힘).

## Pitfalls

1. **에이전트는 SD API(`192.168.50.225:7860`) 직접 호출 금지** — 카탈로그·이력·검증·승인 일관성 깨짐. 항상 `af`만 사용.
2. **PIL로 이미지 직접 생성 금지** — 가짜 에셋. 과거 HoD 해고 사례.
3. **Vision tool로 후보 N장 평가 금지** — 토큰 낭비. 사람이 cherry-pick UI에서 보는 게 표준.
4. **다인원 캐릭터는 별도 asset_key로 단독 생성** — 한 이미지에 3명 이상은 attribute bleeding 거의 확정.
5. **`--wait` 타임아웃**: 단일 5분, 배치는 task당 ~6초. `--timeout N` 으로 조정.
6. **`af gen`의 결과가 1024x1024 raw인 경우** — 후처리(Aseprite shrink/투명화)가 generate 단일 경로에 빠져있을 수 있음. validation_status=fail이면 `af export`로 빼서 직접 처리하거나 `af batch` 경로 사용.

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
