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
    return resp.json()["access_token"]


token = obter_token()
headers = {"Authorization": "Bearer " + token}

print("=" * 70)
print("TESTE A: sem parametro 'campos' (igual ao teste que funcionou)")
print("=" * 70)
resp = requests.get(BASE_URL + "/entidades/Processo", headers=headers, params={"page": 0, "size": 2})
print("Status:", resp.status_code)
print("URL:", resp.url)
dados = resp.json()
print("Tipo da resposta:", type(dados))
if isinstance(dados, list):
    print("Quantidade de registros:", len(dados))
elif isinstance(dados, dict):
    print("Chaves do dict:", list(dados.keys()))
print()

print("=" * 70)
print("TESTE B: com parametro 'campos=id,pasta' (campos basicos conhecidos)")
print("=" * 70)
resp2 = requests.get(BASE_URL + "/entidades/Processo", headers=headers, params={"page": 0, "size": 2, "campos": "id,pasta"})
print("Status:", resp2.status_code)
print("URL:", resp2.url)
dados2 = resp2.json()
print("Tipo da resposta:", type(dados2))
if isinstance(dados2, list):
    print("Quantidade de registros:", len(dados2))
    print("Conteudo:", json.dumps(dados2, indent=2, ensure_ascii=False)[:500])
elif isinstance(dados2, dict):
    print("Chaves do dict:", list(dados2.keys()))
    print("Conteudo:", json.dumps(dados2, indent=2, ensure_ascii=False)[:500])
