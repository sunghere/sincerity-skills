#!/usr/bin/env python3
"""PoC 1: 단순 streaming 텍스트 응답.

`~/.codex/auth.json` 토큰으로 `chatgpt.com/backend-api/codex/responses` 호출.
Expected: "PONG"
"""
import json, urllib.request
from pathlib import Path

auth = json.loads(Path.home().joinpath(".codex/auth.json").read_text())
toks = auth["tokens"]

body = {
    "model": "gpt-5.4-mini",
    "instructions": "Reply with exactly the word PONG and nothing else.",
    "input": [{"type": "message", "role": "user",
               "content": [{"type": "input_text", "text": "ping"}]}],
    "tools": [], "tool_choice": "auto", "parallel_tool_calls": True,
    "store": False, "stream": True,
}
req = urllib.request.Request(
    "https://chatgpt.com/backend-api/codex/responses",
    method="POST",
    headers={
        "Authorization": f"Bearer {toks['access_token']}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "OpenAI-Beta": "responses=v1",
        "chatgpt-account-id": toks.get("account_id", ""),
        "originator": "codex_cli_rs",
        "version": "0.0.0",
    },
    data=json.dumps(body).encode(),
)
text = ""
with urllib.request.urlopen(req, timeout=60) as r:
    for line in r:
        s = line.decode().strip()
        if s.startswith("data: "):
            payload = s[6:]
            if payload == "[DONE]" or not payload: continue
            try: obj = json.loads(payload)
            except: continue
            if obj.get("type") == "response.output_text.delta":
                text += obj.get("delta", "")

print(f"text: {text!r}")
assert "PONG" in text, "expected PONG in response"
print("PASS")
