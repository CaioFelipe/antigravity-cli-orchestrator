#!/usr/bin/env python3
"""
Stress Test Runner: Dispatches 5 parallel subagent sessions across distinct CLI profiles.
Monitors execution, race conditions, credential stability, and outputs a consolidated report.
"""

import sys
import time
import json
import concurrent.futures
import subprocess
from pathlib import Path

PROFILES_TO_TEST = [
    {
        "id": "worker_1_claude",
        "profile": "claude",
        "task_id": "stress_claude",
        "prompt": "Crie um arquivo 'stress_claude.py' contendo uma funcao de ordenacao quicksort com tipagem e testes unitarios executaveis no final. Ao terminar confirme a criacao."
    },
    {
        "id": "worker_2_agy",
        "profile": "agy",
        "task_id": "stress_agy",
        "prompt": "Crie um arquivo 'stress_agy.py' contendo uma funcao de busca binaria com tipagem e testes unitarios executaveis no final. Ao terminar confirme a criacao."
    },
    {
        "id": "worker_3_agy_conta2",
        "profile": "agy-conta2",
        "task_id": "stress_agy_conta2",
        "prompt": "Crie um arquivo 'stress_agy_conta2.py' contendo uma funcao de hash sha256 com testes unitarios executaveis no final. Ao terminar confirme a criacao."
    },
    {
        "id": "worker_4_agyclaude",
        "profile": "agyclaude",
        "task_id": "stress_agyclaude",
        "prompt": "Crie um arquivo 'stress_agyclaude.py' contendo uma funcao geradora de numeros de fibonacci com testes unitarios executaveis no final. Ao terminar confirme a criacao."
    },
    {
        "id": "worker_5_mock",
        "profile": "mock",
        "task_id": "stress_mock",
        "prompt": "Subagente mock: validando barramento de concorrencia e latencia de pipeline."
    }
]

def run_single_worker(item):
    worker_id = item["id"]
    profile = item["profile"]
    task_id = item["task_id"]
    prompt = item["prompt"]

    print(f"[{time.strftime('%H:%M:%S')}] Iniciando {worker_id} ({profile})...")
    start = time.time()

    bridge_script = Path(__file__).resolve().parent / "cli_bridge.py"
    cmd = [
        sys.executable,
        str(bridge_script),
        "--profile", profile,
        "--prompt", prompt,
        "--task-id", task_id
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180
        )
        duration = round(time.time() - start, 2)
        try:
            summary = json.loads(proc.stdout)
        except Exception:
            summary = {
                "status": "error" if proc.returncode != 0 else "success",
                "output_preview": proc.stdout[:300] if proc.stdout else proc.stderr[:300]
            }

        return {
            "worker": worker_id,
            "profile": profile,
            "status": summary.get("status", "unknown"),
            "exit_code": proc.returncode,
            "duration": duration,
            "output_preview": summary.get("output_preview", "")
        }
    except subprocess.TimeoutExpired:
        return {
            "worker": worker_id,
            "profile": profile,
            "status": "timeout",
            "exit_code": -1,
            "duration": round(time.time() - start, 2),
            "output_preview": "Timeout apos 180s"
        }
    except Exception as e:
        return {
            "worker": worker_id,
            "profile": profile,
            "status": "exception",
            "exit_code": 1,
            "duration": round(time.time() - start, 2),
            "output_preview": str(e)
        }

def main():
    print("=" * 70)
    print("      TESTE DE ESTRESSE: 5 SESSOES PARALELAS CONCORRENTES")
    print("=" * 70)
    print(f"Disparando {len(PROFILES_TO_TEST)} subagentes simultaneamente...\n")

    overall_start = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_single_worker, item) for item in PROFILES_TO_TEST]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            print(f"[{time.strftime('%H:%M:%S')}] Concluido: {res['worker']} ({res['profile']}) -> {res['status']} em {res['duration']}s")
            results.append(res)

    total_time = round(time.time() - overall_start, 2)

    print("\n" + "=" * 70)
    print(f"              RESULTADO FINAL (Tempo Total: {total_time}s)")
    print("=" * 70)
    for r in sorted(results, key=lambda x: x["worker"]):
        status_tag = "[OK] " if r["status"] == "success" else "[FALHA]"
        print(f"{status_tag} {r['worker']:22} | Perfil: {r['profile']:12} | Tempo: {r['duration']:5}s | Saida: {r['output_preview'][:50]}...")

    # Save summary report
    report_file = Path(".agents/tasks/stress_test_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_time_seconds": total_time,
            "workers": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\nRelatorio completo salvo em: {report_file}")

if __name__ == "__main__":
    main()
