#!/usr/bin/env python3
"""PoC 4: reasoning encrypted_content 추출 (gpt-5.3-codex 모델).

reasoning은 별도 output item으로 옴. encrypted_content를 다음 turn에 echo
필요 (모델이 사고 흐름을 이어가기 위해).
"""
import json, urllib.request
from pathlib import Path

auth = json.loads(Path.home().joinpath(".codex/auth.json").read_text())
toks = auth["tokens"]
HEADERS = {
    "Authorization": f"Bearer {toks['access_token']}",
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
    "OpenAI-Beta": "responses=v1",
    "chatgpt-account-id": toks.get("account_id", ""),
    "originator": "codex_cli_rs",
    "version": "0.0.0",
}
body = {
    "model": "gpt-5.3-codex",
    "instructions": "You are a careful math assistant.",
    "input": [{"type": "message", "role": "user",
               "content": [{"type": "input_text",
                            "text": "What is 23 * 47? Show reasoning, then answer."}]}],
    "tools": [], "tool_choice": "auto", "parallel_tool_calls": True,
    "store": False, "stream": True,
    "reasoning": {"effort": "medium", "summary": "auto"},
    "include": ["reasoning.encrypted_content"],
}
req = urllib.request.Request(
    "https://chatgpt.com/backend-api/codex/responses",
    method="POST", headers=HEADERS,
    data=json.dumps(body).encode())

output_items, text = [], ""
with urllib.request.urlopen(req, timeout=60) as r:
    buf = b""
    for line in r:
        buf += line
        if line in (b"\n", b"\r\n"):
            ev = buf.decode(); buf = b""
            for sub in ev.split("\n"):
                if not sub.startswith("data:"): continue
                payload = sub[5:].strip()
                if not payload or payload == "[DONE]": continue
                try: obj = json.loads(payload)
                except: continue
                t = obj.get("type")
                if t == "response.output_item.done":
                    item = obj.get("item")
                    if item: output_items.append(item)
                elif t == "response.output_text.delta":
                    text += obj.get("delta", "")

print(f"output items: {len(output_items)}")
reasoning_item = None
for it in output_items:
    print(f"  - type={it.get('type')} keys={list(it.keys())[:6]}")
    if it.get("type") == "reasoning":
        reasoning_item = it
        ec_len = len(it.get("encrypted_content", "") or "")
        print(f"      encrypted_content len: {ec_len}")
print(f"final text: {text[:200]!r}")
assert reasoning_item is not None, "expected reasoning item"
assert reasoning_item.get("encrypted_content"), "expected encrypted_content"
assert "1081" in text, "expected math answer"
print("PASS")
