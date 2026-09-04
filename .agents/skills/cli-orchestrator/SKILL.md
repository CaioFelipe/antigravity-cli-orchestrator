---
name: cli-orchestrator
description: >-
  Orchestrates external CLI-based AI subagents (agy Conta 1, agy Conta 2 via WinCred Hot-Swap,
  Claude Code Anthropic, agyclaude) across multiple accounts to distribute token usage,
  prevent quota exhaustion with a 90% guardrail, and execute tasks in parallel with
  automatic failover and IDE self-healing.
---

# CLI Subagent Orchestrator & Multi-Account Manager

This skill allows Antigravity to delegate work to external AI subagents running in the terminal, distributing token consumption across multiple paid subscriptions and preventing quota exhaustion.

---

## 🎯 When to Use This Skill

1. **Distribute Token Quotas:** You have multiple accounts (e.g. Antigravity Pro Account 1, Antigravity Pro Account 2, Claude Pro) and want to conserve quotas.
2. **Parallel Task Execution:** Delegate independent subtasks (writing tests, creating modules, translating documentation) to subagents while you work on the core codebase.
3. **Heavy / Context-Intensive Work:** Offload huge files or repetitive coding tasks to external CLIs without saturating the IDE's active conversation context window.
4. **Peer Review / Multi-Model Validation:** Ask Claude Code or another subagent to review code or provide an alternative implementation.

---

## 🤖 Available Subagent Profiles

| Perfil | Descrição | Canal / Mecanismo | Melhor Para |
| :--- | :--- | :--- | :--- |
| **`agy`** | Antigravity Conta 1 (Principal) | Binário nativo `agy.exe` | Tarefas gerais, refatorações, código Gemini 3.8 Flash / 3.1 Pro |
| **`agy-conta2`** | Antigravity Conta 2 (Secundária) | Hot-Swap atômico no cofre do Windows (`wincred_manager.py`) | Consumir cota da 2ª assinatura em paralelo |
| **`claude`** | Claude Code Oficial (Anthropic) | CLI nativa `claude` (isolada de conflitos) | Revisão de código, testes, modelos Claude Sonnet / Opus |
| **`agyclaude`** | Claude Code via Antigravity Proxy | Proxy local sob demanda (porta 8080) | Uso da interface do Claude Code com backend Google |
| **`mock`** | Subagente Simulado | Script Python local | Testes rápidos de pipeline com zero consumo de tokens |

---

## 🛡️ Guardrail de Cota 90% (Classificação Inteligente de Tarefas)

O orquestrador implementa uma política ativa de proteção para evitar que qualquer conta esgote completamente a cota:

- **Consumo < 90%:** O subagente pode receber tarefas de qualquer porte (`MICRO` ou `HEAVY`).
- **Consumo $\ge$ 90% (Modo Econômico):**
  - **Tarefas Pesadas (`HEAVY`):** Prompts longos (>280 caracteres), múltiplos arquivos pesados ou refatorações amplas são **bloqueados** preventivamente para esse perfil.
  - **Micro-tarefas (`MICRO`):** Consultas rápidas, perguntas pontuais ou checagens de sintaxe continuam liberadas.
  - **Redirecionamento Automático:** O orquestrador tenta automaticamente redirecionar tarefas pesadas para outra conta disponível com cota saudável.

---

## 🔄 Failover Autônomo & Auto-Assunção (Self-Healing)

Se qualquer CLI externa retornar erro de exaustão durante a execução (`RESOURCE_EXHAUSTED`, `429 Too Many Requests`, `capacity exhausted` ou `Rate limit`):

1. **Cadeia de Failover:** O orquestrador detecta a falha e repassa a tarefa automaticamente para a próxima conta na cadeia (`agyclaude` ➔ `agy` ➔ `agy-conta2` ➔ `claude`).
2. **Auto-Assunção pelo IDE:** Se todas as contas externas estiverem esgotadas, a execução retorna com status:
   ```json
   { "status": "requires_ide_takeover", "fallback_to_ide": true }
   ```
   **REGRA DE CONDUTA PARA O AGENTE:** Quando `fallback_to_ide: true` for retornado, o próprio agente atual do Antigravity IDE **deve assumir a tarefa imediatamente** e executar as alterações ou o código diretamente no workspace por conta própria, garantindo que o usuário nunca fique travado.

---

## 💻 Como Executar Subagents

O orquestrador está centralizado no script bridge universal:

### Comando de Execução Rápida:
```powershell
python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile <perfil> --prompt "<instrução da tarefa>" [--cwd <diretório_de_trabalho>] [--files <arquivo1> <arquivo2>]
```

### Exemplos de Uso:

#### 1. Delegar criação de testes para o `agy` (Conta 1):
```powershell
python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile agy --prompt "Escreva testes unitários completos em pytest para a classe Calculadora" --files src/calculadora.py
```

#### 2. Delegar refatoração para a Conta 2 (`agy-conta2` via Hot-Swap):
```powershell
python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile agy-conta2 --prompt "Otimize a consulta SQL em db_service.py para usar índices" --files src/db_service.py
```

#### 3. Delegar revisão para o `claude` (Anthropic):
```powershell
python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile claude --prompt "Analise security vulnerabilities em auth.py e sugira melhorias" --files src/auth.py
```

---

## 📊 Como Verificar Cotas & Abrir o Dashboard

### Checar cota via linha de comando:
```powershell
python .agents/skills/cli-orchestrator/scripts/quota_guard.py <perfil> "<prompt>"
```

### Abrir o Dashboard Web Interativo:
Execute o atalho:
```powershell
.\abrir_dashboard.bat
```
Ou acesse `http://localhost:5050` no navegador para visualizar os medidores em tempo real e gerenciar as contas.
