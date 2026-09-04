#!/usr/bin/env python3
"""
CLI Subagent Bridge for Antigravity
Orchestrates external AI CLI tools (e.g. agy, claude, aider) as headless subagents.
"""

import os
import sys
import json
import time
import uuid
import argparse
import subprocess
from contextlib import nullcontext
from pathlib import Path

# Add scripts directory to sys.path for wincred_manager
scripts_dir = Path(__file__).resolve().parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

try:
    from wincred_manager import TemporaryCredentialSwap
except ImportError:
    TemporaryCredentialSwap = None

try:
    from proxy_manager import ManagedProxyContext
except ImportError:
    ManagedProxyContext = None


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {
            "profiles": {},
            "default_timeout_seconds": 300,
            "tasks_directory": ".agents/tasks"
        }
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_env_vars(env_dict: dict) -> dict:
    resolved = os.environ.copy()
    for key, value in env_dict.items():
        if isinstance(value, str):
            expanded = os.path.expandvars(value)
            resolved[key] = expanded
    return resolved


def main():
    parser = argparse.ArgumentParser(description="CLI Subagent Bridge for Antigravity")
    parser.add_argument("--profile", default="mock", help="Profile name from config.json (e.g. mock, agy, claude, aider)")
    parser.add_argument("--prompt", required=True, help="Instruction/prompt for the subagent")
    parser.add_argument("--files", nargs="*", default=[], help="Optional list of context files to append or inject")
    parser.add_argument("--task-id", default=None, help="Identifier for the task (default: auto-generated)")
    parser.add_argument("--timeout", type=int, default=None, help="Command timeout in seconds")
    parser.add_argument("--config", default=None, help="Path to config.json")
    parser.add_argument("--cwd", default=None, help="Working directory for the subagent")

    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    config_file = Path(args.config) if args.config else (base_dir / "config.json")
    config = load_config(config_file)

    profiles = config.get("profiles", {})
    if args.profile not in profiles:
        print(json.dumps({
            "status": "error",
            "message": f"Profile '{args.profile}' not found in configuration. Available profiles: {list(profiles.keys())}"
        }, indent=2))
        sys.exit(1)

    profile = profiles[args.profile]
    timeout = args.timeout or config.get("default_timeout_seconds", 300)
    task_id = args.task_id or f"task_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    working_dir = Path(args.cwd) if args.cwd else Path.cwd()

    tasks_dir = working_dir / config.get("tasks_directory", ".agents/tasks")
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Context file aggregation if specified
    context_text = ""
    if args.files:
        context_blocks = []
        for file_path_str in args.files:
            file_path = working_dir / file_path_str
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    context_blocks.append(f"--- FILE: {file_path_str} ---\n{content}\n")
                except Exception as e:
                    context_blocks.append(f"--- FILE: {file_path_str} (error reading: {e}) ---")
        if context_blocks:
            context_text = "\n\nRelevant Context Files:\n" + "\n".join(context_blocks)

    full_prompt = args.prompt + context_text

    # Write task specification
    spec_data = {
        "task_id": task_id,
        "profile": args.profile,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prompt": args.prompt,
        "context_files": args.files,
        "timeout_seconds": timeout
    }
    spec_path = tasks_dir / f"{task_id}_spec.json"
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(spec_data, f, indent=2, ensure_ascii=False)

    # Check Quota Guardrail (90% threshold rule)
    try:
        from scripts.quota_guard import can_execute_task, record_task_execution, set_profile_consumption, classify_task_size
        can_run, task_size, guard_reason = can_execute_task(args.profile, args.prompt, args.files)
        if not can_run:
            print(f"[QUOTA GUARDRAIL] Bloqueado no perfil '{args.profile}': {guard_reason}", file=sys.stderr)
            # Tenta encontrar um perfil alternativo
            candidate_profiles = ["agy", "agy-conta2", "claude"]
            alt_profile = next((p for p in candidate_profiles if p != args.profile and can_execute_task(p, args.prompt, args.files)[0]), None)
            if alt_profile:
                print(f"[QUOTA GUARDRAIL] Redirecionando tarefa automaticamente para perfil alternativo '{alt_profile}'...", file=sys.stderr)
                args.profile = alt_profile
                profile = config.get("profiles", {}).get(alt_profile, {})
            else:
                summary_response = {
                    "status": "blocked_by_quota",
                    "task_id": task_id,
                    "profile": args.profile,
                    "task_size": task_size,
                    "reason": guard_reason,
                    "fallback_to_ide": True,
                    "takeover_prompt": args.prompt,
                    "error": "Todos os perfis externos estão com cota crítica (90%+) ou esgotados. A tarefa deve ser realizada pelo IDE diretamente."
                }
                print(json.dumps(summary_response, indent=2, ensure_ascii=False))
                return
    except ImportError:
        pass

    def check_quota_error(text: str) -> bool:
        lower = text.lower()
        patterns = [
            "resource_exhausted",
            "exhausted your capacity",
            "model_capacity_exhausted",
            "quota exceeded",
            "quota_exhausted",
            "rate limit exceeded",
            "rate_limited",
            "429 too many requests",
            "error: 400 resource_exhausted"
        ]
        return any(p in lower for p in patterns)

    def execute_profile(curr_profile_name, attempt=1, max_attempts=3):
        curr_profile = config.get("profiles", {}).get(curr_profile_name, {})
        if not curr_profile:
            return "error", 1, "", f"Perfil '{curr_profile_name}' não encontrado.", 0.0

        # Build command arguments
        cmd_str = os.path.expandvars(curr_profile.get("command"))
        tmpl_args = curr_profile.get("args_template", ["{prompt}"])
        full_args = [cmd_str]
        for arg_template in tmpl_args:
            full_args.append(arg_template.replace("{prompt}", full_prompt))

        # Environment variables
        env_vars = resolve_env_vars(curr_profile.get("env", {}))

        # Check for credential hot-swap
        c_file = curr_profile.get("credential_file")
        if c_file and TemporaryCredentialSwap:
            swap_ctx = TemporaryCredentialSwap(working_dir / c_file)
        else:
            swap_ctx = nullcontext()

        # Check for proxy requirement
        n_proxy = curr_profile.get("needs_proxy", False)
        p_port = curr_profile.get("proxy_port", 8080)
        if n_proxy and ManagedProxyContext:
            proxy_ctx = ManagedProxyContext(working_dir, p_port)
        else:
            proxy_ctx = nullcontext()

        st_time = time.time()
        s_status = "success"
        e_code = 0
        s_out = ""
        s_err = ""
        err_msg = ""

        try:
            with proxy_ctx, swap_ctx:
                proc = subprocess.run(
                    full_args,
                    cwd=str(working_dir),
                    env=env_vars,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=(sys.platform == "win32" and not cmd_str.endswith(".exe") and cmd_str != "python")
                )
                e_code = proc.returncode
                s_out = proc.stdout
                s_err = proc.stderr
                if e_code != 0:
                    s_status = "failed"
                    err_msg = f"CLI process exited with non-zero status code: {e_code}"
        except subprocess.TimeoutExpired as te:
            s_status = "timeout"
            e_code = -1
            s_out = te.stdout if te.stdout else ""
            s_err = te.stderr if te.stderr else ""
            err_msg = f"Command timed out after {timeout} seconds"
        except FileNotFoundError:
            s_status = "error"
            e_code = 127
            err_msg = f"CLI executable '{cmd_str}' not found on system PATH."
        except Exception as e:
            s_status = "error"
            e_code = 1
            err_msg = str(e)

        dur = round(time.time() - st_time, 2)

        # Detect Quota Exhaustion during run
        combined_text = s_out + " " + s_err
        if check_quota_error(combined_text):
            print(f"[FAILOVER ALERT] Perfil '{curr_profile_name}' atingiu esgotamento de cota!", file=sys.stderr)
            try:
                from scripts.quota_guard import set_profile_consumption
                set_profile_consumption(curr_profile_name, 100.0)
            except Exception:
                pass

            # Fallback Chain
            fallback_map = {
                "agy": "agy-conta2",
                "agy-conta2": "claude",
                "agyclaude": "agy",
                "claude": "agy"
            }
            next_prof = fallback_map.get(curr_profile_name)
            if next_prof and attempt < max_attempts:
                print(f"[AUTO-FAILOVER] Repassando tarefa automaticamente para '{next_prof}' (Tentativa {attempt + 1})...", file=sys.stderr)
                return execute_profile(next_prof, attempt=attempt + 1, max_attempts=max_attempts)
            else:
                # All CLIs exhausted - mark for IDE Takeover
                s_status = "requires_ide_takeover"
                err_msg = "Todas as CLIs externas esgotaram cota. Auto-assunção necessária pelo IDE."

        return s_status, e_code, s_out, s_err, err_msg, dur, curr_profile_name

    status, exit_code, stdout_output, stderr_output, error_message, duration_seconds, final_profile = execute_profile(args.profile)

    # Record execution metrics
    try:
        from scripts.quota_guard import record_task_execution, classify_task_size
        record_task_execution(final_profile, is_heavy=(classify_task_size(args.prompt, args.files) == "HEAVY"))
    except Exception:
        pass

    result_data = {
        "task_id": task_id,
        "requested_profile": args.profile,
        "final_profile": final_profile,
        "status": status,
        "exit_code": exit_code,
        "duration_seconds": duration_seconds,
        "error_message": error_message,
        "fallback_to_ide": (status == "requires_ide_takeover"),
        "stdout": stdout_output,
        "stderr": stderr_output,
        "spec_file": str(spec_path.relative_to(working_dir)).replace("\\", "/"),
    }

    # Save JSON result
    result_json_path = tasks_dir / f"{task_id}_result.json"
    with open(result_json_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    # Save Markdown report for easy reading
    result_md_path = tasks_dir / f"{task_id}_result.md"
    with open(result_md_path, "w", encoding="utf-8") as f:
        f.write(f"# Subagent Task Result: {task_id}\n\n")
        f.write(f"- **Requested Profile:** `{args.profile}`\n")
        f.write(f"- **Executed By:** `{final_profile}`\n")
        f.write(f"- **Status:** `{status}`\n")
        f.write(f"- **Duration:** {duration_seconds}s\n")
        f.write(f"- **Exit Code:** {exit_code}\n\n")
        if status == "requires_ide_takeover":
            f.write("> [!CAUTION]\n> **Auto-Assunção Requerida:** Cotas externas esgotadas. O Agente Principal do Antigravity IDE deve assumir esta tarefa diretamente.\n\n")
        if error_message:
            f.write(f"### Error\n```\n{error_message}\n```\n\n")
        f.write("### Output\n\n")
        f.write(f"```\n{stdout_output.strip()}\n```\n\n")
        if stderr_output.strip():
            f.write("### Stderr\n\n")
            f.write(f"```\n{stderr_output.strip()}\n```\n")

    summary_response = {
        "status": status,
        "task_id": task_id,
        "profile": final_profile,
        "exit_code": exit_code,
        "duration_seconds": duration_seconds,
        "fallback_to_ide": (status == "requires_ide_takeover"),
        "result_file": str(result_json_path.relative_to(working_dir)).replace("\\", "/"),
        "report_file": str(result_md_path.relative_to(working_dir)).replace("\\", "/"),
        "output_preview": (stdout_output[:500] + "...") if len(stdout_output) > 500 else stdout_output.strip(),
        "error": error_message if error_message else None
    }

    print(json.dumps(summary_response, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
