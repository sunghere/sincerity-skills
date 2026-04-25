#!/usr/bin/env python3
"""PoC 2: tool call round-trip.

Round 1: ask weather → LLM calls get_weather
Round 2: send tool result → LLM gives final answer

핵심: response.completed.output은 빈 배열로 옴.
SSE의 response.output_item.done 이벤트에서 직접 누적해야 함.
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
URL = "https://chatgpt.com/backend-api/codex/responses"
tools = [{
    "type": "function", "name": "get_weather",
    "description": "Get current weather for a city.",
    "parameters": {"type": "object",
                   "properties": {"city": {"type": "string"}},
                   "required": ["city"]},
}]

def stream_call(body):
    """SSE accumulator: returns dict with output, text, status."""
    req = urllib.request.Request(URL, method="POST",
                                  headers=HEADERS,
                                  data=json.dumps(body).encode())
    output, text, status = [], "", None
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
                        if item: output.append(item)
                    elif t == "response.output_text.delta":
                        text += obj.get("delta", "")
                    elif t == "response.completed":
                        status = obj["response"].get("status")
    return {"output": output, "text": text, "status": status}

# Round 1
body1 = {
    "model": "gpt-5.4-mini",
    "instructions": "Use get_weather tool when asked about weather.",
    "input": [{"type": "message", "role": "user",
               "content": [{"type": "input_text", "text": "Weather in Tokyo?"}]}],
    "tools": tools, "tool_choice": "auto", "parallel_tool_calls": True,
    "store": False, "stream": True,
}
r1 = stream_call(body1)
print(f"R1 output: {len(r1['output'])} items, status={r1['status']}")
fcall = next(it for it in r1["output"] if it.get("type") == "function_call")
print(f"  function_call: {fcall['name']}({fcall['arguments']})")

# Round 2
body2 = {
    "model": "gpt-5.4-mini",
    "instructions": "Use get_weather tool when asked about weather.",
    "input": [
        {"type": "message", "role": "user",
         "content": [{"type": "input_text", "text": "Weather in Tokyo?"}]},
        *r1["output"],  # echo output items as-is
        {"type": "function_call_output", "call_id": fcall["call_id"],
         "output": "Sunny, 22°C, light breeze"},
    ],
    "tools": tools, "tool_choice": "auto", "parallel_tool_calls": True,
    "store": False, "stream": True,
}
r2 = stream_call(body2)
print(f"R2 final text: {r2['text']!r}")
assert r2["text"] and "22" in r2["text"], "expected weather data in answer"
print("PASS")
