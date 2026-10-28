"""Two small real requests, using a hidden token prompt (never saved)."""
import getpass
import json
from datetime import datetime
from pathlib import Path
import requests

base = "http://127.0.0.1:5057/v1"
token = getpass.getpass("Paste YOUR GenAI web token (hidden), then Enter: ").strip()
if not token:
    raise SystemExit("No token entered.")
model = input("Model [deepseek-pro]: ").strip() or "deepseek-pro"
session = requests.Session()
session.trust_env = False  # loopback must not go through a system proxy
session.headers["Authorization"] = "Bearer " + token
results = {"time": datetime.now().isoformat(), "model": model, "checks": []}
try:
    for streaming in (False, True):
        body = {"model": model, "messages": [{"role": "user", "content": "Reply only: API_OK"}],
                "stream": streaming, "max_tokens": 64}
        with session.post(base + "/chat/completions", json=body, stream=streaming, timeout=120) as response:
            response.raise_for_status()
            if not streaming:
                data = response.json()
                answer = data["choices"][0]["message"]["content"] or ""
            else:
                parts = []
                done = False
                for raw in response.iter_lines():
                    if not raw or not raw.startswith(b"data:"):
                        continue
                    chunk = raw[5:].strip()
                    if chunk == b"[DONE]":
                        done = True
                        break
                    data = json.loads(chunk)
                    if "error" in data:
                        raise RuntimeError("Upstream stream returned an error")
                    choices = data.get("choices", [])
                    if choices:
                        parts.append(choices[0].get("delta", {}).get("content") or "")
                answer = "".join(parts)
                if not done:
                    raise RuntimeError("Stream did not terminate with [DONE]")
            passed = "API_OK" in answer
            results["checks"].append({"stream": streaming, "passed": passed, "reply": answer[:200]})
            print("stream=", streaming, "passed=", passed, "reply=", answer[:200])
            if not passed:
                raise RuntimeError("Expected API_OK was absent; this is not a verified success")
except Exception as exc:
    # Never serialize request headers, credential values or full exception details.
    results["error_type"] = type(exc).__name__
    print("Verification failed:", type(exc).__name__)
finally:
    (Path(__file__).parent / "live-verification.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    session.close()
    token = ""
