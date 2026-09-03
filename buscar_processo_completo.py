# -*- coding: utf-8 -*-
import os
import requests
import json

BASIC_AUTH = os.environ.get("DATAJURI_BASIC_AUTH")
USERNAME = os.environ.get("DATAJURI_USERNAME")
PASSWORD = os.environ.get("DATAJURI_PASSWORD")

AUTH_URL = "https://api.datajuri.com.br/oauth/token"
BASE_URL = "https://api.datajuri.com.br/v1"

PASTA_CONHECIDA = "4004632-35.2025.8.26.0451"


def obter_token():
    headers = {
        "Authorization": "Basic " + BASIC_AUTH,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    dados = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    resp = requests.post(AUTH_URL, headers=headers, data=dados)
    resp.raise_for_status()
    return resp.json()["access_token"]


token = obter_token()
headers = {"Authorization": "Bearer " + token}

print("=" * 70)
print("PASSO 1: Buscar o ID desse processo pela pasta (varrendo todas as paginas)")
print("=" * 70)

todos_registros = []
pagina = 0
while True:
    resp = requests.get(BASE_URL + "/entidades/Processo", headers=headers, params={"campos": "id,pasta", "page": pagina}, timeout=30)
    if resp.status_code != 200:
        print("Erro na pagina", pagina, "- status", resp.status_code)
        break
    dados = resp.json()
    lote = dados.get("rows", []) if isinstance(dados, dict) else []
    if not lote:
        break
    todos_registros.extend(lote)
    print("Pagina", pagina, "-> +" + str(len(lote)) + " registros (acumulado: " + str(len(todos_registros)) + ")")
    pagina += 1
    if pagina > 100:
        print("Limite de seguranca de 100 paginas atingido.")
        break

print("\nTotal de registros carregados no total:", len(todos_registros))

id_encontrado = None
for reg in todos_registros:
    if isinstance(reg, dict) and reg.get("pasta") == PASTA_CONHECIDA:
        id_encontrado = reg.get("id")
        break

print("\nID encontrado:", id_encontrado)

if id_encontrado:
    print("\n" + "=" * 70)
    print("PASSO 2: Buscar esse registro pelo endpoint de item unico (sem 'campos')")
    print("=" * 70)
    url_item = BASE_URL + "/entidades/Processo/" + str(id_encontrado)
    resp2 = requests.get(url_item, headers=headers, timeout=15)
    print("URL:", url_item)
    print("Status:", resp2.status_code)
    print("Resposta completa:")
    print(json.dumps(resp2.json(), indent=2, ensure_ascii=False) if resp2.status_code == 200 else resp2.text)
else:
    print("\nNao foi possivel localizar o ID desse processo. Abortando passo 2.")
