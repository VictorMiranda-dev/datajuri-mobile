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


CANDIDATOS = [
    "valorCausa",
    "valorDaCausa",
    "valor.causa",
    "valorCondenacao",
    "valorProvisao",
    "provisao",
    "provisao.valor",
    "percentualPerda",
    "possibilidadePerda",
    "probabilidadePerda",
    "prognostico",
    "riscoPerda",
    "risco",
    "instanciaAtual",
    "instancia",
    "faseAtual.nome",
    "escritorio.nome",
    "escritorioResponsavel.nome",
    "poloProcessual",
    "qualificacaoParte",
    "tipoParte",
    "natureza",
    "processo.natureza",
    "assunto",
    "objeto",
]


def testar_campo(token, campo):
    url = BASE_URL + "/entidades/Processo"
    headers = {"Authorization": "Bearer " + token}
    params = {"page": 0, "size": 1, "campos": "id," + campo}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            dados = resp.json()
            registros = dados.get("content", dados) if isinstance(dados, dict) else dados
            if isinstance(registros, list) and registros:
                valor_encontrado = registros[0].get(campo, "(campo nao veio na resposta)")
                print("OK   | " + campo.ljust(28) + " -> exemplo: " + str(valor_encontrado))
            else:
                print("VAZIO| " + campo.ljust(28) + " -> resposta sem registros")
        else:
            print("ERRO " + str(resp.status_code) + " | " + campo)
    except Exception as e:
        print("FALHA | " + campo + " -> " + str(e))


if __name__ == "__main__":
    token = obter_token()
    print("Token obtido. Testando " + str(len(CANDIDATOS)) + " campos candidatos...\n")
    for campo in CANDIDATOS:
        testar_campo(token, campo)
    print("\nFIM. Me manda essa lista completa.")
