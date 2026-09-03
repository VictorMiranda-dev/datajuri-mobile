# -*- coding: utf-8 -*-
"""
Script único: Extrator DataJuri (Andamentos + Atividades/Prazos) + Dashboards
================================================================================

Este script faz TUDO de uma vez:
1. Autentica na API do DataJuri (uma vez só)
2. Busca os ANDAMENTOS dos processos -> gera relatorio_datajuri.html
3. Busca as ATIVIDADES/PRAZOS -> gera dashboard_prazos.html

Funciona igual no Windows e no Mac. As únicas diferenças entre os dois
sistemas estão em COMO você configura as credenciais e roda o script
(ver instruções abaixo) — o código Python em si é o mesmo.

⚠️ SEGURANÇA
------------
NUNCA cole usuário, senha ou credenciais diretamente neste arquivo.
Use variáveis de ambiente (instruções abaixo). Isso já está pronto no
código — você só precisa configurar essas variáveis no seu computador.


COMO CONFIGURAR NO MAC
=======================

1) Abra o aplicativo "Terminal" (Spotlight: Cmd+Espaço, digite "Terminal")

2) Verifique se o Python 3 está instalado:
       python3 --version
   Se der erro, instale pelo site oficial: https://www.python.org/downloads/macos/

3) Instale a biblioteca necessária:
       pip3 install requests

4) Gere o Base64 das credenciais de API (clientID + secretID, fornecidos pelo
   administrador do DataJuri), concatenando com "@" entre eles:
       echo -n "clientID@secretID" | base64

5) Configure as variáveis de ambiente (troque pelos valores reais).
   IMPORTANTE: isso vale só para a janela do Terminal aberta no momento.
   Se fechar o Terminal, precisa configurar de novo (a menos que siga o
   passo 6 abaixo para tornar permanente).

       export DATAJURI_BASIC_AUTH="cole_o_base64_aqui"
       export DATAJURI_USERNAME="seu_email_de_login_no_datajuri"
       export DATAJURI_PASSWORD="sua_senha_do_datajuri"

6) (Opcional, recomendado) Para não precisar configurar toda vez, adicione
   essas mesmas 3 linhas "export ..." no final do arquivo de configuração do
   seu terminal. No Mac moderno (com "zsh", que é o padrão), esse arquivo é:
       ~/.zshrc
   Você pode abrir e editar assim:
       nano ~/.zshrc
   Cole as 3 linhas "export ..." no final, salve (Ctrl+O, Enter) e feche
   (Ctrl+X). Depois rode:
       source ~/.zshrc
   Ou simplesmente feche e abra o Terminal de novo.

7) Coloque este arquivo (extrair_dashboard_completo.py) numa pasta, pelo
   Finder ou Terminal, e navegue até ela:
       cd "/caminho/da/pasta/onde/salvou"

8) Rode o script:
       python3 extrair_dashboard_completo.py > log.txt 2>&1

9) Veja o log:
       cat log.txt
   Ou abra pelo Finder com duplo clique.

10) Abra os arquivos gerados (relatorio_datajuri.html e dashboard_prazos.html)
    duplo clique no Finder — abre no navegador padrão.


COMO CONFIGURAR NO WINDOWS
===========================

1) Abra o PowerShell (tecla Windows, digite "PowerShell")

2) Verifique o Python:
       python --version

3) Instale a biblioteca necessária:
       python -m pip install requests

4) Configure as variáveis de ambiente (troque pelos valores reais):
       $env:DATAJURI_BASIC_AUTH="cole_o_base64_aqui"
       $env:DATAJURI_USERNAME="seu_email_de_login_no_datajuri"
       $env:DATAJURI_PASSWORD="sua_senha_do_datajuri"

   Para tornar permanente (não perder ao fechar a janela), use "setx" no
   lugar de "$env:" (uma vez só, depois feche e abra o PowerShell de novo):
       setx DATAJURI_BASIC_AUTH "cole_o_base64_aqui"
       setx DATAJURI_USERNAME "seu_email_de_login_no_datajuri"
       setx DATAJURI_PASSWORD "sua_senha_do_datajuri"

5) Vá até a pasta onde salvou o arquivo:
       cd "C:/caminho/da/pasta"

6) Rode o script:
       python extrair_dashboard_completo.py > log.txt 2>&1

7) Veja o log:
       notepad log.txt

8) Abra os arquivos .html gerados com duplo clique.


SOBRE AS CREDENCIAIS (importante para quem for usar em outra máquina)
========================================================================
- DATAJURI_BASIC_AUTH: é o mesmo para todo mundo da empresa (é a credencial
  da integração/aplicação, não da pessoa). Pode reaproveitar o mesmo valor.
- DATAJURI_USERNAME e DATAJURI_PASSWORD: são o e-mail e senha de login
  PESSOAL de cada um no DataJuri. Cada pessoa deve usar os PRÓPRIOS dados
  aqui, não os de outra pessoa — inclusive porque isso pode afetar quais
  processos/atividades aparecem, dependendo das permissões de cada usuário.


O QUE ESTE SCRIPT GERA
========================
- andamentos_datajuri.csv     (dados brutos de andamentos, em planilha)
- relatorio_datajuri.html     (relatório visual de andamentos)
- atividades_datajuri.csv     (dados brutos de atividades/prazos, em planilha)
- dashboard_prazos.html       (dashboard completo de prazos, com filtros,
                                gráficos, agenda de audiências, etc.)
"""

import csv
import html
import json
import os
import sys
import time
import unicodedata
from datetime import datetime

import requests

# =========================================================================
# CONFIGURAÇÃO COMPARTILHADA
# =========================================================================

AUTH_URL = "https://api.datajuri.com.br/oauth/token"

BASIC_AUTH = os.environ.get("DATAJURI_BASIC_AUTH", "")
USERNAME = os.environ.get("DATAJURI_USERNAME", "")
PASSWORD = os.environ.get("DATAJURI_PASSWORD", "")


def obter_token():
    if not BASIC_AUTH or not USERNAME or not PASSWORD:
        print("ERRO: credenciais incompletas. Defina DATAJURI_BASIC_AUTH, "
              "DATAJURI_USERNAME e DATAJURI_PASSWORD como variáveis de ambiente.")
        sys.exit(1)

    headers = {
        "Authorization": f"Basic {BASIC_AUTH}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
    }

    print("Autenticando na API DataJuri...")
    print(f"  URL: {AUTH_URL}")
    print(f"  Usuario: {USERNAME}")
    print(f"  Basic Auth (primeiros 10 chars): {BASIC_AUTH[:10]}...")

    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=TIMEOUT_SEGUNDOS)

    print(f"  Status HTTP retornado: {resp.status_code}")
    print(f"  Corpo da resposta: '{resp.text}'")
    print(f"  Headers da resposta: {dict(resp.headers)}")

    if resp.status_code != 200:
        print(f"\nERRO {resp.status_code} ao autenticar.")
        sys.exit(1)

    corpo = resp.json()
    token = corpo.get("access_token")
    if not token:
        print(f"ERRO: resposta de autenticação não trouxe 'access_token': {corpo}")
        sys.exit(1)

    print("Token obtido com sucesso.\n")
    return token


# =========================================================================
# PARTE 1: ANDAMENTOS DOS PROCESSOS
# =========================================================================

ANDAMENTOS_URL = "https://api.datajuri.com.br/v1/processo/ultimosAndamentos"

# Filtros da consulta de andamentos (deixe None/"" para não filtrar)
NUMERO_DIAS = 90        # ex: 30 -> últimos 30 dias. None = todos (pode demorar/travar)
CNJ = None              # ex: "0207123-12.2018.8.04.0001". None = todos os processos

PAGE_SIZE_ANDAMENTOS = 200
PAUSA_ENTRE_REQUISICOES = 0.3
TIMEOUT_SEGUNDOS = 120

ARQUIVO_CSV_ANDAMENTOS = "andamentos_datajuri.csv"
ARQUIVO_HTML_ANDAMENTOS = "relatorio_datajuri.html"


# =========================
# EXTRAÇÃO DE ANDAMENTOS
# =========================

def montar_params(page):
    params = {"page": page, "pageSize": PAGE_SIZE_ANDAMENTOS}
    if NUMERO_DIAS is not None:
        params["numeroDias"] = NUMERO_DIAS
    if CNJ:
        params["cnj"] = CNJ
    return params


def extrair_todos_andamentos(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    todos_registros = []
    page = 0

    while True:
        params = montar_params(page)
        print(f"Buscando página {page}...")

        resp = requests.get(ANDAMENTOS_URL, headers=headers, params=params, timeout=TIMEOUT_SEGUNDOS)

        if resp.status_code == 401:
            print("ERRO 401: token inválido ou expirado.")
            sys.exit(1)
        if resp.status_code != 200:
            print(f"ERRO {resp.status_code} ao buscar página {page}: {resp.text[:300]}")
            sys.exit(1)

        # Força a interpretação como UTF-8 (a API nem sempre informa o charset
        # corretamente, o que corrompia acentos como "ç", "ã", "é").
        resp.encoding = "utf-8"

        try:
            dados = resp.json()
        except ValueError:
            print("ERRO: resposta não é um JSON válido.")
            sys.exit(1)

        print(f"  [DEBUG] Resposta crua da API (primeiros 1000 caracteres): {str(dados)[:1000]}")

        if isinstance(dados, list):
            registros = dados
        elif isinstance(dados, dict):
            registros = (
                dados.get("rows")
                or dados.get("content")
                or dados.get("data")
                or dados.get("items")
                or dados.get("andamentos")
                or []
            )
        else:
            registros = []

        if not registros:
            print("Nenhum registro adicional encontrado. Extração concluída.\n")
            break

        todos_registros.extend(registros)
        print(f"  -> {len(registros)} registros nesta página (total acumulado: {len(todos_registros)})")

        if len(registros) < PAGE_SIZE_ANDAMENTOS:
            break

        page += 1
        time.sleep(PAUSA_ENTRE_REQUISICOES)

    return todos_registros


# =========================
# CSV
# =========================

def salvar_csv(registros, caminho_saida):
    if not registros:
        print("Nenhum registro para salvar em CSV.")
        return

    todas_chaves = []
    for r in registros:
        if isinstance(r, dict):
            for k in r.keys():
                if k not in todas_chaves:
                    todas_chaves.append(k)

    with open(caminho_saida, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=todas_chaves)
        writer.writeheader()
        for r in registros:
            if isinstance(r, dict):
                writer.writerow(r)

    print(f"CSV salvo em: {caminho_saida}")


# =========================
# HTML
# =========================

def pegar_campo(registro, *possiveis_nomes, padrao=""):
    """Tenta encontrar um valor no dict testando várias chaves possíveis,
    já que não sabemos o nome exato dos campos retornados pela API."""
    for nome in possiveis_nomes:
        if nome in registro and registro[nome]:
            return registro[nome]
    return padrao


def gerar_relatorio_andamentos(registros, caminho_saida):
    if not registros:
        conteudo_cards = "<p class='vazio'>Nenhum andamento encontrado.</p>"
    else:
        cards = []
        for r in registros:
            if not isinstance(r, dict):
                continue
            cnj = pegar_campo(r, "cnj", "numeroCnj", "numero", "processoId", padrao="—")
            data_andamento = pegar_campo(r, "data", "dataAndamento", "dtAndamento", padrao="—")
            descricao = pegar_campo(r, "descricao", "andamento", "texto", "resumo", padrao="—")
            observacao = pegar_campo(r, "observacao", padrao="")

            observacao_html = html.escape(str(observacao)).replace(chr(10), "<br>") if observacao else ""

            cards.append(f"""
            <div class="card">
                <div class="card-header">
                    <span class="cnj">Processo: {html.escape(str(cnj))}</span>
                    <span class="data">{html.escape(str(data_andamento))}</span>
                </div>
                <div class="descricao"><strong>{html.escape(str(descricao))}</strong></div>
                {"<div class='observacao'>" + observacao_html + "</div>" if observacao_html else ""}
            </div>
            """)
        conteudo_cards = "\n".join(cards)

    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")

    html_final = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório de Andamentos - DataJuri</title>
<style>
    :root {{
        --primary: #1a3a5c;
        --accent: #c9a24b;
        --bg: #f4f6f8;
        --card-bg: #ffffff;
        --text: #2b2b2b;
        --muted: #6b7280;
        --border: #e2e5ea;
    }}
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0;
        font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
    }}
    header {{
        background: var(--primary);
        color: white;
        padding: 28px 32px;
    }}
    header h1 {{
        margin: 0 0 4px 0;
        font-size: 22px;
        font-weight: 600;
    }}
    header p {{
        margin: 0;
        font-size: 13px;
        color: #cdd8e3;
    }}
    .container {{
        max-width: 900px;
        margin: 0 auto;
        padding: 24px 20px 60px;
    }}
    .resumo {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 24px;
        font-size: 14px;
        color: var(--muted);
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
    }}
    .resumo strong {{
        color: var(--text);
        font-size: 20px;
        display: block;
    }}
    .card {{
        background: var(--card-bg);
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent);
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    .card-header {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 6px;
    }}
    .cnj {{
        font-weight: 600;
        color: var(--primary);
        font-size: 14px;
    }}
    .data {{
        font-size: 13px;
        color: var(--muted);
        white-space: nowrap;
    }}
    .observacao {{
        font-size: 12.5px;
        color: var(--muted);
        margin-top: 8px;
        line-height: 1.5;
        white-space: pre-wrap;
    }}
    .descricao {{
        font-size: 14px;
        line-height: 1.5;
        color: var(--text);
    }}
    .vazio {{
        text-align: center;
        color: var(--muted);
        padding: 40px 0;
    }}
    #busca {{
        width: 100%;
        padding: 10px 14px;
        border: 1px solid var(--border);
        border-radius: 8px;
        font-size: 14px;
        margin-bottom: 20px;
    }}
    footer {{
        text-align: center;
        font-size: 12px;
        color: var(--muted);
        padding: 20px 0;
    }}
</style>
</head>
<body>

<header>
    <h1>Relatório de Andamentos Processuais</h1>
    <p>Gerado automaticamente via API DataJuri em {agora}</p>
</header>

<div class="container">
    <div class="resumo">
        <div><strong>{len(registros)}</strong>Andamentos encontrados</div>
    </div>

    <input type="text" id="busca" placeholder="Buscar por número CNJ ou palavra-chave..." onkeyup="filtrar()">

    <div id="lista">
        {conteudo_cards}
    </div>
</div>

<footer>Relatório gerado automaticamente — dados extraídos da API DataJuri</footer>

<script>
function filtrar() {{
    const termo = document.getElementById('busca').value.toLowerCase();
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {{
        const texto = card.textContent.toLowerCase();
        card.style.display = texto.includes(termo) ? '' : 'none';
    }});
}}
</script>

</body>
</html>
"""

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(html_final)

    print(f"Relatório HTML salvo em: {caminho_saida}")


# =========================================================================
# PARTE 2: ATIVIDADES / PRAZOS (DASHBOARD)
# =========================================================================

ENTIDADES_URL = "https://api.datajuri.com.br/v1/entidades/Atividade"

TIMEOUT = 120
PAGE_SIZE_ATIVIDADES = 1000
PAUSA = 0.2

# Filtro de período: só busca atividades com "Prazo do Encarregado" a partir
# desta data. Formato: DD/MM/YYYY (igual ao formato usado pela API).
# Deixe como None para buscar tudo (pode ser bem mais lento - ~23 mil registros).
DATA_INICIO = "01/07/2026"

# Nomes de encarregados que devem ser completamente ignorados no dashboard
# (não aparecem nem nos gráficos, nem no dropdown de filtro, nem na tabela).
# Adicione ou remova nomes aqui, exatamente como aparecem no DataJuri.
ENCARREGADOS_EXCLUIDOS = [
    "Jessica Priscila Rodrigues",
    "Jessica Priscilla Rodrigues",
]

ARQUIVO_CSV_ATIVIDADES = "atividades_datajuri.csv"
ARQUIVO_HTML_ATIVIDADES = "dashboard_prazos.html"

# A cada quantos minutos o navegador deve recarregar sozinho a página do
# dashboard (pra sempre mostrar os dados mais recentes sem precisar apertar
# F5). Deixe como None para desativar essa auto-atualização.
AUTO_REFRESH_MINUTOS = 15

# Campos que vamos buscar da API (nomes EXATOS confirmados na exploração)
CAMPOS = ",".join([
    "id",
    "prazo_do_encarregado",
    "data",
    "hora",
    "encarregado.nome",
    "proprietario.nome",
    "assunto",
    "tipoAtividade",
    "status",
    "processo.pasta",
    "processo.adverso.nome",
    "processo.natureza",
    "processo.advogadoCliente.nome",
    "diasPrazo",
    "observacao",
])


def extrair_todas_atividades(token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    todos = []
    page = 0
    total_esperado = None

    criterio = None
    if DATA_INICIO:
        criterio = f"prazo_do_encarregado | maior ou igual | {DATA_INICIO}"
        print(f"Filtrando atividades com Prazo do Encarregado >= {DATA_INICIO}\n")

    while True:
        params = {"page": page, "pageSize": PAGE_SIZE_ATIVIDADES, "campos": CAMPOS}
        if criterio:
            params["criterio"] = criterio
        print(f"Buscando página {page}...")
        resp = requests.get(ENTIDADES_URL, headers=headers, params=params, timeout=TIMEOUT)
        resp.encoding = "utf-8"

        if resp.status_code == 401:
            print("ERRO 401: token inválido/expirado.")
            sys.exit(1)
        if resp.status_code != 200:
            print(f"ERRO {resp.status_code} na página {page}: {resp.text[:500]}")
            if criterio and page == 0:
                print("\nO filtro por data pode não ter sido aceito pela API.")
                print("Tentando novamente SEM o filtro (vai buscar tudo)...\n")
                criterio = None
                params.pop("criterio", None)
                resp = requests.get(ENTIDADES_URL, headers=headers, params=params, timeout=TIMEOUT)
                resp.encoding = "utf-8"
                if resp.status_code != 200:
                    print(f"ERRO {resp.status_code} mesmo sem filtro: {resp.text[:500]}")
                    sys.exit(1)
            else:
                sys.exit(1)

        dados = resp.json()
        linhas = dados.get("rows", [])
        total_esperado = dados.get("listSize", total_esperado)

        if not linhas:
            print("Nenhum registro adicional. Extração concluída.\n")
            break

        todos.extend(linhas)
        print(f"  -> {len(linhas)} registros (acumulado: {len(todos)}"
              f"{f' de {int(total_esperado)}' if total_esperado else ''})")

        if len(linhas) < PAGE_SIZE_ATIVIDADES:
            break

        page += 1
        time.sleep(PAUSA)

    return todos


def bra_para_iso(data_str):
    """Converte 'DD/MM/YYYY' para 'YYYY-MM-DD'. Retorna None se vazio/inválido."""
    if not data_str:
        return None
    try:
        d = datetime.strptime(data_str.strip(), "%d/%m/%Y")
        return d.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


import unicodedata


def normalizar_nome(nome):
    """Remove acentos e caixa para comparação tolerante (ex: 'Jéssica' == 'jessica')."""
    if not nome:
        return ""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip().lower()


NOMES_EXCLUIDOS_NORMALIZADOS = {normalizar_nome(n) for n in ENCARREGADOS_EXCLUIDOS}


def deve_excluir_encarregado(nome):
    """Compara o nome do encarregado com a lista de exclusão, tolerando
    pequenas variações de grafia (acentos, caixa, "Priscila" vs "Priscilla")."""
    nome_norm = normalizar_nome(nome)
    if not nome_norm:
        return False
    for excluido in NOMES_EXCLUIDOS_NORMALIZADOS:
        if nome_norm == excluido:
            return True
        # match por prefixo tolerante (primeiras ~12 letras) para pegar
        # pequenas variações de grafia no nome do meio
        if nome_norm[:12] == excluido[:12]:
            return True
    return False


def preparar_dados_dashboard(registros):
    """Normaliza os registros para o formato que o dashboard HTML consome."""
    limpos = []
    data_corte = bra_para_iso(DATA_INICIO) if DATA_INICIO else None

    for r in registros:
        nome_encarregado = r.get("encarregado.nome") or ""
        if deve_excluir_encarregado(nome_encarregado):
            continue

        prazo_iso = bra_para_iso(r.get("prazo_do_encarregado"))

        # Filtro de segurança: garante o corte de data mesmo que o filtro
        # da API (parâmetro "criterio") não tenha sido aplicado corretamente.
        # Registros sem data de prazo são mantidos (ex: compromissos gerais).
        if data_corte and prazo_iso and prazo_iso < data_corte:
            continue

        limpos.append({
            "id": r.get("id"),
            "prazoEncarregado": r.get("prazo_do_encarregado") or "",
            "prazoEncarregadoIso": bra_para_iso(r.get("prazo_do_encarregado")),
            "dataFatal": r.get("data") or "",
            "dataFatalIso": bra_para_iso(r.get("data")),
            "encarregado": r.get("encarregado.nome") or "(Sem encarregado)",
            "responsavel": r.get("proprietario.nome") or "",
            "assunto": r.get("assunto") or "(Sem assunto)",
            "tipoAtividade": r.get("tipoAtividade") or "",
            "situacao": r.get("status") or "(Sem situação)",
            "processo": r.get("processo.pasta") or "",
            "adverso": r.get("processo.adverso.nome") or "",
            "natureza": r.get("processo.natureza") or "(Sem natureza)",
            "advogadoCliente": r.get("processo.advogadoCliente.nome") or "",
            "diasPrazo": r.get("diasPrazo") or "",
            "hora": (r.get("hora") or "").strip(),
            "observacaoResumo": (r.get("observacao") or "")[:300],
        })
    return limpos


def gerar_dashboard_atividades(dados, caminho):
    agora = datetime.now().strftime("%d/%m/%Y às %H:%M")
    hoje_iso = datetime.now().strftime("%Y-%m-%d")
    dados_json = json.dumps(dados, ensure_ascii=False)

    meta_refresh = ""
    if AUTO_REFRESH_MINUTOS:
        segundos = int(AUTO_REFRESH_MINUTOS * 60)
        meta_refresh = f'<meta http-equiv="refresh" content="{segundos}">'

    html_final = HTML_TEMPLATE.replace("__DADOS_JSON__", dados_json) \
                               .replace("__DATA_GERACAO__", agora) \
                               .replace("__HOJE_ISO__", hoje_iso) \
                               .replace("__META_REFRESH__", meta_refresh)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(html_final)
    print(f"Dashboard salvo em: {caminho}")


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
__META_REFRESH__
<title>Dashboard de Prazos - Pacaembu</title>
<style>
:root{
  --navy:#003548;
  --navy-light:#0E4A61;
  --red:#F30A3E;
  --gold:#F8C600;
  --cream:#D8D5CD;
  --bg:#F6F7F8;
  --card:#FFFFFF;
  --text:#1C2B33;
  --muted:#64757D;
  --border:#E3E7E9;
  --green:#1F9254;
  --amber:#E58A00;
}
*{box-sizing:border-box;}
body{margin:0;font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;background:var(--bg);color:var(--text);}

header{background:var(--navy);color:#fff;padding:0;position:relative;overflow:hidden;}
.header-inner{padding:24px 32px;position:relative;z-index:2;}
header h1{margin:0 0 2px;font-size:22px;font-weight:700;letter-spacing:.01em;}
header p{margin:0;font-size:12.5px;color:#B7C8D0;}
.deco{position:absolute;top:0;right:0;height:100%;display:flex;z-index:1;opacity:.9;}
.deco div{width:34px;}
.deco .d1{background:var(--red);}
.deco .d2{background:var(--gold);}

.container{max-width:1280px;margin:0 auto;padding:22px 24px 60px;}

.tabs{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap;}
.tab{
  padding:9px 18px;border-radius:999px;border:1.5px solid var(--border);
  background:var(--card);color:var(--muted);font-size:13.5px;font-weight:600;
  cursor:pointer;transition:.15s;
}
.tab:hover{border-color:var(--navy);}
.tab.active{background:var(--navy);color:#fff;border-color:var(--navy);}

.filter-bar{
  display:flex;align-items:center;gap:20px;flex-wrap:wrap;
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:14px 18px;margin-bottom:20px;
}
.filter-group{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
.filter-group label{font-size:12.5px;font-weight:700;color:var(--navy);white-space:nowrap;}
#filtroEncarregado{
  padding:8px 12px;border:1.5px solid var(--border);border-radius:8px;
  font-size:13px;color:var(--text);background:#fff;min-width:220px;
}
.period-pills{display:flex;gap:6px;}
.pill{
  padding:7px 14px;border-radius:999px;border:1.5px solid var(--border);
  background:#fff;color:var(--muted);font-size:12.5px;font-weight:600;
  cursor:pointer;transition:.15s;
}
.pill:hover{border-color:var(--navy);}
.pill.active{background:var(--red);color:#fff;border-color:var(--red);}

.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px;}
.kpi{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 18px;}
.kpi .num{font-size:28px;font-weight:800;color:var(--navy);line-height:1;}
.kpi .lbl{font-size:12.5px;color:var(--muted);margin-top:6px;font-weight:600;}
.kpi.total .num{color:var(--navy);}
.kpi.naoiniciado .num{color:var(--muted);}
.kpi.andamento .num{color:var(--amber);}
.kpi.finalizado .num{color:var(--green);}

.charts-row{display:grid;grid-template-columns:1.1fr 1fr 1.3fr;gap:14px;margin-bottom:24px;}
.charts-row.sem-natureza{grid-template-columns:1.2fr 1.4fr;}
#chartsRowCivil{grid-template-columns:1fr;}
.chart-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;}
.chart-card.escondido{display:none;}
.chart-card h3{margin:0 0 10px;font-size:13.5px;color:var(--navy);font-weight:700;}
.chart-card canvas{max-height:220px;}

.encarregado-list{display:flex;flex-direction:column;gap:8px;max-height:230px;overflow-y:auto;}
.enc-row{display:flex;align-items:center;gap:8px;font-size:12.5px;}
.enc-name{flex:1;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.enc-bar-bg{flex:2;height:8px;background:var(--border);border-radius:6px;overflow:hidden;}
.enc-bar{height:100%;background:var(--navy);}
.enc-count{font-weight:700;color:var(--navy);width:28px;text-align:right;}

.enc-split{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.enc-col h4{margin:0 0 8px;font-size:11.5px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.03em;}
.enc-col .enc-bar-civ{background:#A0522D;}
.enc-col .enc-bar-trab{background:var(--navy);}
.enc-col .encarregado-list{max-height:190px;}

.table-section{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px;}
.table-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;gap:12px;flex-wrap:wrap;}
.table-header h3{margin:0;font-size:15px;color:var(--navy);}
#busca{flex:1;min-width:220px;padding:9px 14px;border:1px solid var(--border);border-radius:8px;font-size:13.5px;}
.count-badge{font-size:12px;color:var(--muted);}

table{width:100%;border-collapse:collapse;font-size:12.5px;}
th{text-align:left;padding:9px 10px;border-bottom:2px solid var(--border);color:var(--navy);font-weight:700;white-space:nowrap;position:sticky;top:0;background:var(--card);}
td{padding:8px 10px;border-bottom:1px solid var(--border);vertical-align:top;}
tr:hover td{background:#FAFBFC;}
.table-scroll{max-height:560px;overflow:auto;border:1px solid var(--border);border-radius:8px;}

.badge{display:inline-block;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700;white-space:nowrap;}
.badge-naoiniciado{background:#EDEFF0;color:var(--muted);}
.badge-andamento{background:#FDF0DA;color:var(--amber);}
.badge-finalizado{background:#E4F3EA;color:var(--green);}
.badge-natureza-trab{background:#E3EEF3;color:var(--navy);}
.badge-natureza-civ{background:#F6E9DC;color:#A0522D;}
.badge-natureza-outra{background:#EEE;color:var(--muted);}

.cnj-cell{font-variant-numeric:tabular-nums;white-space:nowrap;}
.fatal-cell{font-weight:700;}
.fatal-urgente{color:var(--red);}

.agenda-dia{margin-bottom:16px;}
.agenda-dia:last-child{margin-bottom:0;}
.agenda-cabecalho{
  font-size:13px;font-weight:700;color:var(--navy);margin-bottom:8px;
  padding-bottom:6px;border-bottom:2px solid var(--border);
}
.agenda-cabecalho .destaque{color:var(--red);}
.agenda-item{
  padding:8px 10px;border-radius:8px;background:#F8F9FA;margin-bottom:6px;
  font-size:12.5px;line-height:1.5;border-left:3px solid var(--navy);
}
.agenda-item:last-child{margin-bottom:0;}
.agenda-item .assunto{font-weight:700;color:var(--navy);text-transform:uppercase;font-size:11.5px;letter-spacing:.02em;}
.agenda-item .detalhe{color:var(--muted);}
.agenda-vazio{font-size:12px;color:var(--muted);padding:8px 0;}
.agenda-scroll{max-height:420px;overflow-y:auto;}

footer{text-align:center;font-size:11.5px;color:var(--muted);padding:24px 0;}

@media (max-width:1000px){
  .kpi-row{grid-template-columns:repeat(2,1fr);}
  .charts-row, .charts-row.sem-natureza{grid-template-columns:1fr;}
}
</style>
</head>
<body>

<header>
  <div class="deco"><div class="d1"></div><div class="d2"></div></div>
  <div class="header-inner">
    <h1>Dashboard de Prazos — Jurídico Pacaembu</h1>
    <p>Gerado automaticamente via API DataJuri em __DATA_GERACAO__</p>
  </div>
</header>

<div class="container">

  <div class="tabs" id="tabs">
    <div class="tab active" data-natureza="__todos__">Todos</div>
    <div class="tab" data-natureza="Trabalhista">Trabalhista</div>
    <div class="tab" data-natureza="Cível">Cível</div>
  </div>

  <div class="filter-bar">
    <div class="filter-group">
      <label for="filtroEncarregado">Encarregado:</label>
      <select id="filtroEncarregado">
        <option value="__todos__">Todos</option>
      </select>
    </div>
    <div class="filter-group">
      <label>Período:</label>
      <div class="period-pills" id="periodPills">
        <div class="pill active" data-periodo="__todos__">Todos</div>
        <div class="pill" data-periodo="hoje">Hoje</div>
        <div class="pill" data-periodo="semana">Esta semana</div>
        <div class="pill" data-periodo="mes">Este mês</div>
      </div>
    </div>
    <div class="filter-group" id="grupoTipoCivil" style="display:none;">
      <label>Tipo:</label>
      <div class="period-pills" id="tipoCivilPills">
        <div class="pill active" data-tipo="__todos__">Todos</div>
        <div class="pill" data-tipo="processo" id="pillProcesso">Processo</div>
        <div class="pill" data-tipo="notificacao" id="pillNotificacao">Notificação</div>
      </div>
    </div>
    <div class="filter-group" id="grupoAudiencia" style="display:none;">
      <label>Assunto:</label>
      <div class="period-pills" id="audienciaPills">
        <div class="pill active" data-audiencia="__todos__">Todos</div>
        <div class="pill" data-audiencia="audiencia" id="pillAudiencia">Audiências</div>
        <div class="pill" data-audiencia="julgamento" id="pillJulgamento">Julgamentos</div>
      </div>
    </div>
  </div>

  <div class="kpi-row">
    <div class="kpi total"><div class="num" id="kpiTotal">0</div><div class="lbl">Total de prazos</div></div>
    <div class="kpi naoiniciado"><div class="num" id="kpiNaoIniciado">0</div><div class="lbl">Não iniciados</div></div>
    <div class="kpi andamento"><div class="num" id="kpiAndamento">0</div><div class="lbl">Em andamento</div></div>
    <div class="kpi finalizado"><div class="num" id="kpiFinalizado">0</div><div class="lbl">Finalizados</div></div>
  </div>

  <div class="charts-row" id="chartsRow">
    <div class="chart-card">
      <h3>Por Situação</h3>
      <canvas id="chartSituacao"></canvas>
    </div>
    <div class="chart-card" id="cardNatureza">
      <h3>Por Natureza</h3>
      <canvas id="chartNatureza"></canvas>
    </div>
    <div class="chart-card">
      <h3 id="tituloEncarregados">Prazos por Encarregado</h3>
      <div id="encSingle" class="encarregado-list"></div>
      <div id="encSplit" class="enc-split" style="display:none;">
        <div class="enc-col">
          <h4>Advogados Cíveis</h4>
          <div class="encarregado-list" id="listaEncarregadosCivel"></div>
        </div>
        <div class="enc-col">
          <h4>Advogados Trabalhistas</h4>
          <div class="encarregado-list" id="listaEncarregadosTrabalhista"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="charts-row" id="chartsRowCivil" style="display:none;">
    <div class="chart-card" style="width:100%;">
      <h3>Por Advogado do Cliente (escritórios)</h3>
      <div class="encarregado-list" id="listaAdvogadoCliente"></div>
    </div>
  </div>

  <div class="charts-row" id="chartsRowAudiencia" style="display:none;grid-template-columns:1.4fr 1fr;">
    <div class="chart-card">
      <h3 id="tituloAgenda">Agenda</h3>
      <div id="agendaAudiencias"></div>
    </div>
    <div class="chart-card">
      <h3 id="tituloPorMes">Por Mês</h3>
      <div class="encarregado-list" id="listaAudienciaMes"></div>
    </div>
  </div>

  <div class="table-section">
    <div class="table-header">
      <h3>Todos os prazos</h3>
      <input type="text" id="busca" placeholder="Buscar por processo, adverso, encarregado, assunto...">
      <span class="count-badge" id="contagemTabela"></span>
    </div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Processo (CNJ)</th>
            <th>Adverso</th>
            <th>Prazo Encarregado</th>
            <th>Data Fatal</th>
            <th>Encarregado</th>
            <th>Assunto</th>
            <th>Natureza</th>
            <th>Advogado do cliente</th>
            <th>Situação</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </div>

</div>

<footer>Dashboard gerado automaticamente a partir da API DataJuri — Jurídico Pacaembu</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script>
const DADOS = __DADOS_JSON__;
const HOJE_ISO = "__HOJE_ISO__";

let filtroNatureza = "__todos__";
let filtroEncarregado = "__todos__";
let filtroPeriodo = "__todos__";
let filtroTipoCivil = "__todos__";
let filtroAudiencia = "__todos__";
let chartSituacao, chartNatureza;

// Número de processo no formato CNJ completo: NNNNNNN-DD.AAAA.J.TR.OOOO
const CNJ_REGEX = /^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$/;

function classificarTipoProcesso(pasta){
  if(!pasta) return "notificacao";
  return CNJ_REGEX.test(pasta.trim()) ? "processo" : "notificacao";
}

function classificarTipoEvento(assunto){
  const s = normalizar(assunto);
  if(s.includes("julgamento")) return "julgamento";
  if(s.includes("audiencia")) return "audiencia";
  return null;
}

// Remove acentos para comparações não sofrerem com problemas de encoding
// (ex.: "Cível" tem que bater com "civel"/"civ" independente do acento).
function normalizar(s){
  return (s||"").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function classificarNatureza(n){
  const s = normalizar(n);
  if(s.includes("trabalh")) return "trab";
  // Regra: qualquer coisa que não seja explicitamente Trabalhista conta como
  // Cível (isso inclui rótulos como "Societário", "Notificações", etc.,
  // que na prática são tratados como parte da área cível).
  if(s) return "civ";
  return "outra"; // só cai aqui quando não há natureza cadastrada
}
function classificarSituacao(s){
  const t = normalizar(s);
  if(t.includes("nao inic")) return "naoiniciado";
  if(t.includes("andamento")) return "andamento";
  if(t.includes("finaliz")) return "finalizado";
  return "outra";
}

function getSemanaLimites(){
  const hoje = new Date(HOJE_ISO + "T00:00:00");
  const diaSemana = hoje.getDay();
  const inicio = new Date(hoje); inicio.setDate(hoje.getDate() - diaSemana);
  const fim = new Date(inicio); fim.setDate(inicio.getDate() + 6);
  return [inicio, fim];
}
function getMesLimites(){
  const hoje = new Date(HOJE_ISO + "T00:00:00");
  const inicio = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
  const fim = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 0);
  return [inicio, fim];
}

function dentroDoPeriodo(d){
  if(filtroPeriodo === "__todos__") return true;
  if(!d.prazoEncarregadoIso) return false;
  const dt = new Date(d.prazoEncarregadoIso + "T00:00:00");
  if(filtroPeriodo === "hoje") return d.prazoEncarregadoIso === HOJE_ISO;
  if(filtroPeriodo === "semana"){
    const [ini,fim] = getSemanaLimites();
    return dt >= ini && dt <= fim;
  }
  if(filtroPeriodo === "mes"){
    const [ini,fim] = getMesLimites();
    return dt >= ini && dt <= fim;
  }
  return true;
}

// Popula o <select> de encarregados com base na natureza selecionada
function popularEncarregados(){
  const relevantes = DADOS.filter(d=>{
    if(filtroNatureza === "__todos__") return true;
    return classificarNatureza(d.natureza) === (filtroNatureza === "Trabalhista" ? "trab" : "civ");
  });
  const nomes = [...new Set(relevantes.map(d=>d.encarregado))].sort((a,b)=>a.localeCompare(b,"pt-BR"));

  const select = document.getElementById("filtroEncarregado");
  const valorAtual = select.value;
  select.innerHTML = '<option value="__todos__">Todos</option>' +
    nomes.map(n=>`<option value="${n}">${n}</option>`).join("");

  // mantém a seleção se a pessoa ainda estiver na lista, senão volta para "Todos"
  if(nomes.includes(valorAtual)){
    select.value = valorAtual;
  } else {
    select.value = "__todos__";
    filtroEncarregado = "__todos__";
  }
}

function aplicarFiltro(){
  return DADOS.filter(d => {
    if(filtroNatureza !== "__todos__"){
      const alvo = filtroNatureza === "Trabalhista" ? "trab" : "civ";
      if(classificarNatureza(d.natureza) !== alvo) return false;
    }
    if(filtroEncarregado !== "__todos__" && d.encarregado !== filtroEncarregado) return false;
    if(!dentroDoPeriodo(d)) return false;
    if(filtroNatureza === "Cível" && filtroTipoCivil !== "__todos__"){
      if(classificarTipoProcesso(d.processo) !== filtroTipoCivil) return false;
    }
    if(filtroNatureza === "Trabalhista" && filtroAudiencia !== "__todos__"){
      if(classificarTipoEvento(d.assunto) !== filtroAudiencia) return false;
    }
    return true;
  });
}

function atualizarContadoresTipo(){
  // conta processo vs notificação dentro do filtro atual (natureza+encarregado+período),
  // ignorando o próprio filtro de tipo, para mostrar nos rótulos dos pills
  const base = DADOS.filter(d => {
    if(filtroNatureza !== "__todos__"){
      const alvo = filtroNatureza === "Trabalhista" ? "trab" : "civ";
      if(classificarNatureza(d.natureza) !== alvo) return false;
    }
    if(filtroEncarregado !== "__todos__" && d.encarregado !== filtroEncarregado) return false;
    if(!dentroDoPeriodo(d)) return false;
    return true;
  });
  let cProcesso = 0, cNotificacao = 0;
  base.forEach(d=>{
    if(classificarTipoProcesso(d.processo) === "processo") cProcesso++;
    else cNotificacao++;
  });
  document.getElementById("pillProcesso").textContent = `Processo (${cProcesso})`;
  document.getElementById("pillNotificacao").textContent = `Notificação (${cNotificacao})`;
}

function atualizarContadorAudiencia(){
  const base = DADOS.filter(d => {
    if(filtroNatureza !== "__todos__"){
      const alvo = filtroNatureza === "Trabalhista" ? "trab" : "civ";
      if(classificarNatureza(d.natureza) !== alvo) return false;
    }
    if(filtroEncarregado !== "__todos__" && d.encarregado !== filtroEncarregado) return false;
    if(!dentroDoPeriodo(d)) return false;
    return true;
  });
  const totalAudiencia = base.filter(d=>classificarTipoEvento(d.assunto) === "audiencia").length;
  const totalJulgamento = base.filter(d=>classificarTipoEvento(d.assunto) === "julgamento").length;
  document.getElementById("pillAudiencia").textContent = `Audiências (${totalAudiencia})`;
  document.getElementById("pillJulgamento").textContent = `Julgamentos (${totalJulgamento})`;
}

function formatarDiaBR(iso){
  const [ano,mes,dia] = iso.split("-");
  return `${dia}/${mes}/${ano}`;
}
function formatarMesBR(anoMes){
  const [ano,mes] = anoMes.split("-");
  const nomes = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
  return `${nomes[parseInt(mes,10)-1]}/${ano}`;
}

function extrairModalidade(observacao){
  const s = normalizar(observacao);
  if(s.includes("telepresencial")) return "Telepresencial";
  if(s.includes("presencial")) return "Presencial";
  return null;
}

function primeiroNome(nomeCompleto){
  if(!nomeCompleto) return "—";
  return nomeCompleto.trim().split(/\s+/)[0];
}

function formatarCabecalhoData(iso){
  const dt = new Date(iso + "T00:00:00");
  const hoje = new Date(HOJE_ISO + "T00:00:00");
  const amanha = new Date(hoje); amanha.setDate(hoje.getDate()+1);
  const dataFmt = formatarDiaBR(iso);
  if(iso === HOJE_ISO) return {texto: "HOJE", data: dataFmt, destaque:true};
  if(iso === amanha.toISOString().slice(0,10)) return {texto:"AMANHÃ", data: dataFmt, destaque:true};
  const diasSemana = ["Domingo","Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado"];
  return {texto: diasSemana[dt.getDay()], data: dataFmt, destaque:false};
}

function renderAgendaEMes(lista){
  const tipoLabel = filtroAudiencia === "julgamento" ? "julgamento(s)" : "audiência(s)";
  document.getElementById("tituloAgenda").textContent =
    filtroAudiencia === "julgamento" ? "Agenda de Julgamentos" : "Agenda de Audiências";
  document.getElementById("tituloPorMes").textContent = "Por Mês (Data Fatal)";

  const somenteEventos = lista.filter(d=>classificarTipoEvento(d.assunto) === filtroAudiencia);

  // Agrupa por DATA FATAL (não pelo prazo do encarregado)
  const porDia = {};
  const porMes = {};
  somenteEventos.forEach(d=>{
    const iso = d.dataFatalIso;
    if(!iso) return;
    if(!porDia[iso]) porDia[iso] = [];
    porDia[iso].push(d);
    const anoMes = iso.slice(0,7);
    porMes[anoMes] = (porMes[anoMes]||0) + 1;
  });

  const diasOrdenados = Object.keys(porDia).sort();
  const agendaEl = document.getElementById("agendaAudiencias");

  if(!diasOrdenados.length){
    agendaEl.innerHTML = `<p class="agenda-vazio">Nenhum(a) ${tipoLabel} encontrado(a) no filtro atual.</p>`;
  } else {
    agendaEl.innerHTML = `<div class="agenda-scroll">` + diasOrdenados.map(iso=>{
      const itens = porDia[iso];
      const cab = formatarCabecalhoData(iso);
      const qtd = itens.length;
      const cabecalhoTexto = cab.destaque
        ? `<span class="destaque">${cab.texto}</span> (${cab.data}) você tem ${qtd} ${qtd===1?tipoLabel.replace("(s)","") : tipoLabel} `
        : `${cab.texto}, ${cab.data} — ${qtd} ${qtd===1?tipoLabel.replace("(s)","") : tipoLabel}`;

      const itensHtml = itens
        .sort((a,b)=>(a.hora||"99:99").localeCompare(b.hora||"99:99"))
        .map(d=>{
          const modalidade = extrairModalidade(d.observacaoResumo);
          const partes = [];
          partes.push(d.hora ? `às ${d.hora}` : "horário não informado");
          if(modalidade) partes.push(modalidade);
          partes.push(`Encarregado(a): ${primeiroNome(d.encarregado)}`);
          if(d.adverso) partes.push(`Adverso: ${d.adverso}`);
          return `
            <div class="agenda-item">
              <div class="assunto">${d.assunto}</div>
              <div class="detalhe">${partes.join(" — ")}</div>
            </div>
          `;
        }).join("");

      return `
        <div class="agenda-dia">
          <div class="agenda-cabecalho">${cabecalhoTexto}</div>
          ${itensHtml}
        </div>
      `;
    }).join("") + `</div>`;
  }

  const mesesOrdenados = Object.entries(porMes).sort((a,b)=>a[0].localeCompare(b[0]));
  const listaMes = document.getElementById("listaAudienciaMes");
  listaMes.innerHTML = mesesOrdenados.length ? mesesOrdenados.map(([anoMes,qtd])=>`
    <div class="enc-row">
      <div class="enc-name">${formatarMesBR(anoMes)}</div>
      <div class="enc-count">${qtd}</div>
    </div>
  `).join("") : `<p class="agenda-vazio">Sem ${tipoLabel} no filtro atual</p>`;
}

function renderTudo(){
  const lista = aplicarFiltro();
  renderKpis(lista);
  renderEncarregados(lista);
  renderTabela(lista);

  // O filtro Processo/Notificação só aparece na aba Cível
  const grupoTipoCivil = document.getElementById("grupoTipoCivil");
  if(filtroNatureza === "Cível"){
    grupoTipoCivil.style.display = "";
    atualizarContadoresTipo();
  } else {
    grupoTipoCivil.style.display = "none";
  }

  // O filtro Audiências/Julgamento só aparece na aba Trabalhista
  const grupoAudiencia = document.getElementById("grupoAudiencia");
  if(filtroNatureza === "Trabalhista"){
    grupoAudiencia.style.display = "";
    atualizarContadorAudiencia();
  } else {
    grupoAudiencia.style.display = "none";
  }

  // O gráfico "Por Natureza" só faz sentido quando não estamos já filtrando
  // por uma natureza específica (senão vira uma pizza de uma fatia só).
  const cardNatureza = document.getElementById("cardNatureza");
  const chartsRow = document.getElementById("chartsRow");
  if(filtroNatureza === "__todos__"){
    cardNatureza.classList.remove("escondido");
    chartsRow.classList.remove("sem-natureza");
  } else {
    cardNatureza.classList.add("escondido");
    chartsRow.classList.add("sem-natureza");
  }

  // Ranking "Por Advogado do Cliente" só aparece na aba Cível, e só quando
  // não há um encarregado específico selecionado (senão a informação já
  // aparece detalhada dentro do próprio painel do encarregado).
  const chartsRowCivil = document.getElementById("chartsRowCivil");
  if(filtroNatureza === "Cível" && filtroEncarregado === "__todos__"){
    chartsRowCivil.style.display = "";
    renderAdvogadoCliente(lista);
  } else {
    chartsRowCivil.style.display = "none";
  }

  // Painel de Audiências/Julgamentos: só aparece na aba Trabalhista quando
  // um dos dois filtros (Audiências ou Julgamentos) está ativo.
  const chartsRowAudiencia = document.getElementById("chartsRowAudiencia");
  if(filtroNatureza === "Trabalhista" && filtroAudiencia !== "__todos__"){
    chartsRowAudiencia.style.display = "";
    renderAgendaEMes(lista);
  } else {
    chartsRowAudiencia.style.display = "none";
  }

  try{
    renderCharts(lista);
  }catch(e){
    console.warn("Gráficos não puderam ser renderizados (Chart.js pode não ter carregado):", e);
    document.querySelectorAll(".chart-card canvas").forEach(c=>{
      if(!c.dataset.avisado){
        c.insertAdjacentHTML("afterend", "<p style='font-size:11px;color:#999;text-align:center;'>Gráfico indisponível (sem conexão com a internet)</p>");
        c.dataset.avisado = "1";
      }
    });
  }
}

function renderKpis(lista){
  document.getElementById("kpiTotal").textContent = lista.length;
  let ni=0, an=0, fi=0;
  lista.forEach(d=>{
    const c = classificarSituacao(d.situacao);
    if(c==="naoiniciado") ni++;
    else if(c==="andamento") an++;
    else if(c==="finalizado") fi++;
  });
  document.getElementById("kpiNaoIniciado").textContent = ni;
  document.getElementById("kpiAndamento").textContent = an;
  document.getElementById("kpiFinalizado").textContent = fi;
}

function renderCharts(lista){
  const sitCounts = {"Não iniciado":0,"Em andamento":0,"Finalizado":0,"Outra":0};
  const natCounts = {};
  lista.forEach(d=>{
    const cs = classificarSituacao(d.situacao);
    if(cs==="naoiniciado") sitCounts["Não iniciado"]++;
    else if(cs==="andamento") sitCounts["Em andamento"]++;
    else if(cs==="finalizado") sitCounts["Finalizado"]++;
    else sitCounts["Outra"]++;

    const nat = d.natureza || "Sem natureza";
    natCounts[nat] = (natCounts[nat]||0) + 1;
  });

  const ctx1 = document.getElementById("chartSituacao").getContext("2d");
  if(chartSituacao) chartSituacao.destroy();
  chartSituacao = new Chart(ctx1, {
    type:"pie",
    data:{
      labels:Object.keys(sitCounts),
      datasets:[{data:Object.values(sitCounts), backgroundColor:["#64757D","#E58A00","#1F9254","#B7C8D0"]}]
    },
    options:{plugins:{legend:{position:"bottom",labels:{boxWidth:12,font:{size:11}}}}}
  });

  if(filtroNatureza === "__todos__"){
    const ctx2 = document.getElementById("chartNatureza").getContext("2d");
    if(chartNatureza) chartNatureza.destroy();
    chartNatureza = new Chart(ctx2, {
      type:"pie",
      data:{
        labels:Object.keys(natCounts),
        datasets:[{data:Object.values(natCounts), backgroundColor:["#003548","#F8C600","#F30A3E","#B7C8D0","#8AA2AC"]}]
      },
      options:{plugins:{legend:{position:"bottom",labels:{boxWidth:12,font:{size:11}}}}}
    });
  }
}

function renderAdvogadoCliente(lista){
  const counts = {};
  lista.forEach(d=>{
    const nome = d.advogadoCliente || "(Sem advogado do cliente)";
    counts[nome] = (counts[nome]||0) + 1;
  });
  renderBarraLista(document.getElementById("listaAdvogadoCliente"), counts, "enc-bar-civ");
}

function renderBarraLista(container, mapa, corClasse){
  const ordenado = Object.entries(mapa).sort((a,b)=>b[1]-a[1]).slice(0,12);
  const max = ordenado.length ? ordenado[0][1] : 1;
  container.innerHTML = ordenado.length ? ordenado.map(([nome,qtd])=>`
    <div class="enc-row">
      <div class="enc-name" title="${nome}">${nome}</div>
      <div class="enc-bar-bg"><div class="enc-bar ${corClasse}" style="width:${(qtd/max*100)}%"></div></div>
      <div class="enc-count">${qtd}</div>
    </div>
  `).join("") : "<p style='font-size:12px;color:var(--muted);'>Sem registros</p>";
}

function renderEncarregados(lista){
  const titulo = document.getElementById("tituloEncarregados");
  const encSingle = document.getElementById("encSingle");
  const encSplit = document.getElementById("encSplit");

  if(filtroEncarregado !== "__todos__"){
    // já estamos vendo o painel de uma pessoa específica — a lista de
    // ranking não faz sentido, mostramos um resumo dela em texto
    encSplit.style.display = "none";
    encSingle.style.display = "";
    titulo.textContent = "Encarregado selecionado";

    let htmlResumo = `
      <div class="enc-row" style="font-size:14px;font-weight:700;color:var(--navy);">
        ${filtroEncarregado}
      </div>
      <div class="enc-row" style="color:var(--muted);margin-bottom:6px;">
        ${lista.length} prazo(s) no total
      </div>
    `;

    // Na aba Cível, detalha também por Advogado do Cliente (escritório)
    if(filtroNatureza === "Cível"){
      const porEscritorio = {};
      lista.forEach(d=>{
        const nome = d.advogadoCliente || "(Sem advogado do cliente)";
        porEscritorio[nome] = (porEscritorio[nome]||0) + 1;
      });
      const linhas = Object.entries(porEscritorio).sort((a,b)=>b[1]-a[1]);
      if(linhas.length){
        htmlResumo += `<div class="enc-row" style="font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;margin-top:4px;">Por advogado do cliente</div>`;
        htmlResumo += linhas.map(([nome,qtd])=>`
          <div class="enc-row">
            <div class="enc-name" title="${nome}">${nome}</div>
            <div class="enc-count">${qtd}</div>
          </div>
        `).join("");
      }
    }

    encSingle.innerHTML = htmlResumo;
    return;
  }

  if(filtroNatureza === "__todos__"){
    // Visão "Todos": separa em dois mini-cards, Cíveis e Trabalhistas
    titulo.textContent = "Prazos por Encarregado";
    encSingle.style.display = "none";
    encSplit.style.display = "";

    const civCounts = {};
    const trabCounts = {};
    lista.forEach(d=>{
      const cls = classificarNatureza(d.natureza);
      if(cls === "civ") civCounts[d.encarregado] = (civCounts[d.encarregado]||0)+1;
      else if(cls === "trab") trabCounts[d.encarregado] = (trabCounts[d.encarregado]||0)+1;
    });

    renderBarraLista(document.getElementById("listaEncarregadosCivel"), civCounts, "enc-bar-civ");
    renderBarraLista(document.getElementById("listaEncarregadosTrabalhista"), trabCounts, "enc-bar-trab");
    return;
  }

  // Uma natureza específica já selecionada (Trabalhista OU Cível): lista única
  titulo.textContent = "Prazos por Encarregado";
  encSplit.style.display = "none";
  encSingle.style.display = "";
  const counts = {};
  lista.forEach(d=>{ counts[d.encarregado] = (counts[d.encarregado]||0)+1; });
  renderBarraLista(encSingle, counts, "");
}

function badgeSituacao(s){
  const c = classificarSituacao(s);
  return `<span class="badge badge-${c}">${s}</span>`;
}
function badgeNatureza(n){
  const c = classificarNatureza(n);
  const cls = c==="trab" ? "badge-natureza-trab" : c==="civ" ? "badge-natureza-civ" : "badge-natureza-outra";
  return `<span class="badge ${cls}">${n}</span>`;
}
function fatalUrgente(iso){
  if(!iso) return false;
  const dt = new Date(iso+"T00:00:00");
  const hoje = new Date(HOJE_ISO+"T00:00:00");
  const diffDias = (dt-hoje)/86400000;
  return diffDias <= 3;
}

function renderTabela(lista){
  const termo = document.getElementById("busca").value.toLowerCase();
  const filtrada = lista.filter(d=>{
    if(!termo) return true;
    const texto = [d.processo,d.adverso,d.encarregado,d.assunto,d.advogadoCliente,d.responsavel].join(" ").toLowerCase();
    return texto.includes(termo);
  });
  document.getElementById("contagemTabela").textContent = filtrada.length + " registro(s)";
  document.getElementById("tbody").innerHTML = filtrada.map(d=>`
    <tr>
      <td class="cnj-cell">${d.processo || "—"}</td>
      <td>${d.adverso || "—"}</td>
      <td>${d.prazoEncarregado || "—"}</td>
      <td class="fatal-cell ${fatalUrgente(d.dataFatalIso)?'fatal-urgente':''}">${d.dataFatal || "—"}</td>
      <td>${d.encarregado}</td>
      <td>${d.assunto}</td>
      <td>${badgeNatureza(d.natureza)}</td>
      <td>${d.advogadoCliente || "—"}</td>
      <td>${badgeSituacao(d.situacao)}</td>
    </tr>
  `).join("");
}

document.getElementById("tabs").addEventListener("click", (e)=>{
  const tab = e.target.closest(".tab");
  if(!tab) return;
  document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
  tab.classList.add("active");
  filtroNatureza = tab.dataset.natureza;

  // reseta o filtro de tipo (processo/notificação) ao sair da aba Cível
  filtroTipoCivil = "__todos__";
  document.querySelectorAll("#tipoCivilPills .pill").forEach(p=>p.classList.remove("active"));
  document.querySelector('#tipoCivilPills .pill[data-tipo="__todos__"]').classList.add("active");

  // reseta o filtro de audiência ao sair da aba Trabalhista
  filtroAudiencia = "__todos__";
  document.querySelectorAll("#audienciaPills .pill").forEach(p=>p.classList.remove("active"));
  document.querySelector('#audienciaPills .pill[data-audiencia="__todos__"]').classList.add("active");

  popularEncarregados();
  renderTudo();
});

document.getElementById("tipoCivilPills").addEventListener("click", (e)=>{
  const pill = e.target.closest(".pill");
  if(!pill) return;
  document.querySelectorAll("#tipoCivilPills .pill").forEach(p=>p.classList.remove("active"));
  pill.classList.add("active");
  filtroTipoCivil = pill.dataset.tipo;
  renderTudo();
});

document.getElementById("audienciaPills").addEventListener("click", (e)=>{
  const pill = e.target.closest(".pill");
  if(!pill) return;
  document.querySelectorAll("#audienciaPills .pill").forEach(p=>p.classList.remove("active"));
  pill.classList.add("active");
  filtroAudiencia = pill.dataset.audiencia;
  renderTudo();
});

document.getElementById("filtroEncarregado").addEventListener("change", (e)=>{
  filtroEncarregado = e.target.value;
  renderTudo();
});

document.getElementById("periodPills").addEventListener("click", (e)=>{
  const pill = e.target.closest(".pill");
  if(!pill) return;
  document.querySelectorAll(".pill").forEach(p=>p.classList.remove("active"));
  pill.classList.add("active");
  filtroPeriodo = pill.dataset.periodo;
  renderTudo();
});

document.getElementById("busca").addEventListener("input", ()=>{
  renderTabela(aplicarFiltro());
});

popularEncarregados();
renderTudo();
</script>

</body>
</html>
"""


# =========================================================================
# MAIN — roda as duas extrações, uma atrás da outra, usando o mesmo token
# =========================================================================

if __name__ == "__main__":
    token = obter_token()

    print("=" * 70)
    print("PARTE 1: Extraindo ANDAMENTOS dos processos...")
    print("=" * 70)
    registros_andamentos = extrair_todos_andamentos(token)
    salvar_csv(registros_andamentos, ARQUIVO_CSV_ANDAMENTOS)
    gerar_relatorio_andamentos(registros_andamentos, ARQUIVO_HTML_ANDAMENTOS)

    print("\n" + "=" * 70)
    print("PARTE 2: Extraindo ATIVIDADES/PRAZOS...")
    print("=" * 70)
    registros_atividades = extrair_todas_atividades(token)
    salvar_csv(registros_atividades, ARQUIVO_CSV_ATIVIDADES)
    dados_dashboard = preparar_dados_dashboard(registros_atividades)
    gerar_dashboard_atividades(dados_dashboard, ARQUIVO_HTML_ATIVIDADES)

    print("\n" + "=" * 70)
    print("CONCLUÍDO! Arquivos gerados:")
    print(f"  - {ARQUIVO_CSV_ANDAMENTOS}")
    print(f"  - {ARQUIVO_HTML_ANDAMENTOS}")
    print(f"  - {ARQUIVO_CSV_ATIVIDADES}")
    print(f"  - {ARQUIVO_HTML_ATIVIDADES}")
    print("=" * 70)
