#!/usr/bin/env python3
"""
Módulo de captura (probe) de cotas reais do Antigravity CLI e Claude Code CLI.
Executa comandos reais /usage e faz parsing resiliente das janelas de 5h e semanal.
"""

import os
import re
import sys
import json
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from wincred_manager import TemporaryCredentialSwap
except ImportError:
    TemporaryCredentialSwap = None


def parse_agy_usage(raw_text: str) -> Dict[str, Any]:
    """
    Parseia a saída tabulada de `agy -p "/usage"`.
    Exemplo de formato:
    Gemini Models	Weekly Limit Remaining	79%	2026-09-11T02:52:54Z
    Gemini Models	Five Hour Limit Remaining	98%	2026-09-06T02:10:33Z
    Claude and GPT models	Weekly Limit Remaining	100%	2026-09-12T21:12:10Z
    Claude and GPT models	Five Hour Limit Remaining	100%	2026-09-06T02:12:10Z
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    per_model: Dict[str, Any] = {}
    
    # Padrão flexível para capturar: <Modelo> \t <Janela> Limit Remaining \t <Valor>% \t <Timestamp>
    line_pattern = re.compile(
        r"^(?P<model>[\w\s&]+?)\s+(?P<window>Weekly|Five\s+Hour)\s+Limit\s+Remaining\s+(?P<remaining>\d+(?:\.\d+)?)\s*%\s*(?P<reset>\d{4}-\d{2}-\d{2}T[\d:.]+(?:Z|[+-]\d{2}:?\d{2})?)?",
        re.IGNORECASE
    )

    for line in lines:
        match = line_pattern.search(line)
        if match:
            raw_model = match.group("model").strip().lower()
            model_key = "gemini" if "gemini" in raw_model else "claude_gpt"
            window_raw = match.group("window").strip().lower()
            window_key = "weekly" if "weekly" in window_raw else "5h"
            remaining = float(match.group("remaining"))
            consumption = round(max(0.0, 100.0 - remaining), 2)
            reset_at = match.group("reset") or ""

            if model_key not in per_model:
                per_model[model_key] = {}
            per_model[model_key][window_key] = {
                "remaining_percent": remaining,
                "consumption_percent": consumption,
                "reset_at": reset_at
            }

    # Modelo principal de referência para o agy é o Gemini
    gemini_data = per_model.get("gemini", {})
    windows_5h = gemini_data.get("5h", {"remaining_percent": 100.0, "consumption_percent": 0.0, "reset_at": ""})
    windows_weekly = gemini_data.get("weekly", {"remaining_percent": 100.0, "consumption_percent": 0.0, "reset_at": ""})

    parse_ok = bool(per_model)
    return {
        "tool": "agy",
        "parse_ok": parse_ok,
        "windows": {
            "5h": windows_5h,
            "weekly": windows_weekly
        },
        "per_model": per_model,
        "raw_output": raw_text
    }


def parse_claude_usage(raw_text: str) -> Dict[str, Any]:
    """
    Parseia a saída de `claude -p "/usage"`.
    Exemplo de formato:
    Current session: 27% used · resets Sep 5, 10:10pm (America/Cuiaba)
    Current week (all models): 36% used · resets Sep 7, 4am (America/Cuiaba)
    """
    session_match = re.search(r"Current\s+session[^\d%]*?(\d+(?:\.\d+)?)\s*%\s*used(?:[^\w\n\r]*resets?\s*([^(\n\r]+))?", raw_text, re.IGNORECASE)
    week_match = re.search(r"Current\s+week[^\d%]*?(\d+(?:\.\d+)?)\s*%\s*used(?:[^\w\n\r]*resets?\s*([^(\n\r]+))?", raw_text, re.IGNORECASE)

    consumption_5h = float(session_match.group(1)) if session_match else 0.0
    reset_5h_str = session_match.group(2).strip() if (session_match and session_match.group(2)) else ""

    consumption_weekly = float(week_match.group(1)) if week_match else 0.0
    reset_weekly_str = week_match.group(2).strip() if (week_match and week_match.group(2)) else ""

    parse_ok = bool(session_match or week_match)

    return {
        "tool": "claude",
        "parse_ok": parse_ok,
        "windows": {
            "5h": {
                "consumption_percent": consumption_5h,
                "remaining_percent": max(0.0, 100.0 - consumption_5h),
                "reset_at": reset_5h_str
            },
            "weekly": {
                "consumption_percent": consumption_weekly,
                "remaining_percent": max(0.0, 100.0 - consumption_weekly),
                "reset_at": reset_weekly_str
            }
        },
        "raw_output": raw_text
    }


def probe_agy_usage(credential_file: Optional[str] = None, timeout: int = 25) -> Dict[str, Any]:
    """Executa agy -p /usage respeitando o hot-swap de credencial se necessário."""
    agy_cmd = os.path.expandvars(r"%LOCALAPPDATA%\agy\bin\agy.exe")
    if not os.path.exists(agy_cmd):
        agy_cmd = "agy"

    swap_ctx = TemporaryCredentialSwap(credential_file) if (credential_file and TemporaryCredentialSwap) else None

    captured_stdout = ""
    try:
        if swap_ctx:
            with swap_ctx:
                proc = subprocess.run(
                    [agy_cmd, "-p", "/usage", "--dangerously-skip-permissions"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout,
                    shell=(sys.platform == "win32" and not agy_cmd.endswith(".exe"))
                )
                captured_stdout = proc.stdout or ""
        else:
            proc = subprocess.run(
                [agy_cmd, "-p", "/usage", "--dangerously-skip-permissions"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                shell=(sys.platform == "win32" and not agy_cmd.endswith(".exe"))
            )
            captured_stdout = proc.stdout or ""
    except Exception as e:
        return {
            "tool": "agy",
            "parse_ok": False,
            "error": str(e),
            "windows": {
                "5h": {"consumption_percent": 0.0, "remaining_percent": 100.0, "reset_at": ""},
                "weekly": {"consumption_percent": 0.0, "remaining_percent": 100.0, "reset_at": ""}
            }
        }

    res = parse_agy_usage(captured_stdout)
    res["captured_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return res


def probe_claude_usage(config_dir: Optional[str] = None, timeout: int = 25) -> Dict[str, Any]:
    """Executa claude -p /usage com isolamento de diretório de configuração se especificado."""
    env = os.environ.copy()
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = os.path.expandvars(config_dir)

    try:
        proc = subprocess.run(
            ["claude", "-p", "/usage", "--output-format", "text"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
            shell=(sys.platform == "win32")
        )
        captured_stdout = proc.stdout or ""
    except Exception as e:
        return {
            "tool": "claude",
            "parse_ok": False,
            "error": str(e),
            "windows": {
                "5h": {"consumption_percent": 0.0, "remaining_percent": 100.0, "reset_at": ""},
                "weekly": {"consumption_percent": 0.0, "remaining_percent": 100.0, "reset_at": ""}
            }
        }

    res = parse_claude_usage(captured_stdout)
    res["captured_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return res


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Probe de cotas reais do agy e claude")
    parser.add_argument("--tool", choices=["agy", "claude"], default="agy")
    parser.add_argument("--credential", default=None, help="Caminho do arquivo de credencial para o agy")
    parser.add_argument("--config-dir", default=None, help="Diretório de config para o claude")
    args = parser.parse_args()

    if args.tool == "agy":
        result = probe_agy_usage(credential_file=args.credential)
    else:
        result = probe_claude_usage(config_dir=args.config_dir)

    print(json.dumps(result, indent=2, ensure_ascii=False))
