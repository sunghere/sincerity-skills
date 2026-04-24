# 픽셀아트 프롬프트 노하우 (상세)

> SKILL.md 본문은 핵심 4가지만 다룬다. 이 파일은 까다로운 케이스 대응용.

## 모델별 프롬프트 문법

| 모델 | 접두 토큰 | 특징 |
|------|----------|------|
| `pixelArtDiffusionXL_spriteShaper` | (자연어 OK) | SDXL, 픽셀 게임 에셋 최적, BREAK 지원 |
| `ponyDiffusionV6XL` | `score_9, score_8_up, score_7_up, source_anime` | Danbooru 태그 선호, 캐릭터 강함 |
| `meinamix_v12Final`, `dreamshaper_8` | `masterpiece, best quality` | SD1.5, BREAK 지원 |
| `noobaiXLNAIXL_vPred10Version` | (자연어) | SDXL anime 스타일 |
| `v1-5-pruned-emaonly` | (자연어) | SD1.5 베이스 |

## BREAK 구문 (다인원 / 영역 분리)

A1111이 `BREAK` 토큰으로 프롬프트를 청크 분리. 청크별 attention이 격리돼 attribute bleeding 감소.

```
2girls, group portrait,
BREAK
leftmost girl: (long pink twintails:1.5), blue ribbons, ...
BREAK
rightmost girl: (short black bob:1.6), green eyes, ...
```

가중치 `(...:1.3~1.6)`로 핵심 특징 강조. Negative에 `2girls, 4girls, mixed hair colors, color bleeding, duplicate, twins` 추가.

## 다인원 회피 4단계

| Level | 방법 | 적용 |
|-------|------|------|
| 1 | BREAK + 위치 + 가중치 | 2인 이하 |
| 2 | 인원 축소 (3→2, 별도 1샷) | 안정성 ↑ |
| 3 | **단독 생성 + PIL 합성** | 가장 확실, 캐릭터 100% 보존 |
| 4 | Regional Prompter / ControlNet | 서버 확장 필요 |

**3명 이상은 무조건 Level 3** (별도 asset_key로 단독 생성 후 합성).

## 속성 보호 — 경쟁 속성 차단

원하는 속성을 지키려면 대체 속성을 모두 negative로 명시.

| 지키려는 속성 | Negative에 추가할 것 |
|--------------|---------------------|
| 실버/플래티넘 헤어 | `pink hair, gold hair, brown hair, red hair, blue hair, green hair, purple hair, orange hair` |
| 긴 머리 | `short hair, bob, buzz cut, pixie cut` |
| 특정 눈색 (예: 청록) | `red eyes, blue eyes, brown eyes, green eyes, yellow eyes` (청록만 빼고) |
| 동양인 얼굴 | `western face, european features` |

평범한 `low quality, bad anatomy` negative만 쓸 때 대비 유지율 +20~30%.

## 시리즈/브랜드 통일 — 모델 1개 고정

여러 모델 섞으면 비율·스타일·캐릭터 형태가 제각각이라 한 세트로 안 읽힌다.

- **올바른 패턴**: `--models pixelArtDiffusionXL_spriteShaper` 하나로 고정, prompt 변주 + `--seeds 4`로 다양성 확보
- **잘못된 패턴**: 4개 모델 섞어서 8장 → 사용자가 "통일감 없다" 피드백 보장

## 배경 투명화 (생성 후 처리)

SD가 `transparent background` 줘도 흰색/회색 단색 배경을 그리는 경우가 대부분. Asset Factory의 후처리가 처리해주지만 빠진 경우 수동:

```bash
# /tmp/in.png → /tmp/out.png (외곽에서 flood fill, 내부 동색 보존)
floodfill-bg-remove /tmp/in.png --outdir /tmp/
```

배경이 그래디언트거나 주체와 연결돼 있으면 flood fill 불가 → SD 재생성:
- Prompt: `transparent background, isolated on transparent, no background, clean edges`
- Negative: `background, scenery, color fill, gradient background`

## 가짜 에셋 판정 (메타데이터 + 비전)

에이전트가 PIL로 사각형 합성해 "생성 완료" 보고하는 패턴 방지.

1. **파일 크기**: 32x32 PNG ≥ 1KB 정상, <500B 강력 의심 (단, 스프라이트시트는 예외)
2. **색상 수**: PIL `Image.getcolors(65536)` 결과 ≤10개 + 단색 면적 큼 → 의심
3. **확정**: vision tool로 "SD 생성인가 PIL 합성인가" 판정

## 결과는 사용자에게 직접 보게 할 것

`puma`/vision tool로 후보 N장을 일일이 평가하지 말 것 — 토큰 낭비. `af batch --wait`의 출력에 나오는 `cherry-pick URL`을 사용자에게 한 줄로 전달하고 종료. 평가는 사람이.

예외: OCR·수치 측정처럼 정량 검증이 꼭 필요한 경우만.
