# sd-catalog

Asset Factory의 `config/sd_catalog.yml` 메타데이터를 외부에서 큐레이션·버전관리하기 위한 디렉토리.

## 어떻게 쓰는가

### 1) 사용자가 weight/tags/notes 채우기

`sd_catalog.yml`의 `# TODO:` 줄을 직접 수정.
- **모델**: tags(`pixel_art`, `character`, `sdxl`, `sd1.5`, `general`...)와 notes(권장 size, 강점)
- **LoRA**: weight_default(추천값), weight_range(허용 범위), tags, notes
- 추천값 출처: Civitai/HuggingFace 모델카드의 "recommended weight" 섹션

**AI 어시스턴트에 맡기고 싶으면** → [`AUTHORING_PROMPTS.md`](./AUTHORING_PROMPTS.md)의 복붙용 프롬프트 4종(URL 기반 / 이름만 / 텍스트 복붙 / 배치 정리) 참조.

### 2) git push

```bash
cd ~/workspace/sincerity-skills
git add sd-catalog/sd_catalog.yml
git commit -m "sd-catalog: tune <name> weight"
git push
```

### 3) asset-factory가 이 파일을 보게 (한 번만 설정)

asset-factory 서버 기동 시 환경변수 `SD_CATALOG_PATH`를 이 파일로:

```bash
SD_CATALOG_PATH=~/workspace/sincerity-skills/sd-catalog/sd_catalog.yml \
  ~/workspace/asset-factory/run-dev.sh restart
```

또는 `~/workspace/asset-factory/run-dev.sh`의 `nohup` 라인 앞에 `export SD_CATALOG_PATH=...` 추가.

### 4) 다른 머신에서 동기화

`git pull` 한 번이면 됨. asset-factory 재시작 불필요 — server.py가 매 catalog 호출마다 yaml을 다시 읽음 (`catalog.py:load_metadata()` 호출).

## 키 매칭 규칙 (catalog.py)

asset-factory 측 정규화:
- lowercase
- 확장자 제거 (`.safetensors`, `.ckpt`, `.pt`)

따라서 yaml 키도 동일하게 lowercase + 확장자 없이 작성.

예: A1111 LoRA 파일명 `Pixel-Art-XL_v1.1.safetensors` → yaml 키 `pixel-art-xl_v1.1`

## 골격 갱신 (새 LoRA 추가 시)

SD 서버에 새 LoRA를 넣고 a1111을 refresh한 뒤:

```bash
curl http://localhost:8000/api/sd/catalog/loras | jq -r '.items[].name' | sort > /tmp/loras.txt
# 기존 yaml과 diff해서 빠진 키만 추가
```

또는 골격 재생성 스크립트(현재 미작성, 필요시 추가).

## 미매칭 항목의 동작

`config/sd_catalog.yml`(또는 `SD_CATALOG_PATH`)에 키가 없는 모델/LoRA는 카탈로그 응답에서 안전 기본값으로 채워짐:
- `weight_default: 0.7`
- `weight_range: [0.0, 1.0]`
- `tags: []`, `notes: null`, `has_metadata: false`

`has_metadata` 필드로 큐레이션 여부 판별 가능.
