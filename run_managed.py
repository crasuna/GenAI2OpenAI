"""Task Scheduler entry point: log and restart the local server on exit."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from datetime import datetime


def run_once():
    root = Path(__file__).resolve().parent
    logs = root / "logs"
    logs.mkdir(exist_ok=True)
    runtime_log = logs / "server-managed.log"
    # Bound accumulated logs between launches, keeping the previous file.
    if runtime_log.exists() and runtime_log.stat().st_size > 5 * 1024 * 1024:
        runtime_log.replace(logs / "server-managed.previous.log")
    with runtime_log.open("a", encoding="utf-8") as output:
        def note(message):
            output.write(f"\n[{datetime.now().astimezone().isoformat()}] {message}\n")
            output.flush()

        # Do not start a second server over an existing/manual listener.
        with socket.socket() as probe:
            probe.settimeout(2)
            if probe.connect_ex(("127.0.0.1", 5057)) == 0:
                note("Port 5057 already occupied; retry in 10 seconds.")
                return 1
        environment = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        try:
            child = subprocess.Popen(
                [sys.executable, "-u", str(root / "start_local.py")],
                cwd=root, env=environment, stdout=output, stderr=subprocess.STDOUT,
            )
            note(f"Server started: pid={child.pid}")
            status = child.wait()
            note(f"Server exited: pid={child.pid}, exit_code={status}; restarting in 10 seconds.")
        except Exception as exc:
            note(f"Server launch failed: {type(exc).__name__}: {exc}")
        # The supervisor retries even when the server exited with status zero.
        return 1


if __name__ == "__main__":
    while True:
        run_once()
        time.sleep(10)
