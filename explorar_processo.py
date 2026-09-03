# -*- coding: utf-8 -*-
"""
Mostra a estrutura completa de UM processo, pra descobrir os nomes
exatos dos campos disponíveis (incluindo Corréu/Empreiteiro).
"""

import os
import sys
import json
import requests

AUTH_URL = "https://api.datajuri.com.br/oauth/token"
PROCESSO_URL = "https://api.datajuri.com.br/v1/entidades/Processo"

BASIC_AUTH = os.environ.get("DATAJURI_BASIC_AUTH", "")
USERNAME = os.environ.get("DATAJURI_USERNAME", "")
PASSWORD = os.environ.get("DATAJURI_PASSWORD", "")


def obter_token():
    headers = {
        "Authorization": f"Basic {BASIC_AUTH}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=60)
    if resp.status_code != 200:
        print(f"ERRO {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    return resp.json().get("access_token")


token = obter_token()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Pega só 1 processo pra ver a estrutura completa
resp = requests.get(PROCESSO_URL, headers=headers, params={"page": 0, "pageSize": 1}, timeout=60)
resp.encoding = "utf-8"

if resp.status_code != 200:
    print(f"ERRO {resp.status_code}: {resp.text[:500]}")
    sys.exit(1)

dados = resp.json()
linhas = dados.get("rows", [])

if not linhas:
    print("Nenhum processo retornado.")
    sys.exit(1)

print("="*70)
print("CAMPOS DISPONÍVEIS NO PROCESSO (estrutura completa):")
print("="*70)
print(json.dumps(linhas[0], ensure_ascii=False, indent=2))
print("="*70)
print("\nProcure acima por algo como 'correu', 'empreiteiro', 'partes', etc.")
