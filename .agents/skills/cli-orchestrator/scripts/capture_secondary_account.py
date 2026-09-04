#!/usr/bin/env python3
"""
Captures a secondary Antigravity account token by temporarily freeing the Windows Credential
and guiding the user through Google OAuth login.
Restores Account 1 immediately after completion.
"""

import sys
import time
import subprocess
from pathlib import Path

# Add script directory to sys.path to find wincred_manager
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from wincred_manager import read_credential, write_credential, save_to_file, load_from_file, delete_credential

def find_project_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".agents").exists():
            return parent
    # Fallback to parent of .agents
    return current.parent.parent.parent.parent

def main():
    print("=" * 65)
    print("  Assistente de Captura da Conta Secundaria do Antigravity")
    print("=" * 65)
    print()

    project_root = find_project_root()
    credentials_dir = project_root / ".agents" / "credentials"
    credentials_dir.mkdir(parents=True, exist_ok=True)
    conta1_file = credentials_dir / "conta1.json"
    conta2_file = credentials_dir / "conta2.json"

    # Step 1: Guarantee Conta 1 is safely backed up
    current_cred = read_credential()
    if not current_cred:
        # Check if we already have a saved conta1.json
        if conta1_file.exists():
            load_from_file(conta1_file)
            current_cred = read_credential()
        else:
            print("[ERRO] Nenhuma credencial ativa encontrada no cofre do Windows.")
            sys.exit(1)

    save_to_file(conta1_file)
    print(f"[1/4] Backup da Conta 1 salvo com sucesso em:\n      {conta1_file}")

    print()
    print("[2/4] Preparando cofre para o login da Conta 2...")
    print("-> A credencial atual sera liberada temporariamente.")
    print()

    # We wrap in try/finally to ALWAYS restore Conta 1
    try:
        delete_credential()
        print("[OK] Cofre preparado.")

        print()
        print("[3/4] Iniciando o fluxo de login do agy...")
        print("-> A tela de login do Google vai se abrir no navegador.")
        print("-> IMPORTANTE: Escolha 'Usar outra conta' ou coloque o e-mail da sua CONTA 2.")
        print()

        agy_cmd = [r"C:\Users\aluno\AppData\Local\agy\bin\agy.exe", "-p", "Ola, teste de login"]
        
        # Run directly without capturing so the user sees everything
        proc = subprocess.run(agy_cmd, cwd=str(project_root))

        print()
        print("Verificando se o novo token foi recebido...")
        time.sleep(2)

        new_cred = read_credential()
        if new_cred:
            if new_cred.get("blob") != current_cred.get("blob"):
                save_to_file(conta2_file)
                print()
                print("=" * 65)
                print(f"[SUCESSO!] Token da Conta 2 salvo em:\n           {conta2_file}")
                print("=" * 65)
            else:
                print("[AVISO] O login utilizou a mesma credencial anterior.")
                save_to_file(conta2_file)
        else:
            print("[AVISO] Nao foi possivel detectar o token da Conta 2.")

    finally:
        # ALWAYS restore Conta 1
        load_from_file(conta1_file)
        print()
        print("[4/4] Conta 1 RESTAURADA com sucesso no Windows Credential Manager!")
        print("Sua IDE continua operando normalmente com a Conta 1.")

if __name__ == "__main__":
    main()
