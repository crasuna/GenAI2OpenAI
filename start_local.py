"""Local-only launcher for the pinned GenAI2OpenAI checkout.

The client's API key is its own GenAI web-session token. No token is saved.
"""
import sys
import os
from pathlib import Path

# Campus endpoints are reachable directly. Scope this bypass to this process;
# preserve TLS certificate checks and the user's system proxy configuration.
os.environ["NO_PROXY"] = ",".join(filter(None, [os.environ.get("NO_PROXY", os.environ.get("no_proxy", "")),
    "genai.shanghaitech.edu.cn", "genaipic.shanghaitech.edu.cn", "127.0.0.1", "localhost"]))
os.environ["no_proxy"] = os.environ["NO_PROXY"]

sys.path.insert(0, str(Path(__file__).parent))
sys.argv = ["main.py", "--log-level", "WARNING"]
import main
from flask import jsonify, request
from waitress import create_server

# This personal launcher does not expose a cross-origin browser API.
main.app.after_request_funcs.clear()

@main.app.after_request
def wsgi_response_headers(response):
    # Connection is a hop-by-hop header owned by the WSGI server.
    response.headers.pop("Connection", None)
    return response

@main.app.before_request
def local_request_guard():
    if request.headers.get("Origin"):
        return jsonify(error="Browser cross-origin requests are disabled"), 403
    if request.path.startswith("/v1/") and not main.get_request_access_token():
        return jsonify(error="Supply your own GenAI session token as a Bearer key"), 401

if __name__ == "__main__":
    print("Local API: http://127.0.0.1:5057/v1", flush=True)
    print("API key: your own GenAI web token. No password needed.", flush=True)
    create_server(main.app, host="127.0.0.1", port=5057, threads=2).run()
