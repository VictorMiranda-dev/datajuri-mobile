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


def extrair_linhas(resp):
    if resp.status_code != 200:
        return None
    dados = resp.json()
    if isinstance(dados, dict):
        return dados.get("rows", dados.get("content", []))
    if isinstance(dados, list):
        return dados
    return []


token = obter_token()
headers = {"Authorization": "Bearer " + token}

CAMPOS_TESTAR = [
    "valorCausa", "valorDaCausa", "valorProvisionado", "valorProvisionadoAtualizado",
    "possibilidadePerda", "qualificacaoCliente", "instanciaFaseAtual",
    "localidadeFaseAtual", "numeroVaraFaseAtual", "varaFaseAtual",
    "responsavel.nome", "dataDistribuicao", "objeto", "acaoPrincipal",
    "posicaoCliente", "assunto", "natureza", "pasta",
]

print("Buscando o registro conhecido (pasta " + PASTA_CONHECIDA + ") com todos os campos candidatos...\n")

campos_param = "id," + ",".join(CAMPOS_TESTAR)
pagina = 0
registro_alvo = None
while registro_alvo is None:
    resp = requests.get(BASE_URL + "/entidades/Processo", headers=headers, params={"campos": campos_param, "page": pagina}, timeout=30)
    linhas = extrair_linhas(resp)
    if not linhas:
        break
    for reg in linhas:
        if reg.get("pasta") == PASTA_CONHECIDA:
            registro_alvo = reg
            break
    pagina += 1
    if pagina > 300:
        print("Nao encontrado apos 300 paginas, abortando.")
        break

if registro_alvo:
    print("REGISTRO ENCONTRADO:")
    print(json.dumps(registro_alvo, indent=2, ensure_ascii=False))
    print("\n" + "=" * 70)
    print("COMPARACAO COM O GABARITO DO ARQUIVO XLS:")
    print("=" * 70)
    print("Valor da Causa esperado: 30000       | veio 'valorCausa':", registro_alvo.get("valorCausa"))
    print("Valor Provisionado Atualizado esperado: 31092.82 | veio 'valorProvisionado':", registro_alvo.get("valorProvisionado"))
    print("                                                  | veio 'valorProvisionadoAtualizado':", registro_alvo.get("valorProvisionadoAtualizado"))
    print("Possibilidade de Perda esperada: Possivel | veio 'possibilidadePerda':", registro_alvo.get("possibilidadePerda"))
else:
    print("Registro nao encontrado nas paginas percorridas.")
