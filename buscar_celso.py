# -*- coding: utf-8 -*-
"""
Busca processos onde o advogado da parte contraria e
"Celso Jose Bonifacio Junior".
"""

import os
import sys
import time
import csv
import requests

AUTH_URL = "https://api.datajuri.com.br/oauth/token"
PROCESSO_URL = "https://api.datajuri.com.br/v1/entidades/Processo"

BASIC_AUTH = os.environ.get("DATAJURI_BASIC_AUTH", "")
USERNAME = os.environ.get("DATAJURI_USERNAME", "")
PASSWORD = os.environ.get("DATAJURI_PASSWORD", "")

TERMO_BUSCA = "celso jose bonifacio junior"
PAGE_SIZE = 200
TIMEOUT = 120
PAUSA = 0.3

CAMPOS = "id,pasta,cliente.nome,adverso.nome,correu,empreiteiro,advogadoAdverso.nome,tipoAcao,status,advogadoCliente.nome"

ARQUIVO_CSV_SAIDA = "processos_celso_bonifacio.csv"


def obter_token():
    if not BASIC_AUTH or not USERNAME or not PASSWORD:
        print("ERRO: credenciais incompletas.")
        sys.exit(1)
    headers = {
        "Authorization": "Basic " + BASIC_AUTH,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    print("Autenticando na API DataJuri...")
    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=TIMEOUT)
    if resp.status_code != 200:
        print("ERRO " + str(resp.status_code) + ": " + resp.text[:300])
        sys.exit(1)
    token = resp.json().get("access_token")
    if not token:
        print("ERRO: resposta nao trouxe access_token.")
        sys.exit(1)
    print("Token obtido com sucesso.\n")
    return token


def normalizar(texto):
    if texto is None:
        return ""
    texto = str(texto).lower()
    texto = texto.replace("\u00e1", "a").replace("\u00e0", "a").replace("\u00e3", "a").replace("\u00e2", "a")
    texto = texto.replace("\u00e9", "e").replace("\u00ea", "e")
    texto = texto.replace("\u00ed", "i")
    texto = texto.replace("\u00f3", "o").replace("\u00f5", "o").replace("\u00f4", "o")
    texto = texto.replace("\u00fa", "u")
    texto = texto.replace("\u00e7", "c")
    return texto


def buscar_processos(token):
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    termo = normalizar(TERMO_BUSCA)

    encontrados = []
    page = 0
    total_esperado = None
    total_verificado = 0

    print("Procurando '" + TERMO_BUSCA + "' no campo Advogado Adverso...\n")

    while True:
        params = {"page": page, "pageSize": PAGE_SIZE, "campos": CAMPOS}
        print("Buscando pagina " + str(page) + "...")
        resp = requests.get(PROCESSO_URL, headers=headers, params=params, timeout=TIMEOUT)
        resp.encoding = "utf-8"

        if resp.status_code == 401:
            print("ERRO 401: token invalido/expirado.")
            sys.exit(1)
        if resp.status_code != 200:
            print("ERRO " + str(resp.status_code) + ": " + resp.text[:500])
            sys.exit(1)

        dados = resp.json()
        linhas = dados.get("rows", [])
        total_esperado = dados.get("listSize", total_esperado)

        if not linhas:
            print("Busca concluida.\n")
            break

        for processo in linhas:
            total_verificado += 1
            advogado_adverso = normalizar(processo.get("advogadoAdverso.nome", ""))
            if termo in advogado_adverso:
                encontrados.append(processo)

        print("  -> verificados " + str(total_verificado) + " | encontrados: " + str(len(encontrados)))

        if len(linhas) < PAGE_SIZE:
            break

        page += 1
        time.sleep(PAUSA)

    return encontrados


def salvar_resultados(encontrados):
    if not encontrados:
        print("\nNenhum processo encontrado com esse advogado.")
        return

    print("\n" + "=" * 70)
    print("ENCONTRADOS: " + str(len(encontrados)) + " processo(s)")
    print("=" * 70 + "\n")

    for i, p in enumerate(encontrados, 1):
        print(str(i) + ". Pasta: " + str(p.get("pasta", "N/A")))
        print("   Cliente: " + str(p.get("cliente.nome", "N/A")))
        print("   Adverso: " + str(p.get("adverso.nome", "N/A")))
        print("   Advogado Adverso: " + str(p.get("advogadoAdverso.nome", "N/A")))
        print("   Correu: " + str(p.get("correu", "N/A")))
        print("   Empreiteiro: " + str(p.get("empreiteiro", "N/A")))
        print("   Tipo Acao: " + str(p.get("tipoAcao", "N/A")))
        print("   Status: " + str(p.get("status", "N/A")))
        print()

    with open(ARQUIVO_CSV_SAIDA, "w", newline="", encoding="utf-8") as f:
        campos_csv = ["pasta", "cliente.nome", "adverso.nome", "advogadoAdverso.nome",
                      "correu", "empreiteiro", "tipoAcao", "status", "advogadoCliente.nome"]
        writer = csv.DictWriter(f, fieldnames=campos_csv, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(encontrados)

    print("=" * 70)
    print("CSV salvo em: " + ARQUIVO_CSV_SAIDA)
    print("=" * 70)


if __name__ == "__main__":
    token = obter_token()
    encontrados = buscar_processos(token)
    salvar_resultados(encontrados)
