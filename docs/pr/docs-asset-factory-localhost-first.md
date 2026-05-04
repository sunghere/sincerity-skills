# Asset Factory base URL — localhost 우선 + LAN IP 가변성 명시

## 한 줄 요약

스킬 / api.md 의 base URL 안내에서 박힌 LAN IP (`192.168.50.250`) 제거.
`localhost` 가 정답이고, 다른 LAN 기기에서 호출 시에는 *현재 LAN IP 가변* 임을
명시. 영구 고정이 필요하면 Tailscale (`100.72.190.122`) 사용.

## 증상

`192.168.50.250` 이 박혀있던 가이드를 따라 외부 기기 / 멍멍 노트북에서 운영
서버 접속 시 *연결 거부* 발생. 진단해보니 Mac mini 의 LAN IP 가 DHCP 로
`192.168.50.95` 로 바뀌어있었음. 가이드 / 메모리에 박힌 IP 와 실제 IP 가 어긋난
사고.

서버는 `0.0.0.0:47823` binding 이라 *어떤* LAN IP 든 받음 — 문제는 클라이언트가
어떤 IP 로 호출해야 할지 모름.

## 원인

- `asset-factory-api/SKILL.md:271` — base URL 표에 `LAN: http://192.168.50.250:47823` 명시
- `asset-factory-api/references/api.md:13` — `LAN: http://192.168.50.250:47823 (Mac mini IP)` 명시

이 IP 는 *집 공유기 DHCP 가 그때 할당한 값* 일 뿐, 서버가 binding 하는 IP 가
아니라서 시간이 지나면 어긋남.

## 수정

### `asset-factory-api/SKILL.md`

- "Base URL" 행 단순화 — 박힌 LAN IP 제거. `localhost` 가 1차, LAN 호출은 가변
  임을 한 줄 안내, 영구 고정은 Tailscale 추천.
- `version: 10 → 11`

### `asset-factory-api/references/api.md`

- "서버 정보" §의 LAN 줄을 박힌 IP → "운영 호스트의 LAN IP — DHCP 로 가변, `0.0.0.0` binding 이라 현재 IP 무엇이든 받음. `ipconfig getifaddr en0` 로 재확인" 안내로
- Tailscale 줄에 *DHCP 영향 받지 않음* 한 줄 보강
- 테스트 인스턴스 (`localhost:8000`) 도 같이 명시

## 검증

```
grep '192.168.50.\(250\|95\)' asset-factory-api/    → 0 hits (ComfyUI 머신 :225 는 별 정책이라 그대로)
```

## scope 밖 / 후속

- `~/.hermes/skills/devops/paperclip-administration/SKILL.md` 에도 같은 패턴
  (박힌 250/95) — 본 PR 머지 후 로컬 갱신 (외부 repo 아님)
- `asset-factory/HANDOFF.md` 에도 박힌 IP 1건 — 검토 후 별 PR
- 메모리 (`§Paperclip LAN: 3101→3100. 192.168.50.250/...`) 는 `localhost` /
  Tailscale 표기로 갱신

## Related

- `sunghere/asset-factory` PR #69 (`49faec0`) — 운영 메인 default `0.0.0.0:47823` binding (본 PR 의 전제 조건)
- `sunghere/sincerity-skills` PR #21 (`d836ed7`) — `af` CLI default `AF_HOST` 47823
