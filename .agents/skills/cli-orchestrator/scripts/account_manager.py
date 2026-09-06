#!/usr/bin/env python3
"""
Módulo de Gerenciamento Centralizado e Dinâmico de Multi-Contas.
Gerencia .agents/accounts.json e sincroniza os perfis no config.json do orquestrador.
"""

import os
import sys
import json
import time
import uuid
import threading
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from wincred_manager import read_credential, write_credential, delete_credential
except ImportError:
    read_credential = None

def find_project_root() -> Path:
    curr = Path(__file__).resolve()
    for parent in [curr] + list(curr.parents):
        if (parent / ".agents").exists() and parent.name != ".agents":
            return parent
    return Path.cwd()

WORKSPACE_DIR = find_project_root()
ACCOUNTS_REGISTRY_FILE = WORKSPACE_DIR / ".agents" / "accounts.json"
CONFIG_FILE = Path(__file__).resolve().parent.parent / "config.json"
CREDENTIALS_DIR = WORKSPACE_DIR / ".agents" / "credentials"

JOBS: Dict[str, Dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def _get_account_email_from_blob(blob_str: str) -> str:
    # 1. Tenta ler do arquivo do proxy sincronizado
    proxy_acc_file = Path(os.path.expanduser("~/.config/antigravity-proxy/accounts.json"))
    if proxy_acc_file.exists():
        try:
            with open(proxy_acc_file, "r", encoding="utf-8") as f:
                p_data = json.load(f)
            for acc in p_data.get("accounts", []):
                if acc.get("email"):
                    return acc["email"]
        except Exception:
            pass

    # 2. Tenta obter via endpoint de userinfo do Google
    try:
        data = json.loads(blob_str)
        if data.get("email"):
            return data["email"]
        tok = data.get("token", {}).get("access_token")
        if tok:
            import urllib.request
            req = urllib.request.Request("https://www.googleapis.com/oauth2/v2/userinfo", headers={"Authorization": f"Bearer {tok}"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                u_info = json.loads(resp.read().decode("utf-8"))
                if u_info.get("email"):
                    return u_info["email"]
    except Exception:
        pass

    return "caiofelipegl@gmail.com"


def init_accounts_registry() -> Dict[str, Any]:
    """Inicializa ou carrega o registro central .agents/accounts.json."""
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
    
    if ACCOUNTS_REGISTRY_FILE.exists():
        try:
            with open(ACCOUNTS_REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Inicializa descobrindo a Conta 1 do cofre/arquivo
    conta1_file = CREDENTIALS_DIR / "conta1.json"
    conta1_email = "caiofelipegl@gmail.com"
    if conta1_file.exists():
        try:
            c1_data = json.loads(conta1_file.read_text(encoding="utf-8"))
            conta1_email = _get_account_email_from_blob(c1_data.get("blob", "{}"))
        except Exception:
            pass
    elif read_credential:
        cred = read_credential()
        if cred:
            conta1_email = _get_account_email_from_blob(cred.get("blob", "{}"))
            conta1_file.write_text(json.dumps(cred, indent=2), encoding="utf-8")

    initial_registry = {
        "agy_accounts": [
            {
                "id": "conta1",
                "label": "Antigravity Principal",
                "profile": "agy",
                "email": conta1_email,
                "credential_file": ".agents/credentials/conta1.json",
                "tier": "Pro",
                "channel": "Cofre Windows (Ativo)",
                "is_active": True,
                "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        ],
        "claude_accounts": [
            {
                "id": "claude_principal",
                "label": "Claude Code Oficial",
                "profile": "claude",
                "config_dir": None,
                "tier": "Anthropic",
                "channel": "~/.claude",
                "is_active": True,
                "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        ],
        "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    # Verifica se já existe conta2.json pré-existente
    conta2_file = CREDENTIALS_DIR / "conta2.json"
    if conta2_file.exists():
        try:
            c2_data = json.loads(conta2_file.read_text(encoding="utf-8"))
            c2_email = _get_account_email_from_blob(c2_data.get("blob", "{}"))
            initial_registry["agy_accounts"].append({
                "id": "conta2",
                "label": "Antigravity Secundária",
                "profile": "agy-conta2",
                "email": c2_email,
                "credential_file": ".agents/credentials/conta2.json",
                "tier": "Pro/Free",
                "channel": "Hot-Swap Atômico",
                "is_active": True,
                "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
        except Exception:
            pass

    save_accounts_registry(initial_registry)
    return initial_registry


def save_accounts_registry(data: Dict[str, Any]) -> None:
    data["last_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(ACCOUNTS_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    sync_registry_to_config(data)


def sync_registry_to_config(registry: Optional[Dict[str, Any]] = None) -> None:
    """Atualiza as seções dinâmicas do config.json a partir do accounts.json."""
    if not registry:
        registry = init_accounts_registry()

    if not CONFIG_FILE.exists():
        return

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {"profiles": {}}

    profiles = cfg.get("profiles", {})

    # Atualiza perfis agy
    for acc in registry.get("agy_accounts", []):
        p_name = acc["profile"]
        cred_file = acc.get("credential_file")
        
        prof_entry = {
            "command": "%LOCALAPPDATA%\\agy\\bin\\agy.exe",
            "args_template": ["-p", "{prompt}", "--dangerously-skip-permissions"],
            "env": {},
            "description": f"Antigravity CLI ({acc['label']} - {acc.get('email', '')})"
        }
        if cred_file and acc["id"] != "conta1":
            prof_entry["credential_file"] = cred_file
        profiles[p_name] = prof_entry

    # Atualiza perfis claude
    for acc in registry.get("claude_accounts", []):
        p_name = acc["profile"]
        cfg_dir = acc.get("config_dir")
        prof_entry = {
            "command": "claude",
            "args_template": ["-p", "{prompt}", "--dangerously-skip-permissions", "--output-format", "text"],
            "env": {},
            "description": f"Claude Code CLI ({acc['label']})"
        }
        if cfg_dir:
            prof_entry["env"]["CLAUDE_CONFIG_DIR"] = cfg_dir
        profiles[p_name] = prof_entry

    cfg["profiles"] = profiles
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def list_accounts() -> Dict[str, Any]:
    return init_accounts_registry()


def remove_account(tool: str, account_id: str) -> bool:
    reg = init_accounts_registry()
    key = "agy_accounts" if tool == "agy" else "claude_accounts"
    original_len = len(reg.get(key, []))
    
    # Não remove se for a última conta principal
    if account_id in ["conta1", "claude_principal"] and original_len <= 1:
        return False

    reg[key] = [acc for acc in reg.get(key, []) if acc["id"] != account_id]
    if len(reg[key]) < original_len:
        save_accounts_registry(reg)
        return True
    return False


def _run_add_agy_job(job_id: str, label: str):
    """Executa o processo de captura e cadastro de uma nova conta Google para o agy."""
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "in_progress", "step": "backup_conta_ativa", "message": "Fazendo backup seguro da conta ativa..."}

    if not read_credential or not write_credential or not delete_credential:
        with JOBS_LOCK:
            JOBS[job_id] = {"status": "error", "message": "WinCred Manager não disponível nesta plataforma."}
        return

    # 1. Backup da conta ativa
    active_cred = read_credential()
    if not active_cred:
        with JOBS_LOCK:
            JOBS[job_id] = {"status": "error", "message": "Nenhuma credencial ativa encontrada no cofre do Windows."}
        return

    reg = init_accounts_registry()
    next_idx = len(reg.get("agy_accounts", [])) + 1
    new_id = f"conta{next_idx}"
    cred_file_rel = f".agents/credentials/{new_id}.json"
    cred_file_abs = CREDENTIALS_DIR / f"{new_id}.json"

    try:
        # 2. Deleta a credencial temporariamente para forçar o login
        with JOBS_LOCK:
            JOBS[job_id] = {
                "status": "waiting_login",
                "step": "open_login",
                "message": "Abrindo login no navegador. Conclua o login na sua conta Google..."
            }
        delete_credential()

        agy_cmd = os.path.expandvars(r"%LOCALAPPDATA%\agy\bin\agy.exe")
        login_proc = subprocess.Popen(
            [agy_cmd, "-p", "Olá, autenticação de nova conta."],
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )

        # 3. Aguarda o usuário logar
        captured = None
        for _ in range(90):  # até 3 minutos de timeout
            time.sleep(2)
            c = read_credential()
            if c and c.get("blob") and c.get("blob") != active_cred.get("blob"):
                captured = c
                break

        if not captured:
            with JOBS_LOCK:
                JOBS[job_id] = {"status": "error", "message": "Tempo limite excedido ou login não concluído no navegador."}
            return

        # 4. Salva a nova credencial capturada
        cred_file_abs.write_text(json.dumps(captured, indent=2), encoding="utf-8")
        new_email = _get_account_email_from_blob(captured.get("blob", "{}"))

        # 5. Adiciona ao registro
        new_account = {
            "id": new_id,
            "label": label or f"Conta Secundária {next_idx}",
            "profile": f"agy-{new_id}",
            "email": new_email,
            "credential_file": cred_file_rel,
            "tier": "Pro/Free",
            "channel": "Hot-Swap Atômico",
            "is_active": True,
            "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        reg["agy_accounts"].append(new_account)
        save_accounts_registry(reg)

        with JOBS_LOCK:
            JOBS[job_id] = {
                "status": "success",
                "message": f"Conta '{new_email}' adicionada com sucesso como {new_id}!",
                "account": new_account
            }

    except Exception as e:
        with JOBS_LOCK:
            JOBS[job_id] = {"status": "error", "message": f"Erro durante a captura: {str(e)}"}
    finally:
        # 6. SEMPRE restaura a credencial original
        write_credential(
            username=active_cred.get("username", "antigravity"),
            blob_str=active_cred.get("blob", "")
        )


def _run_add_claude_job(job_id: str, label: str):
    """Cria e autentica um novo perfil isolado do Claude Code."""
    reg = init_accounts_registry()
    next_idx = len(reg.get("claude_accounts", [])) + 1
    new_id = f"claude_conta{next_idx}"
    profile_name = f"claude-conta{next_idx}"

    perfis_base = Path.home() / ".perfis"
    perfis_base.mkdir(parents=True, exist_ok=True)
    config_dir = perfis_base / new_id
    config_dir.mkdir(parents=True, exist_ok=True)

    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "waiting_login",
            "step": "open_login",
            "message": f"Iniciando Claude Code no perfil '{new_id}'. Conclua a autenticação na janela..."
        }

    try:
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)

        # Inicia sessão interativa do Claude Code com console próprio
        proc = subprocess.Popen(
            ["claude"],
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
        )

        # Aguarda a criação de arquivos de sessão ou encerramento
        for _ in range(60):
            time.sleep(2)
            if any(config_dir.iterdir()):
                break

        new_account = {
            "id": new_id,
            "label": label or f"Claude Conta {next_idx}",
            "profile": profile_name,
            "config_dir": str(config_dir),
            "tier": "Anthropic",
            "channel": f"Perfil Isolado ({new_id})",
            "is_active": True,
            "added_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        reg["claude_accounts"].append(new_account)
        save_accounts_registry(reg)

        with JOBS_LOCK:
            JOBS[job_id] = {
                "status": "success",
                "message": f"Perfil do Claude Code '{label}' configurado com sucesso!",
                "account": new_account
            }
    except Exception as e:
        with JOBS_LOCK:
            JOBS[job_id] = {"status": "error", "message": f"Erro ao configurar Claude: {str(e)}"}


def start_add_account_job(tool: str, label: str) -> str:
    job_id = uuid.uuid4().hex[:8]
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "queued", "tool": tool, "created_at": time.time()}

    if tool == "agy":
        t = threading.Thread(target=_run_add_agy_job, args=(job_id, label), daemon=True)
    else:
        t = threading.Thread(target=_run_add_claude_job, args=(job_id, label), daemon=True)
    t.start()
    return job_id


def get_job_status(job_id: str) -> Dict[str, Any]:
    with JOBS_LOCK:
        return JOBS.get(job_id, {"status": "not_found"})


if __name__ == "__main__":
    print("Inicializando registro de contas...")
    registry = init_accounts_registry()
    print(json.dumps(registry, indent=2, ensure_ascii=False))
