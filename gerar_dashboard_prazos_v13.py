# -*- coding: utf-8 -*-
import re
import csv
import html
import os
import sys
import requests
from collections import Counter
from datetime import datetime, timedelta

ARQUIVO_CSV = "atividades_datajuri.csv"
ARQUIVO_HTML_SAIDA = "dashboard_prazos.html"

AUTH_URL = "https://api.datajuri.com.br/oauth/token"
API_URL = "https://api.datajuri.com.br/v1"

# Campos que o dashboard usa (mesmos nomes achatados do CSV/API)
CAMPOS_API = (
    "id,prazo_do_encarregado,data,hora,encarregado.nome,encarregadoId,"
    "proprietario.nome,proprietarioId,assunto,tipoAtividade,status,"
    "processo.pasta,processoId,processo.adverso.nome,processo.natureza,"
    "processo.advogadoCliente.nome,diasPrazo,observacao"
)


def ler_credenciais_zshrc():
    """Le as credenciais DATAJURI. Tenta primeiro o ambiente (mais confiavel,
    valores completos), e cai para o arquivo ~/.zshrc como reserva."""
    chaves = ["DATAJURI_BASIC_AUTH", "DATAJURI_USERNAME", "DATAJURI_PASSWORD"]

    # 1) Ambiente (onde as variaveis ja estao carregadas pelo shell)
    creds = {}
    for k in chaves:
        v = os.environ.get(k)
        if v:
            creds[k] = v.strip()
    if all(k in creds for k in chaves):
        return creds

    # 2) Reserva: le o arquivo ~/.zshrc. Captura tudo apos o '=' ate o fim
    #    da linha, so removendo aspas nas pontas -> nao trunca no '=' do base64.
    caminho = os.path.expanduser("~/.zshrc")
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            for linha in f:
                m = re.match(r'\s*export\s+(DATAJURI_[A-Z_]+)=(.+)', linha)
                if m:
                    valor = m.group(2).strip()
                    # remove comentario inline apos espaco, se houver
                    # (nao corta '#' colado ao valor, apenas ' #')
                    if " #" in valor:
                        valor = valor.split(" #", 1)[0].strip()
                    # remove aspas nas pontas
                    if len(valor) >= 2 and valor[0] in "\"'" and valor[-1] == valor[0]:
                        valor = valor[1:-1]
                    creds.setdefault(m.group(1), valor)
    return creds


def obter_token(creds):
    """Autentica na API (mesma logica do extrair_contingencia_civel_api.py)."""
    basic = creds.get("DATAJURI_BASIC_AUTH")
    user = creds.get("DATAJURI_USERNAME")
    senha = creds.get("DATAJURI_PASSWORD")
    if not basic or not user or not senha:
        print("ERRO: credenciais incompletas no ~/.zshrc.")
        print("  Encontrado: " + str(list(creds.keys())))
        sys.exit(1)
    headers = {"Authorization": "Basic " + basic,
               "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "password", "username": user, "password": senha}
    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=120)
    if resp.status_code != 200:
        print("ERRO: falha na autenticacao (HTTP " + str(resp.status_code) + ").")
        print("  BASIC_AUTH lido: " + str(len(basic)) + " caracteres (termina em '" + basic[-2:] + "')")
        print("  Usuario: " + user)
        print("  Resposta da API: " + resp.text[:200])
        sys.exit(1)
    return resp.json().get("access_token")


def carregar_registros():
    """Busca todas as atividades direto da API DataJuri (dados sempre atualizados)."""
    creds = ler_credenciais_zshrc()
    print("Autenticando na API...")
    token = obter_token(creds)
    headers = {"Authorization": "Bearer " + token}

    registros = []
    page = 1
    print("Buscando tarefas (prazos)...")
    while True:
        params = {"campos": CAMPOS_API, "page": page, "pageSize": 100}
        try:
            resp = requests.get(API_URL + "/entidades/Tarefa",
                                 headers=headers, params=params, timeout=120)
            dados = resp.json()
        except Exception as e:
            print("  Aviso: erro na pagina " + str(page) + ": " + str(e))
            break
        linhas = dados.get("rows", [])
        if not linhas:
            break
        registros.extend(linhas)
        print("  Pagina " + str(page) + ": " + str(len(linhas)) + " registros")
        page += 1

    print("Total bruto da API: " + str(len(registros)) + " tarefas")

    # --- Filtro de entrada: manter apenas prazos do mes atual em diante ---
    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)
    filtrados = []
    for r in registros:
        d = data_do_registro(r)
        if d and d >= inicio_mes:
            filtrados.append(r)
    registros = filtrados
    print("Apos filtro (mes atual em diante): " + str(len(registros)) + " tarefas")

    # Salva um CSV de backup com os mesmos campos do dashboard
    if registros:
        try:
            campos = CAMPOS_API.split(",")
            with open(ARQUIVO_CSV, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
                writer.writeheader()
                for r in registros:
                    writer.writerow({c: r.get(c, "") for c in campos})
            print("Backup salvo em: " + ARQUIVO_CSV)
        except Exception as e:
            print("  Aviso: nao consegui salvar backup CSV: " + str(e))

    return registros


def parse_data(valor):
    if not valor:
        return None
    valor = valor.strip()
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    for fmt in formatos:
        try:
            return datetime.strptime(valor[:10], fmt)
        except ValueError:
            continue
    return None


def categoria_status(status):
    s = (status or "").strip().lower()
    if "conclu" in s or "final" in s:
        return "finalizado"
    if "andamento" in s:
        return "andamento"
    if "nao iniciad" in s or "não iniciad" in s or "pendente" in s or s == "":
        return "naoiniciado"
    return "outro"


def campo(reg, chave):
    return (reg.get(chave, "") or "").strip()


def data_do_registro(r):
    data_str = campo(r, "prazo_do_encarregado") or campo(r, "data")
    dt = parse_data(data_str)
    return dt.date() if dt else None


def categoria_area(natureza):
    n = (natureza or "").strip().lower()
    if "trabalh" in n:
        return "trabalhista"
    return "civel"


def opcoes_status_select(cat_atual):
    opcoes = [("naoiniciado", "Não iniciado"), ("andamento", "Em andamento"), ("finalizado", "Finalizado")]
    partes = []
    for valor, label in opcoes:
        sel = " selected" if valor == cat_atual else ""
        partes.append('<option value="' + valor + '"' + sel + '>' + label + '</option>')
    return "".join(partes)


def gerar_linhas_tabela(registros, hoje, semana_inicio, semana_fim, prox_semana_inicio, prox_semana_fim, mes_inicio, mes_fim):
    linhas = []
    for r in registros:
        cat = categoria_status(campo(r, "status"))
        area = categoria_area(campo(r, "processo.natureza"))
        encarregado = campo(r, "encarregado.nome") or "N/A"
        pasta = campo(r, "processo.pasta") or "N/A"
        assunto_val = campo(r, "assunto")
        tipo_val = campo(r, "tipoAtividade")
        assunto_exibir = assunto_val or tipo_val or "N/A"
        span_oculto = ""
        if tipo_val and tipo_val != assunto_exibir:
            span_oculto = '<span class="oculto-busca">' + html.escape(tipo_val) + '</span>'

        d = data_do_registro(r)
        periodos_row = []
        eh_hoje = False
        eh_semana = False
        if d:
            if d == hoje:
                periodos_row.append("dia")
                eh_hoje = True
            if semana_inicio <= d <= semana_fim:
                periodos_row.append("semana")
                eh_semana = True
            if prox_semana_inicio <= d <= prox_semana_fim:
                periodos_row.append("proxsemana")
            if mes_inicio <= d <= mes_fim:
                periodos_row.append("mes")
        periodos_attr = " ".join(periodos_row)

        dia_semana_attr = ""
        if d and semana_inicio <= d <= semana_fim:
            _nomes_dia = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
            dia_semana_attr = _nomes_dia[d.weekday()]

        _texto_assunto = (assunto_val + " " + tipo_val).lower()
        acompanhar_attr = "sim" if "acompanhar" in _texto_assunto else "nao"

        # Destaque visual: prazo de hoje (vermelho) tem prioridade sobre a semana (dourado)
        classe_linha = ""
        if eh_hoje:
            classe_linha = " linha-hoje"
        elif eh_semana:
            classe_linha = " linha-semana"

        # Coluna prazo e encarregado ganham selo quando o prazo e hoje
        selo_hoje = '<span class="selo-hoje">HOJE</span> ' if eh_hoje else ""
        classe_prazo = ' class="prazo-destaque"' if eh_hoje else ""
        classe_enc = ' class="enc-destaque"' if eh_hoje else ""

        linhas.append(
            '<tr data-status="' + cat + '" data-area="' + area + '" data-encarregado="' + html.escape(encarregado.lower()) + '" data-periodos="' + periodos_attr + '" data-diasemana="' + dia_semana_attr + '" data-acompanhar="' + acompanhar_attr + '" class="' + classe_linha.strip() + '">'
            '<td class="pasta-cell"><span class="pasta-texto">' + html.escape(pasta) + '</span>'
            '<button type="button" class="btn-copiar" data-pasta="' + html.escape(pasta) + '" onclick="copiarPasta(this)" title="Copiar numero do processo">&#128203;</button></td>'
            '<td>' + html.escape(campo(r, "processo.adverso.nome") or "N/A") + '</td>'
            '<td' + classe_prazo + '>' + selo_hoje + html.escape(campo(r, "prazo_do_encarregado") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "data") or "N/A") + '</td>'
            '<td' + classe_enc + '>' + html.escape(encarregado) + '</td>'
            '<td>' + html.escape(assunto_exibir) + span_oculto + '</td>'
            '<td><select class="status-select status-' + cat + '" data-original="' + cat + '" onchange="mudarStatus(this)">' + opcoes_status_select(cat) + '</select></td>'
            '</tr>'
        )
    return "".join(linhas)


def gerar_ranking_barras(contador, cor_classe, limite=10, truncar=False, clicavel=False, grupo=""):
    itens = contador.most_common(limite)
    if not itens:
        return '<p class="sem-dados">Sem prazos neste periodo</p>'
    maximo = itens[0][1]
    linhas = []
    for nome, qtd in itens:
        largura = int((qtd / maximo) * 100) if maximo else 0
        if truncar and len(nome) > 30:
            nome_exibir = nome[:27] + "..."
        else:
            nome_exibir = nome
        classe_extra = " rank-row-clicavel" if clicavel else ""
        atributos = ' data-termo="' + html.escape(nome) + '" data-grupo="' + grupo + '" onclick="filtrarPorTermo(this)"' if clicavel else ""
        linhas.append(
            '<div class="rank-row' + classe_extra + '"' + atributos + '>'
            '<div class="rank-nome" title="' + html.escape(nome) + '">' + html.escape(nome_exibir) + '</div>'
            '<div class="rank-bar-bg"><div class="rank-bar ' + cor_classe + '" style="width:' + str(largura) + '%"></div></div>'
            '<div class="rank-qtd">' + str(qtd) + '</div>'
            '</div>'
        )
    return "".join(linhas)


def gerar_html(registros):
    total = len(registros)
    nao_iniciados = sum(1 for r in registros if categoria_status(campo(r, "status")) == "naoiniciado")
    em_andamento = sum(1 for r in registros if categoria_status(campo(r, "status")) == "andamento")
    finalizados = sum(1 for r in registros if categoria_status(campo(r, "status")) == "finalizado")
    total_civel = sum(1 for r in registros if categoria_area(campo(r, "processo.natureza")) == "civel")
    total_trabalhista = sum(1 for r in registros if categoria_area(campo(r, "processo.natureza")) == "trabalhista")

    encarregado_counter_total = Counter()
    assunto_counter = Counter()
    tipo_atividade_counter = Counter()
    for r in registros:
        enc = campo(r, "encarregado.nome")
        if enc:
            encarregado_counter_total[enc] += 1
        assunto = campo(r, "assunto") or campo(r, "tipoAtividade")
        if assunto:
            assunto_counter[assunto] += 1
        tipo_ativ = campo(r, "tipoAtividade")
        if tipo_ativ:
            tipo_atividade_counter[tipo_ativ] += 1

    encarregados_unicos = sorted(encarregado_counter_total.keys())
    opcoes_encarregado = "".join(
        '<option value="' + html.escape(e.lower()) + '">' + html.escape(e) + ' (' + str(encarregado_counter_total[e]) + ')</option>'
        for e in encarregados_unicos
    )

    hoje = datetime.now().date()
    semana_inicio = hoje - timedelta(days=hoje.weekday())
    semana_fim = semana_inicio + timedelta(days=6)
    prox_semana_inicio = semana_fim + timedelta(days=1)
    prox_semana_fim = prox_semana_inicio + timedelta(days=6)
    mes_inicio = hoje.replace(day=1)
    if hoje.month == 12:
        mes_fim = hoje.replace(day=31)
    else:
        proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
        mes_fim = proximo_mes - timedelta(days=1)

    qtd_dia = 0
    qtd_semana = 0
    qtd_prox_semana = 0
    qtd_mes = 0
    enc_dia = Counter()
    enc_semana = Counter()
    enc_prox_semana = Counter()
    enc_mes = Counter()
    assunto_dia = Counter()
    assunto_semana = Counter()
    assunto_prox_semana = Counter()
    assunto_mes = Counter()
    tipo_dia = Counter()
    tipo_semana = Counter()
    tipo_prox_semana = Counter()
    tipo_mes = Counter()

    for r in registros:
        d = data_do_registro(r)
        if not d:
            continue
        enc = campo(r, "encarregado.nome") or "N/A"
        assunto_r = campo(r, "assunto") or campo(r, "tipoAtividade")
        tipo_r = campo(r, "tipoAtividade")
        if d == hoje:
            qtd_dia += 1
            enc_dia[enc] += 1
            if assunto_r:
                assunto_dia[assunto_r] += 1
            if tipo_r:
                tipo_dia[tipo_r] += 1
        if semana_inicio <= d <= semana_fim:
            qtd_semana += 1
            enc_semana[enc] += 1
            if assunto_r:
                assunto_semana[assunto_r] += 1
            if tipo_r:
                tipo_semana[tipo_r] += 1
        if prox_semana_inicio <= d <= prox_semana_fim:
            qtd_prox_semana += 1
            enc_prox_semana[enc] += 1
            if assunto_r:
                assunto_prox_semana[assunto_r] += 1
            if tipo_r:
                tipo_prox_semana[tipo_r] += 1
        if mes_inicio <= d <= mes_fim:
            qtd_mes += 1
            enc_mes[enc] += 1
            if assunto_r:
                assunto_mes[assunto_r] += 1
            if tipo_r:
                tipo_mes[tipo_r] += 1

    # --- Lista de prazos de Acompanhamento (card contador + lista) ---
    def _eh_acompanhar(r):
        return "acompanhar" in ((campo(r, "assunto") + " " + campo(r, "tipoAtividade")).lower())

    prazos_acomp = [r for r in registros if _eh_acompanhar(r)]
    prazos_acomp.sort(key=lambda x: (campo(x, "encarregado.nome") or "zzz").lower())
    total_acomp = len(prazos_acomp)

    if prazos_acomp:
        _itens_ac = []
        for r in prazos_acomp:
            enc_a = campo(r, "encarregado.nome") or "N/A"
            pasta_a = campo(r, "processo.pasta") or "N/A"
            assunto_a = campo(r, "assunto") or campo(r, "tipoAtividade") or "N/A"
            data_a = campo(r, "prazo_do_encarregado") or "N/A"
            area_a = categoria_area(campo(r, "processo.natureza"))
            cat_a = categoria_status(campo(r, "status"))
            _itens_ac.append(
                '<div class="ac-item ac-item-' + cat_a + '">'
                '<div class="ac-topo"><span class="ac-resp">' + html.escape(enc_a) + '</span>'
                '<span class="ac-data">' + html.escape(data_a) + '</span></div>'
                '<div class="ac-proc">' + html.escape(pasta_a) + ' <span class="tag-area tag-' + area_a + '">' + ("Trabalhista" if area_a == "trabalhista" else "Cível") + '</span></div>'
                '<div class="ac-assunto">' + html.escape(assunto_a) + '</div>'
                '</div>'
            )
        bloco_acomp = (
            '<div class="ac-painel" id="acPainel">'
            '<div class="ac-painel-head">Prazos de Acompanhamento <span class="ac-count">' + str(total_acomp) + '</span>'
            '<button class="ac-fechar" onclick="toggleListaAcomp()">Fechar</button></div>'
            '<div class="ac-lista">' + "".join(_itens_ac) + '</div>'
            '</div>'
        )
    else:
        bloco_acomp = '<div class="ac-painel" id="acPainel"><div class="ac-painel-head">Nenhum acompanhamento</div></div>'

    # --- Lista de Prazos Fatais (agrupada: hoje / vencidos / proximos) ---
    def _data_fatal(r):
        d = parse_data(campo(r, "data"))
        return d.date() if d else None

    prazos_fatais = [r for r in registros if _data_fatal(r)]
    prazos_fatais.sort(key=lambda x: _data_fatal(x))
    total_fatal = len(prazos_fatais)

    fatais_hoje = [r for r in prazos_fatais if _data_fatal(r) == hoje]
    fatais_vencidos = [r for r in prazos_fatais if _data_fatal(r) < hoje]
    fatais_futuros = [r for r in prazos_fatais if _data_fatal(r) > hoje]
    total_fatal_hoje = len(fatais_hoje)

    def _card_fatal(r):
        enc_f = campo(r, "encarregado.nome") or "N/A"
        pasta_f = campo(r, "processo.pasta") or "N/A"
        assunto_f = campo(r, "assunto") or campo(r, "tipoAtividade") or "N/A"
        df = _data_fatal(r)
        data_f = df.strftime("%d/%m/%Y")
        area_f = categoria_area(campo(r, "processo.natureza"))
        if df < hoje:
            urg = "vencido"
        elif df == hoje:
            urg = "hoje"
        elif df <= semana_fim:
            urg = "semana"
        else:
            urg = "futuro"
        cat_f = categoria_status(campo(r, "status"))
        _rot_st = {"naoiniciado": "Nao iniciado", "andamento": "Em andamento", "finalizado": "Finalizado", "outro": "Cancelado/Outro"}
        selo_st = '<span class="fa-status fa-status-' + cat_f + '">' + _rot_st.get(cat_f, "Outro") + '</span>'
        return (
            '<div class="fa-item fa-item-' + urg + '" onclick="irParaProcesso(&#39;' + html.escape(pasta_f) + '&#39;)" title="Clique para ver este processo na tabela">'
            '<div class="fa-topo"><span class="fa-data">' + data_f + '</span>' + selo_st + '</div>'
            '<div class="fa-resp">' + html.escape(enc_f) + '</div>'
            '<div class="fa-proc">' + html.escape(pasta_f) + ' <span class="tag-area tag-' + area_f + '">' + ("Trabalhista" if area_f == "trabalhista" else "Cível") + '</span></div>'
            '<div class="fa-assunto">' + html.escape(assunto_f) + '</div>'
            '</div>'
        )

    if prazos_fatais:
        _grupos_fa = []
        for _ch, _rot, _id, _lista, _aberto in [
            ("hoje", "Vencem Hoje", "faGrupoHoje", fatais_hoje, True),
            ("vencido", "Vencidos (anteriores)", "faGrupoVencidos", fatais_vencidos, False),
            ("futuro", "Proximos (a vencer)", "faGrupoFuturos", fatais_futuros, False),
        ]:
            if not _lista:
                continue
            _cls = "fa-grupo" + ("" if _aberto else " fa-grupo-fechado")
            _seta = "&#9662;" if _aberto else "&#9656;"
            _grupos_fa.append(
                '<div class="' + _cls + '" id="' + _id + '">'
                '<div class="fa-grupo-head fa-grupo-' + _ch + '" onclick="toggleGrupoFatal(&#39;' + _id + '&#39;)" title="Clique para abrir ou fechar">'
                '<span class="fa-seta">' + _seta + '</span>' + _rot + ' <span class="fa-grupo-count">' + str(len(_lista)) + '</span></div>'
                '<div class="fa-lista">' + "".join(_card_fatal(r) for r in _lista) + '</div>'
                '</div>'
            )
        bloco_fatal = (
            '<div class="fa-painel" id="faPainel">'
            '<div class="fa-painel-head">Prazos por Data Fatal <span class="fa-count">' + str(total_fatal) + '</span>'
            '<span class="fa-dica">Clique num item para ver o processo na tabela</span>'
            '<button class="ac-fechar" onclick="toggleListaFatal()">Fechar</button></div>'
            + "".join(_grupos_fa) +
            '</div>'
        )
    else:
        bloco_fatal = '<div class="fa-painel" id="faPainel"><div class="fa-painel-head">Nenhum prazo fatal</div></div>'
        total_fatal_hoje = 0

    linhas_tabela = gerar_linhas_tabela(registros, hoje, semana_inicio, semana_fim, prox_semana_inicio, prox_semana_fim, mes_inicio, mes_fim)

    # --- Item (iii): lista dos prazos de HOJE com o responsavel ---
    prazos_hoje = []
    for r in registros:
        if data_do_registro(r) == hoje:
            prazos_hoje.append(r)
    # ordena por nome do encarregado
    prazos_hoje.sort(key=lambda x: (campo(x, "encarregado.nome") or "zzz").lower())

    def _card_hoje(r):
        enc = campo(r, "encarregado.nome") or "N/A"
        pasta = campo(r, "processo.pasta") or "N/A"
        assunto_h = campo(r, "assunto") or campo(r, "tipoAtividade") or "N/A"
        area_h = categoria_area(campo(r, "processo.natureza"))
        cat_h = categoria_status(campo(r, "status"))
        _rot = {"naoiniciado": "Nao iniciado", "andamento": "Em andamento", "finalizado": "Finalizado", "outro": "Outro"}
        tag_area = '<span class="tag-area tag-' + area_h + '">' + ("Trabalhista" if area_h == "trabalhista" else "Cível") + '</span>'
        selo_status = '<span class="hoje-status hoje-status-' + cat_h + '">' + _rot.get(cat_h, "Outro") + '</span>'
        return (
            '<div class="hoje-item hoje-item-' + cat_h + '">'
            '<div class="hoje-topo"><div class="hoje-resp">' + html.escape(enc) + '</div>' + selo_status + '</div>'
            '<div class="hoje-info"><span class="hoje-pasta">' + html.escape(pasta) + '</span> ' + tag_area + '<div class="hoje-assunto">' + html.escape(assunto_h) + '</div></div>'
            '</div>'
        )

    if prazos_hoje:
        grupos_ordem = [
            ("naoiniciado", "Nao Iniciados"),
            ("andamento", "Em Andamento"),
            ("finalizado", "Finalizados"),
            ("outro", "Cancelados / Outros"),
        ]
        blocos_status = []
        for chave, rotulo in grupos_ordem:
            do_grupo = [r for r in prazos_hoje if categoria_status(campo(r, "status")) == chave]
            if not do_grupo:
                continue
            cards = "".join(_card_hoje(r) for r in do_grupo)
            blocos_status.append(
                '<div class="hoje-grupo">'
                '<div class="hoje-grupo-head hoje-grupo-' + chave + '">' + rotulo + ' <span class="hoje-grupo-count">' + str(len(do_grupo)) + '</span></div>'
                '<div class="hoje-lista">' + cards + '</div>'
                '</div>'
            )
        bloco_hoje = (
            '<div class="hoje-card">'
            '<div class="hoje-header"><span class="hoje-dot"></span>Prazos de Hoje &middot; ' + hoje.strftime("%d/%m/%Y") + ' <span class="hoje-count">' + str(len(prazos_hoje)) + '</span></div>'
            + "".join(blocos_status) +
            '</div>'
        )
    else:
        bloco_hoje = (
            '<div class="hoje-card hoje-vazio">'
            '<div class="hoje-header"><span class="hoje-dot"></span>Prazos de Hoje &middot; ' + hoje.strftime("%d/%m/%Y") + '</div>'
            '<div class="hoje-sem">Nenhum prazo para hoje.</div>'
            '</div>'
        )
    # --- Visao sintetica da semana por dia (Seg a Dom) com lista + responsavel ---
    dias_semana_nomes = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]
    colunas_semana = []
    for i in range(7):
        dia_atual = semana_inicio + timedelta(days=i)
        prazos_dia = [r for r in registros if data_do_registro(r) == dia_atual]
        prazos_dia.sort(key=lambda x: (campo(x, "encarregado.nome") or "zzz").lower())
        eh_o_dia = (dia_atual == hoje)
        itens = []
        for r in prazos_dia:
            enc = campo(r, "encarregado.nome") or "N/A"
            pasta = campo(r, "processo.pasta") or "N/A"
            assunto_s = campo(r, "assunto") or campo(r, "tipoAtividade") or "N/A"
            area_s = categoria_area(campo(r, "processo.natureza"))
            itens.append(
                '<div class="sem-item sem-item-' + area_s + '">'
                '<div class="sem-resp">' + html.escape(enc) + '</div>'
                '<div class="sem-proc">' + html.escape(pasta) + '</div>'
                '<div class="sem-assunto">' + html.escape(assunto_s) + '</div>'
                '</div>'
            )
        corpo_col = "".join(itens) if itens else '<div class="sem-vazio">-</div>'
        classe_col = "sem-col sem-col-hoje" if eh_o_dia else "sem-col"
        _cod_dia = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"][i]
        colunas_semana.append(
            '<div class="' + classe_col + ' sem-col-clicavel" data-dia="' + _cod_dia + '" onclick="filtrarDia(\'' + _cod_dia + '\', this)" title="Clique para ver os prazos deste dia na tabela">'
            '<div class="sem-col-head">' + dias_semana_nomes[i] + '<span class="sem-data">' + dia_atual.strftime("%d/%m") + '</span>'
            '<span class="sem-badge">' + str(len(prazos_dia)) + '</span></div>'
            '<div class="sem-col-body">' + corpo_col + '</div>'
            '</div>'
        )
    bloco_semana = (
        '<div class="sem-card">'
        '<div class="sem-header"><span class="sem-dot"></span>Prazos da Semana por Dia &middot; '
        + semana_inicio.strftime("%d/%m") + ' a ' + semana_fim.strftime("%d/%m") + '</div>'
        '<div class="sem-grid">' + "".join(colunas_semana) + '</div>'
        '</div>'
    )
    ranking_dia = gerar_ranking_barras(enc_dia, "bar-azul", truncar=True, clicavel=True, grupo="encarregado")
    ranking_semana = gerar_ranking_barras(enc_semana, "bar-azul", truncar=True, clicavel=True, grupo="encarregado")
    ranking_prox_semana = gerar_ranking_barras(enc_prox_semana, "bar-azul", truncar=True, clicavel=True, grupo="encarregado")
    ranking_mes = gerar_ranking_barras(enc_mes, "bar-azul", truncar=True, clicavel=True, grupo="encarregado")
    ranking_todos = gerar_ranking_barras(encarregado_counter_total, "bar-azul", truncar=True, clicavel=True, grupo="encarregado")

    ranking_assuntos_dia = gerar_ranking_barras(assunto_dia, "bar-vermelho", limite=8, clicavel=True, grupo="assunto")
    ranking_assuntos_semana = gerar_ranking_barras(assunto_semana, "bar-vermelho", limite=8, clicavel=True, grupo="assunto")
    ranking_assuntos_prox_semana = gerar_ranking_barras(assunto_prox_semana, "bar-vermelho", limite=8, clicavel=True, grupo="assunto")
    ranking_assuntos_mes = gerar_ranking_barras(assunto_mes, "bar-vermelho", limite=8, clicavel=True, grupo="assunto")
    ranking_assuntos_todos = gerar_ranking_barras(assunto_counter, "bar-vermelho", limite=8, clicavel=True, grupo="assunto")

    ranking_tipo_dia = gerar_ranking_barras(tipo_dia, "bar-dourado", limite=8, clicavel=True, grupo="tipo")
    ranking_tipo_semana = gerar_ranking_barras(tipo_semana, "bar-dourado", limite=8, clicavel=True, grupo="tipo")
    ranking_tipo_prox_semana = gerar_ranking_barras(tipo_prox_semana, "bar-dourado", limite=8, clicavel=True, grupo="tipo")
    ranking_tipo_mes = gerar_ranking_barras(tipo_mes, "bar-dourado", limite=8, clicavel=True, grupo="tipo")
    ranking_tipo_todos = gerar_ranking_barras(tipo_atividade_counter, "bar-dourado", limite=8, clicavel=True, grupo="tipo")

    data_hoje = "Atualizado em " + datetime.now().strftime("%d/%m/%Y às %H:%M")

    css = (
        "*{margin:0;padding:0;box-sizing:border-box;}"
        "body{background:#f3f1ea;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#233240;min-height:100vh;}"
        ".header{background:#e9e5d9;border-bottom:3px solid #233240;padding:20px 32px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;}"
        ".header-left{display:flex;align-items:center;gap:14px;}"
        ".logo-texto{display:flex;flex-direction:column;line-height:1.05;}"
        ".logo-nome{font-size:20px;font-weight:900;color:#233240;letter-spacing:0.5px;}"
        ".logo-sub{font-size:9px;font-weight:700;color:#6b7280;letter-spacing:3px;}"
        ".logo-mark{display:flex;align-items:stretch;height:34px;border-radius:2px;overflow:hidden;}"
        ".logo-navy{width:28px;background:#233240;}"
        ".logo-flag{position:relative;width:56px;background:#9c3b3b;overflow:hidden;}"
        ".logo-arrow-white{position:absolute;left:0;top:0;width:0;height:0;border-top:17px solid transparent;border-bottom:17px solid transparent;border-left:24px solid #ffffff;}"
        ".logo-arrow-gold{position:absolute;left:3px;top:0;width:0;height:0;border-top:17px solid transparent;border-bottom:17px solid transparent;border-left:20px solid #b8860b;}"
        ".header-center{text-align:center;flex:1;min-width:280px;}"
        ".header-center .kicker{font-size:11px;letter-spacing:3px;color:#8a8471;font-weight:700;margin-bottom:4px;}"
        ".header-center h1{font-size:24px;font-weight:900;color:#233240;letter-spacing:1px;}"
        ".header-center .sub{font-size:13px;color:#6b7280;margin-top:2px;}"
        ".header-right{display:flex;gap:24px;text-align:center;}"
        ".header-right .num{font-size:24px;font-weight:900;color:#233240;}"
        ".header-right .lbl{font-size:10px;color:#8a8471;font-weight:700;letter-spacing:.5px;}"
        ".header-right .data{font-size:11px;color:#9ca3af;margin-top:6px;}"
        ".container{max-width:1500px;margin:0 auto;padding:24px 32px 60px;}"
        ".area-pills-row{display:flex;gap:12px;margin-bottom:18px;flex-wrap:wrap;}"
        ".pill-area{background:#fff;color:#374151;border:2px solid #e2ddc9;padding:12px 22px;border-radius:12px;font-weight:800;font-size:14px;cursor:pointer;transition:.15s;display:flex;align-items:center;gap:10px;}"
        ".pill-area:hover{border-color:#233240;}"
        ".pill-area.active{background:#233240;color:#fff;border-color:#233240;}"
        ".pill-count{background:rgba(0,0,0,0.08);padding:2px 10px;border-radius:999px;font-size:12px;font-weight:800;}"
        ".pill-area.active .pill-count{background:rgba(255,255,255,0.2);}"
        ".filtros-bar{display:flex;align-items:center;gap:20px;flex-wrap:wrap;background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:14px 20px;margin-bottom:22px;}"
        ".filtro-grupo{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}"
        ".filtro-titulo{font-size:11px;font-weight:800;color:#8a8471;letter-spacing:1px;text-transform:uppercase;margin-right:2px;}"
        ".pill{background:#fff;color:#4b5563;border:1.5px solid #e2ddc9;padding:8px 16px;border-radius:999px;font-weight:700;font-size:12.5px;cursor:pointer;transition:.15s;}"
        ".pill:hover{border-color:#233240;}"
        ".pill.active{background:#233240;color:#fff;border-color:#233240;}"
        ".pill.active[data-status='finalizado']{background:#3f6b4f;border-color:#3f6b4f;}"
        ".pill.active[data-status='andamento']{background:#b8860b;border-color:#b8860b;}"
        ".pill.active[data-status='naoiniciado']{background:#9c3b3b;border-color:#9c3b3b;}"
        ".select-encarregado{padding:8px 14px;border:1.5px solid #e2ddc9;border-radius:8px;font-size:12.5px;color:#374151;background:#faf9f5;min-width:220px;}"
        ".select-encarregado:focus{outline:none;border-color:#233240;}"
        ".busca-inline{flex:1;min-width:200px;}"
        ".busca-inline input{width:100%;padding:9px 14px;border:1.5px solid #e2ddc9;border-radius:8px;font-size:13px;background:#faf9f5;}"
        ".busca-inline input:focus{outline:none;border-color:#233240;background:#fff;}"
        ".stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:22px;}"
        "@media (max-width:900px){.stats-grid{grid-template-columns:repeat(2,1fr);}}"
        ".stat-card{background:#fff;border:1px solid #e2ddc9;border-left:6px solid #233240;border-radius:10px;padding:18px 20px;}"
        ".stat-card .lbl{font-size:10.5px;color:#8a8471;font-weight:800;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;}"
        ".stat-card .num{font-size:30px;font-weight:900;color:#233240;margin-bottom:4px;}"
        ".stat-card .desc{font-size:11.5px;color:#9ca3af;}"
        ".stat-total{border-left-color:#233240;} .stat-total .num{color:#233240;}"
        ".stat-naoiniciado{border-left-color:#9c3b3b;} .stat-naoiniciado .num{color:#9c3b3b;}"
        ".stat-andamento{border-left-color:#b8860b;} .stat-andamento .num{color:#8a660a;}"
        ".stat-finalizado{border-left-color:#3f6b4f;} .stat-finalizado .num{color:#3f6b4f;}"
        ".periodo-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:14px;margin-bottom:22px;}"
        "@media (max-width:1450px){.periodo-grid{grid-template-columns:repeat(4,1fr);}}"
        "@media (max-width:1250px){.periodo-grid{grid-template-columns:repeat(3,1fr);}}"
        "@media (max-width:1000px){.periodo-grid{grid-template-columns:repeat(2,1fr);}}"
        ".periodo-acomp{cursor:pointer;transition:.15s;border:1px solid #cfd8ca;background:#f7f9f6;}"
        ".periodo-acomp:hover{box-shadow:0 4px 12px rgba(107,127,102,.25);transform:translateY(-2px);border-color:#6b7f66;}"
        ".periodo-acomp .pnum{color:#6b7f66;}"
        ".ac-painel{display:none;background:#fff;border:1px solid #e2ddc9;border-left:6px solid #6b7f66;border-radius:12px;padding:20px 22px;margin-bottom:22px;}"
        ".ac-painel.ac-aberto{display:block;}"
        ".ac-painel-head{display:flex;align-items:center;gap:10px;font-size:14px;font-weight:900;color:#4f5f4b;text-transform:uppercase;letter-spacing:.3px;margin-bottom:16px;}"
        ".ac-count{background:#6b7f66;color:#fff;font-size:12px;font-weight:800;padding:2px 11px;border-radius:999px;}"
        ".ac-fechar{margin-left:auto;background:#f3f1ea;border:1.5px solid #e2ddc9;color:#6b7280;padding:6px 14px;border-radius:8px;font-size:11.5px;font-weight:700;cursor:pointer;}"
        ".ac-lista{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:11px;max-height:460px;overflow-y:auto;}"
        ".ac-item{background:#faf9f5;border:1px solid #eee6d6;border-left:3px solid #6b7f66;border-radius:9px;padding:10px 12px;}"
        ".ac-item-finalizado{border-left-color:#3f6b4f;}"
        ".ac-item-andamento{border-left-color:#b8860b;}"
        ".ac-item-naoiniciado{border-left-color:#9c3b3b;}"
        ".ac-topo{display:flex;align-items:center;justify-content:space-between;gap:8px;}"
        ".ac-resp{font-size:12px;font-weight:800;color:#233240;}"
        ".ac-data{font-size:10.5px;font-weight:700;color:#8a8471;white-space:nowrap;}"
        ".ac-proc{font-size:10.5px;color:#6b7280;font-weight:600;margin-top:3px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;}"
        ".ac-assunto{font-size:11px;color:#8a8471;margin-top:3px;}"
        ".periodo-fatal{cursor:pointer;transition:.15s;border:1px solid #e0cccc;background:#fdf8f8;}"
        ".periodo-fatal:hover{box-shadow:0 4px 12px rgba(156,59,59,.2);transform:translateY(-2px);border-color:#9c3b3b;}"
        ".periodo-fatal .pnum{color:#9c3b3b;}"
        ".fa-painel{display:none;background:#fff;border:1px solid #e2ddc9;border-left:6px solid #9c3b3b;border-radius:12px;padding:20px 22px;margin-bottom:22px;}"
        ".fa-painel.ac-aberto{display:block;}"
        ".fa-painel-head{display:flex;align-items:center;gap:10px;font-size:14px;font-weight:900;color:#8a2e2e;text-transform:uppercase;letter-spacing:.3px;margin-bottom:16px;flex-wrap:wrap;}"
        ".fa-count{background:#9c3b3b;color:#fff;font-size:12px;font-weight:800;padding:2px 11px;border-radius:999px;}"
        ".fa-dica{font-size:10.5px;font-weight:600;color:#9ca3af;text-transform:none;letter-spacing:0;}"
        ".fa-lista{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:11px;max-height:480px;overflow-y:auto;}"
        ".fa-item{background:#faf9f5;border:1px solid #eee6d6;border-left:3px solid #9ca3af;border-radius:9px;padding:10px 12px;cursor:pointer;transition:.15s;}"
        ".fa-item:hover{background:#fff;box-shadow:0 3px 10px rgba(0,0,0,.1);transform:translateY(-2px);}"
        ".fa-item-vencido{border-left-color:#9c3b3b;background:#fdf1f1;}"
        ".fa-item-hoje{border-left-color:#b8860b;background:#fdf9ee;}"
        ".fa-item-semana{border-left-color:#6b7f66;}"
        ".fa-topo{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px;}"
        ".fa-data{font-size:12.5px;font-weight:900;color:#233240;}"
        ".fa-urg{font-size:9px;font-weight:800;padding:2px 8px;border-radius:999px;text-transform:uppercase;letter-spacing:.3px;white-space:nowrap;}"
        ".fa-urg-vencido{background:#f3dede;color:#8a2e2e;}"
        ".fa-urg-hoje{background:#f3e6c4;color:#7a5c08;}"
        ".fa-urg-semana{background:#e2eadf;color:#3f6b4f;}"
        ".fa-resp{font-size:11.5px;font-weight:700;color:#374151;}"
        ".fa-proc{font-size:10.5px;color:#6b7280;font-weight:600;margin-top:3px;display:flex;align-items:center;gap:6px;flex-wrap:wrap;}"
        ".fa-assunto{font-size:11px;color:#8a8471;margin-top:3px;}"
        ".periodo-fatal-hoje{cursor:pointer;transition:.15s;border:2px solid #9c3b3b;background:#fdf1f1;}"
        ".periodo-fatal-hoje:hover{box-shadow:0 4px 14px rgba(156,59,59,.3);transform:translateY(-2px);}"
        ".periodo-fatal-hoje .pnum{color:#8a2e2e;}"
        ".periodo-fatal-hoje .plbl{color:#8a2e2e;}"
        ".fa-grupo{margin-bottom:20px;border-radius:10px;transition:background .4s;}"
        ".fa-grupo:last-child{margin-bottom:0;}"
        ".fa-grupo-flash{background:#fff8e1;box-shadow:0 0 0 6px #fff8e1;}"
        ".fa-grupo-head{font-size:12px;font-weight:900;letter-spacing:.5px;text-transform:uppercase;padding:7px 13px;border-radius:8px;margin-bottom:11px;display:inline-flex;align-items:center;gap:8px;}"
        ".fa-grupo-count{background:rgba(255,255,255,.4);padding:1px 9px;border-radius:999px;font-size:11px;}"
        ".fa-grupo-hoje{background:#f3e6c4;color:#7a5c08;}"
        ".fa-grupo-vencido{background:#f3dede;color:#8a2e2e;}"
        ".fa-grupo-futuro{background:#e5e7eb;color:#4b5563;}"
        ".fa-grupo-head{cursor:pointer;user-select:none;transition:.15s;}"
        ".fa-grupo-head:hover{filter:brightness(.95);}"
        ".fa-seta{font-size:11px;display:inline-block;width:11px;}"
        ".fa-grupo-fechado .fa-lista{display:none;}"
        ".fa-status{font-size:8.5px;font-weight:800;padding:2px 7px;border-radius:999px;text-transform:uppercase;letter-spacing:.3px;white-space:nowrap;}"
        ".fa-status-naoiniciado{background:#f3dede;color:#8a2e2e;}"
        ".fa-status-andamento{background:#f3e6c4;color:#7a5c08;}"
        ".fa-status-finalizado{background:#dcece1;color:#2f5a3d;}"
        ".fa-status-outro{background:#e5e7eb;color:#4b5563;}"
        ".periodo-card{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:22px;text-align:center;}"
        ".periodo-card .plbl{font-size:11px;color:#8a8471;font-weight:800;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;}"
        ".periodo-card .pnum{font-size:40px;font-weight:900;color:#233240;}"
        ".periodo-card .pdesc{font-size:12px;color:#9ca3af;margin-top:6px;}"
        ".periodo-hoje .pnum{color:#9c3b3b;} .periodo-semana .pnum{color:#b8860b;} .periodo-proxsemana .pnum{color:#6b7f66;} .periodo-mes .pnum{color:#233240;}"
        ".paineis-grid{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:16px;margin-bottom:24px;}"
        "@media (max-width:1350px){.paineis-grid{grid-template-columns:1fr 1fr;}}"
        "@media (max-width:1150px){.paineis-grid{grid-template-columns:1fr;}}"
        ".painel{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:20px;}"
        ".painel-header{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:18px;flex-wrap:wrap;}"
        ".painel-header-left{display:flex;align-items:center;gap:8px;}"
        ".painel-bar{width:4px;height:15px;background:#9c3b3b;border-radius:2px;}"
        ".painel h3{font-size:13px;color:#233240;font-weight:900;letter-spacing:.4px;text-transform:uppercase;}"
        ".mini-pills{display:flex;gap:6px;}"
        ".mini-pill{background:#f3f1ea;color:#6b7280;border:1px solid #e2ddc9;padding:5px 12px;border-radius:999px;font-size:11px;font-weight:700;cursor:pointer;transition:.15s;}"
        ".mini-pill:hover{border-color:#233240;}"
        ".mini-pill.active{background:#233240;color:#fff;border-color:#233240;}"
        ".rank-panel{display:none;}"
        ".rank-panel.active{display:block;}"
        ".rank-row{display:grid;grid-template-columns:170px 1fr auto;align-items:center;gap:10px;margin-bottom:11px;font-size:12px;}"
        ".rank-nome{color:#374151;font-weight:600;white-space:normal;word-break:break-word;line-height:1.3;}"
        ".rank-bar-bg{background:#f3f1ea;border-radius:6px;height:11px;overflow:hidden;align-self:center;}"
        ".rank-bar{height:100%;border-radius:6px;}"
        ".bar-azul{background:linear-gradient(90deg,#233240,#4a6c86);}"
        ".bar-vermelho{background:linear-gradient(90deg,#9c3b3b,#c17b7b);}"
        ".bar-dourado{background:linear-gradient(90deg,#8a660a,#c9a545);}"
        ".rank-qtd{color:#233240;font-weight:800;text-align:right;min-width:20px;align-self:center;}"
        ".sem-dados{font-size:12px;color:#9ca3af;}"
        ".status-select{padding:5px 10px;border-radius:999px;font-size:10.5px;font-weight:800;border:1.5px solid transparent;cursor:pointer;appearance:auto;}"
        ".status-naoiniciado{background:#f3dede;color:#8a2e2e;} .status-andamento{background:#f3e6c4;color:#7a5c08;} .status-finalizado{background:#dcece1;color:#2f5a3d;} .status-outro{background:#e5e7eb;color:#4b5563;}"
        ".status-select.status-alterado{border-color:#b8860b;box-shadow:0 0 0 2px rgba(184,134,11,0.25);}"
        ".btn-limpar{background:#f3f1ea;color:#9ca3af;border:1.5px solid #e2ddc9;padding:9px 16px;border-radius:8px;font-size:12.5px;font-weight:700;cursor:not-allowed;transition:.15s;}"
        ".btn-limpar.tem-alteracoes{background:#9c3b3b;color:#fff;border-color:#9c3b3b;cursor:pointer;}"
        ".btn-limpar.tem-alteracoes:hover{background:#7f2f2f;}"
        ".tabela-card{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:22px;}"
        ".tabela-card h3{font-size:13px;color:#233240;font-weight:900;letter-spacing:.4px;text-transform:uppercase;margin-bottom:14px;}"
        ".contagem{font-size:12px;color:#8a8471;font-weight:700;margin-bottom:12px;}"
        "table{width:100%;border-collapse:collapse;}"
        "th{background:#faf9f5;padding:11px;text-align:left;font-size:10px;font-weight:800;color:#8a8471;text-transform:uppercase;letter-spacing:.4px;border-bottom:2px solid #e2ddc9;white-space:nowrap;}"
        "td{padding:11px;border-bottom:1px solid #f3f1ea;font-size:12.5px;color:#374151;}"
        "tr:hover{background:#faf9f5;}"
        ".pasta-cell{color:#233240;font-weight:800;white-space:nowrap;}"
        ".badge{display:inline-block;padding:4px 12px;border-radius:999px;font-size:10px;font-weight:800;white-space:nowrap;}"
        ".badge-naoiniciado{background:#f3dede;color:#8a2e2e;} .badge-andamento{background:#f3e6c4;color:#7a5c08;} .badge-finalizado{background:#dcece1;color:#2f5a3d;} .badge-outro{background:#e5e7eb;color:#4b5563;}"
        ".oculto{display:none!important;}"
        ".oculto-busca{display:none;}"
        ".periodo-pill{background:#f3f1ea;color:#4b5563;border:1.5px solid #e2ddc9;padding:8px 14px;border-radius:999px;font-weight:700;font-size:12.5px;cursor:pointer;transition:.15s;}"
        ".periodo-pill:hover{border-color:#233240;}"
        ".periodo-pill.active{background:#6b7f66;color:#fff;border-color:#6b7f66;}"
        ".table-wrapper{overflow:auto;max-height:620px;border:1px solid #e2ddc9;border-radius:10px;}"
        "th{position:sticky;top:0;z-index:2;}"
        ".pasta-cell{display:flex;align-items:center;gap:8px;}"
        ".btn-copiar{background:transparent;border:none;cursor:pointer;font-size:13px;padding:3px 5px;border-radius:5px;opacity:0.55;transition:.15s;}"
        ".btn-copiar:hover{opacity:1;background:#f3f1ea;}"
        ".btn-copiar.copiado{opacity:1;color:#16a34a;}"
        ".rank-row-clicavel{cursor:pointer;padding:4px;margin:-4px -4px 7px -4px;border-radius:8px;transition:.15s;}"
        ".rank-row-clicavel:hover{background:#f3f1ea;}"
        # --- Destaque de prazos do dia e da semana ---
        "tr.linha-hoje{background:#fdecec!important;box-shadow:inset 4px 0 0 #9c3b3b;}"
        "tr.linha-hoje:hover{background:#fbe0e0!important;}"
        "tr.linha-semana{background:#fbf4e2!important;box-shadow:inset 4px 0 0 #b8860b;}"
        "tr.linha-semana:hover{background:#f7edd2!important;}"
        ".selo-hoje{display:inline-block;background:#9c3b3b;color:#fff;font-size:9px;font-weight:800;letter-spacing:.5px;padding:2px 7px;border-radius:999px;margin-right:6px;vertical-align:middle;}"
        "td.prazo-destaque{font-weight:800;color:#9c3b3b;}"
        "td.enc-destaque{font-weight:800;color:#233240;}"
        # --- Painel "Prazos de Hoje" com responsavel ---
        ".hoje-card{background:#fff;border:1px solid #e2ddc9;border-left:6px solid #9c3b3b;border-radius:12px;padding:20px 22px;margin-bottom:22px;}"
        ".sem-card{background:#fff;border:1px solid #e2ddc9;border-left:6px solid #233240;border-radius:12px;padding:20px 22px;margin-bottom:22px;}"
        ".sem-header{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:900;color:#233240;letter-spacing:.3px;text-transform:uppercase;margin-bottom:16px;}"
        ".sem-dot{width:10px;height:10px;border-radius:50%;background:#233240;}"
        ".sem-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:10px;}"
        "@media (max-width:1100px){.sem-grid{grid-template-columns:repeat(3,1fr);}}"
        "@media (max-width:640px){.sem-grid{grid-template-columns:repeat(2,1fr);}}"
        ".sem-col{background:#faf9f5;border:1px solid #eee6d6;border-radius:10px;overflow:hidden;display:flex;flex-direction:column;}"
        ".sem-col-hoje{border:2px solid #9c3b3b;box-shadow:0 0 0 3px rgba(156,59,59,.1);}"
        ".sem-col-head{background:#f0ece0;padding:9px 10px;font-size:11.5px;font-weight:800;color:#233240;text-transform:uppercase;letter-spacing:.4px;display:flex;align-items:center;gap:6px;}"
        ".sem-col-hoje .sem-col-head{background:#9c3b3b;color:#fff;}"
        ".sem-data{font-size:10px;font-weight:700;opacity:.7;}"
        ".sem-badge{margin-left:auto;background:#233240;color:#fff;font-size:11px;font-weight:800;padding:1px 9px;border-radius:999px;}"
        ".sem-col-hoje .sem-badge{background:#fff;color:#9c3b3b;}"
        ".sem-col-body{padding:8px;display:flex;flex-direction:column;gap:7px;max-height:340px;overflow-y:auto;}"
        ".sem-item{background:#fff;border:1px solid #eee6d6;border-left:3px solid #b8860b;border-radius:7px;padding:7px 9px;}"
        ".sem-item-trabalhista{border-left-color:#7a5c08;}"
        ".sem-item-civel{border-left-color:#2c4a63;}"
        ".sem-resp{font-size:11.5px;font-weight:800;color:#233240;line-height:1.25;}"
        ".sem-proc{font-size:10.5px;color:#6b7280;font-weight:600;margin-top:2px;word-break:break-all;}"
        ".sem-assunto{font-size:10.5px;color:#8a8471;margin-top:2px;}"
        ".sem-vazio{font-size:13px;color:#c4bda8;text-align:center;padding:14px 0;}"
        ".sem-col-clicavel{cursor:pointer;transition:.15s;}"
        ".sem-col-clicavel:hover{border-color:#233240;box-shadow:0 2px 8px rgba(35,50,64,.12);transform:translateY(-2px);}"
        ".sem-col-sel{border:2px solid #233240!important;box-shadow:0 0 0 3px rgba(35,50,64,.15)!important;}"
        "#btnAcompanhar.active{background:#6b7f66;color:#fff;border-color:#6b7f66;}"
        ".hoje-header{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:900;color:#9c3b3b;letter-spacing:.3px;text-transform:uppercase;margin-bottom:16px;}"
        ".hoje-dot{width:10px;height:10px;border-radius:50%;background:#9c3b3b;box-shadow:0 0 0 4px rgba(156,59,59,.15);}"
        ".hoje-count{background:#9c3b3b;color:#fff;font-size:12px;font-weight:800;padding:2px 11px;border-radius:999px;}"
        ".hoje-lista{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;}"
        ".hoje-item{display:flex;flex-direction:column;gap:5px;background:#faf9f5;border:1px solid #eee6d6;border-radius:10px;padding:12px 14px;}"
        ".hoje-resp{font-size:13px;font-weight:800;color:#233240;}"
        ".hoje-info{font-size:11.5px;color:#6b7280;display:flex;align-items:center;gap:8px;flex-wrap:wrap;}"
        ".hoje-pasta{font-weight:700;color:#233240;}"
        ".hoje-assunto{width:100%;font-size:11.5px;color:#8a8471;margin-top:2px;}"
        ".tag-area{font-size:9.5px;font-weight:800;padding:2px 9px;border-radius:999px;text-transform:uppercase;letter-spacing:.4px;}"
        ".tag-civel{background:#dde7ef;color:#2c4a63;}"
        ".tag-trabalhista{background:#f1e2c4;color:#7a5c08;}"
        ".hoje-sem{font-size:13px;color:#9ca3af;}"
        ".hoje-vazio{border-left-color:#cbd5c0;}"
        ".hoje-vazio .hoje-header{color:#8a8471;} .hoje-vazio .hoje-dot{background:#b7c2ab;box-shadow:none;}"
        ".hoje-grupo{margin-bottom:16px;}"
        ".hoje-grupo:last-child{margin-bottom:0;}"
        ".hoje-grupo-head{font-size:12px;font-weight:900;letter-spacing:.5px;text-transform:uppercase;padding:7px 12px;border-radius:8px;margin-bottom:10px;display:inline-flex;align-items:center;gap:8px;}"
        ".hoje-grupo-count{background:rgba(255,255,255,.35);padding:1px 9px;border-radius:999px;font-size:11px;}"
        ".hoje-grupo-naoiniciado{background:#f3dede;color:#8a2e2e;}"
        ".hoje-grupo-andamento{background:#f3e6c4;color:#7a5c08;}"
        ".hoje-grupo-finalizado{background:#dcece1;color:#2f5a3d;}"
        ".hoje-grupo-outro{background:#e5e7eb;color:#4b5563;}"
        ".hoje-topo{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;}"
        ".hoje-status{font-size:9px;font-weight:800;padding:2px 8px;border-radius:999px;text-transform:uppercase;letter-spacing:.3px;white-space:nowrap;flex-shrink:0;}"
        ".hoje-status-naoiniciado{background:#f3dede;color:#8a2e2e;}"
        ".hoje-status-andamento{background:#f3e6c4;color:#7a5c08;}"
        ".hoje-status-finalizado{background:#dcece1;color:#2f5a3d;}"
        ".hoje-status-outro{background:#e5e7eb;color:#4b5563;}"
        ".hoje-item-naoiniciado{border-left:3px solid #9c3b3b;}"
        ".hoje-item-andamento{border-left:3px solid #b8860b;}"
        ".hoje-item-finalizado{border-left:3px solid #3f6b4f;}"
        ".hoje-item-outro{border-left:3px solid #9ca3af;}"
    )

    js = (
        "var statusAtivo='todos';"
        "var diaAtivo='todos';"
        "var acompanharVisivel=false;"
        "var areaAtiva='todos';"
        "var periodoAtivo='todos';"
        "function filtrarPeriodo(periodo,botao){"
        "periodoAtivo=periodo;"
        "diaAtivo='todos';document.querySelectorAll('.sem-col-clicavel').forEach(function(el){el.classList.remove('sem-col-sel');});"
        "document.querySelectorAll('.periodo-pill').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "aplicarFiltros();}"
        "function filtrarDia(dia,elemento){"
        "if(diaAtivo===dia){diaAtivo='todos';document.querySelectorAll('.sem-col-clicavel').forEach(function(el){el.classList.remove('sem-col-sel');});}"
        "else{diaAtivo=dia;document.querySelectorAll('.sem-col-clicavel').forEach(function(el){el.classList.remove('sem-col-sel');});elemento.classList.add('sem-col-sel');}"
        "periodoAtivo='todos';document.querySelectorAll('.periodo-pill').forEach(function(el){el.classList.remove('active');});var pt=document.querySelector('.periodo-pill[data-periodo=\"todos\"]');if(pt){pt.classList.add('active');}"
        "aplicarFiltros();"
        "document.querySelector('.tabela-card').scrollIntoView({behavior:'smooth',block:'start'});}"
        "function toggleAcompanhar(botao){"
        "acompanharVisivel=!acompanharVisivel;"
        "if(acompanharVisivel){botao.classList.add('active');botao.textContent='Acompanhar: exibindo';}"
        "else{botao.classList.remove('active');botao.textContent='Acompanhar: ocultos';}"
        "aplicarFiltros();}"
        "function toggleListaAcomp(){"
        "var el=document.getElementById('acPainel');"
        "if(!el)return;"
        "el.classList.toggle('ac-aberto');"
        "if(el.classList.contains('ac-aberto')){el.scrollIntoView({behavior:'smooth',block:'nearest'});}}"
        "function toggleGrupoFatal(id){"
        "var g=document.getElementById(id);if(!g)return;"
        "g.classList.toggle('fa-grupo-fechado');"
        "var st=g.querySelector('.fa-seta');"
        "if(st)st.innerHTML=g.classList.contains('fa-grupo-fechado')?'&#9656;':'&#9662;';}"
        "function abrirFataisHoje(){"
        "var el=document.getElementById('faPainel');"
        "if(!el)return;"
        "el.classList.add('ac-aberto');"
        "var g=document.getElementById('faGrupoHoje');"
        "if(g){g.classList.remove('fa-grupo-fechado');"
        "var st=g.querySelector('.fa-seta');if(st)st.innerHTML='&#9662;';"
        "g.scrollIntoView({behavior:'smooth',block:'center'});g.classList.add('fa-grupo-flash');"
        "setTimeout(function(){g.classList.remove('fa-grupo-flash');},1600);}"
        "else{el.scrollIntoView({behavior:'smooth',block:'nearest'});}}"
        "function toggleListaFatal(){"
        "var el=document.getElementById('faPainel');"
        "if(!el)return;"
        "el.classList.toggle('ac-aberto');"
        "if(el.classList.contains('ac-aberto')){el.scrollIntoView({behavior:'smooth',block:'nearest'});}}"
        "function irParaProcesso(pasta){"
        "var pn=document.getElementById('faPainel');if(pn)pn.classList.remove('ac-aberto');"
        "var pa=document.getElementById('acPainel');if(pa)pa.classList.remove('ac-aberto');"
        "statusAtivo='todos';areaAtiva='todos';periodoAtivo='todos';diaAtivo='todos';"
        "acompanharVisivel=true;"
        "var ba=document.getElementById('btnAcompanhar');if(ba){ba.classList.add('active');ba.textContent='Acompanhar: exibindo';}"
        "document.querySelectorAll('.pill[data-status]').forEach(function(el){el.classList.remove('active');});"
        "var ps=document.querySelector('.pill[data-status=\"todos\"]');if(ps)ps.classList.add('active');"
        "document.querySelectorAll('.pill-area').forEach(function(el){el.classList.remove('active');});"
        "var pare=document.querySelector('.pill-area');if(pare)pare.classList.add('active');"
        "document.querySelectorAll('.periodo-pill').forEach(function(el){el.classList.remove('active');});"
        "var pp=document.querySelector('.periodo-pill[data-periodo=\"todos\"]');if(pp)pp.classList.add('active');"
        "document.querySelectorAll('.sem-col-clicavel').forEach(function(el){el.classList.remove('sem-col-sel');});"
        "var sel=document.getElementById('encarregadoSelect');if(sel)sel.value='';"
        "document.getElementById('busca').value=pasta;"
        "aplicarFiltros();"
        "document.querySelector('.tabela-card').scrollIntoView({behavior:'smooth',block:'start'});}"
        "function filtrarStatus(status,botao){"
        "statusAtivo=status;"
        "document.querySelectorAll('.pill[data-status]').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "aplicarFiltros();}"
        "function filtrarArea(area,botao){"
        "areaAtiva=area;"
        "document.querySelectorAll('.pill-area').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "aplicarFiltros();}"
        "function mostrarRanking(grupo,periodo,botao){"
        "var painel=botao.closest('.painel');"
        "painel.querySelectorAll('.mini-pill').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "painel.querySelectorAll('.rank-panel').forEach(function(el){el.classList.remove('active');});"
        "document.getElementById('rank-'+grupo+'-'+periodo).classList.add('active');}"
        "function aplicarFiltros(){"
        "var termo=document.getElementById('busca').value.toLowerCase();"
        "var encarregadoSel=document.getElementById('encarregadoSelect').value;"
        "var visiveis=0;"
        "var cNI=0,cAND=0,cFIN=0,cDia=0,cSem=0,cProx=0,cMes=0,cAcomp=0;"
        "document.querySelectorAll('#tabelaBody tr').forEach(function(linha){"
        "var texto=linha.textContent.toLowerCase();"
        "var statusLinha=linha.getAttribute('data-status');"
        "var areaLinha=linha.getAttribute('data-area');"
        "var encarregadoLinha=linha.getAttribute('data-encarregado');"
        "var periodosLinha=(linha.getAttribute('data-periodos')||'').split(' ');"
        "var passaTexto=texto.includes(termo);"
        "var passaStatus=(statusAtivo==='todos')||(statusLinha===statusAtivo);"
        "var passaArea=(areaAtiva==='todos')||(areaLinha===areaAtiva);"
        "var passaEncarregado=(encarregadoSel==='')||(encarregadoLinha===encarregadoSel);"
        "var passaPeriodo=(periodoAtivo==='todos')||(periodosLinha.indexOf(periodoAtivo)!==-1);"
        "var diaLinha=linha.getAttribute('data-diasemana')||'';"
        "var passaDia=(diaAtivo==='todos')||(diaLinha===diaAtivo);"
        "var acompLinha=linha.getAttribute('data-acompanhar')||'nao';"
        "var passaAcomp=acompanharVisivel||(acompLinha!=='sim');"
        "if(passaTexto&&passaStatus&&passaArea&&passaEncarregado&&passaPeriodo&&passaDia&&acompLinha==='sim')cAcomp++;"
        "var visivel=passaTexto&&passaStatus&&passaArea&&passaEncarregado&&passaPeriodo&&passaDia&&passaAcomp;"
        "linha.classList.toggle('oculto',!visivel);"
        "if(visivel){visiveis++;"
        "if(statusLinha==='naoiniciado')cNI++;else if(statusLinha==='andamento')cAND++;else if(statusLinha==='finalizado')cFIN++;"
        "if(periodosLinha.indexOf('dia')!==-1)cDia++;"
        "if(periodosLinha.indexOf('semana')!==-1)cSem++;"
        "if(periodosLinha.indexOf('proxsemana')!==-1)cProx++;"
        "if(periodosLinha.indexOf('mes')!==-1)cMes++;}"
        "});"
        "document.getElementById('contagemVisivel').textContent=visiveis+' registro(s) exibido(s)';"
        "function _set(id,v){var el=document.getElementById(id);if(el)el.textContent=v;}"
        "_set('statTotal',visiveis);_set('statNaoIniciado',cNI);_set('statAndamento',cAND);_set('statFinalizado',cFIN);"
        "_set('perHoje',cDia);_set('perSemana',cSem);_set('perProxSemana',cProx);_set('perMes',cMes);"
        "_set('hdrTotal',visiveis);_set('hdrAndamento',cAND);_set('hdrFinalizado',cFIN);"
        "_set('statAcompanhar',cAcomp);"
        "}"
        "document.getElementById('busca').addEventListener('input',aplicarFiltros);"
        "document.getElementById('encarregadoSelect').addEventListener('change',aplicarFiltros);"
        "aplicarFiltros();"
        "function mudarStatus(select){"
        "var novoStatus=select.value;"
        "var linha=select.closest('tr');"
        "linha.setAttribute('data-status',novoStatus);"
        "select.classList.remove('status-naoiniciado','status-andamento','status-finalizado','status-outro');"
        "select.classList.add('status-'+novoStatus);"
        "if(novoStatus!==select.getAttribute('data-original')){"
        "select.classList.add('status-alterado');"
        "}else{"
        "select.classList.remove('status-alterado');"
        "}"
        "atualizarContadorAlteracoes();"
        "aplicarFiltros();}"
        "function limparAlteracoes(){"
        "var alterados=0;"
        "document.querySelectorAll('.status-select').forEach(function(select){"
        "var original=select.getAttribute('data-original');"
        "select.value=original;"
        "select.classList.remove('status-naoiniciado','status-andamento','status-finalizado','status-outro','status-alterado');"
        "select.classList.add('status-'+original);"
        "select.closest('tr').setAttribute('data-status',original);"
        "});"
        "atualizarContadorAlteracoes();"
        "aplicarFiltros();}"
        "function atualizarContadorAlteracoes(){"
        "var qtd=document.querySelectorAll('.status-select.status-alterado').length;"
        "var botao=document.getElementById('btnLimparAlteracoes');"
        "if(qtd>0){"
        "botao.textContent='Limpar Alterações ('+qtd+')';"
        "botao.classList.add('tem-alteracoes');"
        "botao.disabled=false;"
        "}else{"
        "botao.textContent='Limpar Alterações';"
        "botao.classList.remove('tem-alteracoes');"
        "botao.disabled=true;"
        "}}"
        "function filtrarPorTermo(elemento){"
        "var termo=elemento.getAttribute('data-termo');"
        "var grupo=elemento.getAttribute('data-grupo');"
        "var painel=elemento.closest('.painel');"
        "var pillAtivo=painel.querySelector('.mini-pill.active');"
        "var periodoDoPainel=pillAtivo?pillAtivo.getAttribute('data-periodo'):'todos';"
        "statusAtivo='todos';"
        "areaAtiva='todos';"
        "periodoAtivo=periodoDoPainel;"
        "document.querySelectorAll('.pill[data-status]').forEach(function(el){el.classList.remove('active');});"
        "document.querySelector('.pill[data-status=\"todos\"]').classList.add('active');"
        "document.querySelectorAll('.pill-area').forEach(function(el){el.classList.remove('active');});"
        "document.querySelector('.pill-area').classList.add('active');"
        "document.querySelectorAll('.periodo-pill').forEach(function(el){el.classList.remove('active');});"
        "var periodoPillGlobal=document.querySelector('.periodo-pill[data-periodo=\"'+periodoDoPainel+'\"]');"
        "if(periodoPillGlobal){periodoPillGlobal.classList.add('active');}"
        "if(grupo==='encarregado'){"
        "document.getElementById('busca').value='';"
        "document.getElementById('encarregadoSelect').value=termo.toLowerCase();"
        "}else{"
        "document.getElementById('busca').value=termo;"
        "document.getElementById('encarregadoSelect').value='';"
        "}"
        "aplicarFiltros();"
        "document.querySelector('.tabela-card').scrollIntoView({behavior:'smooth',block:'start'});"
        "}"
        "function copiarPasta(botao){"
        "var pasta=botao.getAttribute('data-pasta');"
        "function marcarCopiado(){"
        "var original=botao.innerHTML;"
        "botao.innerHTML='&#10003;';"
        "botao.classList.add('copiado');"
        "setTimeout(function(){botao.innerHTML=original;botao.classList.remove('copiado');},1500);"
        "}"
        "if(navigator.clipboard&&navigator.clipboard.writeText){"
        "navigator.clipboard.writeText(pasta).then(marcarCopiado).catch(function(){copiarFallback(pasta,marcarCopiado);});"
        "}else{"
        "copiarFallback(pasta,marcarCopiado);"
        "}}"
        "function copiarFallback(texto,callback){"
        "var temp=document.createElement('textarea');"
        "temp.value=texto;"
        "temp.style.position='fixed';"
        "temp.style.opacity='0';"
        "document.body.appendChild(temp);"
        "temp.focus();"
        "temp.select();"
        "try{document.execCommand('copy');callback();}catch(e){}"
        "document.body.removeChild(temp);"
        "}"
    )

    corpo = (
        '<div class="header">'
        '<div class="header-left">'
        '<div class="logo-texto">'
        '<span class="logo-nome">PACAEMBU</span>'
        '<span class="logo-sub">CONSTRUTORA</span>'
        '</div>'
        '<div class="logo-mark">'
        '<div class="logo-navy"></div>'
        '<div class="logo-flag"><div class="logo-arrow-white"></div><div class="logo-arrow-gold"></div></div>'
        '</div>'
        '</div>'
        '<div class="header-center">'
        '<div class="kicker">JURÍDICO &middot; GESTÃO DE PRAZOS</div>'
        '<h1>PAINEL DE PRAZOS E ATIVIDADES</h1>'
        '<div class="sub">Acompanhamento de prazos do encarregado</div>'
        '</div>'
        '<div class="header-right">'
        '<div><div class="num" id="hdrTotal">' + str(total) + '</div><div class="lbl">TOTAL</div></div>'
        '<div><div class="num" id="hdrAndamento">' + str(em_andamento) + '</div><div class="lbl">EM ANDAMENTO</div></div>'
        '<div><div class="num" id="hdrFinalizado">' + str(finalizados) + '</div><div class="lbl">FINALIZADOS</div><div class="data">' + data_hoje + '</div></div>'
        '</div>'
        '</div>'
        '<div class="container">'
        '<div class="area-pills-row">'
        '<button class="pill-area active" onclick="filtrarArea(\'todos\', this)">Todos os Processos <span class="pill-count">' + str(total) + '</span></button>'
        '<button class="pill-area" onclick="filtrarArea(\'civel\', this)">Cível <span class="pill-count">' + str(total_civel) + '</span></button>'
        '<button class="pill-area" onclick="filtrarArea(\'trabalhista\', this)">Trabalhista <span class="pill-count">' + str(total_trabalhista) + '</span></button>'
        '</div>'
        '<div class="filtros-bar">'
        '<div class="filtro-grupo">'
        '<span class="filtro-titulo">Status</span>'
        '<button class="pill active" data-status="todos" onclick="filtrarStatus(\'todos\', this)">Todos</button>'
        '<button class="pill" data-status="naoiniciado" onclick="filtrarStatus(\'naoiniciado\', this)">Não iniciados</button>'
        '<button class="pill" data-status="andamento" onclick="filtrarStatus(\'andamento\', this)">Em andamento</button>'
        '<button class="pill" data-status="finalizado" onclick="filtrarStatus(\'finalizado\', this)">Finalizados</button>'
        '</div>'
        '<div class="filtro-grupo">'
        '<span class="filtro-titulo">Encarregado</span>'
        '<select id="encarregadoSelect" class="select-encarregado"><option value="">Todos</option>' + opcoes_encarregado + '</select>'
        '</div>'
        '<div class="filtro-grupo">'
        '<span class="filtro-titulo">Período</span>'
        '<button class="periodo-pill active" data-periodo="todos" onclick="filtrarPeriodo(\'todos\', this)">Todos</button>'
        '<button class="periodo-pill" data-periodo="dia" onclick="filtrarPeriodo(\'dia\', this)">Hoje</button>'
        '<button class="periodo-pill" data-periodo="semana" onclick="filtrarPeriodo(\'semana\', this)">Semana</button>'
        '<button class="periodo-pill" data-periodo="proxsemana" onclick="filtrarPeriodo(\'proxsemana\', this)">Próx. Semana</button>'
        '<button class="periodo-pill" data-periodo="mes" onclick="filtrarPeriodo(\'mes\', this)">Mês</button>'
        '</div>'
        '<div class="filtro-grupo"><span class="filtro-titulo">Acompanhar</span>'
        '<button id="btnAcompanhar" class="pill" onclick="toggleAcompanhar(this)">Acompanhar: ocultos</button></div>'
        '<div class="busca-inline"><input type="text" id="busca" placeholder="Buscar por processo, adverso, assunto..."></div>'
        '<button id="btnLimparAlteracoes" class="btn-limpar" onclick="limparAlteracoes()" disabled>Limpar Alterações</button>'
        '</div>'
        '<div class="stats-grid">'
        '<div class="stat-card stat-total"><div class="lbl">Total de Prazos</div><div class="num" id="statTotal">' + str(total) + '</div><div class="desc">Registros no periodo</div></div>'
        '<div class="stat-card stat-naoiniciado"><div class="lbl">Não Iniciados</div><div class="num" id="statNaoIniciado">' + str(nao_iniciados) + '</div><div class="desc">Aguardando início</div></div>'
        '<div class="stat-card stat-andamento"><div class="lbl">Em Andamento</div><div class="num" id="statAndamento">' + str(em_andamento) + '</div><div class="desc">Em execução ativa</div></div>'
        '<div class="stat-card stat-finalizado"><div class="lbl">Finalizados</div><div class="num" id="statFinalizado">' + str(finalizados) + '</div><div class="desc">Concluídos</div></div>'
        '</div>'
        '<div class="periodo-grid">'
        '<div class="periodo-card periodo-hoje"><div class="plbl">Prazos Hoje</div><div class="pnum" id="perHoje">' + str(qtd_dia) + '</div><div class="pdesc">' + hoje.strftime("%d/%m/%Y") + '</div></div>'
        '<div class="periodo-card periodo-semana"><div class="plbl">Prazos Esta Semana</div><div class="pnum" id="perSemana">' + str(qtd_semana) + '</div><div class="pdesc">' + semana_inicio.strftime("%d/%m") + ' a ' + semana_fim.strftime("%d/%m") + '</div></div>'
        '<div class="periodo-card periodo-proxsemana"><div class="plbl">Prazos Próxima Semana</div><div class="pnum" id="perProxSemana">' + str(qtd_prox_semana) + '</div><div class="pdesc">' + prox_semana_inicio.strftime("%d/%m") + ' a ' + prox_semana_fim.strftime("%d/%m") + '</div></div>'
        '<div class="periodo-card periodo-mes"><div class="plbl">Prazos Este Mês</div><div class="pnum" id="perMes">' + str(qtd_mes) + '</div><div class="pdesc">' + mes_inicio.strftime("%m/%Y") + '</div></div>'
        '<div class="periodo-card periodo-acomp" onclick="toggleListaAcomp()" title="Clique para ver a lista"><div class="plbl">Acompanhamentos</div><div class="pnum" id="statAcompanhar">' + str(total_acomp) + '</div><div class="pdesc">Clique para ver a lista</div></div>'
        '<div class="periodo-card periodo-fatal" onclick="toggleListaFatal()" title="Clique para ver a lista"><div class="plbl">Data Fatal</div><div class="pnum" id="statFatal">' + str(total_fatal) + '</div><div class="pdesc">Clique para ver a lista</div></div>'
        '<div class="periodo-card periodo-fatal-hoje" onclick="abrirFataisHoje()" title="Clique para ver os fatais de hoje"><div class="plbl">Fatais Hoje</div><div class="pnum" id="statFatalHoje">' + str(total_fatal_hoje) + '</div><div class="pdesc">Vencem em ' + hoje.strftime("%d/%m") + '</div></div>'
        '</div>'
        + bloco_acomp + bloco_fatal +
        '<div class="paineis-grid">'
        '<div class="painel">'
        '<div class="painel-header">'
        '<div class="painel-header-left"><div class="painel-bar"></div><h3>Prazos por Encarregado</h3></div>'
        '<div class="mini-pills">'
        '<button class="mini-pill" data-periodo="dia" onclick="mostrarRanking(\'encarregado\',\'dia\', this)">Hoje</button>'
        '<button class="mini-pill" data-periodo="semana" onclick="mostrarRanking(\'encarregado\',\'semana\', this)">Semana</button>'
        '<button class="mini-pill" data-periodo="proxsemana" onclick="mostrarRanking(\'encarregado\',\'proxsemana\', this)">Próx. Semana</button>'
        '<button class="mini-pill active" data-periodo="mes" onclick="mostrarRanking(\'encarregado\',\'mes\', this)">Mês</button>'
        '<button class="mini-pill" data-periodo="todos" onclick="mostrarRanking(\'encarregado\',\'todos\', this)">Todos</button>'
        '</div>'
        '</div>'
        '<div class="rank-panel" id="rank-encarregado-dia">' + ranking_dia + '</div>'
        '<div class="rank-panel" id="rank-encarregado-semana">' + ranking_semana + '</div>'
        '<div class="rank-panel" id="rank-encarregado-proxsemana">' + ranking_prox_semana + '</div>'
        '<div class="rank-panel active" id="rank-encarregado-mes">' + ranking_mes + '</div>'
        '<div class="rank-panel" id="rank-encarregado-todos">' + ranking_todos + '</div>'
        '</div>'
        '<div class="painel">'
        '<div class="painel-header">'
        '<div class="painel-header-left"><div class="painel-bar"></div><h3>Principais Assuntos</h3></div>'
        '<div class="mini-pills">'
        '<button class="mini-pill" data-periodo="dia" onclick="mostrarRanking(\'assunto\',\'dia\', this)">Hoje</button>'
        '<button class="mini-pill" data-periodo="semana" onclick="mostrarRanking(\'assunto\',\'semana\', this)">Semana</button>'
        '<button class="mini-pill" data-periodo="proxsemana" onclick="mostrarRanking(\'assunto\',\'proxsemana\', this)">Próx. Semana</button>'
        '<button class="mini-pill active" data-periodo="mes" onclick="mostrarRanking(\'assunto\',\'mes\', this)">Mês</button>'
        '<button class="mini-pill" data-periodo="todos" onclick="mostrarRanking(\'assunto\',\'todos\', this)">Todos</button>'
        '</div>'
        '</div>'
        '<div class="rank-panel" id="rank-assunto-dia">' + ranking_assuntos_dia + '</div>'
        '<div class="rank-panel" id="rank-assunto-semana">' + ranking_assuntos_semana + '</div>'
        '<div class="rank-panel" id="rank-assunto-proxsemana">' + ranking_assuntos_prox_semana + '</div>'
        '<div class="rank-panel active" id="rank-assunto-mes">' + ranking_assuntos_mes + '</div>'
        '<div class="rank-panel" id="rank-assunto-todos">' + ranking_assuntos_todos + '</div>'
        '</div>'
        '<div class="painel">'
        '<div class="painel-header">'
        '<div class="painel-header-left"><div class="painel-bar"></div><h3>Tipo de Atividade</h3></div>'
        '<div class="mini-pills">'
        '<button class="mini-pill" data-periodo="dia" onclick="mostrarRanking(\'tipo\',\'dia\', this)">Hoje</button>'
        '<button class="mini-pill" data-periodo="semana" onclick="mostrarRanking(\'tipo\',\'semana\', this)">Semana</button>'
        '<button class="mini-pill" data-periodo="proxsemana" onclick="mostrarRanking(\'tipo\',\'proxsemana\', this)">Próx. Semana</button>'
        '<button class="mini-pill active" data-periodo="mes" onclick="mostrarRanking(\'tipo\',\'mes\', this)">Mês</button>'
        '<button class="mini-pill" data-periodo="todos" onclick="mostrarRanking(\'tipo\',\'todos\', this)">Todos</button>'
        '</div>'
        '</div>'
        '<div class="rank-panel" id="rank-tipo-dia">' + ranking_tipo_dia + '</div>'
        '<div class="rank-panel" id="rank-tipo-semana">' + ranking_tipo_semana + '</div>'
        '<div class="rank-panel" id="rank-tipo-proxsemana">' + ranking_tipo_prox_semana + '</div>'
        '<div class="rank-panel active" id="rank-tipo-mes">' + ranking_tipo_mes + '</div>'
        '<div class="rank-panel" id="rank-tipo-todos">' + ranking_tipo_todos + '</div>'
        '</div>'
        '</div>'
        + bloco_semana +
        bloco_hoje +
        '<div class="tabela-card">'
        '<h3>Todos os Prazos</h3>'
        '<div class="contagem" id="contagemVisivel"></div>'
        '<div class="table-wrapper"><table><thead><tr>'
        '<th>Processo (Pasta)</th><th>Adverso</th><th>Prazo Encarregado</th><th>Data Fatal</th><th>Encarregado</th><th>Assunto</th><th>Status</th>'
        '</tr></thead><tbody id="tabelaBody">' + linhas_tabela + '</tbody></table></div>'
        '</div>'
        '</div>'
    )

    return (
        '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Painel de Prazos - Pacaembu</title>'
        '<style>' + css + '</style></head><body>' + corpo +
        '<script>' + js + '</script></body></html>'
    )


if __name__ == "__main__":
    registros = carregar_registros()
    print("Carregados " + str(len(registros)) + " registro(s) da API.")
    resultado = gerar_html(registros)
    with open(ARQUIVO_HTML_SAIDA, "w", encoding="utf-8") as f:
        f.write(resultado)
    print("Dashboard salvo em: " + ARQUIVO_HTML_SAIDA)

    import os
    os.makedirs("web_app", exist_ok=True)
    caminho_web = os.path.join("web_app", "index.html")
    with open(caminho_web, "w", encoding="utf-8") as f:
        f.write(resultado)
    print("Cópia web_app atualizada em: " + caminho_web)
    print("Abra esse arquivo no navegador para visualizar.")
