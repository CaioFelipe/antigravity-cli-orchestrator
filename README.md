# 🚀 Antigravity CLI Orchestrator

> **Orquestrador de Subagentes CLI Multi-Contas para Antigravity IDE, Claude Code e Gemini.**  
> Distribua o consumo de tokens entre múltiplas assinaturas, execute tarefas em paralelo, proteja suas cotas com o Guardrail 90% e conte com recuperação autônoma (Self-Healing).

---

## 🤖 Para Assistentes de IA (Onboarding Automatizado)

Se você é uma IA (Antigravity, Claude Code, Cursor, Copilot) ajudando um usuário a instalar ou rodar este projeto, **leia imediatamente o arquivo dedicado de onboarding:**

👉 **[INSTRUCTIONS_FOR_AI.md](./INSTRUCTIONS_FOR_AI.md)** 👈

Ele contém o roteiro passo a passo com todas as perguntas interativas e comandos para você rodar no terminal do usuário.

---

## ✨ Principais Recursos

### 1. 📊 Monitoramento de Cotas 100% Real (5h & Semanal)
- Captura métricas reais diretamente das CLIs oficiais (`agy -p "/usage"` e `claude -p "/usage"`).
- Medidores duplos por conta: **Janela de 5 Horas** (com hora exata de renovação) e **Limite Semanal** (com data de reset).
- Cache assíncrono com TTL (`usage_cache.py`) garantindo navegação instantânea no Dashboard sem bloquear chamadas.

### 2. 👥 Multi-Contas Dinâmico e Escalável ($N$ Contas)
- **Google Antigravity:** Permite cadastrar $N$ contas alternadas via Hot-Swap atômico na API Win32 (`CredReadW`/`CredWriteW`) sem criar usuários no Windows.
- **Claude Code (Anthropic):** Permite adicionar múltiplos perfis independentes com isolamento total via `CLAUDE_CONFIG_DIR` (`%USERPROFILE%\.perfis\claude_contaN`).
- Interface interativa com botões **"+ Adicionar Conta"** e exclusão segura.

### 3. 🛡️ Guardrail de Cota 90% (Classificador Inteligente)
- Monitora em tempo real a cota de cada CLI a partir do gargalo mais restritivo.
- Quando o consumo atinge 90% ou mais, o sistema ativa o **Modo Econômico**:
  - **Tarefas Pesadas (`HEAVY`):** Bloqueadas preventivamente para evitar zerar a conta.
  - **Micro-tarefas (`MICRO`):** Perguntas pontuais e testes rápidos continuam autorizados.

### 4. 🔄 Failover Autônomo & Auto-Assunção (Self-Healing)
- Se qualquer CLI esgotar a cota no meio do caminho (`RESOURCE_EXHAUSTED` / `429`), o orquestrador repassa a tarefa automaticamente para o próximo perfil com maior folga.
- Se todas as CLIs externas esgotarem, o **próprio Agente do Antigravity IDE assume o restante do trabalho** diretamente no workspace sem travar o fluxo.

### 5. 🖥️ Interface Gráfica Web Dinâmica (Dashboard)
- Painel interativo moderno com Glassmorphism e Tailwind CSS rodando localmente em `http://localhost:5050`.
- Métricas 100% reais de todas as contas conectadas, sem dados mockados.
- Console de execução em tempo real, controle de proxy e gerenciamento de contas.
- **Como abrir:** Dê dois cliques em `abrir_dashboard.bat`.

### 6. 🌐 Skills Globais do Antigravity
- **`cli-orchestrator`:** Orquestração de subagentes CLI multi-contas.
- **`claude-architect`:** Planejamento arquitetural, estruturas de sistemas e resolução de problemas complexos delegados diretamente ao **Claude Sonnet**.
- Disponíveis globalmente em `%USERPROFILE%\.gemini\config\skills\`.

---

## 📂 Estrutura do Projeto

```text
splendid-fermi/
├── .agents/
│   └── skills/
│       └── cli-orchestrator/
│           ├── SKILL.md                  # Definição e runbook da Skill
│           ├── config.json               # Perfis de subagentes (agy, agy-conta2, claude, etc.)
│           ├── scripts/
│           │   ├── cli_bridge.py         # Ponte de execução com failover
│           │   ├── quota_guard.py        # Guardrail 90% e classificador de tarefas
│           │   ├── wincred_manager.py    # Hot-swap seguro do cofre Windows
│           │   ├── proxy_manager.py      # Ciclo de vida sob demanda do proxy
│           │   ├── dashboard_server.py   # Servidor web local zero-dependency
│           │   └── sync_agy_to_proxy.py  # Sincronizador de credenciais
│           └── web/
│               └── dashboard.html        # Interface gráfica web interativa
├── INSTRUCTIONS_FOR_AI.md                # Guia de instalação para assistentes de IA
├── abrir_dashboard.bat                   # Atalho de 1 clique para o Dashboard
├── capturar_conta_secundaria_agy.bat     # Captura da Conta 2 com backup seguro da Conta 1
└── .gitignore                            # Blindagem absoluta de credenciais
```

---

## 🚀 Como Iniciar

1. **Abrir o Dashboard Web:**
   Execute `.\abrir_dashboard.bat` e acesse `http://localhost:5050`.
2. **Executar um subagente via terminal:**
   ```powershell
   python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile agy --prompt "Sua instrução aqui"
   ```

---

## 🔒 Segurança de Credenciais

Este projeto foi desenhado com segurança em primeiro lugar:
- O arquivo `.gitignore` exclui estritamente `.agents/credentials/`, `accounts.json`, `.perfis/` e arquivos de tokens.
- Nenhuma credencial ou token privado é enviado ao Git.
