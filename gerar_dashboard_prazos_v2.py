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
        print("Rode primeiro o extrair_dashboard_completo.py")
        sys.exit(1)
    with open(ARQUIVO_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def parse_data(valor):
    if not valor:
        return None
    valor = valor.strip()
    formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"]
    for fmt in formatos:
        try:
            return datetime.strptime(valor[:10], fmt)
        except ValueError:
            continue
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", valor)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
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


def campo(reg, *chaves):
    for chave in chaves:
        if chave in reg and reg[chave]:
            return reg[chave]
    return ""


def gerar_linhas_tabela(registros):
    linhas = []
    for r in registros:
        cat = categoria_status(campo(r, "status"))
        linhas.append(
            '<tr data-status="' + cat + '">'
            '<td class="pasta-cell">' + html.escape(campo(r, "processo.pasta") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "processo.adverso.nome") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "prazo_do_encarregado", "data") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "encarregado.nome") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "assunto") or "N/A") + '</td>'
            '<td><span class="badge badge-' + cat + '">' + html.escape(campo(r, "status") or "N/A") + '</span></td>'
            '</tr>'
        )
    return "".join(linhas)


def gerar_grafico_mensal(registros):
    contagem = defaultdict(int)
    for r in registros:
        data_str = campo(r, "prazo_do_encarregado", "data")
        dt = parse_data(data_str)
        if dt:
            chave = (dt.year, dt.month)
            contagem[chave] += 1

    if not contagem:
        return '<p class="sem-dados">Sem dados de data suficientes</p>'

    chaves_ordenadas = sorted(contagem.keys())[-12:]
    maximo = max(contagem[k] for k in chaves_ordenadas) if chaves_ordenadas else 1

    barras = []
    for (ano, mes) in chaves_ordenadas:
        qtd = contagem[(ano, mes)]
        altura = int((qtd / maximo) * 100) if maximo else 0
        label_mes = MESES_PT[mes - 1]
        barras.append(
            '<div class="mes-col">'
            '<div class="mes-qtd">' + str(qtd) + '</div>'
            '<div class="mes-bar-bg"><div class="mes-bar" style="height:' + str(altura) + '%"></div></div>'
            '<div class="mes-label">' + label_mes + '<br>' + str(ano) + '</div>'
            '</div>'
        )
    return '<div class="mes-grafico">' + "".join(barras) + '</div>'


def gerar_top_assuntos(registros, limite=5):
    contador = Counter()
    for r in registros:
        assunto = (campo(r, "assunto") or "N/A").strip() or "N/A"
        contador[assunto] += 1

    itens = contador.most_common(limite)
    if not itens:
        return '<p class="sem-dados">Sem registros</p>'

    maximo = itens[0][1]
    linhas = []
    for nome, qtd in itens:
        largura = int((qtd / maximo) * 100) if maximo else 0
        nome_curto = nome if len(nome) <= 46 else nome[:43] + "..."
        linhas.append(
            '<div class="assunto-row">'
            '<div class="assunto-nome" title="' + html.escape(nome) + '">' + html.escape(nome_curto) + '</div>'
            '<div class="assunto-bar-bg"><div class="assunto-bar" style="width:' + str(largura) + '%"></div></div>'
            '<div class="assunto-qtd">' + str(qtd) + '</div>'
            '</div>'
        )
    return "".join(linhas)


def gerar_html(registros):
    total = len(registros)
    nao_iniciados = sum(1 for r in registros if categoria_status(campo(r, "status")) == "naoiniciado")
    em_andamento = sum(1 for r in registros if categoria_status(campo(r, "status")) == "andamento")
    finalizados = sum(1 for r in registros if categoria_status(campo(r, "status")) == "finalizado")

    linhas_tabela = gerar_linhas_tabela(registros)
    grafico_mensal = gerar_grafico_mensal(registros)
    top_assuntos = gerar_top_assuntos(registros)

    data_hoje = datetime.now().strftime("%d/%m/%Y")

    css = (
        "*{margin:0;padding:0;box-sizing:border-box;}"
        "body{background:#f4f1ea;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#0f2942;min-height:100vh;}"
        ".header{background:#eae6da;border-bottom:3px solid #0f2942;padding:20px 32px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px;}"
        ".header-left{display:flex;align-items:center;gap:16px;}"
        ".logo-text{font-size:22px;font-weight:900;color:#0f2942;letter-spacing:1px;}"
        ".logo-bars{display:flex;height:26px;width:110px;overflow:hidden;border-radius:2px;}"
        ".logo-bars div{flex:1;}"
        ".lb1{background:#0f2942;} .lb2{background:#f0ad2e;} .lb3{background:#d1293d;clip-path:polygon(0 0,70% 0,100% 50%,70% 100%,0 100%);}"
        ".header-center{text-align:center;flex:1;min-width:280px;}"
        ".header-center .kicker{font-size:11px;letter-spacing:3px;color:#8a8471;font-weight:700;margin-bottom:4px;}"
        ".header-center h1{font-size:26px;font-weight:900;color:#0f2942;letter-spacing:1px;}"
        ".header-center .sub{font-size:13px;color:#6b7280;margin-top:2px;}"
        ".header-right{display:flex;gap:26px;text-align:center;}"
        ".header-right .num{font-size:26px;font-weight:900;color:#0f2942;}"
        ".header-right .lbl{font-size:10px;color:#8a8471;font-weight:700;letter-spacing:.5px;}"
        ".header-right .data{font-size:11px;color:#9ca3af;margin-top:6px;}"
        ".container{max-width:1440px;margin:0 auto;padding:24px 32px 60px;}"
        ".filtros-bar{display:flex;align-items:center;gap:24px;flex-wrap:wrap;background:#fff;border:1px solid #e5e1d3;border-radius:12px;padding:14px 20px;margin-bottom:22px;}"
        ".filtro-grupo{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}"
        ".filtro-titulo{font-size:11px;font-weight:800;color:#8a8471;letter-spacing:1px;text-transform:uppercase;margin-right:4px;}"
        ".pill{background:#fff;color:#4b5563;border:1.5px solid #e5e1d3;padding:8px 18px;border-radius:999px;font-weight:700;font-size:13px;cursor:pointer;transition:.15s;}"
        ".pill:hover{border-color:#0f2942;}"
        ".pill.active{background:#0f2942;color:#fff;border-color:#0f2942;}"
        ".pill.active[data-status='finalizado']{background:#1f9d55;border-color:#1f9d55;}"
        ".pill.active[data-status='andamento']{background:#f0ad2e;border-color:#f0ad2e;}"
        ".pill.active[data-status='naoiniciado']{background:#d1293d;border-color:#d1293d;}"
        ".busca-inline{flex:1;min-width:220px;}"
        ".busca-inline input{width:100%;padding:9px 14px;border:1.5px solid #e5e1d3;border-radius:8px;font-size:13px;background:#faf9f5;}"
        ".busca-inline input:focus{outline:none;border-color:#0f2942;background:#fff;}"
        ".stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-bottom:22px;}"
        "@media (max-width:900px){.stats-grid{grid-template-columns:repeat(2,1fr);}}"
        ".stat-card{background:#fff;border:1px solid #e5e1d3;border-left:6px solid #0f2942;border-radius:10px;padding:20px 22px;}"
        ".stat-card .lbl{font-size:11px;color:#8a8471;font-weight:800;letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;}"
        ".stat-card .num{font-size:32px;font-weight:900;color:#0f2942;margin-bottom:4px;}"
        ".stat-card .desc{font-size:12px;color:#9ca3af;}"
        ".stat-total{border-left-color:#0f2942;} .stat-total .num{color:#0f2942;}"
        ".stat-naoiniciado{border-left-color:#d1293d;} .stat-naoiniciado .num{color:#d1293d;}"
        ".stat-andamento{border-left-color:#f0ad2e;} .stat-andamento .num{color:#b5790a;}"
        ".stat-finalizado{border-left-color:#1f9d55;} .stat-finalizado .num{color:#1f9d55;}"
        ".paineis-grid{display:grid;grid-template-columns:1.3fr 1fr;gap:18px;margin-bottom:24px;}"
        "@media (max-width:1050px){.paineis-grid{grid-template-columns:1fr;}}"
        ".painel{background:#fff;border:1px solid #e5e1d3;border-radius:12px;padding:22px;}"
        ".painel-header{display:flex;align-items:center;gap:8px;margin-bottom:20px;}"
        ".painel-bar{width:4px;height:16px;background:#d1293d;border-radius:2px;}"
        ".painel h3{font-size:14px;color:#0f2942;font-weight:900;letter-spacing:.5px;text-transform:uppercase;}"
        ".mes-grafico{display:flex;align-items:flex-end;gap:10px;height:200px;overflow-x:auto;padding-top:10px;}"
        ".mes-col{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;min-width:44px;height:100%;}"
        ".mes-qtd{font-size:12px;font-weight:800;color:#0f2942;margin-bottom:4px;}"
        ".mes-bar-bg{width:26px;flex:1;display:flex;align-items:flex-end;background:#f4f1ea;border-radius:4px;overflow:hidden;}"
        ".mes-bar{width:100%;background:linear-gradient(180deg,#f0ad2e,#0f2942);border-radius:4px 4px 0 0;min-height:2px;}"
        ".mes-label{font-size:10px;color:#8a8471;text-align:center;margin-top:6px;font-weight:700;line-height:1.3;}"
        ".assunto-row{display:grid;grid-template-columns:160px 1fr auto;align-items:center;gap:12px;margin-bottom:14px;}"
        ".assunto-nome{font-size:12.5px;color:#374151;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}"
        ".assunto-bar-bg{background:#f4f1ea;border-radius:6px;height:14px;overflow:hidden;}"
        ".assunto-bar{height:100%;border-radius:6px;background:linear-gradient(90deg,#d1293d,#f0ad2e);}"
        ".assunto-qtd{font-size:13px;font-weight:900;color:#0f2942;min-width:30px;text-align:right;}"
        ".sem-dados{font-size:12px;color:#9ca3af;}"
        ".tabela-card{background:#fff;border:1px solid #e5e1d3;border-radius:12px;padding:22px;}"
        ".tabela-card h3{font-size:14px;color:#0f2942;font-weight:900;letter-spacing:.5px;text-transform:uppercase;margin-bottom:16px;}"
        ".contagem{font-size:12px;color:#8a8471;font-weight:700;margin-bottom:12px;}"
        "table{width:100%;border-collapse:collapse;}"
        "th{background:#faf9f5;padding:11px;text-align:left;font-size:10.5px;font-weight:800;color:#8a8471;text-transform:uppercase;letter-spacing:.4px;border-bottom:2px solid #e5e1d3;white-space:nowrap;}"
        "td{padding:11px;border-bottom:1px solid #f4f1ea;font-size:12.5px;color:#374151;}"
        "tr:hover{background:#faf9f5;}"
        ".pasta-cell{color:#0f2942;font-weight:800;white-space:nowrap;}"
        ".badge{display:inline-block;padding:4px 12px;border-radius:999px;font-size:10.5px;font-weight:800;white-space:nowrap;}"
        ".badge-naoiniciado{background:#fde2e4;color:#b31730;} .badge-andamento{background:#fdf0d5;color:#a06600;} .badge-finalizado{background:#dcf5e2;color:#137a37;} .badge-outro{background:#e5e7eb;color:#4b5563;}"
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
        "var visiveis=0;"
        "document.querySelectorAll('#tabelaBody tr').forEach(function(linha){"
        "var texto=linha.textContent.toLowerCase();"
        "var statusLinha=linha.getAttribute('data-status');"
        "var passaTexto=texto.includes(termo);"
        "var passaStatus=(statusAtivo==='todos')||(statusLinha===statusAtivo);"
        "var visivel=passaTexto&&passaStatus;"
        "linha.classList.toggle('oculto',!visivel);"
        "if(visivel)visiveis++;});"
        "document.getElementById('contagemVisivel').textContent=visiveis+' registro(s) exibido(s)';}"
        "document.getElementById('busca').addEventListener('input',aplicarFiltros);"
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
        '<div class="busca-inline"><input type="text" id="busca" placeholder="Buscar por processo, adverso, encarregado, assunto..."></div>'
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
        '<div class="painel-header"><div class="painel-bar"></div><h3>5 Principais Assuntos</h3></div>'
        + top_assuntos +
        '</div>'
        '</div>'
        '<div class="tabela-card">'
        '<h3>Todos os Prazos</h3>'
        '<div class="contagem" id="contagemVisivel"></div>'
        '<div class="table-wrapper"><table><thead><tr>'
        '<th>Processo (Pasta)</th><th>Adverso</th><th>Prazo</th><th>Encarregado</th><th>Assunto</th><th>Status</th>'
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
