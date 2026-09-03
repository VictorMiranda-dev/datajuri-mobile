# -*- coding: utf-8 -*-
import os
import requests
import json

CLIENT_ID = os.environ.get("DATAJURI_CLIENT_ID", "jfa8h8oz45fsgc34r4t")
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
    dados = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
    }
    resp = requests.post(AUTH_URL, headers=headers, data=dados)
    resp.raise_for_status()
    return resp.json()["access_token"]


def testar_relatorio_direto(token):
    print("=" * 70)
    print("TESTE 1: Tentando acessar o link do relatorio diretamente")
    print("=" * 70)
    url = "https://dj4.datajuri.com.br/CRelatorio.jw?id=178443&acao=gerar&urlRet=LRelatorio.jw"
    headers = {"Authorization": "Bearer " + token}
    try:
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        print("Status:", resp.status_code)
        print("URL final (apos redirecionamentos):", resp.url)
        print("Primeiros 500 caracteres da resposta:")
        print(resp.text[:500])
    except Exception as e:
        print("Erro:", e)
    print()


def testar_entidade(token, nome_entidade):
    print("-" * 70)
    print("Testando entidade:", nome_entidade)
    url = BASE_URL + "/entidades/" + nome_entidade
    headers = {"Authorization": "Bearer " + token}
    params = {"page": 0, "size": 1}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        print("Status:", resp.status_code)
        if resp.status_code == 200:
            dados = resp.json()
            registros = dados.get("content", dados) if isinstance(dados, dict) else dados
            if isinstance(registros, list) and registros:
                print("OK! Campos disponiveis no primeiro registro:")
                print(json.dumps(list(registros[0].keys()), indent=2, ensure_ascii=False))
            else:
                print("Resposta OK mas sem registros de exemplo. Corpo bruto:")
                print(json.dumps(dados, indent=2, ensure_ascii=False)[:1000])
        else:
            print("Resposta:", resp.text[:300])
    except Exception as e:
        print("Erro:", e)
    print()


if __name__ == "__main__":
    if not BASIC_AUTH or not USERNAME or not PASSWORD:
        print("ERRO: variaveis de ambiente DATAJURI_BASIC_AUTH, DATAJURI_USERNAME, DATAJURI_PASSWORD nao definidas.")
        print("Rode antes: source ~/.zshrc  (ou abra um novo terminal)")
        exit(1)

    token = obter_token()
    print("Token obtido com sucesso.\n")

    testar_relatorio_direto(token)

    print("=" * 70)
    print("TESTE 2: Tentando entidades que podem conter dados de contingencia")
    print("=" * 70)
    candidatos = [
        "Processo",
        "Contingencia",
        "ContingenciaCivel",
        "Provisao",
        "ProvisaoCivel",
        "RelatorioContingencia",
    ]
    for nome in candidatos:
        testar_entidade(token, nome)

    print("=" * 70)
    print("FIM DOS TESTES")
    print("=" * 70)
    print("Me manda toda essa saida que eu identifico o caminho certo.")
