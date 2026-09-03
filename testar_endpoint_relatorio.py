# -*- coding: utf-8 -*-
import os
import requests

BASIC_AUTH = os.environ.get("DATAJURI_BASIC_AUTH")
USERNAME = os.environ.get("DATAJURI_USERNAME")
PASSWORD = os.environ.get("DATAJURI_PASSWORD")

AUTH_URL = "https://api.datajuri.com.br/oauth/token"
BASE_URL = "https://api.datajuri.com.br"

ID_RELATORIO = "178443"


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

candidatos = [
    "/v1/relatorios",
    "/v1/relatorios/" + ID_RELATORIO,
    "/v1/relatorios/" + ID_RELATORIO + "/executar",
    "/v1/relatorios/" + ID_RELATORIO + "/dados",
    "/v1/relatorios/" + ID_RELATORIO + "/gerar",
    "/v1/relatorio/" + ID_RELATORIO,
    "/v1/entidades/Relatorio",
    "/v1/entidades/Relatorio/" + ID_RELATORIO,
]

for caminho in candidatos:
    url = BASE_URL + caminho
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(caminho.ljust(45), "-> status", resp.status_code, "| tamanho:", len(resp.text))
        if resp.status_code == 200:
            print("   CONTEUDO (ate 800 chars):", resp.text[:800])
    except Exception as e:
        print(caminho.ljust(45), "-> ERRO:", e)
