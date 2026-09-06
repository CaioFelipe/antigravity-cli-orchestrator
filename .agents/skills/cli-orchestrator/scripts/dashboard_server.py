#!/usr/bin/env python3
"""
Dashboard HTTP Server para Antigravity & Claude Orchestrator
Servidor local leve e sem dependências externas, hospedando a GUI e a REST API com métricas 100% reais.
"""

import os
import sys
import json
import socket
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 5050
SCRIPTS_DIR = Path(__file__).resolve().parent
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from quota_guard import get_profile_quota_status, set_profile_consumption, _ensure_tracker_file
from proxy_manager import is_proxy_healthy
from usage_cache import get_usage
from account_manager import (
    init_accounts_registry,
    list_accounts,
    start_add_account_job,
    get_job_status,
    remove_account,
    WORKSPACE_DIR
)


class DashboardHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        # 1. Arquivo estático da interface
        if self.path == "/" or self.path.startswith("/index"):
            html_file = WEB_DIR / "dashboard.html"
            if html_file.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_file.read_bytes())
            else:
                self.send_error(404, "dashboard.html not found")
            return

        # 2. Status Geral do Dashboard
        if self.path == "/api/status":
            reg = list_accounts()
            tracker = _ensure_tracker_file()
            profiles_quota = {}

            # Lista dinâmica de perfis conhecidos
            known_profiles = ["agy", "claude", "agyclaude", "mock"]
            for acc in reg.get("agy_accounts", []):
                if acc.get("profile") not in known_profiles:
                    known_profiles.append(acc["profile"])
            for acc in reg.get("claude_accounts", []):
                if acc.get("profile") not in known_profiles:
                    known_profiles.append(acc["profile"])

            for prof in known_profiles:
                q_status = get_profile_quota_status(prof)
                prof_data = tracker.get("profiles", {}).get(prof, {})
                q_status["requests"] = prof_data.get("requests", 0)
                profiles_quota[prof] = q_status

            # Anexa uso real por conta em reg
            for acc in reg.get("agy_accounts", []):
                u = get_usage("agy", account_id=acc["id"], credential_file=acc.get("credential_file"), async_refresh=True)
                acc["usage"] = u

            for acc in reg.get("claude_accounts", []):
                u = get_usage("claude", account_id=acc["id"], config_dir=acc.get("config_dir"), async_refresh=True)
                acc["usage"] = u

            proxy_online = is_proxy_healthy(8080)

            status_data = {
                "accounts_registry": reg,
                "proxy": {
                    "is_running": proxy_online,
                    "port": 8080,
                    "url": "http://127.0.0.1:8080"
                },
                "quotas": profiles_quota
            }
            self._send_json(status_data)
            return

        # 3. Listagem detalhada de contas
        if self.path == "/api/accounts":
            reg = list_accounts()
            for acc in reg.get("agy_accounts", []):
                acc["usage"] = get_usage("agy", account_id=acc["id"], credential_file=acc.get("credential_file"), async_refresh=True)
            for acc in reg.get("claude_accounts", []):
                acc["usage"] = get_usage("claude", account_id=acc["id"], config_dir=acc.get("config_dir"), async_refresh=True)
            self._send_json(reg)
            return

        # 4. Status de Job Assíncrono (ex: /api/jobs/<id>)
        if self.path.startswith("/api/jobs/"):
            job_id = self.path.replace("/api/jobs/", "").strip()
            job_info = get_job_status(job_id)
            self._send_json(job_info)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        # 1. Adicionar nova conta (job assíncrono)
        if self.path == "/api/accounts/add":
            tool = payload.get("tool", "agy")
            label = payload.get("label", "")
            job_id = start_add_account_job(tool, label)
            self._send_json({"success": True, "job_id": job_id})
            return

        # 2. Remover conta
        if self.path == "/api/accounts/delete":
            tool = payload.get("tool", "agy")
            account_id = payload.get("account_id", "")
            success = remove_account(tool, account_id)
            self._send_json({"success": success})
            return

        # 3. Forçar refresh de cota
        if self.path == "/api/accounts/refresh":
            tool = payload.get("tool", "agy")
            account_id = payload.get("account_id", "conta1")
            cred_file = payload.get("credential_file")
            cfg_dir = payload.get("config_dir")
            u = get_usage(tool, account_id=account_id, credential_file=cred_file, config_dir=cfg_dir, force=True, async_refresh=True)
            self._send_json({"success": True, "usage": u})
            return

        # 4. Sincronizar contas para o proxy
        if self.path == "/api/sync":
            sync_script = SCRIPTS_DIR / "sync_agy_to_proxy.py"
            proc = subprocess.run([sys.executable, str(sync_script)], cwd=str(WORKSPACE_DIR), capture_output=True, text=True)
            self._send_json({"success": proc.returncode == 0, "message": "Contas sincronizadas com sucesso!"})
            return

        # 5. Alternar status do proxy Claude
        if self.path == "/api/proxy/toggle":
            is_running = is_proxy_healthy(8080)
            if is_running:
                subprocess.run(["antigravity-claude-proxy", "stop"], shell=True, capture_output=True)
            else:
                subprocess.run(["antigravity-claude-proxy", "start"], shell=True, capture_output=True)
            self._send_json({"success": True, "now_running": not is_running})
            return

        # 6. Reset manual de medidor (para testes de guardrail)
        if self.path == "/api/reset-quota":
            prof = payload.get("profile", "agy")
            pct = payload.get("percent", 15.0)
            set_profile_consumption(prof, pct)
            self._send_json({"success": True, "profile": prof, "consumption": pct})
            return

        # 7. Disparo rápido de subagente
        if self.path == "/api/dispatch":
            profile = payload.get("profile", "agy")
            prompt = payload.get("prompt", "Ping")
            bridge_script = SCRIPTS_DIR / "cli_bridge.py"

            cmd = [
                sys.executable, str(bridge_script),
                "--profile", profile,
                "--prompt", prompt,
                "--cwd", str(WORKSPACE_DIR)
            ]
            proc = subprocess.run(cmd, cwd=str(WORKSPACE_DIR), capture_output=True, text=True, encoding="utf-8", errors="replace")
            try:
                out_data = json.loads(proc.stdout)
                self._send_json(out_data)
            except Exception:
                self._send_json({
                    "status": "error",
                    "output_preview": proc.stdout or proc.stderr,
                    "duration_seconds": 0
                })
            return

        self.send_error(404, "Endpoint not found")


def run():
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, DashboardHandler)
    print(f"=== Antigravity Orchestrator Dashboard (Live Metrics) ===")
    print(f"URL: http://127.0.0.1:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")


if __name__ == "__main__":
    run()
