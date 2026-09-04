---
name: cli-orchestrator
description: >-
  Orchestrates external CLI-based AI subagents (e.g. agy with secondary account,
  claude-code, aider) to distribute token usage, expand effective context window,
  and run parallel decoupled tasks.
---

# CLI Subagent Orchestrator

This skill enables Antigravity to delegate subtasks to other AI models or secondary accounts running via terminal CLIs.

## When to Use This Skill

1. **Distribute Token Quotas:** You have multiple accounts (e.g. a secondary Antigravity account or Claude Pro account) and want to conserve the IDE's quota.
2. **Expand Effective Context Window:** You need to analyze or refactor multiple large files or submodules without saturating the primary conversation context.
3. **Decompose Complex Tasks:** Break down a large feature into modular, isolated tasks (e.g. creating test suites, drafting boilerplates, translating docs) that can be dispatched to subagents.
4. **Cross-Vendor Comparison / Peer Review:** Ask Claude Code or another AI CLI to review code or generate an alternative implementation.

---

## How to Execute Subagents

The primary execution entry point is the bridge runner:
```powershell
python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile <profile> --prompt "<instruction>" [--files <file1> <file2>] [--task-id <id>]
```

### Profiles Available in `config.json`

- `agy`: Antigravity CLI conectado à Conta 1 principal.
- `agy-conta2`: Antigravity CLI com Hot-Swap dinâmico para a Conta 2 secundária.
- `claude`: Claude Code CLI oficial autenticado na conta Anthropic.
- `agyclaude`: Claude Code modificado com backend Antigravity/Gemini e perfil isolado em `%USERPROFILE%\.perfis\agyclaude`.
- `mock`: Subagente simulado rápido para testes sem custo de tokens e verificação de pipeline.

---

## Standard Workflow

### 1. Structure the Subagent Prompt
Make instructions self-contained and explicit:
- State the objective clearly.
- Specify the input files and expected output files or structure.
- Request non-interactive, direct execution.

### 2. Dispatch the Task

**Synchronous execution (for quick tasks < 30s):**
```powershell
python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile claude --prompt "Implement unit tests for math_utils.py" --files src/math_utils.py
```

**Asynchronous background execution (for long tasks):**
Run using `run_command` with low `WaitMsBeforeAsync` (e.g. 500ms) to launch it as a background task. Monitor with `manage_task`.

### 3. Read and Integrate Results
The runner automatically outputs:
- A brief JSON summary to stdout.
- Full results in `.agents/tasks/<task_id>_result.json`.
- A human-readable Markdown report in `.agents/tasks/<task_id>_result.md`.

Inspect the result, review any files changed by the subagent in the workspace, and report progress or continue development.
