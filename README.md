# sincerity-skills

Sincerity (sunghere) 컴퍼니용 Claude/Hermes 스킬 모음. Paperclip GitHub import 호환.

## 등록된 스킬

| Slug | 한 줄 요약 |
|------|-----------|
| `asset-factory-api` | Asset Factory REST API로 게임 픽셀아트 에셋 생성. JSON 스펙만 제출하고 polling. |
| `desire-to-design` | 모호한 창작 욕망을 7단계 대화로 한 페이지짜리 컨셉 문서(CONCEPT.md)로 구체화. |
| `improve-codebase-architecture` | 코드베이스에서 deepening 기회를 찾아 모듈을 깊게 만드는 리팩터 제안. (mattpocock/skills v1) |
| `ubiquitous-language` | 대화에서 DDD 유비쿼터스 언어 글로서리를 추출해 UBIQUITOUS_LANGUAGE.md 로 저장. (mattpocock/skills v1) |

## 구조 규약

각 스킬은 루트의 디렉토리 하나로 표현되며, 최소 `SKILL.md` 한 파일을 가진다.

```
<slug>/
  SKILL.md        # YAML frontmatter (name, version, description, triggers) + 본문
  references/     # 선택: 참조 문서
  scripts/        # 선택: 도구 스크립트
  templates/      # 선택: 보일러플레이트
```

`SKILL.md` frontmatter:

```yaml
---
name: <slug와 동일>
version: <정수, 시작은 1>
description: "한 줄 설명 (Paperclip UI/카탈로그에 노출됨)"
triggers:
  - 자연어 키워드
  - 영문/한글 둘 다
---
```

## Paperclip 등록

1. UI: Skills → Add → GitHub repo
2. URL: `https://github.com/sunghere/sincerity-skills`
3. 등록 후 회사의 모든 스킬에 `sunghere/sincerity-skills/<slug>` 키로 노출
4. `paperclip-skill-update` 스킬로 capability 매핑 추가하고 직원에게 배포

## 로컬 배포 — `skillctl`

`scripts/skillctl.py` — Python stdlib only (의존성 0). Claude Code, Codex, Hermes(다중 프로파일)에 symlink 기반으로 배포한다. `git pull` 만 하면 모든 타겟이 자동으로 최신 상태가 된다.

### 빠른 시작

```bash
# 어떤 타겟이 감지됐는지 확인
python3 scripts/skillctl.py targets

# 어떤 스킬이 어디에 있는지 매트릭스로 확인
python3 scripts/skillctl.py status

# 한 스킬을 한 Hermes 프로파일에 배포
python3 scripts/skillctl.py deploy improve-codebase-architecture --target hermes:deepkkumi

# 모든 스킬을 모든 Hermes 프로파일 + Claude + Codex 에 일괄 배포
python3 scripts/skillctl.py deploy --all -t hermes:* -t claude -t codex

# 제거
python3 scripts/skillctl.py undeploy ubiquitous-language -t hermes:paperclip

# 깨진 symlink 진단
python3 scripts/skillctl.py doctor

# SKILL.md frontmatter 검증
python3 scripts/skillctl.py validate
```

### 타겟 슬러그

| Slug | 배포 위치 |
|---|---|
| `claude` | `~/.claude/skills/<skill>` |
| `codex`  | `~/.codex/skills/<skill>` |
| `hermes:default` | `~/.hermes/skills/<skill>` |
| `hermes:<profile>` | `~/.hermes/profiles/<profile>/skills/<skill>` |
| `hermes:*` | 위 default 포함 모든 감지된 Hermes 프로파일 |

bare `hermes` 는 거부 — 어느 프로파일에 배포할지 호출자가 명시 선택해야 한다 (`hermes:default` 또는 `hermes:<profile>` 또는 `hermes:*`). 잘못된 프로파일에 배포하는 사고를 방지.

`-t` (=`--target`) 는 반복 사용 가능. 여러 타겟에 한번에 배포하려면 `-t claude -t codex` 처럼 나열한다.

### 안전성

- 타겟에 같은 이름의 **실 디렉토리** 가 있으면 **에러로 중단**. 자동 덮어쓰기 절대 없음.
- 다른 곳을 가리키는 symlink 가 있으면 `--force` 없이는 교체 안 함.
- 깨진 symlink 는 `deploy` 시 자동 교체. `doctor` 로도 진단 가능.
- 같은 명령 재실행 OK (idempotent — 이미 올바른 symlink면 "already linked" 출력).

### 짧은 별칭으로 쓰기 (선택)

```bash
# 한 번만 실행: ~/.local/bin/skillctl 에 launcher 설치
bash scripts/install.sh

# 그 다음부터는 어디서든
skillctl status
skillctl deploy --all -t hermes:*
```

`install.sh` 는 `~/.local/bin/skillctl` 에 launcher 스크립트만 만든다 (실제 로직은 `scripts/skillctl.py` 그대로). `~/.local/bin` 이 PATH 에 없으면 안내 메시지를 출력한다. 제거는 `rm ~/.local/bin/skillctl`.

### 테스트

```bash
python3 -m unittest tests.test_skillctl
```

stdlib `unittest` 만 사용. 모든 경로는 `SKILLCTL_CLAUDE_HOME` / `SKILLCTL_CODEX_HOME` / `SKILLCTL_HERMES_HOME` env 로 override 가능 → 테스트가 hermetic.
