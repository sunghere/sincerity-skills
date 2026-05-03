# sincerity-skills

Sincerity (sunghere) 컴퍼니용 Claude/Hermes 스킬 모음. Paperclip GitHub import 호환.

## 등록된 스킬

| Slug | 한 줄 요약 |
|------|-----------|
| `asset-factory-api` | Asset Factory REST API로 게임 픽셀아트 에셋 생성. JSON 스펙만 제출하고 polling. |
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

## 로컬 hermes에 동기화

```bash
# 단일 스킬을 hermes로 복사
ln -sf ~/workspace/sincerity-skills/asset-factory-api ~/.hermes/skills/devops/asset-factory-api
```

또는 hermes 쪽에서 `skill_create`로 별도 작성. 양쪽이 갈라지지 않도록 주의.
