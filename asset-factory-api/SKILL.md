---
name: asset-factory-api
version: 1
description: "Asset Factory REST API로 게임 픽셀아트 에셋을 요청한다. JSON 스펙만 던지면 SD 생성·검증·갤러리·승인까지 서비스가 자동 처리. 에이전트는 polling으로 결과만 확인 (토큰 비용 ≈ 0). SD API 직접 호출 대체."
triggers:
  - asset factory
  - asset-factory
  - 에셋 팩토리
  - 픽셀아트 생성
  - 게임 에셋
  - 스프라이트 생성
  - sprite generation
  - design asset
  - cherry-pick
---

# Asset Factory API

게임 픽셀아트 에셋 생성 파이프라인. **에이전트는 JSON 스펙만 제출하고 polling**, 실제 SD 호출·검증·후처리·승인 UI는 서비스가 처리한다.

## When to use

- 픽셀아트 캐릭터/스프라이트/UI 아이콘이 필요할 때
- 같은 에셋의 여러 후보를 뽑고 사람이 cherry-pick 하고 싶을 때
- 게임 프로젝트에 일관된 스타일로 다량 에셋을 채워야 할 때

## When NOT to use

- 1회성 비픽셀 이미지 (제품 일러스트 등) → SD API 직접 호출이 더 빠름
- 콘셉트 탐색/즉시 1장만 보고 싶음 → 그냥 generate-asset CLI

## 서버 정보

- **Base URL**: `http://localhost:8000` (페이퍼클립 에이전트는 같은 Mac mini에서 동작 → localhost로 충분)
  - LAN 다른 머신에서 호출하려면 `http://192.168.50.250:8000` (Mac mini LAN IP)
  - Tailscale: `http://yoons-macmini.tailbff496.ts.net:8000` 또는 `http://100.72.190.122:8000`
  - 환경변수 `AF_HOST` 있으면 그걸 우선
  - ⚠️ 서버를 LAN에 노출하려면 `AF_HOST=0.0.0.0 ./run-dev.sh restart`로 재기동 필요 (기본 127.0.0.1)
- **API Key**: `.env`의 `API_KEY`. 변경(POST/PATCH)은 `x-api-key` 헤더 필요. 미설정 환경은 모두 공개.
- **백엔드 SD**: AUTOMATIC1111 `192.168.50.225:7860` (Asset Factory가 알아서 호출 — **에이전트는 SD 직접 안 침**)
- **Web UI**: `/app/` (사람이 후보 갤러리에서 승인/리젝)
- **헬스체크**: `GET /api/health`, `GET /api/health/sd`

## 핵심 워크플로 (3 패턴)

### 패턴 A — 단일 생성 (1 asset, 1 candidate)

```bash
JOB=$(curl -s -X POST "${AF:-http://localhost:8000}/api/generate" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $AF_API_KEY" \
  -d '{
    "project": "wooridul-factory",
    "asset_key": "kitten_idle",
    "category": "character",
    "prompt": "pixel art, cute orange tabby kitten, idle pose, transparent background, clean edges",
    "negative_prompt": "background, scenery, blurry, jpeg artifacts",
    "expected_size": 64,
    "max_colors": 32
  }' | jq -r .job_id)

# polling — 토큰 비용 0
while :; do
  S=$(curl -s "${AF:-http://localhost:8000}/api/jobs/$JOB" | jq -r .status)
  case "$S" in
    completed|failed) break ;;
  esac
  sleep 3
done
```

### 패턴 B — 디자인 배치 (여러 후보, cherry-pick) ⭐ 권장

같은 asset에 대해 prompts × models × loras × seeds 곱집합으로 후보를 풀고, 사람이 UI에서 베스트 1장을 골라 메인 승격하는 흐름. 캐릭터 컨셉 픽업·아이콘 시리즈에 최적.

```bash
RESP=$(curl -s -X POST "${AF:-http://localhost:8000}/api/mcp/design_asset" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $AF_API_KEY" \
  -d '{
    "project": "wooridul-factory",
    "asset_key": "warrior_idle",
    "category": "character",
    "prompts": [
      "pixel art warrior, sword and shield, idle pose, transparent background",
      "pixel art knight, full plate armor, idle pose, transparent background"
    ],
    "models": ["pixelArtDiffusionXL"],
    "loras": [
      [{"name": "pixel-art-xl-v1.1", "weight": 0.7}]
    ],
    "seeds_per_combo": 4,
    "common": {
      "steps": 28, "cfg": 7.0, "sampler": "DPM++ 2M",
      "expected_size": 64, "max_colors": 32, "max_retries": 3
    }
  }')
BATCH_ID=$(echo "$RESP" | jq -r .batch_id)
JOB=$(echo "$RESP" | jq -r .job_id)
echo "후보 수: $(echo "$RESP" | jq -r .expanded_count) / ETA: $(echo "$RESP" | jq -r .estimated_eta_seconds)s"
echo "사람에게 알림: http://localhost:8000/cherry-pick?batch=$BATCH_ID"
```

폴링은 패턴 A와 동일. 완료되면 사용자에게 cherry-pick URL 전달하고 종료. **사람이 UI에서 승인 → 메인 에셋으로 자동 승격 → asset_history에 이전 버전 보존**. 에이전트가 후보 이미지 비교를 직접 할 필요 없음.

### 패턴 C — 스펙 파일 기반 대량 생성

`specs/<project>.json` 파일을 미리 두고:

```bash
curl -s -X POST "${AF:-http://localhost:8000}/api/generate/batch" \
  -H "Content-Type: application/json" \
  -H "x-api-key: $AF_API_KEY" \
  -d '{"spec_id": "wooridul-factory"}'
```

스펙에 `"generation_config.candidates_per_asset": 4`를 두면 자산마다 4장씩.

## Polling 패턴 (필수 숙지)

`GET /api/jobs/{job_id}` 응답 필드:
- `status`: `pending` / `running` / `completed` / `failed`
- `total_count`, `completed_count`, `failed_count`
- `error_message`

**규칙**:
- 첫 polling 5초 후, 이후 3~5초 간격
- 단일: 30초~2분, 배치: task당 ~6초 (응답의 `estimated_eta_seconds` 참고)
- `status == "failed"`면 `error_message` 확인하고 사용자에게 보고
- timeout 한계: 단일 5분, 배치 (task_count × 15초) 권장

## 카탈로그 활용 — spec 짜기 전에

```bash
# 사용 가능한 모델 (pixel/anime/general 등 tags 포함)
curl -s "${AF:-http://localhost:8000}/api/sd/catalog/models" | jq '.[] | {name, tags, notes}'

# LoRA + 권장 weight
curl -s "${AF:-http://localhost:8000}/api/sd/catalog/loras" | jq '.[] | {name, weight_default, weight_range, tags, notes}'
```

`config/sd_catalog.yml`에 정리된 메타가 머지돼서 응답됨 — 어느 모델이 픽셀아트 강한지, LoRA 권장 weight가 얼마인지 여기서 확인하고 spec 짜기.

## 픽셀아트 프롬프트 노하우 (Asset Factory에 적용)

> 출처: 기존 `stable-diffusion-api` 스킬 운영 경험 압축. SD 직접 호출이 아닌 Asset Factory를 쓰더라도 **프롬프트 품질은 에이전트 책임**이므로 동일 원칙 적용.

### 1. 픽셀아트 기본 토큰

```
필수 prefix: "pixel art, "
배경 투명: "transparent background, isolated, no background, clean edges"
스타일 강화: "sharp pixels, retro game asset, 16-bit / 32-bit style"
```

### 2. Negative prompt 표준 세트

```
"background, scenery, gradient background, color fill,
 blurry, jpeg artifacts, anti-aliased, smooth shading,
 3d render, photo, realistic"
```

### 3. 캐릭터 일관성 — 속성 보호

특정 색/스타일을 유지하려면 **경쟁 속성을 negative에 명시적으로 차단**:

- 실버 헤어 유지: `pink hair, gold hair, brown hair, red hair, blue hair, green hair`
- 긴 머리 유지: `short hair, bob, buzz cut`
- 특정 눈색: `red eyes, blue eyes, brown eyes` (원하는 색만 빼고 다)

체감 유지율 20~30% 향상.

### 4. 다인원 캐릭터 — Attribute Bleeding 회피

**규칙: 한 이미지에 3명 이상 절대 X**. 캐릭터마다 별도 asset_key로 단독 생성 후 합성하는 게 가장 확실.

2인 이하라도 BREAK 구문 + 위치 키워드 + 가중치 1.5:

```
2girls, group portrait,
BREAK
leftmost girl: (long pink twintails:1.5), blue ribbons, ...
BREAK
rightmost girl: (short black bob:1.6), green eyes, ...
```

### 5. 시리즈/브랜드 통일 — 단일 모델 고정

여러 스타일 모델 섞으면 한 세트로 안 읽힘. **브랜드 캐릭터 묶음은 모델 1개로 고정**, 다양성은 prompt 변주 + seed 랜덤으로 확보.

### 6. 모델별 토큰 문법

- **meinamix, dreamshaper (SD1.5)**: `masterpiece, best quality, ...` + BREAK 지원
- **ponyDiffusionV6XL**: `score_9, score_8_up, score_7_up, source_anime` 접두 필수, Danbooru 태그
- **pixelArtDiffusionXL**: 자연어 길어도 OK, BREAK 지원, 픽셀 게임 에셋 최적

## 결과 확인 / 사람에게 전달

### 후보 이미지 직접 비교 금지

**Vision tool로 후보 N장을 평가하지 말 것** — 토큰 낭비. 사용자가 UI에서 직접 보는 게 빠르고 정확.

올바른 패턴:
1. 패턴 B로 batch enqueue
2. polling으로 completed 확인
3. 사용자에게 한 줄로 보고: `cherry-pick URL: http://localhost:8000/cherry-pick?batch=<id> — 후보 N장 준비됨`
4. 종료. 평가는 사람이.

예외: OCR·수치 측정 같은 정량 검증이 꼭 필요한 경우만 vision 사용.

### 단일 generate 결과 받아오기

자동 승인이 필요하면 (사람 cherry-pick 없이):

```bash
ASSET=$(curl -s "${AF:-http://localhost:8000}/api/assets?project=wooridul-factory" \
  | jq -r '.[] | select(.asset_key=="kitten_idle") | .id')

curl -s "${AF:-http://localhost:8000}/api/assets/$ASSET/image" -o ~/workspace/assets/kitten_idle.png
```

또는 export로 일괄 복사:

```bash
curl -X POST "${AF:-http://localhost:8000}/api/export" \
  -H "Content-Type: application/json" -H "x-api-key: $AF_API_KEY" \
  -d '{"project": "wooridul-factory", "save_manifest": true}'
# → ~/workspace/assets/<project>/<category>/<asset_key>.png + asset-manifest.json
```

## 주요 엔드포인트 빠른 참조

| 용도 | Method · Path |
|------|---------------|
| 헬스 / SD 연결 | `GET /api/health`, `GET /api/health/sd` |
| 모델/LoRA 카탈로그 | `GET /api/sd/catalog/{models,loras}` |
| 단일 생성 | `POST /api/generate` 🔑 |
| 스펙 파일 배치 | `POST /api/generate/batch` 🔑 |
| 디자인 배치 (cherry-pick) | `POST /api/mcp/design_asset` 🔑 ⭐ |
| 잡 상태 polling | `GET /api/jobs/{job_id}` |
| 최근 잡 타임라인 | `GET /api/jobs/recent?limit=10` |
| SSE 이벤트 스트림 | `GET /api/events` |
| 에셋 목록/요약 | `GET /api/assets`, `GET /api/assets/summary` |
| 에셋 단건/이미지 | `GET /api/assets/{id}/{detail,image}` |
| 후보 슬롯 목록 | `GET /api/assets/{id}/candidates` |
| 후보 → 메인 승격 | `POST /api/assets/approve-from-candidate` 🔑 |
| 재생성 | `POST /api/assets/{id}/regenerate` 🔑 |
| 검증 (단일/전체) | `POST /api/validate/{id}`, `POST /api/validate/all` 🔑 |
| 실패 일괄 재처리 | `POST /api/batch/{revalidate,regenerate}-failed` 🔑 |
| 디렉토리 → DB 동기화 | `POST /api/projects/scan` 🔑 |
| 승인본 export | `POST /api/export` 🔑, `GET /api/export/manifest` |

🔑 = API Key 필요 (`x-api-key` 헤더), ⭐ = 가장 자주 쓰는 진입점

## Pitfalls

1. **패턴 B에서 `loras`는 2차원 배열** — 바깥 리스트가 "곱집합 한 칸", 안 리스트가 그 칸에 동시 적용할 LoRA들. 단일 LoRA도 `[[{"name":"...","weight":0.7}]]`로 감싸야 함.
2. **`spec_id`는 서버측 `specs/*.json` 파일명** — 에이전트가 임의 파일명 보내면 404. 새 spec 추가는 사용자한테 부탁하거나 인라인 `spec` 필드 사용.
3. **API Key 누락은 401**, 다른 회사 키로는 403. `.env`에 키 없으면 헤더 빠져도 OK.
4. **batch_id ≠ job_id** — cherry-pick UI는 `batch_id`, polling은 `job_id`. 두 값 다 응답에 있음.
5. **completed_count == total_count인데 status가 running** — 워커가 마지막 task 마무리 중. 한 번 더 polling.
6. **expected_size는 SD 생성 해상도가 아닌 "최종 픽셀아트 크기"** — 서버가 SD 1024 → Aseprite shrink → expected_size로 처리. SDXL 모델인데 width/height를 64로 보내면 깨짐. width/height는 비워두고 expected_size만 지정 권장.
7. **picking 직후 polling = 0초** — `created_at`까지 시간 보고 첫 polling은 최소 5초 대기. 즉시 polling은 status가 아직 `pending`이라 의미 없음.
8. **Vision tool로 후보 평가 금지** — 토큰 낭비. cherry-pick URL을 사람에게 전달하는 게 표준.
9. **재생성은 metadata 보존** — `POST /api/assets/{id}/regenerate`는 기존 prompt/steps/cfg/sampler 그대로 다시 SD 호출. 프롬프트 바꾸려면 새 generate 호출하고 select-candidate.
10. **GC가 후보를 지움** — 선택된 후보도 GC 대상. 메인 승격 후 24h 내에 export로 복사하거나 `~/workspace/assets/`에 백업. `GET /api/system/gc/status`로 GC 활동 확인.

## Paperclip 워크플로 (페이퍼클립 직원용)

페이퍼클립 이슈가 "에셋 N장 만들어줘" 형태일 때 표준 흐름:

1. **이슈에서 요구사항 추출** — project, 에셋 종류(character/icon/bg), 수량, 스타일 키워드
2. **카탈로그 GET** — `GET /api/sd/catalog/{models,loras}`로 사용 가능한 자원 확인
3. **spec 작성** — 위 패턴 B (디자인 배치)가 기본. 후보 4~8장으로 충분
4. **`POST /api/mcp/design_asset`** → `batch_id`, `job_id` 받기
5. **이슈에 코멘트** — `cherry-pick URL: http://localhost:8000/cherry-pick?batch=<id>` + ETA
6. **polling** (background) — completed 시 이슈에 다시 코멘트로 알림
7. **사람 승인 후** — 필요시 `POST /api/export`로 프로젝트 디렉토리에 복사

🔴 **금지 사항**:
- SD API (`192.168.50.225:7860`) 직접 호출 — Asset Factory를 통해야 카탈로그·이력·검증·승인이 일관됨
- PIL로 이미지 직접 생성 (가짜 에셋) — 과거 HoD 해고 사례
- Vision tool로 후보 N장 평가 — 토큰 낭비, 사람이 UI로 보면 됨

## Related skills

- `stable-diffusion-api` — SD 직접 호출 (Asset Factory 우회가 필요한 예외 상황만)
- `paperclip-api` — 페이퍼클립 이슈/코멘트/승인 API
- `pixel-art` — 일반 픽셀아트 변환 노하우 (이미지 → 픽셀)
