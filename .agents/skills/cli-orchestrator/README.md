# Guia de Configuração: CLI Subagent Orchestrator

Este sistema permite que o **Antigravity IDE** comande outras IAs via linha de comando (CLI), distribuindo tokens entre contas e aumentando a capacidade de contexto através de subagentes paralelos.

---

## 1. Como Usar Duas Contas do Antigravity (`agy`) via Hot-Swap

Não é necessário criar usuários adicionais no Windows nem mexer em configurações complicadas!

### Passo 1: Capturar o token da sua Conta 2
Execute o assistente com um duplo clique em:
`C:\Users\aluno\Documents\antigravity\splendid-fermi\capturar_conta_secundaria_agy.bat`
*(ou execute no terminal `.\capturar_conta_secundaria_agy.bat`)*

- Ele abrirá o navegador.
- Escolha **"Usar outra conta"** e faça login com sua **Conta 2**.
- O assistente captura o token, salva em `.agents/credentials/conta2.json` e **restaura a sua Conta 1 imediatamente**.

### Passo 2: Usar a Conta 2 nas tarefas
Basta usar o perfil `agy-conta2`!
```powershell
python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile agy-conta2 --prompt "Sua instrução aqui"
```
O orquestrador troca a chave no cofre por frações de segundo, executa com a Conta 2 consumindo a cota da sua assinatura, e devolve a Conta 1 para a IDE logo em seguida.

---

## 2. Como Usar o Claude Code (`claude`)

Se você tem uma conta Anthropic (Claude Pro / API):
1. Instale o Claude Code:
   ```powershell
   npm install -g @anthropic-ai/claude-code
   ```
2. Faça o login inicial no terminal:
   ```powershell
   claude
   ```
3. O perfil `claude` no `config.json` usará a flag `-p` para executar instruções de forma direta e headless, sem travar o terminal esperando confirmações.

---

## 3. Como Usar o Aider (`aider`)

Para usar o Aider com modelos locais (Ollama), DeepSeek, OpenAI ou Claude:
```powershell
pip install aider-chat
```
O perfil `aider` já inclui as flags `--yes --no-git` para aplicar alterações diretamente sem travar a execução.

---

## 4. Testando o Sistema

Para verificar se o pipeline está 100% operacional sem gastar tokens:
```powershell
python .agents/skills/cli-orchestrator/scripts/cli_bridge.py --profile mock --prompt "Teste de subagente" --task-id "teste_inicial"
```

Os resultados de qualquer execução são salvos em:
- `.agents/tasks/<task_id>_spec.json` (Especificação da tarefa e contexto enviado)
- `.agents/tasks/<task_id>_result.json` (Resultado estruturado em JSON)
- `.agents/tasks/<task_id>_result.md` (Relatório formatado em Markdown)

---

## 5. Personalizando Perfis (`config.json`)

Você pode adicionar quantos perfis quiser no arquivo `.agents/skills/cli-orchestrator/config.json`:
```json
{
  "profiles": {
    "meu-cli-custom": {
      "command": "minha-ferramenta",
      "args_template": ["--exec", "{prompt}"],
      "env": {
        "MINHA_API_KEY": "..."
      },
      "description": "Meu subagente customizado"
    }
  }
}
```
