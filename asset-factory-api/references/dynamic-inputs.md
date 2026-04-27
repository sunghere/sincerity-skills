# 동적 입력 (PoseExtract / ControlNet) — Reference

> SKILL.md 본문에서 분리. chain 시나리오 (사용자 사진 → 포즈 추출 → 캐릭터 합성) 일 때만 본다.

---

## 동적 입력 라벨

특정 변형은 사용자 이미지를 입력으로 받는다. 어떤 변형이 어떤 라벨을 받는지는 catalog 의 `input_labels` 에 명시:

```jsonc
// af workflow describe sprite/pose_extract
{
  "input_labels": [
    {
      "label": "source_image",
      "required": true,
      "description": "Pose 추출할 원본 이미지",
      "alternatives": []
    },
    {
      "label": "pose_image",
      "required": false,
      "default": "pose_grid_1x3_mini_2.5h_1280x640.png",
      "alternatives": [...]
    }
  ]
}
```

→ `--input <label>=<source>` 형식으로 박는다. `<source>` 3가지:

| 형식 | 의미 |
|---|---|
| `@./local.png` | 로컬 파일 — 자동 업로드 |
| `<asset_id>` | 기존 에셋 (UUID 직접) |
| `run:<run_id>/<output_label>` | 이전 run 의 특정 출력 (chain 표준 — ⚠️ server-side 미구현, asset_id 직접 룩업으로 우회) |

---

## chain 표준 패턴 — 사용자 사진 → 포즈 추출 → 캐릭터 합성

```bash
# 1) 포즈 추출 (사용자 사진 → OpenPose stick figure)
af workflow gen sprite/pose_extract pj_chain step1 \
   --subject "extract pose" \
   --input source_image=@./user_pose.jpg \
   --bypass-approval --wait
# → 응답에 job_id="..." 잡아둠 (chain *입력* syntax `run:<id>/<output>` 은 server-side 미구현)

# 2) 추출된 포즈로 캐릭터 합성
af workflow gen sprite/pixel_alpha pj_chain step2 \
   --subject "knight, blue armor, holding silver sword" \
   --input pose_image=run:run_aaa.../pixel_alpha \
   --wait
```

> chain 중간물(`step1`)은 `--bypass-approval` 권장 — 검수 가치 없는 변환물.

> ⏳ `run:<run_id>/<output>` syntax 부분 충족. 특정 output label 참조는 asset_id 직접 룩업 (`af list <project>` → metadata 매칭) 으로 우회.

---

## 직접 업로드 endpoint

```bash
# 로컬 파일 업로드 (subfolder 지정 가능)
af workflow upload ./pose.png --subfolder asset-factory

# 또는 multipart REST
curl -X POST http://localhost:47823/api/workflows/inputs \
  -H "x-api-key: $API_KEY" \
  -F "file=@./pose.png" \
  -F "subfolder=asset-factory"

→ {"name": "pose_a1b2.png", "subfolder": "asset-factory"}
```

응답의 `name` 을 generate 의 `workflow_params.load_images.<label>` 에 박아 사용.

### 기존 asset → input 재업로드

```bash
# 기존 asset 의 image_path 를 ComfyUI input/ 으로 복사
curl -X POST http://localhost:47823/api/workflows/inputs/from-asset \
  -H "x-api-key: $API_KEY" \
  -d '{"asset_id": "uuid-...", "subfolder": "asset-factory"}'
```

PoseExtract 결과를 다른 워크플로우의 ControlNet 입력으로 chain 시 사용. 1차에선 chain 자동화 안 함 — 사용자가 명시적으로 asset_id 전달.

---

## 보안·검증 (서버측 자동)

업로드 시 자동 적용:

- **content-type whitelist** (PNG/JPEG/WEBP) — 1차 cheap 거부
- `MAX_INPUT_BYTES` 상한 (기본 ~16MB; env-var `ASSET_FACTORY_MAX_INPUT_BYTES`) — 413
- **이미지 정화** (`_decode_and_reencode_image`) — polyglot trailing strip + 메타 정화 + DecompressionBomb 캐치
- `_safe_subfolder` / `_safe_input_filename` — path traversal / 비-whitelist 문자 정규화

→ ComfyUI 로 forward 되는 bytes 는 *재인코딩된 정화본* (원본 sha256 과 다를 수 있음).

---

## Pitfalls (chain 전용)

1. **`--input` 라벨 오타**: catalog 에 없는 라벨 박으면 `report.skipped` 에 기록되고 *조용히* 무시. `--dry-run` (⏳ 미구현) 또는 작은 변형 candidates=1 실 호출로 검증.
2. **`job_id` 보관**: `gen` 응답의 `job_id` 잡아둬야 잡 추적/cherry-pick 가능. *chain 입력* 표준 syntax `run:<run_id>/<output>` 는 server-side 미구현 — 현재는 `--input source_image=<asset_id>` 로 우회 (`af list <project>` → 원하는 출력 라벨 매칭).
3. **chain 중간물 격리**: `tmp_*` / `sim_*` project 로 모은다. 정식 project 에 섞으면 `af list` 가 지저분 + cherry-pick 큐에 무의미한 중간물 쌓임.
4. **PoseExtract 결과는 stick figure**: 사람이 보면 의미 없는 흑백 라인 — *정상 동작*. ControlNet 노드만 이걸 해석.
5. **`pose_image` alternatives 활용**: catalog 의 `alternatives` 에 1×3, 1×4, 3×3 grid 가 명시됨. 등신·포즈 수 변경 시 alternative 만 바꿔도 OK (full path 다시 업로드 불필요).
