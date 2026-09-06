---
name: claude-architect
description: >-
  Planejamento de estruturas de sistemas, resolução de problemas complexos e discussão
  de decisões arquiteturais utilizando Claude Sonnet via Antigravity CLI Orchestrator.
---

# Planejador Arquitetural & Especialista Claude Sonnet

Esta Skill instrui o agente do Antigravity a consultar ativamente o **Claude Sonnet** (via CLI oficial do Claude Code) sempre que for necessário:
1. **Planejar Estruturas de Sistemas:** Definir arquiteturas de software (Clean Architecture, microsserviços, monólitos modulares), modelagem de banco de dados (relacional/NoSQL), schemas de API e estruturação de pastas e módulos.
2. **Resolver Problemas Complexos:** Investigar bugs desafiadores, problemas de concorrência, otimização crítica de desempenho, memory leaks ou algoritmos complexos.
3. **Discutir Decisões Técnicas:** Avaliar trade-offs de engenharia, seleção de bibliotecas/frameworks, estratégias de migração e decisões de design.

---

## 🚀 Como Invocar o Claude Sonnet

Execute o comando bridge do orquestrador via terminal PowerShell:

```powershell
python "$env:USERPROFILE\.gemini\config\skills\cli-orchestrator\scripts\cli_bridge.py" --profile claude --prompt "<instrução da tarefa em português>" [--files <arquivo1> <arquivo2>]
```

### Parâmetros:
- `--profile claude`: Direciona a consulta ao Claude Code oficial (Claude Sonnet).
- `--prompt`: O briefing claro do problema, arquitetura a ser desenhada ou decisão a ser tomada.
- `--files`: Lista de arquivos de código ou documentação relevantes para dar contexto completo.
- `--cwd`: Diretório de trabalho atual do projeto.

---

## 📋 Diretrizes Operacionais para o Antigravity

- **Antes de Grandes Decisões:** Quando o usuário solicitar uma nova funcionalidade de grande porte, um novo sistema ou refatoração estrutural, execute uma chamada ao Claude Sonnet para obter uma segunda opinião arquitetural e validar riscos antes de propor o plano definitivo.
- **Leitura do Resultado:** O resultado completo da análise do Claude Sonnet será salvo em `.agents/tasks/<task_id>_result.md`. Leia o arquivo, sintetize as conclusões e apresente-as ao usuário em português brasileiro.
- **Failover / Guardrail:** Se o Claude Code esgotar a cota (`429` ou `RESOURCE_EXHAUSTED`), o orquestrador fará failover automático e, em última instância, você (Antigravity IDE) assumirá a resolução diretamente.
