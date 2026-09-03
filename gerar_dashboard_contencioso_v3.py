# -*- coding: utf-8 -*-
"""
Dashboard do Contencioso (Cível, Trabalhista, Tributário) - Pacaembu
Versão 3.

Consolida:
  - Nomes de campo REAIS confirmados no extrair_contingencia_civel_api.py
    (pasta, cliente.nome, adverso.nome, advogadoCliente.nome,
     advogadoAdverso.nome, faseAtual.instancia, natureza, assunto, status)
  - Regras de negocio do script de contingencia:
       * pasta com formato CNJ valido
       * primeira instancia
       * status ativo
       * exclui incidentes e cumprimento de sentenca
       * natureza civel/trabalhista/tributario
    Todas podem ser desligadas com --sem-filtros (para depuracao).
  - Deducao de UF via numero CNJ (mais confiavel que cidade):
       TJ-SP=26, TJ-MT=11, TJ-PR=16
       TRT-SP=02/15, TRT-MT=23, TRT-PR=09
    Se nao conseguir pelo CNJ, cai no dicionario de cidades (fallback).
  - Interatividade completa (v2): cards, pills, rankings, timeline,
    barra de prognostico e modal com todos os campos do processo.

Modos:
  python3 gerar_dashboard_contencioso_v3.py               -> dashboard real
  python3 gerar_dashboard_contencioso_v3.py --descobrir   -> mostra os campos
  python3 gerar_dashboard_contencioso_v3.py --sem-filtros -> nao aplica filtros de qualidade
  python3 gerar_dashboard_contencioso_v3.py --demo        -> dashboard com dados falsos
"""
import re
import os
import sys
import csv
import json
import html
import random
import unicodedata
from collections import Counter, OrderedDict
from datetime import datetime, timedelta

try:
    import requests
except Exception:
    requests = None

ARQUIVO_HTML_SAIDA = "dashboard_contencioso.html"
ARQUIVO_CSV = "processos_datajuri.csv"

AUTH_URL = "https://api.datajuri.com.br/oauth/token"
API_URL = "https://api.datajuri.com.br/v1"
ENTIDADE = "Processo"

# Campos confirmados (base sempre presente) + candidatos a descobrir
CAMPOS_CERTOS = ["pasta", "cliente.nome", "adverso.nome",
                 "advogadoCliente.nome", "advogadoAdverso.nome",
                 "status", "localizacaoFisica"]

CANDIDATOS_A_DESCOBRIR = OrderedDict([
    ("natureza",          ["natureza"]),
    ("assunto",           ["assunto", "tipoAcao"]),     # tipoAcao como fallback (retornado no default)
    ("instancia",         ["faseAtual.instancia", "instancia"]),
    ("estado",            ["faseAtual.estado", "estado", "uf"]),          # NOVO: UF direto do DataJuri!
    ("cidade",            ["faseAtual.localidade", "localidade", "cidade", "comarca", "cidade.nome", "comarca.nome", "foro", "foro.nome"]),
    ("valorCausa",        ["valorCausa", "valorDaCausa", "valor_causa"]),
    ("valorProvisionado", ["valorProvisionado", "valorProvisao", "provisao", "valorContingencia",
                           "contingencia", "valorProvavel", "valorProvisaoContabil"]),
    ("prognostico",       ["prognostico", "possibilidadePerda", "probabilidadePerda", "risco",
                           "grauRisco", "classificacaoRisco", "chanceExito", "perda",
                           "perdaProvavel", "chanceDePerda", "avaliacaoRisco", "avaliacao",
                           "probabilidade", "expectativa", "prognosticoPerda"]),
    ("dataDistribuicao",  ["dataDistribuicao", "dataCadastro", "dataDistribuido", "dataAjuizamento",
                           "dataProtocolo", "dataAutuacao"]),
    # Campos contextuais (aparecem no modal como "outros campos"):
    ("tipoProcesso",      ["tipoProcesso", "tipo_processo", "tipo"]),
    ("tipoAcao",          ["tipoAcao"]),
    ("varaFase",          ["faseAtual.vara"]),
    ("tipoFase",          ["faseAtual.tipo"]),
    ("grupoResponsavel",  ["grupoResponsavel.nome", "grupo.nome"]),
    ("dataAbertura",      ["dataAbertura", "dataCadastro"]),
    ("valorCausaAtualizado",     ["valorCausaAtualizado"]),
    ("valorProvisionadoAtualizado", ["valorProvisionadoAtualizado"]),
])

REGEX_CNJ = re.compile(r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$')

# =====================================================================
#  DEDUCAO DE UF PELO NUMERO CNJ
# =====================================================================
# Numero CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
# J = segmento (8=TJ, 5=TRT, 4=TRF, 1=STF, 3=STJ)
# TR = codigo do tribunal (2 digitos)
TRIBUNAL_UF = {
    # Justica Estadual (segmento 8)
    ("8", "26"): "SP", ("8", "11"): "MT", ("8", "16"): "PR",
    # Justica do Trabalho (segmento 5)
    ("5", "02"): "SP", ("5", "15"): "SP", ("5", "23"): "MT", ("5", "09"): "PR",
    # Justica Federal (segmento 4) - regionais, aproximacao:
    ("4", "03"): "SP",   # TRF3 = SP/MS
    # TRF1 (01) cobre MT + varios estados -> nao decide sozinho
    # TRF4 (04) cobre PR/SC/RS -> nao decide sozinho
}


def uf_pelo_cnj(pasta):
    """Devolve 'SP','MT','PR' ou None a partir do numero CNJ."""
    if not pasta:
        return None
    m = re.match(r'^\d{7}-\d{2}\.\d{4}\.(\d)\.(\d{2})\.\d{4}$', pasta.strip())
    if not m:
        return None
    return TRIBUNAL_UF.get((m.group(1), m.group(2)))


# =====================================================================
#  FALLBACK: MAPA CIDADE -> UF (usado se o CNJ nao decidir)
# =====================================================================
CIDADES_SP = {
    "sao paulo","campinas","ribeirao preto","bauru","sorocaba","sao jose do rio preto",
    "araraquara","presidente prudente","santos","guarulhos","sao bernardo do campo",
    "osasco","santo andre","jundiai","piracicaba","sao jose dos campos","sao carlos",
    "marilia","franca","limeira","taubate","mogi das cruzes","diadema","carapicuiba",
    "itaquaquecetuba","barueri","cotia","suzano","embu","embu das artes","praia grande",
    "sao vicente","cubatao","guaruja","americana","rio claro","aracatuba","jau",
    "botucatu","assis","ourinhos","itapetininga","registro","itu","salto","valinhos",
    "vinhedo","paulinia","hortolandia","sumare","indaiatuba","mogi guacu","mogi mirim",
    "atibaia","braganca paulista","itatiba","jacarei","caraguatatuba","ubatuba",
    "sao sebastiao","itanhaem","peruibe","itapecerica da serra","taboao da serra",
    "ferraz de vasconcelos","poa","aruja","itapevi","jandira","mairipora","francisco morato",
    "franco da rocha","caieiras","santana de parnaiba","ibiuna","piedade","boituva",
    "porto feliz","tiete","tatui","cerquilho","pirassununga","leme","araras","mococa",
    "sao joao da boa vista","cravinhos","batatais","sertaozinho","catanduva","barretos",
    "olimpia","penapolis","birigui","lins","novo horizonte","matao","bebedouro",
    "fernandopolis","jales","votuporanga","adamantina","dracena","tupa","garca","lencois paulista",
}
CIDADES_MT = {
    "cuiaba","varzea grande","rondonopolis","sinop","tangara da serra","caceres","sorriso",
    "lucas do rio verde","barra do garcas","primavera do leste","alta floresta","nova mutum",
    "pontes e lacerda","colider","juina","mirassol d'oeste","mirassol doeste","diamantino",
    "campo verde","jaciara","pocone","chapada dos guimaraes","guaranta do norte",
    "matupa","juara","peixoto de azevedo","aripuana","comodoro","vila rica",
    "querencia","canarana","agua boa","nova xavantina","brasnorte","paranatinga","confresa",
    "porto alegre do norte","alto araguaia","alto taquari","itiquira","dom aquino","nova olimpia",
    "campo novo do parecis","sapezal","campos de julio","tapurah","itauba","claudia",
    "vera","santa carmem","feliz natal","marcelandia",
}
CIDADES_PR = {
    "curitiba","londrina","maringa","ponta grossa","cascavel","sao jose dos pinhais",
    "foz do iguacu","colombo","guarapuava","paranagua","araucaria","toledo","apucarana",
    "pinhais","campo largo","arapongas","almirante tamandare","umuarama","piraquara","cambe",
    "campo mourao","paranavai","francisco beltrao","pato branco","cianorte","dois vizinhos",
    "sarandi","fazenda rio grande","rolandia","irati","uniao da vitoria","telemaco borba",
    "castro","cornelio procopio","medianeira","marechal candido rondon","palmas","laranjeiras do sul",
    "jacarezinho","ibipora","matinhos","pontal do parana","antonina","morretes","guaratuba",
    "quatro barras","campo magro","lapa","bocaiuva do sul","tijucas do sul",
    "sao mateus do sul","rio negro","reboucas","prudentopolis","imbituva","imbau",
    "ortigueira","tibagi","ivaipora","assai","cambara",
    "santo antonio da platina","siqueira campos","jaguariaiva","arapoti",
}

UF_LABEL = {"SP": "São Paulo", "MT": "Mato Grosso", "PR": "Paraná", "outros": "Outros"}


def _norm(txt):
    if not txt:
        return ""
    txt = unicodedata.normalize("NFKD", str(txt))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.lower().strip()


def uf_pela_cidade(cidade):
    if not cidade:
        return None
    c = _norm(cidade)
    m = re.search(r'[\s/,\-]([a-z]{2})\s*$', c)
    if m:
        uf = m.group(1).upper()
        if uf in ("SP", "MT", "PR"):
            return uf
    c2 = re.sub(r'[\s/,\-]+[a-z]{2}\s*$', '', c).strip()
    if c2 in CIDADES_SP:
        return "SP"
    if c2 in CIDADES_MT:
        return "MT"
    if c2 in CIDADES_PR:
        return "PR"
    return None


def deduzir_uf(pasta, cidade, estado=None):
    """Prioridade: campo estado direto -> CNJ -> cidade -> outros."""
    # 1) campo estado da API (mais confiavel)
    if estado:
        e = str(estado).strip().upper()
        if e in ("SP", "MT", "PR"):
            return e, "campo estado"
        if e in ("SÃO PAULO", "SAO PAULO"):
            return "SP", "campo estado"
        if e in ("MATO GROSSO",):
            return "MT", "campo estado"
        if e in ("PARANÁ", "PARANA"):
            return "PR", "campo estado"
    # 2) numero CNJ
    uf = uf_pelo_cnj(pasta)
    if uf:
        return uf, "CNJ"
    # 3) nome da cidade
    uf = uf_pela_cidade(cidade)
    if uf:
        return uf, "cidade"
    return "outros", "-"


# =====================================================================
#  AUTENTICACAO (v13)
# =====================================================================
def ler_credenciais_zshrc():
    chaves = ["DATAJURI_BASIC_AUTH", "DATAJURI_USERNAME", "DATAJURI_PASSWORD"]
    creds = {}
    for k in chaves:
        v = os.environ.get(k)
        if v:
            creds[k] = v.strip()
    if all(k in creds for k in chaves):
        return creds
    caminho = os.path.expanduser("~/.zshrc")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            for linha in f:
                m = re.match(r'\s*export\s+(DATAJURI_[A-Z_]+)=(.+)', linha)
                if m:
                    valor = m.group(2).strip()
                    if " #" in valor:
                        valor = valor.split(" #", 1)[0].strip()
                    if len(valor) >= 2 and valor[0] in "\"'" and valor[-1] == valor[0]:
                        valor = valor[1:-1]
                    creds.setdefault(m.group(1), valor)
    return creds


def obter_token(creds):
    basic = creds.get("DATAJURI_BASIC_AUTH")
    user = creds.get("DATAJURI_USERNAME")
    senha = creds.get("DATAJURI_PASSWORD")
    if not basic or not user or not senha:
        print("ERRO: credenciais incompletas. Verifique DATAJURI_* no ~/.zshrc.")
        sys.exit(1)
    headers = {"Authorization": "Basic " + basic,
               "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "password", "username": user, "password": senha}
    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=120)
    if resp.status_code != 200:
        print("ERRO: falha na autenticacao (HTTP " + str(resp.status_code) + ").")
        print("  Resposta: " + resp.text[:200])
        sys.exit(1)
    return resp.json().get("access_token")


def _get_processo(headers, campos, page=1, pageSize=100):
    params = {"campos": campos, "page": page, "pageSize": pageSize}
    resp = requests.get(API_URL + "/entidades/" + ENTIDADE,
                        headers=headers, params=params, timeout=120)
    try:
        return resp.status_code, resp.json()
    except Exception:
        return resp.status_code, {}


def explorar_campos(headers):
    """Testa uma bateria grande de nomes de campos candidatos e mostra
    quais a API aceita, quais tem dados, e amostras dos valores."""
    print("=== EXPLORACAO DE CAMPOS DA ENTIDADE Processo ===\n")
    candidatos_potenciais = [
        # PROGNOSTICO / RISCO / PERDA
        "prognostico", "possibilidadePerda", "probabilidadePerda", "probabilidadeExito",
        "risco", "grauRisco", "grauDeRisco", "classificacaoRisco", "nivelRisco",
        "chanceExito", "chanceDeExito", "chance", "chanceGanho", "chancePerda",
        "perda", "perdaProvavel", "chanceDePerda", "possibilidadeDePerda",
        "avaliacaoRisco", "avaliacao", "probabilidade", "expectativa",
        "expectativaExito", "expectativaGanho", "expectativaPerda",
        "prognosticoPerda", "analiseContingencia", "contingencia", "contingenciaAtual",
        "perdaEsperada", "tipoContingencia", "tipoRisco", "provisaoTipo",
        "classificacaoContingencia", "avaliacaoContingencia", "previsaoResultado",
        "resultadoEsperado", "analiseRisco", "parecer", "expectativaResultado",
        "diagnosticoContingencia", "diagnostico", "classificacao", "resultadoProvavel",
        # DATAS
        "dataDistribuicao", "dataAbertura", "dataCadastro", "dataAjuizamento",
        "dataProtocolo", "dataAutuacao", "dataAlteracao", "dataFato", "dataCitacao",
        # VALORES
        "valorCausa", "valorProvisionado", "valorProvisao", "valorContingencia",
        "provisao", "contingencia", "valorProvavel", "valorProvisaoContabil",
        "valorCausaAtualizado", "valorProvisionadoAtualizado",
        "valorContingenciaAtualizado", "valorContabil", "valorPerdaProvavel",
        "valorPossivel", "valorRemoto", "valorTotal", "valorAtualizado",
    ]

    com_dados = OrderedDict()
    vazios = []
    inexistentes = []
    for cand in candidatos_potenciais:
        st, dados = _get_processo(headers, "id," + cand, page=1, pageSize=50)
        if st != 200 or not dados.get("rows"):
            inexistentes.append(cand)
            continue
        amostras = []
        for r in dados["rows"]:
            v = r.get(cand)
            if v is not None and str(v).strip() != "":
                amostras.append(v)
        if amostras:
            com_dados[cand] = amostras[:3]
        else:
            vazios.append(cand)

    print("[COM DADOS] Campos aceitos pela API E com valor em pelo menos 1 processo:")
    if com_dados:
        for k, s in com_dados.items():
            print(f"  ✓ {k}")
            for a in s:
                print(f"      amostra: {a!r}")
    else:
        print("  (nenhum encontrado com dados)")

    print("\n[VAZIOS] Campos aceitos mas 100% vazios na amostra de 50:")
    for k in vazios:
        print(f"  - {k}")

    print("\nTotal testado:", len(candidatos_potenciais),
          "| com dados:", len(com_dados),
          "| vazios:", len(vazios),
          "| inexistentes:", len(inexistentes))


def resolver_campos_extras(headers):
    """Descobre os nomes reais dos campos nao confirmados (valor, prognostico, etc).
    Um candidato so eh aceito se pelo menos 1 dos 30 registros de amostra
    tiver esse campo preenchido — para nao 'encontrar' um campo aceito pela
    API mas 100% vazio na base."""
    print("Descobrindo campos opcionais (valor, prognostico, cidade, data)...")
    mapa = OrderedDict()
    for conceito, candidatos in CANDIDATOS_A_DESCOBRIR.items():
        achou = None
        vazio_mas_existe = None
        for cand in candidatos:
            st, dados = _get_processo(headers, "id," + cand, page=1, pageSize=30)
            if st != 200 or not dados.get("rows"):
                continue
            preenchidos = 0
            for r in dados["rows"]:
                v = r.get(cand)
                if v is not None and str(v).strip() != "":
                    preenchidos += 1
            if preenchidos > 0:
                achou = cand
                break
            elif not vazio_mas_existe:
                vazio_mas_existe = cand  # existe mas amostra 100% vazia
        # se nenhum candidato tinha dado, aceita o 1o que ao menos existe
        if not achou:
            achou = vazio_mas_existe
        mapa[conceito] = achou
        marca = ("-> " + achou) if achou else "(nao encontrado)"
        print("  " + conceito.ljust(18) + marca)
    return mapa


def descobrir_e_imprimir(headers):
    print("=== CAMPOS RETORNADOS PELA API (entidade Processo) ===\n")
    params = {"page": 1, "pageSize": 3}
    resp = requests.get(API_URL + "/entidades/" + ENTIDADE,
                        headers=headers, params=params, timeout=120)
    try:
        dados = resp.json()
    except Exception:
        dados = {}
    rows = dados.get("rows", [])
    if rows:
        chaves = sorted(rows[0].keys())
        print("Campos default (" + str(len(chaves)) + "):")
        for c in chaves:
            print("  - " + c)
        print("\nExemplo do 1o registro:")
        print(json.dumps(rows[0], ensure_ascii=False, indent=2)[:3000])
    print("\n--- Testando campos opcionais ---")
    resolver_campos_extras(headers)


# =====================================================================
#  FILTROS DE QUALIDADE (do extrair_contingencia_civel_api.py)
# =====================================================================
# Filtro POSITIVO: so aceita processo com status ativo.
# 'aguardando citacao' tambem eh ativo (aguardando decisao processual).
STATUS_ATIVOS = ("ativ", "aguardando", "andamento", "em curso")


def esta_ativo(status):
    s = (status or "").strip().lower()
    if not s:
        return False  # sem status -> exclui por seguranca
    # Se o texto contem qualquer palavra que denote encerramento, exclui
    encerramento = ("finaliz", "arquiv", "encerr", "extint", "cancel", "baix",
                    "transit", "acordo homolog", "julgado")
    if any(e in s for e in encerramento):
        return False
    # Aceita se contem qualquer palavra que denote atividade
    return any(a in s for a in STATUS_ATIVOS)


def passa_filtros(reg, campos_extras):
    """Aplica filtros de qualidade. Se um campo nao foi descoberto na API,
    o filtro correspondente eh pulado (tolerancia)."""
    pasta = (reg.get("pasta") or "").strip()
    if not REGEX_CNJ.match(pasta):
        return False
    # SO processos ATIVOS (Ativo, Aguardando Citacao, Em andamento...)
    if not esta_ativo(reg.get("status")):
        return False
    # SO judiciais: se o campo tipoProcesso existir e nao for 'Judicial', exclui
    ctp = campos_extras.get("tipoProcesso")
    if ctp:
        tp = (reg.get(ctp) or "").strip().lower()
        if tp and "judicial" not in tp:
            return False
    # tipoAcao: exclui notificacoes (extrajudiciais)
    cta = campos_extras.get("tipoAcao")
    if cta:
        ta = (reg.get(cta) or "").strip().lower()
        if "notifica" in ta:
            return False
    # natureza: so filtra se o campo existir na API
    cn = campos_extras.get("natureza")
    if cn:
        natureza = (reg.get(cn) or "").strip().lower()
        if natureza and not ("civel" in natureza or "cível" in natureza or "civil" in natureza
                             or "trabalh" in natureza or "tribut" in natureza):
            return False
    # instancia: so filtra se existir e nao for primeira
    ci = campos_extras.get("instancia")
    if ci:
        instancia = (reg.get(ci) or "").strip().lower()
        if instancia and "primeira" not in instancia:
            return False
    # assunto: exclui incidente e cumprimento de sentenca
    ca = campos_extras.get("assunto")
    if ca:
        assunto = (reg.get(ca) or "").strip().lower()
        if "incidente" in assunto or "cumprimento de sentenca" in assunto or "cumprimento de sentença" in assunto:
            return False
    return True


def carregar_registros(headers, campos_extras, aplicar_filtros=True):
    campos_todos = CAMPOS_CERTOS + [v for v in campos_extras.values() if v]
    campos_str = ",".join(["id"] + list(OrderedDict.fromkeys(campos_todos)))
    registros = []
    total_bruto = 0
    status_counter_bruto = Counter()
    status_counter_valido = Counter()
    page = 1
    print("Buscando processos...")
    while True:
        st, dados = _get_processo(headers, campos_str, page=page, pageSize=100)
        linhas = dados.get("rows", []) if isinstance(dados, dict) else []
        if not linhas:
            break
        total_bruto += len(linhas)
        for r in linhas:
            status_counter_bruto[(r.get("status") or "(vazio)").strip()] += 1
        if aplicar_filtros:
            linhas = [r for r in linhas if passa_filtros(r, campos_extras)]
        for r in linhas:
            status_counter_valido[(r.get("status") or "(vazio)").strip()] += 1
        registros.extend(linhas)
        print("  Pagina " + str(page) + ": " + str(len(linhas)) + " validos")
        page += 1
    print("Total bruto : " + str(total_bruto))
    print("Total valido: " + str(len(registros)))
    print("\nStatus encontrados na base bruta (top 15):")
    for s, q in status_counter_bruto.most_common(15):
        marca = "  [ATIVO]" if s in status_counter_valido else "  (excluido)"
        print(f"  {q:5d} x {s!r}{marca}")
    if registros:
        try:
            cols = list(OrderedDict.fromkeys(["id"] + campos_todos))
            with open(ARQUIVO_CSV, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for r in registros:
                    w.writerow({c: r.get(c, "") for c in cols})
            print("Backup salvo em: " + ARQUIVO_CSV)
        except Exception as e:
            print("  Aviso: nao consegui salvar CSV: " + str(e))
    return registros


# =====================================================================
#  PARSERS
# =====================================================================
def esc_attr(s):
    """Escape seguro para atributo HTML — remove caracteres de controle e
    escapa aspas/tags. Previne quebra silenciosa do parser HTML por \\n, \\r,
    tabs ou aspas em nomes com apostrofos etc."""
    if s is None:
        return ""
    s = re.sub(r'[\x00-\x1f\x7f]', ' ', str(s))
    return html.escape(s, quote=True)


def gc(reg, campo):
    """Getter direto por nome de campo (o campo pode ser None)."""
    if not campo:
        return ""
    v = reg.get(campo, "")
    return (str(v).strip() if v is not None else "")


def parse_data(valor):
    if not valor:
        return None
    valor = str(valor).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(valor[:10], fmt)
        except ValueError:
            continue
    return None


def parse_valor(valor):
    if valor is None or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    s = re.sub(r'[^\d,.\-]', '', str(valor).strip())
    if not s:
        return 0.0
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def categoria_area(natureza):
    n = (natureza or "").strip().lower()
    if "trabalh" in n:
        return "trabalhista"
    if "tribut" in n or "fiscal" in n:
        return "tributario"
    return "civel"


AREA_LABEL = {"civel": "Cível", "trabalhista": "Trabalhista", "tributario": "Tributário"}


def bucket_prognostico(valor):
    p = (valor or "").strip().lower()
    if not p:
        return "naoclassificado"
    if "prov" in p:
        return "provavel"
    if "poss" in p:
        return "possivel"
    if "remot" in p or "improv" in p:
        return "remota"
    return "naoclassificado"


PROG_LABEL = {"provavel": "Provável", "possivel": "Possível",
              "remota": "Remota", "naoclassificado": "Não classificado"}
PROG_ORDEM = ["provavel", "possivel", "remota", "naoclassificado"]


def eh_aguardando_citacao(status, instancia):
    txt = ((status or "") + " " + (instancia or "")).lower()
    return "citac" in txt or "citaç" in txt


def fmt_moeda(v):
    try:
        s = "{:,.2f}".format(float(v))
    except Exception:
        s = "0.00"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_moeda_curta(v):
    v = float(v or 0)
    if abs(v) >= 1_000_000:
        return "R$ " + ("{:,.1f}".format(v / 1_000_000)).replace(",", ".") + " mi"
    if abs(v) >= 1_000:
        return "R$ " + ("{:,.0f}".format(v / 1_000)).replace(",", ".") + " mil"
    return fmt_moeda(v)


# =====================================================================
#  COMPONENTES HTML
# =====================================================================
def ranking_barras(contador, cor_classe, limite=10, grupo="", truncar=40):
    itens = contador.most_common(limite)
    if not itens:
        return '<p class="sem-dados">Sem dados</p>'
    maximo = itens[0][1]
    out = []
    for nome, qtd in itens:
        largura = int((qtd / maximo) * 100) if maximo else 0
        nome_exib = (nome[:truncar - 3] + "...") if (truncar and len(nome) > truncar) else nome
        out.append(
            '<div class="rank-row rank-row-clicavel" data-termo="' + html.escape(nome) +
            '" data-grupo="' + grupo + '" onclick="filtrarPorTermo(this)">'
            '<div class="rank-nome" title="' + html.escape(nome) + '">' + html.escape(nome_exib) + '</div>'
            '<div class="rank-bar-bg"><div class="rank-bar ' + cor_classe + '" style="width:' + str(largura) + '%"></div></div>'
            '<div class="rank-qtd">' + str(qtd) + '</div></div>'
        )
    return "".join(out)


def barra_prognostico(dist, total):
    cores = {"provavel": "#9c3b3b", "possivel": "#b8860b",
             "remota": "#3f6b4f", "naoclassificado": "#9ca3af"}
    seg = []
    for k in PROG_ORDEM:
        q = dist.get(k, 0)
        if q == 0:
            continue
        pct = (q / total * 100) if total else 0
        seg.append('<div class="pg-seg" data-prog="' + k + '" onclick="filtrarProgClique(\'' + k + '\')" '
                   'style="width:' + str(round(pct, 2)) + '%;background:' + cores[k] + '" '
                   'title="' + PROG_LABEL[k] + ': ' + str(q) + ' (clique para filtrar)"></div>')
    legenda = []
    for k in PROG_ORDEM:
        q = dist.get(k, 0)
        legenda.append(
            '<div class="pg-leg pg-leg-clic" onclick="filtrarProgClique(\'' + k + '\')">'
            '<span class="pg-dot" style="background:' + cores[k] + '"></span>'
            '<span class="pg-leg-lbl">' + PROG_LABEL[k] + '</span>'
            '<span class="pg-leg-num">' + str(q) + '</span></div>'
        )
    return ('<div class="pg-bar">' + "".join(seg) + '</div>'
            '<div class="pg-legenda">' + "".join(legenda) + '</div>')


def timeline_12meses(registros, campo_data, campo_data_fallback, campo_natureza, hoje):
    """Barras empilhadas por area. ACERVO ACUMULADO com HISTORICO COMPLETO:
    do mes da primeira abertura ate o mes atual, mostrando quantos processos
    ativos ja existiam ate o fim de cada mes."""
    meses_pt = ["", "jan", "fev", "mar", "abr", "mai", "jun",
                "jul", "ago", "set", "out", "nov", "dez"]
    # coleta (data_abertura, area) para todos os processos
    processos = []
    for r in registros:
        d = parse_data(gc(r, campo_data))
        if not d and campo_data_fallback:
            d = parse_data(gc(r, campo_data_fallback))
        if d:
            area = categoria_area(gc(r, campo_natureza))
            processos.append((d.date(), area))
    if not processos:
        return [], 0
    # Grafico comeca em jan/2024 fixo (o acervo anterior fica embutido em jan/24)
    INICIO_ANO = 2024
    INICIO_MES = 1
    seq = []
    yy, mm = INICIO_ANO, INICIO_MES
    while (yy, mm) <= (hoje.year, hoje.month):
        seq.append((yy, mm))
        mm += 1
        if mm > 12:
            mm = 1
            yy += 1
    stacked = {}
    for (yy, mm) in seq:
        if mm == 12:
            fim_mes = datetime(yy + 1, 1, 1).date() - timedelta(days=1)
        else:
            fim_mes = datetime(yy, mm + 1, 1).date() - timedelta(days=1)
        cont = {"civel": 0, "trabalhista": 0, "tributario": 0}
        for (d, area) in processos:
            if d <= fim_mes:
                cont[area] += 1
        stacked[(yy, mm)] = cont
    totais = [sum(stacked[k].values()) for k in seq]
    maximo = max(totais) if totais and max(totais) > 0 else 1
    cols = []
    for (yy, mm), tot in zip(seq, totais):
        chave = "%04d-%02d" % (yy, mm)
        destaque = " tl-col-atual" if (yy, mm) == (hoje.year, hoje.month) else ""
        segc = stacked[(yy, mm)]["civel"]
        segt = stacked[(yy, mm)]["trabalhista"]
        segb = stacked[(yy, mm)]["tributario"]
        altura_total = int((tot / maximo) * 150) + (2 if tot else 0)
        if tot > 0:
            h_civel = int(round((segc / tot) * altura_total))
            h_trab = int(round((segt / tot) * altura_total))
            h_trib = altura_total - h_civel - h_trab
        else:
            h_civel = h_trab = h_trib = 0
        titulo = f"{meses_pt[mm]}/{yy}: {tot} ativos (Civel {segc}, Trab {segt}, Trib {segb})"
        cols.append(
            '<div class="tl-col' + destaque + '" data-mes="' + chave + '" '
            'title="' + titulo + '">'
            '<div class="tl-val">' + str(tot) + '</div>'
            '<div class="tl-bar-wrap"><div class="tl-stack">'
            '<div class="tl-seg tl-seg-trib" style="height:' + str(h_trib) + 'px"></div>'
            '<div class="tl-seg tl-seg-trab" style="height:' + str(h_trab) + 'px"></div>'
            '<div class="tl-seg tl-seg-civel" style="height:' + str(h_civel) + 'px"></div>'
            '</div></div>'
            '<div class="tl-lbl">' + meses_pt[mm] + '<span class="tl-ano">/' + str(yy)[2:] + '</span></div>'
            '</div>'
        )
    return cols, totais[-1] if totais else 0


def area_tag(area):
    return '<span class="tag-area tag-' + area + '">' + AREA_LABEL[area] + '</span>'


def prog_badge(bucket):
    return '<span class="badge badge-prog-' + bucket + '">' + PROG_LABEL[bucket] + '</span>'


# =====================================================================
#  GERACAO DO DASHBOARD
# =====================================================================
def diagnosticar(registros, extras):
    """Imprime valores unicos e estatisticas dos campos criticos, para o
    usuario ver o que a API esta devolvendo."""
    print("\n" + "=" * 70)
    print("DIAGNOSTICO DOS CAMPOS")
    print("=" * 70)

    def _analisar_categorico(nome_conceito, campo, top=15):
        print(f"\n[{nome_conceito}] -> API: {campo!r}")
        if not campo:
            print("  (campo nao existe na API)")
            return
        c = Counter()
        vazios = 0
        for r in registros:
            v = r.get(campo)
            if v is None or (isinstance(v, str) and not v.strip()):
                vazios += 1
            else:
                c[str(v).strip()] += 1
        print(f"  Vazios: {vazios} de {len(registros)}")
        print(f"  Valores unicos: {len(c)}")
        for val, qtd in c.most_common(top):
            print(f"    {qtd:5d} x {val!r}")

    def _analisar_numerico(nome_conceito, campo):
        print(f"\n[{nome_conceito}] -> API: {campo!r}")
        if not campo:
            print("  (campo nao existe na API)")
            return
        vazios = zeros = ok = 0
        soma = 0.0
        amostras = []
        for r in registros:
            v = r.get(campo)
            if v is None or v == "":
                vazios += 1
            else:
                p = parse_valor(v)
                if p == 0:
                    zeros += 1
                else:
                    ok += 1
                    soma += p
                    if len(amostras) < 3:
                        amostras.append((v, p))
        print(f"  Vazios: {vazios} | Zero: {zeros} | Com valor: {ok} | Soma: {fmt_moeda(soma)}")
        if amostras:
            print("  Amostras (bruto -> parseado):")
            for bruto, parseado in amostras:
                print(f"    {bruto!r} -> {parseado}")

    def _analisar_data(nome_conceito, campo):
        print(f"\n[{nome_conceito}] -> API: {campo!r}")
        if not campo:
            print("  (campo nao existe na API)")
            return
        vazios = ok = falha = 0
        anos = Counter()
        amostras_falha = []
        for r in registros:
            v = r.get(campo)
            if v is None or (isinstance(v, str) and not v.strip()):
                vazios += 1
            else:
                d = parse_data(v)
                if d:
                    ok += 1
                    anos[d.year] += 1
                else:
                    falha += 1
                    if len(amostras_falha) < 5:
                        amostras_falha.append(str(v))
        print(f"  Vazios: {vazios} | Parseou OK: {ok} | Nao parseou: {falha}")
        if anos:
            print("  Distribuicao por ano (top 10):")
            for ano, qtd in anos.most_common(10):
                print(f"    {qtd:5d} x {ano}")
        if amostras_falha:
            print("  Amostras que nao parsearam:")
            for a in amostras_falha:
                print(f"    {a!r}")

    _analisar_categorico("prognostico", extras.get("prognostico"))
    _analisar_categorico("natureza",    extras.get("natureza"))
    _analisar_categorico("instancia",   extras.get("instancia"))
    _analisar_categorico("estado",      extras.get("estado"))
    _analisar_numerico  ("valorCausa",            extras.get("valorCausa"))
    _analisar_numerico  ("valorCausaAtualizado",  extras.get("valorCausaAtualizado"))
    _analisar_numerico  ("valorProvisionado",           extras.get("valorProvisionado"))
    _analisar_numerico  ("valorProvisionadoAtualizado", extras.get("valorProvisionadoAtualizado"))
    _analisar_data      ("dataDistribuicao", extras.get("dataDistribuicao"))
    _analisar_data      ("dataAbertura",     extras.get("dataAbertura"))
    print("\n" + "=" * 70)


def gerar_html(registros, extras):
    hoje = datetime.now().date()
    campo_natureza = extras.get("natureza")
    campo_assunto = extras.get("assunto")
    campo_instancia = extras.get("instancia")
    campo_estado = extras.get("estado")
    campo_cidade = extras.get("cidade")
    campo_causa = extras.get("valorCausa")
    campo_provisao = extras.get("valorProvisionado")
    campo_prog = extras.get("prognostico")
    campo_data = extras.get("dataDistribuicao")

    total = len(registros)
    area_counter = Counter()
    uf_counter = Counter()
    prog_counter = Counter()
    assunto_counter = Counter()
    adv_cliente_counter = Counter()
    adv_adverso_counter = Counter()
    fase_counter = Counter()  # faseAtual.instancia
    cidade_counter = Counter()
    aguardando = 0
    soma_causa = 0.0
    soma_provisao = 0.0
    ufs_por_metodo = Counter()

    detalhes = []
    linhas_tabela = []

    for idx, r in enumerate(registros):
        pasta = gc(r, "pasta") or ("#" + str(r.get("id", "")))
        natureza = gc(r, campo_natureza)
        cliente = gc(r, "cliente.nome") or "-"
        adverso = gc(r, "adverso.nome") or "-"
        advc = gc(r, "advogadoCliente.nome")
        adva = gc(r, "advogadoAdverso.nome")
        assunto = gc(r, campo_assunto)
        instancia = gc(r, campo_instancia)
        status = gc(r, "status")
        cidade = gc(r, campo_cidade)
        estado_valor = gc(r, campo_estado)

        area = categoria_area(natureza)
        uf, metodo_uf = deduzir_uf(pasta, cidade, estado_valor)
        prog = bucket_prognostico(gc(r, campo_prog))
        vcausa_orig = parse_valor(gc(r, campo_causa))
        vprov_orig = parse_valor(gc(r, campo_provisao))
        # Prefere o valor atualizado (com correcao monetaria) quando existir
        vcausa_at = parse_valor(gc(r, extras.get("valorCausaAtualizado")))
        vprov_at = parse_valor(gc(r, extras.get("valorProvisionadoAtualizado")))
        vcausa = vcausa_at if vcausa_at > 0 else vcausa_orig
        vprov = vprov_at if vprov_at > 0 else vprov_orig
        # Data: prefere dataDistribuicao; se vazia, cai em dataAbertura
        d = parse_data(gc(r, campo_data))
        if not d:
            d = parse_data(gc(r, extras.get("dataAbertura")))
        ag = eh_aguardando_citacao(status, instancia)

        area_counter[area] += 1
        uf_counter[uf] += 1
        prog_counter[prog] += 1
        ufs_por_metodo[metodo_uf] += 1
        if assunto:
            assunto_counter[assunto] += 1
        if advc:
            adv_cliente_counter[advc] += 1
        if adva:
            adv_adverso_counter[adva] += 1
        if instancia:
            fase_counter[instancia] += 1
        if cidade:
            cidade_counter[cidade] += 1
        if ag:
            aguardando += 1
        soma_causa += vcausa
        soma_provisao += vprov

        det = {
            "pasta": pasta,
            "area_label": AREA_LABEL[area],
            "natureza": natureza,
            "cliente": cliente,
            "adverso": adverso,
            "advogadoCliente": advc,
            "advogadoAdverso": adva,
            "assunto": assunto,
            "instancia": instancia,
            "cidade": cidade,
            "uf": UF_LABEL.get(uf, uf) + (" (via " + metodo_uf + ")" if metodo_uf != "-" else ""),
            "valorCausa": fmt_moeda(vcausa) if vcausa else "-",
            "valorProvisionado": fmt_moeda(vprov) if vprov else "-",
            "prognostico": PROG_LABEL[prog],
            "dataDistribuicao": d.strftime("%d/%m/%Y") if d else "-",
            "status": status,
            "aguardandoCitacao": "Sim" if ag else "Não",
        }
        for k, v in r.items():
            if k in ("id",):
                continue
            if k not in det and v not in (None, "", []):
                det["_" + k] = str(v)
        detalhes.append(det)

        # data-mes = data de distribuicao para filtro de timeline (compatibilidade)
        mes_attr = d.strftime("%Y-%m") if d else ""
        # ano/mesabertura: baseado em dataAbertura para o filtro de periodo
        d_ab = parse_data(gc(r, extras.get("dataAbertura"))) or d
        ano_attr = d_ab.strftime("%Y") if d_ab else ""
        mesab_attr = d_ab.strftime("%m") if d_ab else ""
        linhas_tabela.append(
            '<tr data-idx="' + str(idx) + '" data-area="' + area + '" data-uf="' + uf +
            '" data-prog="' + prog + '" data-fase="' + esc_attr(instancia) +
            '" data-assunto="' + esc_attr(assunto) +
            '" data-cidade="' + esc_attr(cidade) +
            '" data-advcliente="' + esc_attr(advc) +
            '" data-advadverso="' + esc_attr(adva) +
            '" data-agc="' + ("sim" if ag else "nao") +
            '" data-mes="' + mes_attr + '" data-ano="' + ano_attr + '" data-mesabertura="' + mesab_attr + '"'
            ' data-causa="' + str(vcausa) + '" data-provisao="' + str(vprov) + '">'
            '<td class="pasta-cell" onclick="abrirDetalhes(' + str(idx) + ')" title="Ver todos os campos">'
            '<span class="pasta-link">' + html.escape(pasta) + '</span></td>'
            '<td>' + area_tag(area) + '</td>'
            '<td>' + html.escape(assunto or "-") + '</td>'
            '<td>' + html.escape(cliente) + '</td>'
            '<td>' + html.escape(adverso) + '</td>'
            '<td>' + html.escape(advc or "-") + '</td>'
            '<td>' + html.escape(adva or "-") + '</td>'
            '<td>' + html.escape(instancia or "-") + '</td>'
            '<td class="td-num">' + (fmt_moeda(vcausa) if vcausa else "-") + '</td>'
            '<td>' + html.escape(cidade or "-") +
            (' <span class="uf-mini">' + uf + '</span>' if uf != "outros" else '') + '</td>'
            '</tr>'
        )

    civel = area_counter.get("civel", 0)
    trab = area_counter.get("trabalhista", 0)
    trib = area_counter.get("tributario", 0)
    provaveis = prog_counter.get("provavel", 0)

    def pill_area(area, label):
        cnt = total if area == "todos" else area_counter.get(area, 0)
        ativo = " active" if area == "todos" else ""
        return ('<div class="pill-area' + ativo + '" data-area="' + area +
                '" onclick="filtrarArea(\'' + area + '\',this)">' + label +
                '<span class="pill-count">' + str(cnt) + '</span></div>')
    pills_area = (pill_area("todos", "Todos") + pill_area("civel", "Cível") +
                  pill_area("trabalhista", "Trabalhista") + pill_area("tributario", "Tributário"))

    def pill_uf(uf, label):
        cnt = total if uf == "todos" else uf_counter.get(uf, 0)
        ativo = " active" if uf == "todos" else ""
        return ('<div class="pill-uf' + ativo + '" data-uf="' + uf +
                '" onclick="filtrarUf(\'' + uf + '\',this)">' + label +
                '<span class="pill-count">' + str(cnt) + '</span></div>')
    pills_uf = (pill_uf("todos", "Todos os Estados") + pill_uf("SP", "SP") +
                pill_uf("MT", "MT") + pill_uf("PR", "PR") + pill_uf("outros", "Outros"))

    def pill_prog(bucket, label):
        ativo = " active" if bucket == "todos" else ""
        return ('<div class="pill" data-prog="' + bucket + '"' + ativo +
                ' onclick="filtrarProg(\'' + bucket + '\',this)">' + label + '</div>')
    pills_prog = (pill_prog("todos", "Todos") + pill_prog("provavel", "Provável") +
                  pill_prog("possivel", "Possível") + pill_prog("remota", "Remota"))

    fases = sorted(fase_counter.keys())
    opts_fase = '<option value="">Todas as instâncias</option>' + "".join(
        '<option value="' + html.escape(f) + '">' + html.escape(f) + ' (' + str(fase_counter[f]) + ')</option>'
        for f in fases)

    # Anos disponiveis a partir da dataAbertura (comecando em 2024)
    anos_set = set()
    for r in registros:
        d = parse_data(gc(r, campo_data)) or parse_data(gc(r, extras.get("dataAbertura")))
        if d and d.year >= 2024:
            anos_set.add(d.year)
    anos_disp = sorted(anos_set)
    opts_ano = '<option value="">Todos os anos</option>' + "".join(
        '<option value="' + str(a) + '">' + str(a) + '</option>' for a in anos_disp)

    meses_nomes = [("01","Janeiro"),("02","Fevereiro"),("03","Março"),("04","Abril"),
                   ("05","Maio"),("06","Junho"),("07","Julho"),("08","Agosto"),
                   ("09","Setembro"),("10","Outubro"),("11","Novembro"),("12","Dezembro")]
    opts_mes = '<option value="">Todos os meses</option>' + "".join(
        '<option value="' + n + '">' + l + '</option>' for n, l in meses_nomes)

    tl_cols, tl_total = timeline_12meses(registros, campo_data, extras.get("dataAbertura"), campo_natureza, hoje)
    rk_assuntos = ranking_barras(assunto_counter, "bar-vermelho", limite=10, grupo="assunto")
    rk_advcli = ranking_barras(adv_cliente_counter, "bar-azul", limite=10, grupo="advcliente", truncar=30)
    rk_advadv = ranking_barras(adv_adverso_counter, "bar-dourado", limite=10, grupo="advadverso", truncar=30)
    rk_fase = ranking_barras(fase_counter, "bar-azul", limite=10, grupo="fase")
    rk_cidade = ranking_barras(cidade_counter, "bar-verde", limite=10, grupo="cidade")
    pg_html = barra_prognostico(prog_counter, total)
    atualizado = "Atualizado em " + datetime.now().strftime("%d/%m/%Y às %H:%M")

    # aviso amigavel se campo essencial nao foi encontrado
    avisos = []
    if not campo_natureza:
        avisos.append("natureza (divisão Cível/Trab./Trib. usará apenas ‘Cível’)")
    if not campo_assunto:
        avisos.append("assunto")
    if not campo_instancia:
        avisos.append("instância")
    if not campo_cidade:
        avisos.append("cidade")
    if not campo_causa:
        avisos.append("valor da causa")
    if not campo_provisao:
        avisos.append("valor provisionado")
    if not campo_data:
        avisos.append("data de distribuição")
    barra_aviso = ""
    if avisos:
        barra_aviso = (
            '<div class="aviso">'
            'Não localizei os campos: <b>' + ", ".join(avisos) + '</b>. '
            'Rode <code>python3 gerar_dashboard_contencioso_v3.py --descobrir</code> '
            'para eu ajustar o mapeamento.'
            '</div>'
        )

    css = (
        "*{margin:0;padding:0;box-sizing:border-box;}"
        "body{background:#f3f1ea;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#233240;min-height:100vh;}"
        ".header{background:#e9e5d9;border-bottom:3px solid #233240;padding:20px 32px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;}"
        ".header-left{display:flex;align-items:center;gap:14px;}"
        ".logo-mark{display:flex;align-items:stretch;height:34px;border-radius:2px;overflow:hidden;}"
        ".logo-navy{width:28px;background:#233240;}"
        ".logo-flag{position:relative;width:56px;background:#9c3b3b;overflow:hidden;}"
        ".logo-arrow-white{position:absolute;left:0;top:0;width:0;height:0;border-top:17px solid transparent;border-bottom:17px solid transparent;border-left:24px solid #fff;}"
        ".logo-arrow-gold{position:absolute;left:3px;top:0;width:0;height:0;border-top:17px solid transparent;border-bottom:17px solid transparent;border-left:20px solid #b8860b;}"
        ".logo-texto{display:flex;flex-direction:column;line-height:1.05;}"
        ".logo-nome{font-size:20px;font-weight:900;color:#233240;letter-spacing:.5px;}"
        ".logo-sub{font-size:9px;font-weight:700;color:#6b7280;letter-spacing:3px;}"
        ".header-center{text-align:center;flex:1;min-width:280px;}"
        ".header-center .kicker{font-size:11px;letter-spacing:3px;color:#8a8471;font-weight:700;margin-bottom:4px;}"
        ".header-center h1{font-size:23px;font-weight:900;color:#233240;letter-spacing:1px;}"
        ".header-center .sub{font-size:13px;color:#6b7280;margin-top:2px;}"
        ".header-right{display:flex;gap:26px;text-align:center;align-items:center;}"
        ".header-right .num{font-size:22px;font-weight:900;color:#233240;}"
        ".header-right .lbl{font-size:10px;color:#8a8471;font-weight:700;letter-spacing:.5px;}"
        ".header-right .data{font-size:11px;color:#9ca3af;margin-top:6px;}"
        ".container{max-width:1500px;margin:0 auto;padding:24px 32px 60px;}"
        ".aviso{background:#fff5e6;border:1px solid #f0d9a0;color:#7a5c08;padding:12px 18px;border-radius:10px;font-size:12.5px;margin-bottom:18px;}"
        ".aviso code{background:#f3e6c4;padding:1px 6px;border-radius:4px;font-size:11.5px;}"
        ".pills-linha{display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap;align-items:center;}"
        ".pills-titulo{font-size:11px;font-weight:800;color:#8a8471;letter-spacing:1.5px;text-transform:uppercase;margin-right:4px;}"
        ".pill-area,.pill-uf{background:#fff;color:#374151;border:2px solid #e2ddc9;padding:10px 18px;border-radius:12px;font-weight:800;font-size:13px;cursor:pointer;transition:.15s;display:flex;align-items:center;gap:9px;}"
        ".pill-area:hover,.pill-uf:hover{border-color:#233240;}"
        ".pill-area.active{background:#233240;color:#fff;border-color:#233240;}"
        ".pill-uf.active{background:#6b7f66;color:#fff;border-color:#6b7f66;}"
        ".pill-count{background:rgba(0,0,0,0.08);padding:2px 10px;border-radius:999px;font-size:12px;font-weight:800;}"
        ".pill-area.active .pill-count,.pill-uf.active .pill-count{background:rgba(255,255,255,0.2);}"
        ".filtros-bar{display:flex;align-items:center;gap:18px;flex-wrap:wrap;background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:14px 20px;margin-bottom:22px;}"
        ".filtro-grupo{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}"
        ".filtro-titulo{font-size:11px;font-weight:800;color:#8a8471;letter-spacing:1px;text-transform:uppercase;}"
        ".pill{background:#fff;color:#4b5563;border:1.5px solid #e2ddc9;padding:8px 16px;border-radius:999px;font-weight:700;font-size:12.5px;cursor:pointer;transition:.15s;}"
        ".pill:hover{border-color:#233240;}"
        ".pill.active{background:#233240;color:#fff;border-color:#233240;}"
        ".pill.active[data-prog='provavel']{background:#9c3b3b;border-color:#9c3b3b;}"
        ".pill.active[data-prog='possivel']{background:#b8860b;border-color:#b8860b;}"
        ".pill.active[data-prog='remota']{background:#3f6b4f;border-color:#3f6b4f;}"
        ".select-fase{padding:8px 14px;border:1.5px solid #e2ddc9;border-radius:8px;font-size:12.5px;color:#374151;background:#faf9f5;min-width:220px;}"
        ".select-fase:focus{outline:none;border-color:#233240;}"
        ".busca-inline{flex:1;min-width:200px;}"
        ".busca-inline input{width:100%;padding:9px 14px;border:1.5px solid #e2ddc9;border-radius:8px;font-size:13px;background:#faf9f5;}"
        ".busca-inline input:focus{outline:none;border-color:#233240;background:#fff;}"
        ".btn-limpar{background:#f3f1ea;color:#9c3b3b;border:1.5px solid #eecccc;padding:8px 14px;border-radius:8px;font-size:12px;font-weight:800;cursor:pointer;transition:.15s;}"
        ".btn-limpar:hover{background:#9c3b3b;color:#fff;border-color:#9c3b3b;}"
        ".stats-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:16px;}"
        "@media (max-width:1200px){.stats-grid{grid-template-columns:repeat(3,1fr);}}"
        "@media (max-width:700px){.stats-grid{grid-template-columns:repeat(2,1fr);}}"
        ".stat-card{background:#fff;border:1px solid #e2ddc9;border-left:6px solid #233240;border-radius:10px;padding:16px 18px;cursor:pointer;transition:.15s;}"
        ".stat-card:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(35,50,64,.12);}"
        ".stat-card .lbl{font-size:10px;color:#8a8471;font-weight:800;letter-spacing:.8px;text-transform:uppercase;margin-bottom:6px;}"
        ".stat-card .num{font-size:28px;font-weight:900;color:#233240;}"
        ".stat-card .sublbl{font-size:10.5px;color:#c4bda8;margin-top:4px;font-style:italic;}"
        ".stat-total{border-left-color:#233240;}"
        ".stat-civel{border-left-color:#2c4a63;} .stat-civel .num{color:#2c4a63;}"
        ".stat-trab{border-left-color:#8a660a;} .stat-trab .num{color:#8a660a;}"
        ".stat-trib{border-left-color:#6b7f66;} .stat-trib .num{color:#4f5f4b;}"
        ".stat-agc{border-left-color:#9c3b3b;} .stat-agc .num{color:#9c3b3b;}"
        ".stat-prov{border-left-color:#9c3b3b;} .stat-prov .num{color:#9c3b3b;}"
        ".valores-grid{display:grid;grid-template-columns:1fr;gap:16px;margin-bottom:22px;}"
        "@media (max-width:700px){.valores-grid{grid-template-columns:1fr;}}"
        ".valor-card{background:#233240;color:#fff;border-radius:12px;padding:22px 26px;display:flex;align-items:center;justify-content:space-between;}"
        ".valor-card.vc-prov{background:#9c3b3b;}"
        ".valor-card .vlbl{font-size:12px;font-weight:800;letter-spacing:1px;text-transform:uppercase;opacity:.85;}"
        ".valor-card .vnum{font-size:30px;font-weight:900;margin-top:4px;}"
        ".valor-card .vsub{font-size:11px;opacity:.7;margin-top:2px;}"
        ".valor-icon{font-size:34px;opacity:.35;}"
        ".paineis-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:22px;}"
        "@media (max-width:1150px){.paineis-grid{grid-template-columns:1fr;}}"
        ".painel{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:20px;}"
        ".painel-header{display:flex;align-items:center;gap:8px;margin-bottom:16px;}"
        ".painel-bar{width:4px;height:15px;background:#9c3b3b;border-radius:2px;}"
        ".painel h3{font-size:13px;color:#233240;font-weight:900;letter-spacing:.4px;text-transform:uppercase;}"
        ".rank-row{display:grid;grid-template-columns:160px 1fr auto;align-items:center;gap:10px;margin-bottom:11px;font-size:12px;}"
        ".rank-nome{color:#374151;font-weight:600;white-space:normal;word-break:break-word;line-height:1.3;}"
        ".rank-bar-bg{background:#f3f1ea;border-radius:6px;height:11px;overflow:hidden;align-self:center;}"
        ".rank-bar{height:100%;border-radius:6px;}"
        ".bar-azul{background:linear-gradient(90deg,#233240,#4a6c86);}"
        ".bar-vermelho{background:linear-gradient(90deg,#9c3b3b,#c17b7b);}"
        ".bar-dourado{background:linear-gradient(90deg,#8a660a,#c9a545);}"
        ".bar-verde{background:linear-gradient(90deg,#4f5f4b,#8ca081);}"
        ".rank-qtd{color:#233240;font-weight:800;text-align:right;min-width:20px;align-self:center;}"
        ".rank-row-clicavel{cursor:pointer;padding:4px;margin:-4px -4px 7px -4px;border-radius:8px;transition:.15s;}"
        ".rank-row-clicavel:hover{background:#f3f1ea;transform:translateX(2px);}"
        ".sem-dados{font-size:12px;color:#9ca3af;}"
        ".tl-card{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:22px 24px;margin-bottom:22px;}"
        ".tl-head{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:900;color:#233240;text-transform:uppercase;letter-spacing:.3px;margin-bottom:6px;}"
        ".tl-dot{width:10px;height:10px;border-radius:50%;background:#233240;}"
        ".tl-sub{font-size:12px;color:#9ca3af;margin-bottom:18px;}"
        ".tl-grid{display:flex;align-items:flex-end;gap:4px;height:220px;overflow-x:auto;padding-bottom:4px;}"
        ".tl-col{flex:0 0 42px;}"
        ".tl-col{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;cursor:pointer;padding:0 2px;border-radius:6px;transition:.15s;}"
        ".tl-col:hover{background:#faf9f5;}"
        ".tl-val{font-size:12px;font-weight:800;color:#233240;margin-bottom:4px;}"
        ".tl-bar-wrap{display:flex;align-items:flex-end;height:135px;width:60%;}"
        ".tl-bar{width:100%;background:linear-gradient(180deg,#4a6c86,#233240);border-radius:4px 4px 0 0;min-height:2px;transition:.2s;}"
        ".tl-stack{width:100%;display:flex;flex-direction:column;justify-content:flex-end;}"
        ".tl-seg{width:100%;transition:.2s;}"
        ".tl-seg-civel{background:#233240;}"
        ".tl-seg-trab{background:#9c3b3b;}"
        ".tl-seg-trib{background:#b8860b;}"
        ".tl-seg-civel:first-child{border-radius:0 0 4px 4px;}"
        ".tl-stack .tl-seg:last-child{border-radius:4px 4px 0 0;}"
        ".tl-legenda{display:flex;gap:22px;margin-top:14px;font-size:11.5px;color:#4b5563;font-weight:700;}"
        ".tl-leg-dot{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:middle;}"
        ".tl-col:hover .tl-bar{filter:brightness(1.15);}"
        ".tl-col-atual .tl-bar{background:linear-gradient(180deg,#c17b7b,#9c3b3b);}"
        ".tl-col.sel .tl-bar{background:linear-gradient(180deg,#c9a545,#8a660a);}"
        ".tl-lbl{font-size:10.5px;color:#8a8471;font-weight:700;margin-top:8px;text-transform:uppercase;}"
        ".tl-ano{color:#c4bda8;}"
        ".pg-card{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:22px 24px;margin-bottom:22px;}"
        ".pg-head{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:900;color:#233240;text-transform:uppercase;letter-spacing:.3px;margin-bottom:16px;}"
        ".pg-dot{width:10px;height:10px;border-radius:50%;background:#9c3b3b;}"
        ".pg-bar{display:flex;height:28px;border-radius:8px;overflow:hidden;margin-bottom:16px;background:#f3f1ea;}"
        ".pg-seg{height:100%;cursor:pointer;transition:.15s;}"
        ".pg-seg:hover{filter:brightness(1.15);}"
        ".pg-legenda{display:flex;gap:26px;flex-wrap:wrap;}"
        ".pg-leg{display:flex;align-items:center;gap:8px;}"
        ".pg-leg-clic{cursor:pointer;padding:4px 8px;border-radius:6px;transition:.15s;}"
        ".pg-leg-clic:hover{background:#f3f1ea;}"
        ".pg-leg .pg-dot{width:12px;height:12px;border-radius:3px;}"
        ".pg-leg-lbl{font-size:12.5px;color:#4b5563;font-weight:700;}"
        ".pg-leg-num{font-size:14px;color:#233240;font-weight:900;}"
        ".tabela-card{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:22px;}"
        ".tabela-card h3{font-size:13px;color:#233240;font-weight:900;letter-spacing:.4px;text-transform:uppercase;margin-bottom:6px;}"
        ".tabela-topo{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:12px;}"
        ".contagem{font-size:12px;color:#8a8471;font-weight:700;}"
        ".filtros-ativos{display:flex;gap:6px;flex-wrap:wrap;}"
        ".chip-filtro{background:#faf9f5;border:1px solid #e2ddc9;color:#4b5563;padding:4px 10px;border-radius:999px;font-size:11px;font-weight:700;display:inline-flex;align-items:center;gap:6px;}"
        ".chip-filtro span{color:#9c3b3b;cursor:pointer;font-weight:900;}"
        ".table-wrapper{overflow:auto;max-height:640px;border:1px solid #e2ddc9;border-radius:10px;}"
        "table{width:100%;border-collapse:collapse;}"
        "th{background:#faf9f5;padding:11px;text-align:left;font-size:10px;font-weight:800;color:#8a8471;text-transform:uppercase;letter-spacing:.4px;border-bottom:2px solid #e2ddc9;white-space:nowrap;position:sticky;top:0;z-index:2;}"
        "td{padding:10px 11px;border-bottom:1px solid #f3f1ea;font-size:12px;color:#374151;}"
        "td.td-num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}"
        "tr:hover{background:#faf9f5;}"
        ".pasta-cell{cursor:pointer;white-space:nowrap;}"
        ".pasta-link{color:#233240;font-weight:800;border-bottom:1.5px dashed #b8860b;transition:.15s;}"
        ".pasta-cell:hover .pasta-link{color:#9c3b3b;border-bottom-color:#9c3b3b;}"
        ".tag-area{font-size:9.5px;font-weight:800;padding:2px 9px;border-radius:999px;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap;}"
        ".tag-civel{background:#dde7ef;color:#2c4a63;}"
        ".tag-trabalhista{background:#f1e2c4;color:#7a5c08;}"
        ".tag-tributario{background:#dcece1;color:#3f6b4f;}"
        ".badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:9.5px;font-weight:800;white-space:nowrap;text-transform:uppercase;letter-spacing:.3px;}"
        ".badge-prog-provavel{background:#f3dede;color:#8a2e2e;}"
        ".badge-prog-possivel{background:#f3e6c4;color:#7a5c08;}"
        ".badge-prog-remota{background:#dcece1;color:#2f5a3d;}"
        ".badge-prog-naoclassificado{background:#e5e7eb;color:#4b5563;}"
        ".uf-mini{background:#f3f1ea;color:#6b7280;font-size:9px;font-weight:800;padding:1px 6px;border-radius:4px;margin-left:4px;}"
        ".oculto{display:none!important;}"
        ".modal-overlay{position:fixed;inset:0;background:rgba(35,50,64,.5);backdrop-filter:blur(3px);display:none;align-items:center;justify-content:center;z-index:1000;padding:24px;}"
        ".modal-overlay.aberto{display:flex;}"
        ".modal{background:#fff;border-radius:14px;max-width:800px;width:100%;max-height:88vh;overflow:hidden;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.4);}"
        ".modal-header{background:#233240;color:#fff;padding:22px 26px;display:flex;justify-content:space-between;align-items:flex-start;gap:16px;}"
        ".modal-header .mtag{font-size:10px;letter-spacing:2px;text-transform:uppercase;font-weight:800;opacity:.7;margin-bottom:6px;}"
        ".modal-header h2{font-size:20px;font-weight:900;letter-spacing:.5px;font-family:'Courier New',monospace;}"
        ".modal-close{background:rgba(255,255,255,.15);border:none;color:#fff;width:36px;height:36px;border-radius:50%;font-size:20px;cursor:pointer;font-weight:900;line-height:1;}"
        ".modal-close:hover{background:rgba(255,255,255,.28);}"
        ".modal-body{padding:24px 26px;overflow-y:auto;flex:1;}"
        ".mod-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px 22px;margin-bottom:22px;}"
        "@media (max-width:600px){.mod-grid{grid-template-columns:1fr;}}"
        ".mod-item{border-bottom:1px solid #f3f1ea;padding-bottom:10px;}"
        ".mod-lbl{font-size:10px;font-weight:800;color:#8a8471;letter-spacing:.8px;text-transform:uppercase;margin-bottom:4px;}"
        ".mod-val{font-size:13.5px;color:#233240;font-weight:600;word-break:break-word;}"
        ".mod-val.vazio{color:#c4bda8;font-style:italic;font-weight:400;}"
        ".mod-secao-titulo{font-size:11px;font-weight:900;color:#9c3b3b;text-transform:uppercase;letter-spacing:1px;margin:8px 0 12px;padding-bottom:6px;border-bottom:2px solid #f3dede;}"
        ".toast{position:fixed;bottom:32px;left:50%;transform:translateX(-50%) translateY(80px);background:#233240;color:#fff;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:700;box-shadow:0 8px 24px rgba(0,0,0,.25);z-index:2000;opacity:0;transition:.28s;pointer-events:none;}"
        ".toast.toast-show{transform:translateX(-50%) translateY(0);opacity:1;}"
    )

    logo = (
        '<div class="header-left">'
        '<div class="logo-mark"><div class="logo-navy"></div>'
        '<div class="logo-flag"><div class="logo-arrow-white"></div><div class="logo-arrow-gold"></div></div></div>'
        '<div class="logo-texto"><span class="logo-nome">PACAEMBU</span>'
        '<span class="logo-sub">CONSTRUTORA</span></div></div>'
    )
    header = (
        '<div class="header">' + logo +
        '<div class="header-center"><div class="kicker">JURÍDICO CONTENCIOSO</div>'
        '<h1>Painel do Contencioso</h1>'
        '<div class="sub">Cível &middot; Trabalhista &middot; Tributário</div></div>'
        '<div class="header-right">'
        '<div><div class="num" id="hdrTotal">' + str(total) + '</div><div class="lbl">Processos</div>'
        '<div class="data">' + atualizado + '</div></div>'
        '</div></div>'
    )

    stats = (
        '<div class="stats-grid">'
        '<div class="stat-card stat-total" onclick="filtrarAreaBotao(\'todos\')">'
        '<div class="lbl">Total de Processos</div><div class="num" id="stTotal">' + str(total) + '</div>'
        '<div class="sublbl">clique para ver todos</div></div>'
        '<div class="stat-card stat-civel" onclick="filtrarAreaBotao(\'civel\')">'
        '<div class="lbl">Cível</div><div class="num" id="stCivel">' + str(civel) + '</div>'
        '<div class="sublbl">filtrar cíveis</div></div>'
        '<div class="stat-card stat-trab" onclick="filtrarAreaBotao(\'trabalhista\')">'
        '<div class="lbl">Trabalhista</div><div class="num" id="stTrab">' + str(trab) + '</div>'
        '<div class="sublbl">filtrar trabalhistas</div></div>'
        '<div class="stat-card stat-trib" onclick="filtrarAreaBotao(\'tributario\')">'
        '<div class="lbl">Tributário</div><div class="num" id="stTrib">' + str(trib) + '</div>'
        '<div class="sublbl">filtrar tributários</div></div>'
        '<div class="stat-card stat-agc" onclick="filtrarAgc()">'
        '<div class="lbl">Aguardando Citação</div><div class="num" id="stAgc">' + str(aguardando) + '</div>'
        '<div class="sublbl">clique para filtrar</div></div>'
        '</div>'
    )

    valores = ''

    filtros = (
        '<div class="pills-linha"><span class="pills-titulo">Área:</span>' + pills_area + '</div>'
        '<div class="pills-linha"><span class="pills-titulo">Estado:</span>' + pills_uf + '</div>'
        '<div class="filtros-bar">'
        '<div class="filtro-grupo"><select class="select-fase" id="anoSelect" style="min-width:140px;">' + opts_ano + '</select></div>'
        '<div class="filtro-grupo"><select class="select-fase" id="mesSelect" style="min-width:150px;">' + opts_mes + '</select></div>'
        '<div class="filtro-grupo"><select class="select-fase" id="faseSelect">' + opts_fase + '</select></div>'
        '<div class="busca-inline"><input type="text" id="busca" placeholder="Buscar por processo, cliente, adverso, assunto, cidade..."></div>'
        '<button class="btn-limpar" onclick="limparFiltros()">Limpar filtros</button>'
        '</div>'
    )

    timeline_card = (
        '<div class="tl-card"><div class="tl-head"><span class="tl-dot"></span>Evolução do Acervo de Processos</div>'
        '<div class="tl-sub">Total de processos ativos ao fim de cada mês, empilhados por área. Acervo atual: ' + str(tl_total) + ' processos.</div>'
        '<div class="tl-grid">' + "".join(tl_cols) + '</div>'
        '<div class="tl-legenda">'
        '<span><span class="tl-leg-dot" style="background:#233240"></span>Cível</span>'
        '<span><span class="tl-leg-dot" style="background:#9c3b3b"></span>Trabalhista</span>'
        '<span><span class="tl-leg-dot" style="background:#b8860b"></span>Tributário</span>'
        '</div></div>'
    )

    prog_card = (
        '<div class="pg-card"><div class="pg-head"><span class="pg-dot"></span>Possibilidade de Perda</div>'
        + pg_html + '</div>'
    )

    paineis1 = (
        '<div class="paineis-grid">'
        '<div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Assuntos dos Processos</h3></div>' + rk_assuntos + '</div>'
        '<div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Advogado do Cliente</h3></div>' + rk_advcli + '</div>'
        '<div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Advogado Adverso</h3></div>' + rk_advadv + '</div>'
        '</div>'
    )
    paineis2 = (
        '<div class="paineis-grid" style="grid-template-columns:1fr 1fr;">'
        '<div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Processos por Instância</h3></div>' + rk_fase + '</div>'
        '<div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Processos por Cidade</h3></div>' + rk_cidade + '</div>'
        '</div>'
    )

    cabecalhos = ["Processo", "Área", "Assunto", "Cliente", "Adverso", "Adv. Cliente",
                  "Adv. Adverso", "Instância", "Cidade"]
    th = "".join("<th>" + c + "</th>" for c in cabecalhos)
    tabela = (
        '<div class="tabela-card" id="tabelaCard"><h3>Todos os Processos</h3>'
        '<div class="tabela-topo">'
        '<div class="contagem" id="contagem">' + str(total) + ' processo(s)</div>'
        '<div class="filtros-ativos" id="chipsAtivos"></div>'
        '</div>'
        '<div class="table-wrapper"><table><thead><tr>' + th + '</tr></thead>'
        '<tbody id="tabelaBody">' + "".join(linhas_tabela) + '</tbody></table></div></div>'
    )

    modal = (
        '<div class="modal-overlay" id="modalOverlay" onclick="if(event.target===this)fecharModal()">'
        '<div class="modal">'
        '<div class="modal-header">'
        '<div><div class="mtag" id="mArea">-</div><h2 id="mPasta">-</h2></div>'
        '<button class="modal-close" onclick="fecharModal()">&times;</button>'
        '</div>'
        '<div class="modal-body" id="modalBody"></div>'
        '</div></div>'
    )

    corpo = ('<div class="container">' + barra_aviso + stats + filtros +
             timeline_card + paineis1 + paineis2 + tabela + '</div>' + modal)

    detalhes_json = json.dumps(detalhes, ensure_ascii=False)

    js = (
        "var DADOS=" + detalhes_json + ";"
        "var areaAtiva='todos',ufAtiva='todos',progAtivo='todos',mesAtivo='',agcAtivo=false;"
        "var termoAtivo={grupo:'',valor:''};"
        "function scrollTabela(){document.getElementById('tabelaCard').scrollIntoView({behavior:'smooth',block:'start'});}"
        "function filtrarArea(a,el){areaAtiva=a;"
        "document.querySelectorAll('.pill-area').forEach(function(p){p.classList.remove('active');});"
        "if(el)el.classList.add('active');else document.querySelectorAll('.pill-area').forEach(function(p){if(p.getAttribute('data-area')===a)p.classList.add('active');});"
        "aplicar();}"
        "function filtrarAreaBotao(a){filtrarArea(a,null);scrollTabela();}"
        "function filtrarUf(u,el){ufAtiva=u;"
        "document.querySelectorAll('.pill-uf').forEach(function(p){p.classList.remove('active');});"
        "if(el)el.classList.add('active');else document.querySelectorAll('.pill-uf').forEach(function(p){if(p.getAttribute('data-uf')===u)p.classList.add('active');});"
        "aplicar();scrollTabela();}"
        "function filtrarProg(p,el){progAtivo=p;"
        "document.querySelectorAll('.pill[data-prog]').forEach(function(x){x.classList.remove('active');});"
        "if(el)el.classList.add('active');else document.querySelectorAll('.pill[data-prog]').forEach(function(x){if(x.getAttribute('data-prog')===p)x.classList.add('active');});"
        "aplicar();}"
        "function filtrarProgBotao(p){filtrarProg(p,null);scrollTabela();}"
        "function filtrarProgClique(p){filtrarProg(p,null);scrollTabela();}"
        "function filtrarAgc(){agcAtivo=!agcAtivo;aplicar();scrollTabela();}"
        "function filtrarMes(m){"
        "if(mesAtivo===m){mesAtivo='';}else{mesAtivo=m;}"
        "document.querySelectorAll('.tl-col').forEach(function(c){c.classList.toggle('sel',c.getAttribute('data-mes')===mesAtivo&&mesAtivo!=='');});"
        "aplicar();scrollTabela();}"
        "function filtrarPorTermo(el){"
        "var t=el.getAttribute('data-termo');var g=el.getAttribute('data-grupo');"
        "termoAtivo={grupo:g,valor:t};document.getElementById('busca').value='';"
        "aplicar();scrollTabela();}"
        "function limparFiltros(){"
        "areaAtiva='todos';ufAtiva='todos';progAtivo='todos';mesAtivo='';agcAtivo=false;"
        "termoAtivo={grupo:'',valor:''};"
        "document.getElementById('busca').value='';document.getElementById('faseSelect').value='';document.getElementById('anoSelect').value='';document.getElementById('mesSelect').value='';"
        "document.querySelectorAll('.pill-area').forEach(function(p){p.classList.toggle('active',p.getAttribute('data-area')==='todos');});"
        "document.querySelectorAll('.pill-uf').forEach(function(p){p.classList.toggle('active',p.getAttribute('data-uf')==='todos');});"
        "document.querySelectorAll('.pill[data-prog]').forEach(function(p){p.classList.toggle('active',p.getAttribute('data-prog')==='todos');});"
        "document.querySelectorAll('.tl-col').forEach(function(c){c.classList.remove('sel');});"
        "aplicar();}"
        "function fmtMoeda(v){return 'R$ '+v.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});}"
        "function fmtCurta(v){if(Math.abs(v)>=1000000)return 'R$ '+(v/1000000).toFixed(1).replace('.',',')+' mi';if(Math.abs(v)>=1000)return 'R$ '+Math.round(v/1000).toLocaleString('pt-BR')+' mil';return fmtMoeda(v);}"
        "function aplicar(){"
        "var termo=document.getElementById('busca').value.toLowerCase();"
        "var faseSel=document.getElementById('faseSelect').value;"
        "var anoSel=document.getElementById('anoSelect').value;"
        "var mesSel=document.getElementById('mesSelect').value;"
        "var vis=0,cCivel=0,cTrab=0,cTrib=0,cAgc=0,cProv=0,sCausa=0,sProv=0;"
        "document.querySelectorAll('#tabelaBody tr').forEach(function(l){"
        "var texto=l.textContent.toLowerCase();"
        "var area=l.getAttribute('data-area');var uf=l.getAttribute('data-uf');"
        "var prog=l.getAttribute('data-prog');var fase=l.getAttribute('data-fase')||'';"
        "var agc=l.getAttribute('data-agc');var mes=l.getAttribute('data-mes')||'';"
        "var ano=l.getAttribute('data-ano')||'';"
        "var mesab=l.getAttribute('data-mesabertura')||'';"
        "var pTxt=texto.includes(termo);"
        "var pArea=(areaAtiva==='todos')||(area===areaAtiva);"
        "var pUf=(ufAtiva==='todos')||(uf===ufAtiva);"
        "var pProg=(progAtivo==='todos')||(prog===progAtivo);"
        "var pFase=(faseSel==='')||(fase===faseSel);"
        "var pAno=(anoSel==='')||(ano===anoSel);"
        "var pMesAb=(mesSel==='')||(mesab===mesSel);"
        "var pMes=(mesAtivo==='')||(mes===mesAtivo);"
        "var pAgc=(!agcAtivo)||(agc==='sim');"
        "var pTermo=true;"
        "if(termoAtivo.valor){var attr='data-'+termoAtivo.grupo;var val=l.getAttribute(attr)||'';pTermo=(val===termoAtivo.valor);}"
        "var ok=pTxt&&pArea&&pUf&&pProg&&pFase&&pAno&&pMesAb&&pMes&&pAgc&&pTermo;"
        "l.classList.toggle('oculto',!ok);"
        "if(ok){vis++;"
        "if(area==='civel')cCivel++;else if(area==='trabalhista')cTrab++;else if(area==='tributario')cTrib++;"
        "if(agc==='sim')cAgc++;if(prog==='provavel')cProv++;"
        "sCausa+=parseFloat(l.getAttribute('data-causa')||0);"
        "sProv+=parseFloat(l.getAttribute('data-provisao')||0);}"
        "});"
        "function s(id,v){var e=document.getElementById(id);if(e)e.textContent=v;}"
        "s('stTotal',vis);s('stCivel',cCivel);s('stTrab',cTrab);s('stTrib',cTrib);s('stAgc',cAgc);s('stProv',cProv);"
        "s('hdrTotal',vis);"
        "s('vCausa',fmtMoeda(sCausa));"
        "s('contagem',vis+' processo(s)');"
        "renderChips();"
        "}"
        "function renderChips(){"
        "var cont=document.getElementById('chipsAtivos');var out=[];"
        "var labelArea={civel:'Cível',trabalhista:'Trabalhista',tributario:'Tributário'};"
        "var labelProg={provavel:'Provável',possivel:'Possível',remota:'Remota'};"
        "var labelUf={SP:'São Paulo',MT:'Mato Grosso',PR:'Paraná',outros:'Outros estados'};"
        "if(areaAtiva!=='todos')out.push({t:'Área: '+labelArea[areaAtiva],f:function(){filtrarArea('todos',null);}});"
        "if(ufAtiva!=='todos')out.push({t:'Estado: '+labelUf[ufAtiva],f:function(){filtrarUf('todos',null);}});"
        "if(progAtivo!=='todos')out.push({t:'Prognóstico: '+labelProg[progAtivo],f:function(){filtrarProg('todos',null);}});"
        "if(mesAtivo)out.push({t:'Mês: '+mesAtivo,f:function(){filtrarMes(mesAtivo);}});"
        "if(agcAtivo)out.push({t:'Aguardando citação',f:function(){agcAtivo=false;aplicar();}});"
        "if(termoAtivo.valor)out.push({t:termoAtivo.grupo+': '+termoAtivo.valor,f:function(){termoAtivo={grupo:'',valor:''};aplicar();}});"
        "var fs=document.getElementById('faseSelect').value;"
        "if(fs)out.push({t:'Instância: '+fs,f:function(){document.getElementById('faseSelect').value='';aplicar();}});"
        "var ans=document.getElementById('anoSelect').value;"
        "if(ans)out.push({t:'Ano: '+ans,f:function(){document.getElementById('anoSelect').value='';aplicar();}});"
        "var mns=document.getElementById('mesSelect').value;"
        "var mesNomes={'01':'Jan','02':'Fev','03':'Mar','04':'Abr','05':'Mai','06':'Jun','07':'Jul','08':'Ago','09':'Set','10':'Out','11':'Nov','12':'Dez'};"
        "if(mns)out.push({t:'Mês: '+(mesNomes[mns]||mns),f:function(){document.getElementById('mesSelect').value='';aplicar();}});"
        "cont.innerHTML='';"
        "out.forEach(function(c,i){var el=document.createElement('div');el.className='chip-filtro';"
        "el.innerHTML=c.t+' <span title=\"remover\">&times;</span>';"
        "el.querySelector('span').addEventListener('click',c.f);cont.appendChild(el);});"
        "}"
        "function mostrarToast(texto){"
        "var t=document.getElementById('toast');if(!t){t=document.createElement('div');t.id='toast';t.className='toast';document.body.appendChild(t);}"
        "t.textContent=texto;t.classList.add('toast-show');"
        "clearTimeout(window._toastTimer);"
        "window._toastTimer=setTimeout(function(){t.classList.remove('toast-show');},2200);}"
        "function abrirDetalhes(idx){"
        "var d=DADOS[idx];if(!d)return;"
        # copia numero do processo pra area de transferencia
        "if(d.pasta){"
        "if(navigator.clipboard&&navigator.clipboard.writeText){"
        "navigator.clipboard.writeText(d.pasta).then(function(){mostrarToast('📋 '+d.pasta+' copiado');}).catch(function(){});"
        "}else{"
        "var ta=document.createElement('textarea');ta.value=d.pasta;document.body.appendChild(ta);ta.select();try{document.execCommand('copy');mostrarToast('📋 '+d.pasta+' copiado');}catch(e){}document.body.removeChild(ta);"
        "}}"
        "document.getElementById('mArea').textContent=d.area_label||'-';"
        "document.getElementById('mPasta').textContent=d.pasta||'-';"
        "var principais=["
        "['Cliente','cliente'],['Adverso','adverso'],"
        "['Advogado do Cliente','advogadoCliente'],['Advogado Adverso','advogadoAdverso'],"
        "['Assunto','assunto'],['Natureza','natureza'],"
        "['Instância','instancia'],['Status','status'],"
        "['Cidade','cidade'],['Estado','uf'],"
        "['Data de Distribuição','dataDistribuicao'],['Aguardando Citação','aguardandoCitacao'],"
        "['Valor da Causa','valorCausa'],"
        "['Prognóstico','prognostico']"
        "];"
        "var html='<div class=\"mod-secao-titulo\">Dados principais</div><div class=\"mod-grid\">';"
        "principais.forEach(function(p){var v=d[p[1]];var vazio=(!v||v==='-'||v==='');"
        "html+='<div class=\"mod-item\"><div class=\"mod-lbl\">'+p[0]+'</div>'"
        "+'<div class=\"mod-val'+(vazio?' vazio':'')+'\">'+(vazio?'não informado':v)+'</div></div>';});"
        "html+='</div>';"
        "var extras=[];for(var k in d){if(k.charAt(0)==='_')extras.push([k.substring(1),d[k]]);}"
        "if(extras.length){html+='<div class=\"mod-secao-titulo\">Outros campos</div><div class=\"mod-grid\">';"
        "extras.forEach(function(e){html+='<div class=\"mod-item\"><div class=\"mod-lbl\">'+e[0]+'</div>'"
        "+'<div class=\"mod-val\">'+e[1]+'</div></div>';});html+='</div>';}"
        "document.getElementById('modalBody').innerHTML=html;"
        "document.getElementById('modalOverlay').classList.add('aberto');"
        "document.body.style.overflow='hidden';"
        "}"
        "function fecharModal(){"
        "document.getElementById('modalOverlay').classList.remove('aberto');"
        "document.body.style.overflow='';}"
        "document.addEventListener('keydown',function(e){if(e.key==='Escape')fecharModal();});"
        "document.getElementById('busca').addEventListener('input',aplicar);"
        "document.getElementById('faseSelect').addEventListener('change',aplicar);"
        "document.getElementById('anoSelect').addEventListener('change',aplicar);"
        "document.getElementById('mesSelect').addEventListener('change',aplicar);"
        "aplicar();"
    )

    print("UF resolvida por: " + str(dict(ufs_por_metodo)))
    return (
        '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Painel do Contencioso - Pacaembu</title>'
        '<style>' + css + '</style></head><body>' + header + corpo +
        '<script>' + js + '</script></body></html>'
    )


# =====================================================================
#  DEMO
# =====================================================================
def gerar_demo():
    naturezas = ["Cível", "Cível", "Cível", "Cível", "Trabalhista", "Trabalhista",
                 "Tributário", "Cível"]
    assuntos = ["Rescisão contratual", "Indenização por danos", "Vício construtivo",
                "Cobrança", "Horas extras", "Verbas rescisórias", "Execução fiscal",
                "Distrato imobiliário", "Atraso na obra", "Multa contratual"]
    advs_cli = ["Dra. Marina Alves", "Dr. Rafael Souza", "Dra. Beatriz Lima",
                "Dr. Paulo Nunes", "Dra. Camila Rocha"]
    advs_adv = ["Dr. Fernando Dias", "Dra. Helena Castro", "Dr. Marcos Vieira",
                "Escritório Andrade & Cia", "Dra. Juliana Prado"]
    instancias = ["Primeira Instância", "Primeira Instância", "Primeira Instância"]
    cidades_sp = ["São Paulo", "Campinas", "Bauru", "Sorocaba", "Santos", "Piracicaba"]
    cidades_mt = ["Cuiabá", "Várzea Grande", "Rondonópolis", "Sinop"]
    cidades_pr = ["Curitiba", "Londrina", "Maringá", "Cascavel"]
    prognosticos = ["Provável", "Possível", "Remota", "Possível", "Remota", "Remota"]
    registros = []
    hoje = datetime.now()
    # gera pastas CNJ REAIS por estado (permite testar a deducao)
    tribunais_por_uf = [("SP", "26"), ("SP", "26"), ("SP", "26"),
                        ("MT", "11"), ("PR", "16")]
    for i in range(160):
        uf, tr = random.choice(tribunais_por_uf)
        cidades = {"SP": cidades_sp, "MT": cidades_mt, "PR": cidades_pr}[uf]
        pasta = "%07d-%02d.%04d.8.%s.%04d" % (
            random.randint(1, 9999999), random.randint(1, 99),
            2024 - random.randint(0, 1), tr, random.randint(1, 999))
        d = hoje - timedelta(days=random.randint(0, 400))
        registros.append({
            "id": 1000 + i,
            "pasta": pasta,
            "cliente.nome": "Pacaembu Construtora",
            "adverso.nome": random.choice(["João P. Santos", "Metalúrgica ABC Ltda", "Construtora XYZ",
                                           "Maria F. Oliveira", "Condomínio Central"]),
            "advogadoCliente.nome": random.choice(advs_cli),
            "advogadoAdverso.nome": random.choice(advs_adv),
            "faseAtual.instancia": random.choice(instancias),
            "natureza": random.choice(naturezas),
            "assunto": random.choice(assuntos),
            "status": random.choice(["Ativo", "Ativo", "Ativo", "Aguardando Citação"]),
            "cidade": random.choice(cidades),
            "valorCausa": round(random.uniform(15000, 2500000), 2),
            "valorProvisionado": round(random.uniform(0, 800000), 2),
            "prognostico": random.choice(prognosticos),
            "dataDistribuicao": d.strftime("%Y-%m-%d"),
        })
    extras = {"cidade": "cidade", "valorCausa": "valorCausa",
              "valorProvisionado": "valorProvisionado", "prognostico": "prognostico",
              "dataDistribuicao": "dataDistribuicao"}
    return registros, extras


# =====================================================================
#  MAIN
# =====================================================================
def main():
    args = sys.argv[1:]

    if "--demo" in args:
        print("Modo DEMO: gerando dashboard com dados sinteticos.")
        registros, extras = gerar_demo()
        html_final = gerar_html(registros, extras)
        with open(ARQUIVO_HTML_SAIDA, "w", encoding="utf-8") as f:
            f.write(html_final)
        print("Dashboard de exemplo salvo em: " + ARQUIVO_HTML_SAIDA)
        return

    if requests is None:
        print("ERRO: 'requests' nao instalado. Rode: pip3 install requests")
        sys.exit(1)

    creds = ler_credenciais_zshrc()
    print("Autenticando na API DataJuri...")
    token = obter_token(creds)
    headers = {"Authorization": "Bearer " + token}

    if "--descobrir" in args:
        descobrir_e_imprimir(headers)
        return

    if "--explorar" in args:
        explorar_campos(headers)
        return

    extras = resolver_campos_extras(headers)
    aplicar = "--sem-filtros" not in args
    if not aplicar:
        print("AVISO: --sem-filtros ativo -> nao vou aplicar os filtros de qualidade.")
    registros = carregar_registros(headers, extras, aplicar_filtros=aplicar)
    diagnosticar(registros, extras)
    html_final = gerar_html(registros, extras)
    with open(ARQUIVO_HTML_SAIDA, "w", encoding="utf-8") as f:
        f.write(html_final)
    print("Dashboard salvo em: " + ARQUIVO_HTML_SAIDA)
    print("Abra: open " + ARQUIVO_HTML_SAIDA)


if __name__ == "__main__":
    main()
