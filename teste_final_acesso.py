# -*- coding: utf-8 -*-
import os
import requests
import json

BASIC_AUTH = os.environ.get("DATAJURI_BASIC_AUTH")
USERNAME = os.environ.get("DATAJURI_USERNAME")
PASSWORD = os.environ.get("DATAJURI_PASSWORD")

AUTH_URL = "https://api.datajuri.com.br/oauth/token"
BASE_URL = "https://api.datajuri.com.br/v1"


def obter_token():
    headers = {
        "Authorization": "Basic " + BASIC_AUTH,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    dados = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    resp = requests.post(AUTH_URL, headers=headers, data=dados)
    resp.raise_for_status()
    return resp.json()


print("=" * 70)
print("TESTE 1: Confirmar autenticacao e ver dados do token")
print("=" * 70)
token_info = obter_token()
print(json.dumps(token_info, indent=2, ensure_ascii=False))
token = token_info["access_token"]
headers = {"Authorization": "Bearer " + token}

print("\n" + "=" * 70)
print("TESTE 2: Pedir a lista de todas as entidades disponiveis")
print("=" * 70)
for caminho in ["/entidades", "/entidades/", "/entidade"]:
    resp = requests.get(BASE_URL + caminho, headers=headers, timeout=15)
    print(caminho, "-> status", resp.status_code)
    if resp.status_code == 200:
        print("CONTEUDO:")
        print(resp.text[:3000])
    print()

print("=" * 70)
print("TESTE 3: Confirmar que a entidade Processo funciona (controle positivo)")
print("=" * 70)
resp = requests.get(BASE_URL + "/entidades/Processo", headers=headers, params={"campos": "id,pasta", "page": 0}, timeout=15)
print("Status:", resp.status_code)
dados = resp.json()
qtd = len(dados.get("rows", [])) if isinstance(dados, dict) else 0
print("Registros na pagina 0:", qtd)
if isinstance(dados, dict):
    print("listSize (total geral, se disponivel):", dados.get("listSize"))

print("\n" + "=" * 70)
print("TESTE 4: Testar entidades do modulo financeiro/juridico que ainda nao tentamos")
print("=" * 70)
outras_entidades = ["Atividade", "Andamento", "Pessoa", "Cliente", "Adverso", "Usuario", "Escritorio", "CampoPersonalizado"]
for nome in outras_entidades:
    resp = requests.get(BASE_URL + "/entidades/" + nome, headers=headers, params={"page": 0}, timeout=15)
    print(nome.ljust(20), "-> status", resp.status_code)
