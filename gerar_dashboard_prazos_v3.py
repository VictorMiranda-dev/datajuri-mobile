# -*- coding: utf-8 -*-
import csv
import html
import os
import sys
import re
from collections import Counter, defaultdict
from datetime import datetime

ARQUIVO_CSV = "atividades_datajuri.csv"
ARQUIVO_HTML_SAIDA = "dashboard_prazos.html"

MESES_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


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


def gerar_grafico_mensal(registros):
    contagem = defaultdict(int)
    for r in registros:
        data_str = campo(r, "prazo_do_encarregado") or campo(r, "data")
        dt = parse_data(data_str)
        if dt:
            contagem[(dt.year, dt.month)] += 1

    hoje = datetime.now()
    janela = []
    ano, mes = hoje.year, hoje.month
    for _ in range(12):
        janela.append((ano, mes))
        mes += 1
        if mes == 13:
            mes = 1
            ano += 1

    maximo = max([contagem.get(k, 0) for k in janela] + [1])

    barras = []
    for (a, m) in janela:
        qtd = contagem.get((a, m), 0)
        altura = int((qtd / maximo) * 100) if maximo else 0
        barras.append(
            '<div class="mes-col">'
            '<div class="mes-qtd">' + str(qtd) + '</div>'
            '<div class="mes-bar-bg"><div class="mes-bar" style="height:' + str(max(altura, 3)) + '%"></div></div>'
            '<div class="mes-label">' + MESES_PT[m - 1] + '<br>' + str(a) + '</div>'
            '</div>'
        )
    return '<div class="mes-grafico">' + "".join(barras) + '</div>'


def gerar_ranking_barras(contador, cor_classe, limite=8):
    itens = contador.most_common(limite)
    if not itens:
        return '<p class="sem-dados">Sem registros</p>'
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

    encarregado_counter = Counter()
    assunto_counter = Counter()
    for r in registros:
        enc = campo(r, "encarregado.nome")
        if enc:
            encarregado_counter[enc] += 1
        assunto = campo(r, "assunto") or campo(r, "tipoAtividade")
        if assunto:
            assunto_counter[assunto] += 1

    encarregados_unicos = sorted(encarregado_counter.keys())
    opcoes_encarregado = "".join(
        '<option value="' + html.escape(e.lower()) + '">' + html.escape(e) + ' (' + str(encarregado_counter[e]) + ')</option>'
        for e in encarregados_unicos
    )

    linhas_tabela = gerar_linhas_tabela(registros)
    grafico_mensal = gerar_grafico_mensal(registros)
    ranking_encarregados = gerar_ranking_barras(encarregado_counter, "bar-azul")
    ranking_assuntos = gerar_ranking_barras(assunto_counter, "bar-vermelho")

    data_hoje = datetime.now().strftime("%d/%m/%Y")

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
        ".paineis-grid{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:16px;margin-bottom:24px;}"
        "@media (max-width:1150px){.paineis-grid{grid-template-columns:1fr;}}"
        ".painel{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:20px;}"
        ".painel-header{display:flex;align-items:center;gap:8px;margin-bottom:18px;}"
        ".painel-bar{width:4px;height:15px;background:#9c3b3b;border-radius:2px;}"
        ".painel h3{font-size:13px;color:#233240;font-weight:900;letter-spacing:.4px;text-transform:uppercase;}"
        ".mes-grafico{display:flex;align-items:flex-end;gap:8px;height:190px;overflow-x:auto;padding-top:10px;}"
        ".mes-col{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;min-width:38px;height:100%;}"
        ".mes-qtd{font-size:11px;font-weight:800;color:#233240;margin-bottom:4px;}"
        ".mes-bar-bg{width:22px;flex:1;display:flex;align-items:flex-end;background:#f3f1ea;border-radius:4px;overflow:hidden;}"
        ".mes-bar{width:100%;background:linear-gradient(180deg,#b8860b,#233240);border-radius:4px 4px 0 0;min-height:2px;}"
        ".mes-label{font-size:9.5px;color:#8a8471;text-align:center;margin-top:6px;font-weight:700;line-height:1.3;}"
        ".rank-row{display:grid;grid-template-columns:110px 1fr auto;align-items:center;gap:10px;margin-bottom:11px;font-size:12px;}"
        ".rank-nome{color:#374151;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600;}"
        ".rank-bar-bg{background:#f3f1ea;border-radius:6px;height:11px;overflow:hidden;}"
        ".rank-bar{height:100%;border-radius:6px;}"
        ".bar-azul{background:linear-gradient(90deg,#233240,#4a6c86);}"
        ".bar-vermelho{background:linear-gradient(90deg,#9c3b3b,#c17b7b);}"
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
        '<div class="paineis-grid">'
        '<div class="painel">'
        '<div class="painel-header"><div class="painel-bar"></div><h3>Prazos por Mes (ultimos 12 meses)</h3></div>'
        + grafico_mensal +
        '</div>'
        '<div class="painel">'
        '<div class="painel-header"><div class="painel-bar"></div><h3>Prazos por Encarregado</h3></div>'
        + ranking_encarregados +
        '</div>'
        '<div class="painel">'
        '<div class="painel-header"><div class="painel-bar"></div><h3>5 Principais Assuntos</h3></div>'
        + ranking_assuntos +
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
