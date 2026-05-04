# af CLI default AF_HOST 47823 — 운영/테스트 포트 분리 명시화

## 한 줄 요약

`af` CLI 의 `AF_HOST` default 를 운영 포트 (47823) 로 변경 + SKILL.md 에 base URL
정책 (운영 47823 / 테스트 8000) 표 명시. 에이전트가 default 호출로 dev 인스턴스
(8000) 에 작업하던 사고 차단.

## 증상

Asset Factory 메인 서버는 `0.0.0.0:47823` (LAN-facing) 으로 띄워져 있고 멍멍과 외부
LAN/Tailscale 클라이언트가 모두 그 포트로 접근. 그런데 `af` CLI 의 `AF_HOST`
default 가 `http://localhost:8000` 이라, 환경변수 없이 `af workflow gen ...` 한
에이전트가 *테스트 / dev 인스턴스 (8000)* 로 가는 상황. 메인 DB / 큐와 별개라
"에이전트가 작업했는데 멍멍 화면에 안 보임" 류의 사고 가능.

`asset-factory-api/references/api.md` 의 모든 curl 예시는 이미 `:47823` 으로
적혀있어, *문서와 CLI default 가 모순* 인 상태였음.

## 원인

- `asset-factory-api/scripts/af.mjs:36` — `AF_HOST || "http://localhost:8000"` (dev 시절 default 가 화석화)
- `asset-factory-api/scripts/af.mjs:30` 주석 — 같은 default 를 안내
- `asset-factory-api/scripts/af.mjs:356` help string — 같은 default 를 안내
- `asset-factory-api/SKILL.md` — base URL 정책 자체가 명시 안 됨 → 정합성 가드 없음

## 수정

- `scripts/af.mjs:36` default `:8000` → `:47823` (운영 메인)
- 주석 / help string 에 "운영 메인 / 테스트는 :8000 명시 override" 안내 추가
- `SKILL.md` `## REST API` 섹션 직후에 "Base URL — 운영 vs 테스트 분리" 표 추가
  (운영 47823 / 테스트 8000 / 사고 사유 한 줄)
- `version: 9 → 10`

## 검증

- `grep localhost:8000 asset-factory-api/` → 의도된 테스트 안내 2건만 남음 (af.mjs L33, L356)
- `grep localhost:47823 asset-factory-api/` → 23건 (af.mjs 3 + dynamic-inputs.md 2 + api.md 18) 모두 일치
- 기존 `af` 호출자가 명시적으로 `AF_HOST=http://localhost:8000` 를 박아둔 케이스는
  영향 없음 (override 그대로 동작). default 만 변경.

## scope 밖 / 후속

본 PR 은 sincerity-skills 측 정합 (Step B). asset-factory 본체 측 정합은 별 PR (Step A):
- `~/workspace/asset-factory/run-dev.sh` default port 8000 → 47823 + status 표시 버그 fix
- `~/workspace/asset-factory/AGENTS.md` §9 운영/테스트 표 갱신
- 로컬 `~/.hermes/skills/devops/asset-factory-admin/SKILL.md` (운영 관리) 의
  `127.0.0.1:8000` 경로 갱신

## Related

- 직전 PR #19 (cherry-pick URL 정정) — 같은 root cause 계열 (스킬과 실 서버
  endpoint 의 모순). 본 PR 은 호스트 부분.
