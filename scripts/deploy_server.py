#!/usr/bin/env python3
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = os.environ.get("ZENAIL_DEPLOY_HOST", "0.0.0.0")
PORT = int(os.environ.get("ZENAIL_DEPLOY_PORT", "8766"))
DEPLOY_SECRET = os.environ.get("DEPLOY_WEBHOOK_SECRET", "")
DEPLOY_SCRIPT = os.environ.get("ZENAIL_DEPLOY_SCRIPT", "/opt/zenail/scripts/deploy-from-github.sh")


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"ok": True})
            return
        self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/api/deploy":
            self._json(404, {"ok": False, "error": "not found"})
            return

        if DEPLOY_SECRET and self.headers.get("X-Deploy-Secret", "") != DEPLOY_SECRET:
            self._json(403, {"ok": False, "error": "invalid deploy secret"})
            return

        if not os.path.exists(DEPLOY_SCRIPT):
            self._json(503, {"ok": False, "error": f"deploy script not found: {DEPLOY_SCRIPT}"})
            return

        try:
            result = subprocess.run(
                ["bash", DEPLOY_SCRIPT],
                capture_output=True,
                text=True,
                timeout=600,
                cwd="/opt/zenail",
                env=os.environ.copy(),
            )
            self._json(
                200 if result.returncode == 0 else 500,
                {
                    "ok": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": result.stdout[-4000:],
                    "stderr": result.stderr[-2000:],
                },
            )
        except subprocess.TimeoutExpired:
            self._json(504, {"ok": False, "error": "deploy script timed out"})
        except Exception as exc:
            self._json(503, {"ok": False, "error": str(exc)})

    def log_message(self, fmt: str, *args) -> None:
        print(f"[zenail-deploy] {self.address_string()} - {fmt % args}", flush=True)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[zenail-deploy] listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

