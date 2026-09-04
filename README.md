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

### 1. 👥 Multi-Contas sem Troca de Usuário no Windows (Hot-Swap)
- Utiliza a API nativa da Win32 (`CredReadW` / `CredWriteW`) para alternar credenciais OAuth salvas no Cofre do Windows em milissegundos.
- Use a **Conta 1 (Principal)** e a **Conta 2 (Secundária)** simultaneamente, dobrando sua cota de tokens.

### 2. 🛡️ Guardrail de Cota 90% (Classificador Inteligente)
- Monitora em tempo real a cota de cada CLI.
- Quando o consumo atinge 90% ou mais, o sistema ativa o **Modo Econômico**:
  - **Tarefas Pesadas (`HEAVY`):** Bloqueadas preventivamente para evitar zerar a conta.
  - **Micro-tarefas (`MICRO`):** Perguntas pontuais e testes rápidos continuam autorizados.

### 3. 🔄 Failover Autônomo & Auto-Assunção (Self-Healing)
- Se qualquer CLI esgotar a cota no meio do caminho (`RESOURCE_EXHAUSTED` / `429`), o orquestrador repassa a tarefa automaticamente para o próximo perfil.
- Se todas as CLIs externas esgotarem, o **próprio Agente do Antigravity IDE assume o restante do trabalho** diretamente no workspace sem travar o fluxo.

### 4. 🖥️ Interface Gráfica Amigável (Web Dashboard)
- Painel interativo moderno com Glassmorphism e Tailwind CSS rodando localmente em `http://localhost:5050`.
- Medidores de cota com cores dinâmicas e alertas de 90%.
- Ações rápidas: sincronização de contas, controle do proxy e console de execução de subagentes.
- **Como abrir:** Dê dois cliques em `abrir_dashboard.bat`.

### 5. 🌐 Skill Global do Antigravity
- A Skill está instalada globalmente em `%USERPROFILE%\.gemini\config\skills\cli-orchestrator\SKILL.md`.
- **Qualquer novo chat ou projeto** aberto no Antigravity reconhece e usa os subagentes nativamente.

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
