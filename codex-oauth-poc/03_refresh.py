#!/usr/bin/env python3
"""PoC 3: Token refresh + ~/.codex/auth.json 저장.

WARNING: 실제 refresh를 트리거하므로 실행 전에 백업이 필요.
이 스크립트는 dry-run 옵션 없이 실제 토큰을 회전한다.
"""
import json, time, base64, urllib.request, urllib.parse
from pathlib import Path

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
TOKEN_URL = "https://auth.openai.com/oauth/token"

def jwt_payload(jwt: str) -> dict:
    parts = jwt.split(".")
    if len(parts) < 2: return {}
    p = parts[1]
    pad = len(p) % 4
    if pad: p += "=" * (4 - pad)
    return json.loads(base64.urlsafe_b64decode(p))

auth_path = Path.home() / ".codex/auth.json"
auth = json.loads(auth_path.read_text())
toks = auth["tokens"]

# Show expiry of current access token
acc_claims = jwt_payload(toks["access_token"])
exp = acc_claims.get("exp", 0)
secs_left = exp - int(time.time()) if exp else 0
print(f"current access_token expires in: {secs_left/3600:.1f}h")

# Backup
bak = Path.home() / ".codex/auth.json.bak"
bak.write_text(json.dumps(auth, indent=2))
print(f"backup: {bak}")

# Refresh
data = urllib.parse.urlencode({
    "grant_type": "refresh_token",
    "refresh_token": toks["refresh_token"],
    "client_id": CLIENT_ID,
}).encode()
req = urllib.request.Request(TOKEN_URL, method="POST", data=data,
    headers={"Content-Type": "application/x-www-form-urlencoded",
             "Accept": "application/json"})

with urllib.request.urlopen(req, timeout=20) as r:
    resp = json.load(r)

assert "access_token" in resp, "missing access_token in refresh response"
assert "refresh_token" in resp, "missing refresh_token (rotated)"
print(f"refresh OK — new keys: {list(resp.keys())}")

# Save
auth["tokens"]["access_token"] = resp["access_token"]
auth["tokens"]["refresh_token"] = resp["refresh_token"]
if resp.get("id_token"):
    auth["tokens"]["id_token"] = resp["id_token"]
auth["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
auth_path.write_text(json.dumps(auth, indent=2))

# Verify new token works
HEADERS = {
    "Authorization": f"Bearer {resp['access_token']}",
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
    "OpenAI-Beta": "responses=v1",
    "chatgpt-account-id": toks.get("account_id", ""),
    "originator": "codex_cli_rs",
    "version": "0.0.0",
}
body = {
    "model": "gpt-5.4-mini",
    "instructions": "Reply: PONG",
    "input": [{"type": "message", "role": "user",
               "content": [{"type": "input_text", "text": "ping"}]}],
    "tools": [], "tool_choice": "auto", "parallel_tool_calls": True,
    "store": False, "stream": True,
}
req2 = urllib.request.Request(
    "https://chatgpt.com/backend-api/codex/responses",
    method="POST", headers=HEADERS,
    data=json.dumps(body).encode())
text = ""
with urllib.request.urlopen(req2, timeout=30) as r:
    for line in r:
        s = line.decode().strip()
        if s.startswith("data: "):
            payload = s[6:]
            if payload == "[DONE]" or not payload: continue
            try: obj = json.loads(payload)
            except: continue
            if obj.get("type") == "response.output_text.delta":
                text += obj.get("delta", "")
print(f"new token verified: text={text!r}")
print("PASS")
