# -*- coding: utf-8 -*-
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
        "Authorization": "Basic " + BASIC_AUTH,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=60)
    if resp.status_code != 200:
        print("ERRO " + str(resp.status_code) + ": " + resp.text[:300])
        sys.exit(1)
    return resp.json().get("access_token")


token = obter_token()
headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

CANDIDATOS = [
    "advogadoAdverso",
    "advogadoAdverso.nome",
    "patronoAdverso",
    "patronoAdverso.nome",
    "procuradorAdverso",
    "procuradorAdverso.nome",
    "advogadoContrario",
    "advogadoContrario.nome",
    "advogadoCorreu",
    "advogadoCorreu.nome",
    "advogadoEmpreiteiro",
    "advogadoEmpreiteiro.nome",
    "advogado",
    "advogado.nome",
    "patrono",
    "patrono.nome",
    "procurador",
    "procurador.nome",
    "advogado2",
    "advogado2.nome",
    "advogadoReu",
    "advogadoReu.nome",
    "outroAdvogado",
    "outroAdvogado.nome",
]

campos_base = "id,pasta,cliente.nome,adverso.nome,correu,empreiteiro,advogadoCliente.nome"

print("=" * 70)
print("TESTANDO NOMES DE CAMPO PARA ADVOGADO DA PARTE CONTRARIA...")
print("=" * 70)

encontrados = []

for candidato in CANDIDATOS:
    campos_teste = campos_base + "," + candidato
    resp = requests.get(
        PROCESSO_URL,
        headers=headers,
        params={"page": 0, "pageSize": 3, "campos": campos_teste},
        timeout=60,
    )
    resp.encoding = "utf-8"

    if resp.status_code == 200:
        dados = resp.json()
        linhas = dados.get("rows", [])
        chave_esperada = candidato
        tem_campo = any(chave_esperada in linha for linha in linhas)
        if tem_campo:
            valores = [linha.get(chave_esperada, "") for linha in linhas]
            tem_valor_nao_vazio = any(v for v in valores)
            marcador = "COM DADOS" if tem_valor_nao_vazio else "vazio nos 3 exemplos"
            print("OK (" + marcador + "): '" + candidato + "' -> " + json.dumps(valores, ensure_ascii=False))
            encontrados.append(candidato)
        else:
            print("Nao existe: '" + candidato + "'")
    else:
        print("Falhou (" + str(resp.status_code) + "): '" + candidato + "'")

print("\n" + "=" * 70)
print("CAMPOS QUE EXISTEM: " + str(encontrados))
print("=" * 70)
