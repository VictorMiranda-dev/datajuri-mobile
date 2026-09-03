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
    "dataAbertura",
    "data.abertura",
    "valorCausa",
    "valorDaCausa",
    "valor",
    "valorProvisionado",
    "valorProvisionadoAtualizado",
    "valorProvisao",
    "possibilidadePerda",
    "probabilidadePerda",
    "posicaoCliente",
    "qualificacaoCliente",
    "instanciaFaseAtual",
    "faseAtual.instancia",
    "localidadeFaseAtual",
    "faseAtual.localidade",
    "numeroVaraFaseAtual",
    "faseAtual.numeroVara",
    "varaFaseAtual",
    "faseAtual.vara",
    "advogadoAdverso.nome",
    "responsavel.nome",
    "natureza",
    "assunto",
    "assuntoPrincipal",
]


def testar_campo_isolado(token, campo):
    url = BASE_URL + "/entidades/Processo"
    headers = {"Authorization": "Bearer " + token}
    params = {"campos": "id," + campo}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            dados = resp.json()
            registros = dados.get("content", dados) if isinstance(dados, dict) else dados
            if isinstance(registros, list) and len(registros) > 0:
                exemplo = None
                for reg in registros[:20]:
                    val = reg.get(campo)
                    if val not in (None, "", "N/A"):
                        exemplo = val
                        break
                if exemplo is not None:
                    print("OK   | " + campo.ljust(28) + " -> " + str(exemplo) + "  (" + str(len(registros)) + " registros)")
                else:
                    print("OK*  | " + campo.ljust(28) + " -> campo existe mas vazio nos 20 primeiros  (" + str(len(registros)) + " registros)")
            else:
                print("VAZIO| " + campo.ljust(28) + " -> resposta sem registros")
        else:
            print("ERRO " + str(resp.status_code) + " | " + campo + " -> " + resp.text[:150])
    except Exception as e:
        print("FALHA | " + campo + " -> " + str(e))


if __name__ == "__main__":
    token = obter_token()
    print("Token obtido. Testando " + str(len(CANDIDATOS)) + " campos (isolados desta vez)...\n")
    for campo in CANDIDATOS:
        testar_campo_isolado(token, campo)
    print("\nFIM. Me manda essa lista completa.")
