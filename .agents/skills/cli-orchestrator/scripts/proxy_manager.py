#!/usr/bin/env python3
"""
Lifecycle Manager for Antigravity Claude Proxy
Handles on-demand startup, reference counting, and automatic shutdown
when no agyclaude sessions are active.
"""

import os
import sys
import json
import time
import socket
import urllib.request
import subprocess
from pathlib import Path

STATE_FILE_NAME = ".agents/tasks/proxy_state.json"
LOCK_FILE_NAME = ".agents/tasks/proxy.lock"

def is_port_open(port=8080, host="127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def is_proxy_healthy(port=8080, host="127.0.0.1") -> bool:
    try:
        url = f"http://{host}:{port}/health"
        req = urllib.request.Request(url, headers={"User-Agent": "AntigravityOrchestrator"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("status") == "ok"
    except Exception:
        return False


class ProxyLifecycleManager:
    def __init__(self, workspace_dir: Path, port: int = 8080):
        self.workspace_dir = Path(workspace_dir)
        self.port = port
        self.state_file = self.workspace_dir / STATE_FILE_NAME
        self.lock_file = self.workspace_dir / LOCK_FILE_NAME
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _read_state(self) -> dict:
        if not self.state_file.exists():
            return {"active_sessions": 0, "pid": None}
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"active_sessions": 0, "pid": None}

    def _write_state(self, state: dict):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def start_proxy_if_needed(self, timeout=15) -> bool:
        """Starts proxy if not running and increments session reference count."""
        state = self._read_state()
        active = state.get("active_sessions", 0)

        # Check if already running
        if not is_proxy_healthy(self.port):
            # Launch proxy via CLI
            subprocess.run(
                ["antigravity-claude-proxy", "start"],
                cwd=str(self.workspace_dir),
                capture_output=True,
                shell=True
            )
            # Wait for proxy to come online
            start_wait = time.time()
            while time.time() - start_wait < timeout:
                if is_proxy_healthy(self.port):
                    break
                time.sleep(0.3)

        state["active_sessions"] = active + 1
        self._write_state(state)
        return is_proxy_healthy(self.port)

    def stop_proxy_if_idle(self):
        """Decrements session reference count. If 0, stops proxy immediately."""
        state = self._read_state()
        active = max(0, state.get("active_sessions", 1) - 1)
        state["active_sessions"] = active
        self._write_state(state)

        if active == 0:
            # Stop proxy
            subprocess.run(
                ["antigravity-claude-proxy", "stop"],
                cwd=str(self.workspace_dir),
                capture_output=True,
                shell=True
            )
            # Short wait to release socket
            time.sleep(0.5)


class ManagedProxyContext:
    """Context manager for cleanly acquiring and releasing the proxy."""
    def __init__(self, workspace_dir: Path, port: int = 8080):
        self.mgr = ProxyLifecycleManager(workspace_dir, port)

    def __enter__(self):
        self.mgr.start_proxy_if_needed()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.mgr.stop_proxy_if_idle()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["start", "stop", "status"], default="status")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    mgr = ProxyLifecycleManager(Path.cwd(), args.port)
    if args.action == "start":
        res = mgr.start_proxy_if_needed()
        print(f"Proxy started: {res}")
    elif args.action == "stop":
        mgr.stop_proxy_if_idle()
        print("Proxy stopped if idle.")
    elif args.action == "status":
        print(f"Port {args.port} healthy: {is_proxy_healthy(args.port)}")
        print(f"State file: {mgr._read_state()}")
