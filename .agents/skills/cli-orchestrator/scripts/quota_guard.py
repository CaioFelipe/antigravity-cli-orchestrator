#!/usr/bin/env python3
"""
Quota Guardrail & Smart Task Sizer for CLI Orchestrator
Monitors token/request consumption per profile and enforces the 90% threshold rule:
when consumption >= 90%, heavy tasks are blocked, permitting only micro-tasks.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Tuple, Dict, Any, List

STATE_DIR = Path(".agents/tasks")
TRACKER_FILE = STATE_DIR / "quota_tracker.json"
ACCOUNTS_FILE = Path(os.path.expanduser("~/.config/antigravity-proxy/accounts.json"))

# Limite para considerar a tarefa "MICRO"
MAX_MICRO_PROMPT_CHARS = 280
HEAVY_KEYWORDS = [
    "refatore", "refactor", "reescreva", "rewrite", "crie um", "crie uma", 
    "implemente", "implement", "arquitetura", "completo", "todos os arquivos",
    "stress test", "benchmark", "full test"
]

def _ensure_tracker_file() -> Dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not TRACKER_FILE.exists():
        initial = {
            "profiles": {
                "mock": {"requests": 0, "simulated_consumption": 0.0},
                "agy": {"requests": 0, "simulated_consumption": 15.0},
                "agy-conta2": {"requests": 0, "simulated_consumption": 10.0},
                "claude": {"requests": 0, "simulated_consumption": 20.0},
                "agyclaude": {"requests": 0, "simulated_consumption": 92.0}
            },
            "last_updated": time.time()
        }
        with open(TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=2)
        return initial
    try:
        with open(TRACKER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"profiles": {}, "last_updated": time.time()}


def _save_tracker_file(data: Dict[str, Any]):
    try:
        with open(TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def get_profile_quota_status(profile: str) -> Dict[str, Any]:
    """
    Retorna o percentual real de consumo (0.0 a 100.0) e o status do perfil a partir do cache de cota.
    Se for agy ou claude, extrai as janelas reais de 5h e semanal.
    """
    tracker = _ensure_tracker_file()
    profile_data = tracker.get("profiles", {}).get(profile, {})
    consumption = profile_data.get("simulated_consumption", 10.0)
    windows_data = None
    stale = False

    # Tenta obter dados reais para agy e claude via usage_cache
    try:
        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from usage_cache import get_usage

        if profile == "agy" or profile.startswith("agy-"):
            account_id = "conta1" if profile == "agy" else profile.replace("agy-", "")
            cred_file = f".agents/credentials/{account_id}.json" if account_id != "conta1" else None
            real_usage = get_usage("agy", account_id=account_id, credential_file=cred_file, async_refresh=True)
            if real_usage and real_usage.get("parse_ok") and not real_usage.get("loading"):
                w5h = real_usage.get("windows", {}).get("5h", {})
                w_week = real_usage.get("windows", {}).get("weekly", {})
                c_5h = w5h.get("consumption_percent", 0.0)
                c_week = w_week.get("consumption_percent", 0.0)
                consumption = max(c_5h, c_week)
                windows_data = real_usage.get("windows")
                stale = real_usage.get("stale", False)

        elif profile == "claude" or profile.startswith("claude-"):
            account_id = "principal" if profile == "claude" else profile.replace("claude-", "")
            real_usage = get_usage("claude", account_id=account_id, async_refresh=True)
            if real_usage and real_usage.get("parse_ok") and not real_usage.get("loading"):
                w5h = real_usage.get("windows", {}).get("5h", {})
                w_week = real_usage.get("windows", {}).get("weekly", {})
                c_5h = w5h.get("consumption_percent", 0.0)
                c_week = w_week.get("consumption_percent", 0.0)
                consumption = max(c_5h, c_week)
                windows_data = real_usage.get("windows")
                stale = real_usage.get("stale", False)
    except Exception:
        pass

    # Checa accounts.json do proxy para rate-limits ativos do agyclaude
    is_rate_limited = False
    if ACCOUNTS_FILE.exists() and profile == "agyclaude":
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                acc_data = json.load(f)
            for acc in acc_data.get("accounts", []):
                for model, limit_info in acc.get("modelRateLimits", {}).items():
                    if limit_info.get("isRateLimited"):
                        is_rate_limited = True
                        break
        except Exception:
            pass

    if is_rate_limited:
        consumption = 100.0

    if consumption >= 100.0 or is_rate_limited:
        status = "EXHAUSTED"
    elif consumption >= 90.0:
        status = "CRITICAL"  # Modo Econômico: Apenas Micro-Tarefas
    elif consumption >= 70.0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    res = {
        "profile": profile,
        "consumption_percent": round(consumption, 1),
        "status": status,
        "is_rate_limited": is_rate_limited,
        "economic_mode": consumption >= 90.0
    }
    if windows_data:
        res["windows"] = windows_data
        res["stale"] = stale
    return res


def record_task_execution(profile: str, is_heavy: bool = False):
    """
    Increments consumption counter after executing a task.
    """
    tracker = _ensure_tracker_file()
    if profile not in tracker.get("profiles", {}):
        tracker.setdefault("profiles", {})[profile] = {"requests": 0, "simulated_consumption": 10.0}

    prof = tracker["profiles"][profile]
    prof["requests"] = prof.get("requests", 0) + 1
    # Heavy tasks consume more quota points
    increment = 4.0 if is_heavy else 0.5
    prof["simulated_consumption"] = min(100.0, prof.get("simulated_consumption", 10.0) + increment)
    tracker["last_updated"] = time.time()
    _save_tracker_file(tracker)


def set_profile_consumption(profile: str, percent: float):
    """Manually update or reset profile consumption (useful for GUI / testing)."""
    tracker = _ensure_tracker_file()
    if profile not in tracker.get("profiles", {}):
        tracker.setdefault("profiles", {})[profile] = {"requests": 0, "simulated_consumption": percent}
    else:
        tracker["profiles"][profile]["simulated_consumption"] = max(0.0, min(100.0, percent))
    tracker["last_updated"] = time.time()
    _save_tracker_file(tracker)


def classify_task_size(prompt: str, files: List[str] = None) -> str:
    """
    Classifies a task as 'MICRO' or 'HEAVY'.
    """
    prompt_clean = prompt.strip()
    
    # Se muitos arquivos forem passados, é HEAVY
    if files and len(files) > 1:
        return "HEAVY"

    # Se o prompt for longo, é HEAVY
    if len(prompt_clean) > MAX_MICRO_PROMPT_CHARS:
        return "HEAVY"

    # Se contém palavras-chave de tarefas pesadas, é HEAVY
    lower_prompt = prompt_clean.lower()
    for kw in HEAVY_KEYWORDS:
        if kw in lower_prompt:
            return "HEAVY"

    return "MICRO"


def can_execute_task(profile: str, prompt: str, files: List[str] = None) -> Tuple[bool, str, str]:
    """
    Validates if a task can be executed by the given profile based on the 90% threshold rule.
    Returns: (allowed: bool, task_size: 'MICRO'|'HEAVY', reason: str)
    """
    status = get_profile_quota_status(profile)
    task_size = classify_task_size(prompt, files)

    if status["status"] == "EXHAUSTED":
        return False, task_size, f"Perfil '{profile}' com cota esgotada (100% ou rate-limited)."

    if status["consumption_percent"] >= 90.0:
        if task_size == "HEAVY":
            return False, task_size, (
                f"[GUARDRAIL 90%] Consumo em {status['consumption_percent']}%. "
                f"Tarefas pesadas bloqueadas neste perfil para preservação de cota. "
                f"Apenas micro-tarefas rápidas são permitidas."
            )
        else:
            return True, task_size, (
                f"[GUARDRAIL 90% APROVADO] Consumo em {status['consumption_percent']}%. "
                f"Micro-tarefa autorizada em modo econômico."
            )

    return True, task_size, f"Autorizado (Consumo normal: {status['consumption_percent']}%)."


if __name__ == "__main__":
    import sys
    prof = sys.argv[1] if len(sys.argv) > 1 else "agy"
    test_prompt = sys.argv[2] if len(sys.argv) > 2 else "Responda se o sistema está online"
    allowed, size, reason = can_execute_task(prof, test_prompt)
    print(f"Profile: {prof} | Task Size: {size} | Allowed: {allowed}")
    print(f"Reason: {reason}")
