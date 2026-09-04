# 🤖 Guia de Instalação e Configuração Interativa (Instruções para a IA)

> **ATENÇÃO PARA A IA (ASSISTENTE):**  
> Este documento é uma **diretriz operacional para você**. Quando um usuário abrir este repositório e solicitar ajuda para configurar o projeto na máquina dele, **assuma o papel de Engenheiro de Onboarding**, converse com o usuário passo a passo, realize as verificações automáticas no terminal e configure todo o ecossistema de subagentes de forma interativa e amigável.

---

## 🎯 Seu Objetivo

Configurar o **Antigravity CLI Orchestrator** na máquina do usuário para que ele consiga:
1. Orquestrar múltiplos subagentes de IA via CLI (`agy`, `agy-conta2`, `claude`, `agyclaude`);
2. Utilizar 2 contas do Google Antigravity simultaneamente sem criar usuários extras no Windows;
3. Proteger a cota com a trava inteligente do **Guardrail 90%** (tarefas pesadas bloqueadas em cota baixa);
4. Ter **Failover Automático & Auto-Assunção (Self-Healing)** se qualquer conta esgotar a cota;
5. Disponibilizar a Skill globalmente no Antigravity IDE (funcionando em **qualquer chat**);
6. Abrir a interface gráfica (Dashboard Web) para monitoramento em tempo real.

---

## 📋 Protocolo de Execução Passo a Passo (Siga esta ordem)

### PASSO 1: Boas-vindas e Entrevista Inicial

Inicie a conversa cumprimentando o usuário, explicando brevemente o que é o projeto e fazendo as seguintes perguntas para entender o cenário dele:

```text
"Olá! Sou seu assistente de configuração do Antigravity CLI Orchestrator. 
Vou te guiar na configuração das suas contas e dos subagentes.

Para começarmos, me conte quais destas opções você possui:
1. Você já usa o Antigravity IDE ou agy CLI conectado na sua conta Google principal?
2. Você possui uma 2ª conta Google (institucional, corporativa ou outro Gmail) para dobrar sua cota?
3. Você possui o Claude Code oficial instalado e autenticado na Anthropic?
4. Gostaria de habilitar o agyclaude (Claude Code conectado aos modelos do Antigravity/Gemini)?"
```

---

### PASSO 2: Verificação Automática do Ambiente

Enquanto o usuário responde, execute os seguintes comandos no terminal dele para validar os pré-requisitos:

```powershell
# 1. Checar Sistema Operacional e Python
python --version

# 2. Checar Node.js e NPM
node --version
npm --version

# 3. Checar se o binário agy existe
where agy.exe

# 4. Checar se o Claude oficial existe
where claude
```

> **Critérios:**
> - Python $\ge$ 3.10 (necessário para scripts de Hot-Swap e Dashboard).
> - Node.js $\ge$ 18 (necessário para Claude Code e proxies).
> - Windows 10/11 (necessário para o gerenciador de credenciais Win32 `CredReadW`/`CredWriteW`).

---

### PASSO 3: Configuração das Contas (Conforme Respostas do Usuário)

#### Cenário A: Conta 1 do Antigravity (Principal)
A conta principal já fica armazenada no Cofre do Windows (`gemini:antigravity`).
Execute o script para capturar e fazer o backup seguro da Conta 1:

```powershell
python -c "from scripts.wincred_manager import read_credential; import json, pathlib; c = read_credential(); pathlib.Path('.agents/credentials').mkdir(parents=True, exist_ok=True); open('.agents/credentials/conta1.json', 'w', encoding='utf-8').write(json.dumps(c, indent=2)); print('Conta 1 capturada com sucesso!')"
```

#### Cenário B: Conta 2 do Antigravity (Secundária - Dobrar Cota)
Se o usuário tiver uma 2ª conta Google:
1. Explique: *"Vou abrir o navegador para você logar na sua segunda conta Google. Não se preocupe: a sua primeira conta está salva e segura."*
2. Execute o arquivo auxiliar:
   ```powershell
   .\capturar_conta_secundaria_agy.bat
   ```
3. Aguarde o usuário concluir o login no navegador. O script salvará automaticamente `.agents/credentials/conta2.json` e **restaurará a Conta 1 imediatamente no cofre**.

#### Cenário C: Claude Code Oficial (Anthropic)
Se o usuário tiver o Claude Code oficial:
- Verifique se a pasta `%USERPROFILE%\.claude` existe.
- Tranquilize o usuário: *"O orquestrador foi desenvolvido com isolamento estrito de perfil (`%USERPROFILE%\.perfis\agyclaude`). O seu login pago na Anthropic nunca será sobrescrito ou afetado."*

#### Cenário D: agyclaude (Claude Code via Antigravity)
Se o usuário quiser o `agyclaude`:
1. Instale o pacote a partir do fork mantido:
   ```powershell
   npm install -g https://github.com/CaioFelipe/agy_claude.git
   ```
2. Sincronize as contas salvas diretamente para o proxy:
   ```powershell
   python .agents/skills/cli-orchestrator/scripts/sync_agy_to_proxy.py
   ```

---

### PASSO 4: Instalar a Skill Globalmente no Antigravity IDE

Para que o usuário possa usar o comando de subagentes em **qualquer novo chat ou projeto que ele abrir no Antigravity**:

1. Crie o diretório global de skills:
   ```powershell
   New-Item -ItemType Directory -Path "$env:USERPROFILE\.gemini\config\skills\cli-orchestrator" -Force
   ```
2. Copie o arquivo `SKILL.md` atualizado para o diretório global:
   ```powershell
   Copy-Item -Path ".agents\skills\cli-orchestrator\SKILL.md" -Destination "$env:USERPROFILE\.gemini\config\skills\cli-orchestrator\SKILL.md" -Force
   ```
3. Informe ao usuário: *"A Skill do Orquestrador agora está instalada globalmente! Qualquer chat que você abrir no Antigravity reconhecerá os subagentes automaticamente."*

---

### PASSO 5: Teste de Validação e Inicialização do Dashboard

Execute um teste de pipeline para confirmar que tudo está funcionando:

```powershell
# 1. Teste simulado rápido (zero tokens)
python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile mock --prompt "Teste de Onboarding"

# 2. Iniciar o Dashboard Web e abrir no navegador
.\abrir_dashboard.bat
```

Apresente ao usuário o link: `http://localhost:5050` e mostre que ele pode visualizar:
- O status de todas as contas conectadas;
- Os medidores de cota com o Guardrail 90% ativo;
- Os botões de ação para testar subagentes em tempo real.

---

## 🔒 Regras Críticas de Segurança para a IA

> [!CAUTION]
> 1. **NUNCA faça commit ou push de arquivos dentro de `.agents/credentials/`**, de arquivos `.json.secret` ou de `accounts.json`.
> 2. Verifique sempre o arquivo `.gitignore` antes de rodar qualquer comando Git.
> 3. Nunca exiba tokens OAuth ou refresh tokens em texto plano para o usuário no chat.

---

## ❓ FAQ & Solução Rápida de Problemas

- **Erro `Port 8080 already in use`:**  
  O proxy do `agyclaude` encerra automaticamente quando ocioso. Se ficou algum processo preso, rode `antigravity-claude-proxy stop` ou use o botão no Dashboard.
- **Erro `RESOURCE_EXHAUSTED`:**  
  O orquestrador possui **Failover Automático**. Ele tentará a próxima conta (`agy-conta2` ou `claude`) e, se todas falharem, o próprio agente do IDE assume o restante do trabalho sem travar o usuário.
- **Como alterar a cota manualmente para testar o Guardrail 90%:**  
  Acesse `http://localhost:5050`, clique em "Resetar" no card de cota ou execute:
  ```powershell
  python -c "from scripts.quota_guard import set_profile_consumption; set_profile_consumption('agy', 92.0)"
  ```
