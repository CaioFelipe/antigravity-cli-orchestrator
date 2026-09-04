#!/usr/bin/env python3
"""
Dashboard HTTP Server for Antigravity & Claude Orchestrator
Lightweight, zero-dependency server hosting the GUI and REST API.
"""

import os
import sys
import json
import socket
import urllib.request
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 5050
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

sys.path.insert(0, str(SCRIPTS_DIR.parent))

from scripts.quota_guard import get_profile_quota_status, set_profile_consumption, _ensure_tracker_file
from scripts.proxy_manager import is_proxy_healthy, is_port_open

class DashboardHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/index"):
            html_file = WEB_DIR / "dashboard.html"
            if html_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_file.read_bytes())
            else:
                self.send_error(404, "dashboard.html not found")
        elif self.path == "/api/status":
            tracker = _ensure_tracker_file()
            profiles_quota = {}
            for prof in ["agy", "agy-conta2", "claude", "agyclaude", "mock"]:
                q_status = get_profile_quota_status(prof)
                prof_data = tracker.get("profiles", {}).get(prof, {})
                q_status["requests"] = prof_data.get("requests", 0)
                profiles_quota[prof] = q_status

            proxy_online = is_proxy_healthy(8080)
            status_data = {
                "accounts": {
                    "conta1": {"email": "caiofelipegl@gmail.com", "tier": "Pro", "channel": "Nativo"},
                    "conta2": {"email": "caio.lopes@unemat.br", "tier": "Pro/Free", "channel": "Hot-Swap"},
                    "claude": {"profile": "Oficial Anthropic", "path": "~/.claude", "isolated": True}
                },
                "proxy": {
                    "is_running": proxy_online,
                    "port": 8080,
                    "url": "http://127.0.0.1:8080"
                },
                "quotas": profiles_quota
            }
            self._send_json(status_data)
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if self.path == "/api/sync":
            sync_script = SCRIPTS_DIR / "sync_agy_to_proxy.py"
            proc = subprocess.run([sys.executable, str(sync_script)], cwd=str(WORKSPACE_DIR), capture_output=True, text=True)
            self._send_json({"success": proc.returncode == 0, "message": "Contas sincronizadas com sucesso!"})

        elif self.path == "/api/proxy/toggle":
            is_running = is_proxy_healthy(8080)
            if is_running:
                subprocess.run(["antigravity-claude-proxy", "stop"], shell=True, capture_output=True)
            else:
                subprocess.run(["antigravity-claude-proxy", "start"], shell=True, capture_output=True)
            self._send_json({"success": True, "now_running": not is_running})

        elif self.path == "/api/reset-quota":
            prof = payload.get("profile", "agy")
            pct = payload.get("percent", 15.0)
            set_profile_consumption(prof, pct)
            self._send_json({"success": True, "profile": prof, "consumption": pct})

        elif self.path == "/api/dispatch":
            profile = payload.get("profile", "agy")
            prompt = payload.get("prompt", "Ping")
            bridge_script = SCRIPTS_DIR / "cli_bridge.py"
            
            cmd = [
                sys.executable, str(bridge_script),
                "--profile", profile,
                "--prompt", prompt,
                "--cwd", str(WORKSPACE_DIR)
            ]
            proc = subprocess.run(cmd, cwd=str(WORKSPACE_DIR), capture_output=True, text=True)
            try:
                out_data = json.loads(proc.stdout)
                self._send_json(out_data)
            except Exception:
                self._send_json({
                    "status": "error",
                    "output_preview": proc.stdout or proc.stderr,
                    "duration_seconds": 0
                })
        else:
            self.send_error(404, "Endpoint not found")

def run():
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"=== Antigravity Orchestrator Dashboard ===")
    print(f"URL: http://127.0.0.1:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")

if __name__ == "__main__":
    run()
