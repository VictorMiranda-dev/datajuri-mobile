# -*- coding: utf-8 -*-
"""
Testa vários nomes possíveis para o campo "Corréu/Empreiteiro" até
descobrir qual é o nome real usado pela API do DataJuri.
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

# Candidatos a nome do campo "Corréu/Empreiteiro"
CANDIDATOS = [
    "correu.nome",
    "correuEmpreiteiro.nome",
    "correu_empreiteiro.nome",
    "empreiteiro.nome",
    "correuempreiteiro.nome",
    "parteContraria2.nome",
    "adverso2.nome",
    "reu2.nome",
    "outroReu.nome",
    "corre.nome",
    "correu",
    "empreiteiro",
]

campos_base = "id,pasta,cliente.nome"

print("="*70)
print("TESTANDO NOMES DE CAMPO...")
print("="*70)

encontrados = []

for candidato in CANDIDATOS:
    campos_teste = f"{campos_base},{candidato}"
    resp = requests.get(
        PROCESSO_URL,
        headers=headers,
        params={"page": 0, "pageSize": 1, "campos": campos_teste},
        timeout=60,
    )
    resp.encoding = "utf-8"

    if resp.status_code == 200:
        dados = resp.json()
        linhas = dados.get("rows", [])
        if linhas and candidato.split(".")[0] in str(linhas[0].keys()):
            print(f"✅ FUNCIONOU: '{candidato}'")
            print(f"   Exemplo: {json.dumps(linhas[0], ensure_ascii=False)}")
            encontrados.append(candidato)
        else:
            print(f"⚠️  Aceito mas campo não veio na resposta: '{candidato}'")
    else:
        print(f"❌ Falhou ({resp.status_code}): '{candidato}'")

print("\n" + "="*70)
if encontrados:
    print(f"CAMPOS QUE FUNCIONARAM: {encontrados}")
else:
    print("Nenhum candidato funcionou. Precisamos ver a documentação da API.")
print("="*70)
