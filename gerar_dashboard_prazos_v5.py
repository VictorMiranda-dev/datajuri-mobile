# -*- coding: utf-8 -*-
import csv
import html
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

ARQUIVO_CSV = "atividades_datajuri.csv"
ARQUIVO_HTML_SAIDA = "dashboard_prazos.html"


def carregar_registros():
    if not os.path.exists(ARQUIVO_CSV):
        print("ERRO: arquivo '" + ARQUIVO_CSV + "' nao encontrado.")
        sys.exit(1)
    with open(ARQUIVO_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


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


def gerar_linhas_tabela(registros):
    linhas = []
    for r in registros:
        cat = categoria_status(campo(r, "status"))
        encarregado = campo(r, "encarregado.nome") or "N/A"
        linhas.append(
            '<tr data-status="' + cat + '" data-encarregado="' + html.escape(encarregado.lower()) + '">'
            '<td class="pasta-cell">' + html.escape(campo(r, "processo.pasta") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "processo.adverso.nome") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "prazo_do_encarregado") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "data") or "N/A") + '</td>'
            '<td>' + html.escape(encarregado) + '</td>'
            '<td>' + html.escape(campo(r, "assunto") or campo(r, "tipoAtividade") or "N/A") + '</td>'
            '<td><span class="badge badge-' + cat + '">' + html.escape(campo(r, "status") or "N/A") + '</span></td>'
            '</tr>'
        )
    return "".join(linhas)


def gerar_ranking_barras(contador, cor_classe, limite=10):
    itens = contador.most_common(limite)
    if not itens:
        return '<p class="sem-dados">Sem prazos neste periodo</p>'
    maximo = itens[0][1]
    linhas = []
    for nome, qtd in itens:
        largura = int((qtd / maximo) * 100) if maximo else 0
        nome_curto = nome if len(nome) <= 30 else nome[:27] + "..."
        linhas.append(
            '<div class="rank-row">'
            '<div class="rank-nome" title="' + html.escape(nome) + '">' + html.escape(nome_curto) + '</div>'
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

    for r in registros:
        d = data_do_registro(r)
        if not d:
            continue
        enc = campo(r, "encarregado.nome") or "N/A"
        if d == hoje:
            qtd_dia += 1
            enc_dia[enc] += 1
        if semana_inicio <= d <= semana_fim:
            qtd_semana += 1
            enc_semana[enc] += 1
        if prox_semana_inicio <= d <= prox_semana_fim:
            qtd_prox_semana += 1
            enc_prox_semana[enc] += 1
        if mes_inicio <= d <= mes_fim:
            qtd_mes += 1
            enc_mes[enc] += 1

    linhas_tabela = gerar_linhas_tabela(registros)
    ranking_dia = gerar_ranking_barras(enc_dia, "bar-azul")
    ranking_semana = gerar_ranking_barras(enc_semana, "bar-azul")
    ranking_prox_semana = gerar_ranking_barras(enc_prox_semana, "bar-azul")
    ranking_mes = gerar_ranking_barras(enc_mes, "bar-azul")
    ranking_todos = gerar_ranking_barras(encarregado_counter_total, "bar-azul")
    ranking_assuntos = gerar_ranking_barras(assunto_counter, "bar-vermelho", limite=8)
    ranking_tipo_atividade = gerar_ranking_barras(tipo_atividade_counter, "bar-dourado", limite=8)

    data_hoje = hoje.strftime("%d/%m/%Y")

    css = (
        "*{margin:0;padding:0;box-sizing:border-box;}"
        "body{background:#f3f1ea;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#233240;min-height:100vh;}"
        ".header{background:#e9e5d9;border-bottom:3px solid #233240;padding:20px 32px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;}"
        ".header-left{display:flex;align-items:center;gap:16px;}"
        ".logo-text{font-size:22px;font-weight:900;color:#233240;letter-spacing:1px;}"
        ".logo-bars{display:flex;height:24px;width:100px;overflow:hidden;border-radius:2px;}"
        ".logo-bars div{flex:1;}"
        ".lb1{background:#233240;} .lb2{background:#b8860b;} .lb3{background:#9c3b3b;clip-path:polygon(0 0,70% 0,100% 50%,70% 100%,0 100%);}"
        ".header-center{text-align:center;flex:1;min-width:280px;}"
        ".header-center .kicker{font-size:11px;letter-spacing:3px;color:#8a8471;font-weight:700;margin-bottom:4px;}"
        ".header-center h1{font-size:24px;font-weight:900;color:#233240;letter-spacing:1px;}"
        ".header-center .sub{font-size:13px;color:#6b7280;margin-top:2px;}"
        ".header-right{display:flex;gap:24px;text-align:center;}"
        ".header-right .num{font-size:24px;font-weight:900;color:#233240;}"
        ".header-right .lbl{font-size:10px;color:#8a8471;font-weight:700;letter-spacing:.5px;}"
        ".header-right .data{font-size:11px;color:#9ca3af;margin-top:6px;}"
        ".container{max-width:1500px;margin:0 auto;padding:24px 32px 60px;}"
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
        ".periodo-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:22px;}"
        "@media (max-width:1000px){.periodo-grid{grid-template-columns:repeat(2,1fr);}}"
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
        ".rank-row{display:grid;grid-template-columns:110px 1fr auto;align-items:center;gap:10px;margin-bottom:11px;font-size:12px;}"
        ".rank-nome{color:#374151;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600;}"
        ".rank-bar-bg{background:#f3f1ea;border-radius:6px;height:11px;overflow:hidden;}"
        ".rank-bar{height:100%;border-radius:6px;}"
        ".bar-azul{background:linear-gradient(90deg,#233240,#4a6c86);}"
        ".bar-vermelho{background:linear-gradient(90deg,#9c3b3b,#c17b7b);}"
        ".bar-dourado{background:linear-gradient(90deg,#8a660a,#c9a545);}"
        ".rank-qtd{color:#233240;font-weight:800;text-align:right;min-width:20px;}"
        ".sem-dados{font-size:12px;color:#9ca3af;}"
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
        ".table-wrapper{overflow-x:auto;}"
    )

    js = (
        "var statusAtivo='todos';"
        "function filtrarStatus(status,botao){"
        "statusAtivo=status;"
        "document.querySelectorAll('.pill[data-status]').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "aplicarFiltros();}"
        "function mostrarRanking(periodo,botao){"
        "document.querySelectorAll('.mini-pill').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "document.querySelectorAll('.rank-panel').forEach(function(el){el.classList.remove('active');});"
        "document.getElementById('rank-'+periodo).classList.add('active');}"
        "function aplicarFiltros(){"
        "var termo=document.getElementById('busca').value.toLowerCase();"
        "var encarregadoSel=document.getElementById('encarregadoSelect').value;"
        "var visiveis=0;"
        "document.querySelectorAll('#tabelaBody tr').forEach(function(linha){"
        "var texto=linha.textContent.toLowerCase();"
        "var statusLinha=linha.getAttribute('data-status');"
        "var encarregadoLinha=linha.getAttribute('data-encarregado');"
        "var passaTexto=texto.includes(termo);"
        "var passaStatus=(statusAtivo==='todos')||(statusLinha===statusAtivo);"
        "var passaEncarregado=(encarregadoSel==='')||(encarregadoLinha===encarregadoSel);"
        "var visivel=passaTexto&&passaStatus&&passaEncarregado;"
        "linha.classList.toggle('oculto',!visivel);"
        "if(visivel)visiveis++;});"
        "document.getElementById('contagemVisivel').textContent=visiveis+' registro(s) exibido(s)';}"
        "document.getElementById('busca').addEventListener('input',aplicarFiltros);"
        "document.getElementById('encarregadoSelect').addEventListener('change',aplicarFiltros);"
        "aplicarFiltros();"
    )

    corpo = (
        '<div class="header">'
        '<div class="header-left">'
        '<span class="logo-text">PACAEMBU</span>'
        '<div class="logo-bars"><div class="lb1"></div><div class="lb2"></div><div class="lb3"></div></div>'
        '</div>'
        '<div class="header-center">'
        '<div class="kicker">JURIDICO &middot; GESTAO DE PRAZOS</div>'
        '<h1>PAINEL DE PRAZOS E ATIVIDADES</h1>'
        '<div class="sub">Acompanhamento de prazos do encarregado</div>'
        '</div>'
        '<div class="header-right">'
        '<div><div class="num">' + str(total) + '</div><div class="lbl">TOTAL</div></div>'
        '<div><div class="num">' + str(em_andamento) + '</div><div class="lbl">EM ANDAMENTO</div></div>'
        '<div><div class="num">' + str(finalizados) + '</div><div class="lbl">FINALIZADOS</div><div class="data">' + data_hoje + '</div></div>'
        '</div>'
        '</div>'
        '<div class="container">'
        '<div class="filtros-bar">'
        '<div class="filtro-grupo">'
        '<span class="filtro-titulo">Status</span>'
        '<button class="pill active" data-status="todos" onclick="filtrarStatus(\'todos\', this)">Todos</button>'
        '<button class="pill" data-status="naoiniciado" onclick="filtrarStatus(\'naoiniciado\', this)">Nao iniciados</button>'
        '<button class="pill" data-status="andamento" onclick="filtrarStatus(\'andamento\', this)">Em andamento</button>'
        '<button class="pill" data-status="finalizado" onclick="filtrarStatus(\'finalizado\', this)">Finalizados</button>'
        '</div>'
        '<div class="filtro-grupo">'
        '<span class="filtro-titulo">Encarregado</span>'
        '<select id="encarregadoSelect" class="select-encarregado"><option value="">Todos</option>' + opcoes_encarregado + '</select>'
        '</div>'
        '<div class="busca-inline"><input type="text" id="busca" placeholder="Buscar por processo, adverso, assunto..."></div>'
        '</div>'
        '<div class="stats-grid">'
        '<div class="stat-card stat-total"><div class="lbl">Total de Prazos</div><div class="num">' + str(total) + '</div><div class="desc">Registros no periodo</div></div>'
        '<div class="stat-card stat-naoiniciado"><div class="lbl">Nao Iniciados</div><div class="num">' + str(nao_iniciados) + '</div><div class="desc">Aguardando inicio</div></div>'
        '<div class="stat-card stat-andamento"><div class="lbl">Em Andamento</div><div class="num">' + str(em_andamento) + '</div><div class="desc">Em execucao ativa</div></div>'
        '<div class="stat-card stat-finalizado"><div class="lbl">Finalizados</div><div class="num">' + str(finalizados) + '</div><div class="desc">Concluidos</div></div>'
        '</div>'
        '<div class="periodo-grid">'
        '<div class="periodo-card periodo-hoje"><div class="plbl">Prazos Hoje</div><div class="pnum">' + str(qtd_dia) + '</div><div class="pdesc">' + hoje.strftime("%d/%m/%Y") + '</div></div>'
        '<div class="periodo-card periodo-semana"><div class="plbl">Prazos Esta Semana</div><div class="pnum">' + str(qtd_semana) + '</div><div class="pdesc">' + semana_inicio.strftime("%d/%m") + ' a ' + semana_fim.strftime("%d/%m") + '</div></div>'
        '<div class="periodo-card periodo-proxsemana"><div class="plbl">Prazos Proxima Semana</div><div class="pnum">' + str(qtd_prox_semana) + '</div><div class="pdesc">' + prox_semana_inicio.strftime("%d/%m") + ' a ' + prox_semana_fim.strftime("%d/%m") + '</div></div>'
        '<div class="periodo-card periodo-mes"><div class="plbl">Prazos Este Mes</div><div class="pnum">' + str(qtd_mes) + '</div><div class="pdesc">' + mes_inicio.strftime("%m/%Y") + '</div></div>'
        '</div>'
        '<div class="paineis-grid">'
        '<div class="painel">'
        '<div class="painel-header">'
        '<div class="painel-header-left"><div class="painel-bar"></div><h3>Prazos por Encarregado</h3></div>'
        '<div class="mini-pills">'
        '<button class="mini-pill" onclick="mostrarRanking(\'dia\', this)">Hoje</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\'semana\', this)">Semana</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\'proxsemana\', this)">Prox. Semana</button>'
        '<button class="mini-pill active" onclick="mostrarRanking(\'mes\', this)">Mes</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\'todos\', this)">Todos</button>'
        '</div>'
        '</div>'
        '<div class="rank-panel" id="rank-dia">' + ranking_dia + '</div>'
        '<div class="rank-panel" id="rank-semana">' + ranking_semana + '</div>'
        '<div class="rank-panel" id="rank-proxsemana">' + ranking_prox_semana + '</div>'
        '<div class="rank-panel active" id="rank-mes">' + ranking_mes + '</div>'
        '<div class="rank-panel" id="rank-todos">' + ranking_todos + '</div>'
        '</div>'
        '<div class="painel">'
        '<div class="painel-header"><div class="painel-header-left"><div class="painel-bar"></div><h3>Principais Assuntos</h3></div></div>'
        + ranking_assuntos +
        '</div>'
        '<div class="painel">'
        '<div class="painel-header"><div class="painel-header-left"><div class="painel-bar"></div><h3>Tipo de Atividade</h3></div></div>'
        + ranking_tipo_atividade +
        '</div>'
        '</div>'
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
    print("Carregados " + str(len(registros)) + " registro(s) do CSV.")
    resultado = gerar_html(registros)
    with open(ARQUIVO_HTML_SAIDA, "w", encoding="utf-8") as f:
        f.write(resultado)
    print("Dashboard salvo em: " + ARQUIVO_HTML_SAIDA)
    print("Abra esse arquivo no navegador para visualizar.")
