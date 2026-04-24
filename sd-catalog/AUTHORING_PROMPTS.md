# sd_catalog.yml 작성 도우미 프롬프트

이 디렉토리의 `sd_catalog.yml`은 SD 모델/LoRA 메타데이터를 사람이 큐레이션하는 파일이다. 항목이 많아질수록 수동 입력이 부담이므로, **AI 어시스턴트(Claude/ChatGPT 등)에게 맡기는 표준 프롬프트**를 이 문서에 정리해둔다.

---

## 사용 방법

1. 아래 프롬프트 중 상황에 맞는 것을 복사
2. `<…>` 표시된 부분에 실제 값 채우기
3. AI에 던지기 → YAML 블록 받기 → `sd_catalog.yml`에 병합
4. git commit & push

---

## 프롬프트 A — Civitai/HF 모델카드 URL로 자동 조사

> 사용자가 LoRA 이름과 Civitai/HuggingFace URL만 가지고 있을 때. AI가 페이지를 fetch해서 추천 weight·태그·트리거워드를 뽑아낸다.

```
다음 LoRA/모델을 Asset Factory 카탈로그에 등록하려고 한다. 각 URL을 읽고 sd_catalog.yml 형식의 YAML 블록을 출력해줘.

입력:
- 이름: <파일명에서 확장자 제거, 소문자. 예: pixel-art-xl-v1.1>
  URL: <Civitai 또는 HuggingFace URL>
- 이름: <...>
  URL: <...>

추출 규칙:
1. weight_default: 모델카드의 "recommended weight" / "strength" / 사용 예시에서 가장 자주 나오는 값. 명시 없으면 0.7
2. weight_range: 최소/최대 권장값. 명시 없으면 [0.4, 1.0] (LoRA 일반적 안전 범위)
3. tags: 다음 중 해당되는 것만 선택 — character / style / face / pose / clothing / background / effect / pixel_art / anime / realistic / sdxl / sd1.5 / illustrious / pony / noob
4. notes: 한국어 1~2문장. 핵심 특징, stack 호환성, 주의사항. 트리거 워드 있으면 반드시 포함 (예: `트리거: "masterpiece, cute"`).
5. 추측하지 말 것. 모델카드에 없는 정보는 해당 필드를 생략하거나 notes에 "카드 정보 부족"으로 표기.

출력: YAML 블록만. 설명 불필요. sd_catalog.yml의 `loras:` 아래에 바로 붙여넣을 수 있는 형식.

예시 출력:
```yaml
  pixel-art-xl-v1.1:
    weight_default: 0.8
    weight_range: [0.6, 1.2]
    tags: [pixel_art, style, sdxl]
    notes: "도트 스타일 강제 적용. 트리거: 'pixel art'. 캐릭터 LoRA와 stack 가능(총합 weight 1.5 이하 권장)."
```
```

---

## 프롬프트 B — 이름만 있고 정보 없음 (웹 검색 필요)

> 사용자가 LoRA 파일명만 알고 있을 때. AI가 Civitai/Google 검색으로 모델을 역추적.

```
다음 LoRA들의 추천 weight를 조사해서 sd_catalog.yml YAML 블록을 생성해줘.

LoRA 파일명 (소문자, 확장자 제거):
- <예: pixel-art-xl-v1.1>
- <예: detail_tweaker_xl>
- <예: add_detail>

조사 절차:
1. 파일명으로 Civitai 검색 (https://civitai.com/search/models?query=...)
2. 가장 다운로드 많은 버전의 모델카드 확인
3. "About this version" / "Recommended settings" / 사용 예시 이미지 prompt의 `<lora:name:N>` weight 참조
4. 여러 값이 언급되면 가장 빈도 높은 것. 명시 없으면 0.7
5. 검색 결과 애매하면 Google 검색 (`site:civitai.com "<파일명>"`) 보조

출력 규칙:
- YAML 블록만. `loras:` 아래에 붙여넣을 형식
- 조사 실패한 항목은 `notes: "카드 미확인 — 기본값"`으로 표기하고 weight_default: 0.7, weight_range: [0.4, 1.0]
- 각 항목 뒤에 출처 URL을 주석으로 달아둠 (사용자가 재검증할 수 있게)

예시:
```yaml
  pixel-art-xl-v1.1:
    weight_default: 0.8
    weight_range: [0.6, 1.2]
    tags: [pixel_art, style, sdxl]
    notes: "도트 강제. 트리거 'pixel art'."
  # 출처: https://civitai.com/models/XXXXXX
```
```

---

## 프롬프트 C — 모델카드 텍스트 복붙 (가장 확실)

> 사용자가 브라우저에서 Civitai 페이지를 열어 About/Description 영역을 복사해 가져왔을 때. AI는 외부 fetch 없이 주어진 텍스트만 분석.

```
다음은 Civitai/HuggingFace 모델카드에서 복사한 텍스트다. sd_catalog.yml 항목 하나를 만들어줘.

이름 (yaml 키): <소문자, 확장자 제거. 예: detail_tweaker_xl>
타입: <"lora" 또는 "model">

----- 모델카드 텍스트 -----
<여기에 About / Description / Usage Tips / Version Info 영역 복붙>
----- 끝 -----

추출 항목:
- LoRA인 경우: weight_default, weight_range, tags, notes
- Model인 경우: tags, notes

규칙:
- 추천 weight는 카드에 명시된 숫자만 사용 (추측 금지)
- 여러 값 있으면 "most used" / "recommended" 쪽 우선
- 트리거 워드가 있으면 notes에 반드시 명시
- tags 허용값: character / style / face / pose / clothing / background / effect / pixel_art / anime / realistic / sdxl / sd1.5 / illustrious / pony / noob / general
- notes는 한국어 1~2문장. 권장 size, stack 호환, 주의사항 위주.

출력: YAML 블록만.
```

---

## 프롬프트 D — 배치 정리 (10개 이상 한 번에)

> 기존 yaml에 이미 일부 채워져 있고 `# TODO` 자리만 채우면 되는 상황. AI에 현재 yaml + 정보 소스를 통째로 주고 diff 형태로 받는다.

```
sd_catalog.yml의 `# TODO` 자리만 채워서 최종 버전을 만들어줘.

현재 yaml:
<파일 전체 복붙>

추가 정보 (Civitai URL / 트리거 워드 / 권장값 등):
- <loraname1>: <URL 또는 'weight 0.8, 트리거 X' 형식으로>
- <loraname2>: <...>
- ...

규칙:
- `# TODO:` 코멘트 제거하고 실제 값으로 대체
- 정보 없는 항목은 weight_default 0.7, weight_range [0.4, 1.0], tags []로 두되 notes에 "미조사"
- 기존 작성된 값(채워진 곳)은 절대 변경하지 말 것
- 최종 전체 yaml 출력 (diff 아님)

출력: 완전한 yaml 전체.
```

---

## 실무 팁

### Civitai 페이지에서 뽑아야 할 핵심 3요소

1. **"About this version" 섹션의 "Recommended settings"** — weight와 sampler/CFG 언급
2. **"Showcase" 이미지의 prompt** — `<lora:name:0.8>` 형태로 실전 weight 확인
3. **"Trigger Words"** — 프롬프트에 반드시 들어가야 하는 키워드. notes에 필수 기재.

### weight_range 가이드

카드에 명시 없을 때 타입별 경험칙:

| LoRA 유형 | 기본 범위 | 비고 |
|----------|----------|------|
| character | [0.6, 1.0] | 너무 높으면 다른 특징 묻힘 |
| style | [0.4, 1.2] | 스타일 강제 정도 조절 |
| face / expression | [0.3, 0.8] | stack 시 낮게 |
| detail / enhancer | [0.2, 0.6] | 대체로 낮게 |
| concept / pose | [0.5, 1.0] | 중간 |

### sd_catalog.yml 필드 요약

- `weight_default`: 단독 사용 시 기본 weight
- `weight_range`: UI 슬라이더 범위 또는 안전 범위
- `tags`: 검색·필터용 (자유 리스트, 추천 값 위 참고)
- `notes`: 1~2문장. 트리거 워드 / stack 호환 / 주의사항
- `has_metadata`: 자동 채워짐 (yaml에 키 있으면 true)

### 주의

- **yaml 키는 항상 lowercase + 확장자 제거**. `Pixel-Art-XL_v1.1.safetensors` → `pixel-art-xl_v1.1`
- `af catalog loras`로 실제 SD 서버가 인식한 이름 확인한 뒤 그걸 그대로 키로 사용하는 게 안전
- 매칭 실패 증상: `has_metadata: false`가 응답에 떠있음

---

## 빠른 워크플로 (권장)

```bash
# 1. 현재 SD 서버에 있는 LoRA 이름 목록 확인
af catalog loras | jq -r '.items[] | .name'

# 2. 빠진 키 찾기
diff <(af catalog loras | jq -r '.items[].name | ascii_downcase | sub("\\.(safetensors|ckpt|pt)$";"")' | sort) \
     <(grep -E '^  [a-z0-9_.-]+:$' sd_catalog.yml | sed 's/^  //;s/:$//' | sort)

# 3. 빠진 것만 프롬프트 A/B/C로 채우고
# 4. sd_catalog.yml에 추가

# 5. push
cd ~/workspace/sincerity-skills
git add sd-catalog/sd_catalog.yml
git commit -m "sd-catalog: add <name> weights"
git push

# asset-factory는 다음 catalog 호출 시 자동으로 최신 yaml을 읽음 (재시작 불필요)
```
