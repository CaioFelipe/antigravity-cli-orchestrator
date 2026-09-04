#!/usr/bin/env python3
"""
Syncs existing agy credentials (conta1 and conta2) directly into antigravity-claude-proxy.
Zero manual login required!
"""

import json
import time
from pathlib import Path

def sync():
    home = Path.home()
    proxy_config_dir = home / ".config" / "antigravity-proxy"
    proxy_config_dir.mkdir(parents=True, exist_ok=True)
    accounts_file = proxy_config_dir / "accounts.json"

    accounts = []
    
    mapping = [
        ("conta1.json", "caiofelipegl@gmail.com"),
        ("conta2.json", "caio.lopes@unemat.br"),
    ]

    for filename, email in mapping:
        cred_path = Path(".agents/credentials") / filename
        if cred_path.exists():
            with open(cred_path, "r", encoding="utf-8") as f:
                d = json.load(f)
            token_data = json.loads(d["blob"])
            refresh_token = token_data.get("token", {}).get("refresh_token")
            if refresh_token:
                accounts.append({
                    "email": email,
                    "source": "oauth",
                    "refreshToken": refresh_token,
                    "projectId": None,
                    "addedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "lastUsed": None,
                    "modelRateLimits": {}
                })
                print(f"[OK] Conta vinculada: {email}")

    payload = {
        "accounts": accounts,
        "settings": {
            "maxRetries": 5
        },
        "activeIndex": 0
    }

    with open(accounts_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"\n[SUCESSO] {len(accounts)} contas sincronizadas com sucesso em:")
    print(f"          {accounts_file}")

if __name__ == "__main__":
    sync()
