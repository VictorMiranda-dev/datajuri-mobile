# -*- coding: utf-8 -*-
"""
Busca processos onde "Brumar de Marilia Portaria e Limpeza Ltda" aparece
em QUALQUER campo do processo (Corréu/Empreiteiro, Adverso, Partes, etc).
Não depende de saber o nome exato do campo na API.
"""

import os
import sys
import time
import json
import csv
import requests

AUTH_URL = "https://api.datajuri.com.br/oauth/token"
PROCESSO_URL = "https://api.datajuri.com.br/v1/entidades/Processo"

BASIC_AUTH = os.environ.get("DATAJURI_BASIC_AUTH", "")
USERNAME = os.environ.get("DATAJURI_USERNAME", "")
PASSWORD = os.environ.get("DATAJURI_PASSWORD", "")

TERMO_BUSCA = "brumar de marilia"  # minúsculo, sem acento pra facilitar comparação
PAGE_SIZE = 200
TIMEOUT = 120
PAUSA = 0.3

ARQUIVO_CSV_SAIDA = "processos_brumar_marilia.csv"


def obter_token():
    if not BASIC_AUTH or not USERNAME or not PASSWORD:
        print("ERRO: credenciais incompletas. Configure as variáveis de ambiente.")
        sys.exit(1)

    headers = {
        "Authorization": f"Basic {BASIC_AUTH}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}

    print("Autenticando na API DataJuri...")
    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=TIMEOUT)

    if resp.status_code != 200:
        print(f"ERRO {resp.status_code} ao autenticar: {resp.text[:300]}")
        sys.exit(1)

    token = resp.json().get("access_token")
    if not token:
        print("ERRO: resposta não trouxe access_token.")
        sys.exit(1)

    print("Token obtido com sucesso.\n")
    return token


def normalizar(texto):
    """Remove acentos e deixa minúsculo, pra comparação mais tolerante."""
    if texto is None:
        return ""
    texto = str(texto).lower()
    substituicoes = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "õ": "o", "ô": "o",
        "ú": "u",
        "ç": "c",
    }
    for original, novo in substituicoes.items():
        texto = texto.replace(original, novo)
    return texto


def contem_termo(valor, termo):
    """Busca recursivamente o termo em qualquer string dentro de dicts/listas."""
    if isinstance(valor, dict):
        return any(contem_termo(v, termo) for v in valor.values())
    if isinstance(valor, list):
        return any(contem_termo(v, termo) for v in valor)
    if isinstance(valor, str):
        return termo in normalizar(valor)
    return False


def extrair_campo_texto(valor, caminho=""):
    """Achata um dict/list em uma lista de (caminho, valor_texto) pra exibir onde bateu."""
    resultado = []
    if isinstance(valor, dict):
        for k, v in valor.items():
            novo_caminho = f"{caminho}.{k}" if caminho else k
            resultado.extend(extrair_campo_texto(v, novo_caminho))
    elif isinstance(valor, list):
        for i, v in enumerate(valor):
            resultado.extend(extrair_campo_texto(v, f"{caminho}[{i}]"))
    else:
        resultado.append((caminho, valor))
    return resultado


def buscar_processos(token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    termo = normalizar(TERMO_BUSCA)

    encontrados = []
    page = 0
    total_esperado = None
    total_verificado = 0

    print(f"Procurando por: '{TERMO_BUSCA}' em todos os processos...\n")

    while True:
        params = {"page": page, "pageSize": PAGE_SIZE}
        print(f"Buscando página {page}...")
        resp = requests.get(PROCESSO_URL, headers=headers, params=params, timeout=TIMEOUT)
        resp.encoding = "utf-8"

        if resp.status_code == 401:
            print("ERRO 401: token inválido/expirado ou sem permissão.")
            sys.exit(1)
        if resp.status_code != 200:
            print(f"ERRO {resp.status_code} na página {page}: {resp.text[:500]}")
            sys.exit(1)

        dados = resp.json()
        linhas = dados.get("rows", [])
        total_esperado = dados.get("listSize", total_esperado)

        if not linhas:
            print("Nenhum registro adicional. Busca concluída.\n")
            break

        for processo in linhas:
            total_verificado += 1
            if contem_termo(processo, termo):
                encontrados.append(processo)

        print(f"  -> verificados {total_verificado}"
              f"{f' de {int(total_esperado)}' if total_esperado else ''}"
              f" | encontrados até agora: {len(encontrados)}")

        if len(linhas) < PAGE_SIZE:
            break

        page += 1
        time.sleep(PAUSA)

    return encontrados


def salvar_resultados(encontrados):
    if not encontrados:
        print("\n⚠️  Nenhum processo encontrado com esse termo.")
        return

    print(f"\n{'='*70}")
    print(f"ENCONTRADOS: {len(encontrados)} processo(s)")
    print(f"{'='*70}\n")

    linhas_csv = []

    for i, processo in enumerate(encontrados, 1):
        pasta = processo.get("pasta", processo.get("id", "N/A"))
        print(f"{i}. Processo/Pasta: {pasta}")

        # Mostra em quais campos o termo apareceu
        campos_planos = extrair_campo_texto(processo)
        termo = normalizar(TERMO_BUSCA)
        for caminho, valor in campos_planos:
            if isinstance(valor, str) and termo in normalizar(valor):
                print(f"     -> Campo '{caminho}': {valor}")

        linhas_csv.append({
            "pasta": pasta,
            "id": processo.get("id", ""),
            "json_completo": json.dumps(processo, ensure_ascii=False),
        })
        print()

    with open(ARQUIVO_CSV_SAIDA, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["pasta", "id", "json_completo"])
        writer.writeheader()
        writer.writerows(linhas_csv)

    print(f"{'='*70}")
    print(f"CSV salvo em: {ARQUIVO_CSV_SAIDA}")
    print(f"{'='*70}")


if __name__ == "__main__":
    token = obter_token()
    encontrados = buscar_processos(token)
    salvar_resultados(encontrados)
