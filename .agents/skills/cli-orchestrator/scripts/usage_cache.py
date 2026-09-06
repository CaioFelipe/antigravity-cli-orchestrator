#!/usr/bin/env python3
"""
Módulo de Cache Assíncrono com TTL para Cotas de CLIs.
Implementa padrão Stale-While-Revalidate e escrita atômica para alta performance.
"""

import os
import sys
import json
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from usage_probe import probe_agy_usage, probe_claude_usage

def find_project_root() -> Path:
    curr = Path(__file__).resolve()
    for parent in [curr] + list(curr.parents):
        if (parent / ".agents").exists() and parent.name != ".agents":
            return parent
    return Path.cwd()

WORKSPACE_DIR = find_project_root()
CACHE_FILE = WORKSPACE_DIR / ".agents" / "tasks" / "usage_cache.json"

DEFAULT_TTL = {
    "agy": 600,     # 10 minutos
    "claude": 180   # 3 minutos
}

_REFRESH_LOCKS: Dict[str, threading.Lock] = {}
_REFRESH_LOCKS_GUARD = threading.Lock()
_IN_FLIGHT_KEYS = set()


def _get_key_lock(key: str) -> threading.Lock:
    with _REFRESH_LOCKS_GUARD:
        if key not in _REFRESH_LOCKS:
            _REFRESH_LOCKS[key] = threading.Lock()
        return _REFRESH_LOCKS[key]


def _read_cache() -> Dict[str, Any]:
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cache(data: Dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = CACHE_FILE.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(CACHE_FILE)
    except Exception as e:
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass


def _execute_refresh_worker(tool: str, account_id: str, credential_file: Optional[str], config_dir: Optional[str]):
    key = f"{tool}:{account_id}"
    lock = _get_key_lock(key)
    if not lock.acquire(blocking=False):
        return

    try:
        if tool == "agy":
            data = probe_agy_usage(credential_file=credential_file)
        else:
            data = probe_claude_usage(config_dir=config_dir)

        cache_data = _read_cache()
        cache_data[key] = {
            "tool": tool,
            "account_id": account_id,
            "cached_at": time.time(),
            "data": data
        }
        _write_cache(cache_data)
    finally:
        with _REFRESH_LOCKS_GUARD:
            _IN_FLIGHT_KEYS.discard(key)
        lock.release()


def get_usage(
    tool: str,
    account_id: str = "principal",
    credential_file: Optional[str] = None,
    config_dir: Optional[str] = None,
    force: bool = False,
    async_refresh: bool = True
) -> Dict[str, Any]:
    """
    Retorna os dados de cota para uma dada ferramenta e conta.
    Se o cache estiver expirado, dispara atualização em background (se async_refresh=True)
    e retorna o valor atual como 'stale: True'.
    """
    key = f"{tool}:{account_id}"
    cache = _read_cache()
    entry = cache.get(key)
    ttl = DEFAULT_TTL.get(tool, 300)

    now = time.time()
    is_fresh = entry and (now - entry.get("cached_at", 0) < ttl)

    if is_fresh and not force:
        result = dict(entry.get("data", {}))
        result["stale"] = False
        result["cached_at_str"] = time.strftime("%H:%M:%S", time.localtime(entry.get("cached_at", 0)))
        return result

    # Se não temos nenhum dado em cache e é a primeira vez, podemos fazer síncrono ou async
    if not entry:
        if async_refresh:
            # Agenda em background e devolve placeholder imediato para não congelar HTTP
            with _REFRESH_LOCKS_GUARD:
                if key not in _IN_FLIGHT_KEYS:
                    _IN_FLIGHT_KEYS.add(key)
                    t = threading.Thread(
                        target=_execute_refresh_worker,
                        args=(tool, account_id, credential_file, config_dir),
                        daemon=True
                    )
                    t.start()
            return {
                "tool": tool,
                "account_id": account_id,
                "parse_ok": True,
                "stale": True,
                "loading": True,
                "windows": {
                    "5h": {"consumption_percent": 0.0, "remaining_percent": 100.0, "reset_at": ""},
                    "weekly": {"consumption_percent": 0.0, "remaining_percent": 100.0, "reset_at": ""}
                }
            }
        else:
            _execute_refresh_worker(tool, account_id, credential_file, config_dir)
            entry = _read_cache().get(key, {})
            result = dict(entry.get("data", {}))
            result["stale"] = False
            return result

    # Já temos dado anterior, mas expirou: dispara worker assíncrono e devolve dado stale
    with _REFRESH_LOCKS_GUARD:
        if key not in _IN_FLIGHT_KEYS:
            _IN_FLIGHT_KEYS.add(key)
            t = threading.Thread(
                target=_execute_refresh_worker,
                args=(tool, account_id, credential_file, config_dir),
                daemon=True
            )
            t.start()

    result = dict(entry.get("data", {}))
    result["stale"] = True
    result["cached_at_str"] = time.strftime("%H:%M:%S", time.localtime(entry.get("cached_at", 0)))
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Testador de cache de cotas")
    parser.add_argument("--tool", choices=["agy", "claude"], default="agy")
    parser.add_argument("--account", default="conta1")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    print("Obtendo uso...")
    res = get_usage(args.tool, args.account, force=args.force, async_refresh=False)
    print(json.dumps(res, indent=2, ensure_ascii=False))
