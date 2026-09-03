# -*- coding: utf-8 -*-
import csv
import html
import os
import sys
from collections import Counter

ARQUIVO_CSV = "processos_celso_bonifacio.csv"
ARQUIVO_HTML_SAIDA = "dashboard_celso_bonifacio.html"


def carregar_processos():
    if not os.path.exists(ARQUIVO_CSV):
        print("ERRO: arquivo nao encontrado. Rode primeiro o buscar_celso.py")
        sys.exit(1)
    processos = []
    with open(ARQUIVO_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for linha in reader:
            processos.append(linha)
    return processos


def categoria_status(status):
    s = (status or "").strip().lower()
    if "ativo" in s or "pendente" in s:
        return "ativo"
    if "arquivado" in s:
        return "arquivado"
    if "encerrado" in s:
        return "encerrado"
    return "outro"


def categoria_area(tipo_acao):
    t = (tipo_acao or "").strip().lower()
    if "trabalhista" in t:
        return "trabalhista"
    return "civel"


def badge_status(status):
    cat = categoria_status(status)
    return '<span class="badge badge-' + cat + '">' + html.escape(status or "N/A") + '</span>'


def gerar_linhas_tabela(processos):
    linhas = []
    for p in processos:
        cat = categoria_status(p.get("status", ""))
        area = categoria_area(p.get("tipoAcao", ""))
        linhas.append(
            '<tr data-status="' + cat + '" data-area="' + area + '">'
            '<td class="pasta-cell">' + html.escape(p.get("pasta", "") or "N/A") + '</td>'
            '<td>' + html.escape(p.get("cliente.nome", "") or "N/A") + '</td>'
            '<td>' + html.escape(p.get("adverso.nome", "") or "N/A") + '</td>'
            '<td>' + html.escape(p.get("advogadoAdverso.nome", "") or "N/A") + '</td>'
            '<td>' + html.escape(p.get("tipoAcao", "") or "N/A") + '</td>'
            '<td>' + badge_status(p.get("status", "")) + '</td>'
            '</tr>'
        )
    return "".join(linhas)


def gerar_barra_ranking(contador, cor_classe, limite=8):
    itens = contador.most_common(limite)
    if not itens:
        return '<p class="sem-dados">Sem registros</p>'
    maximo = itens[0][1]
    linhas = []
    for nome, qtd in itens:
        largura = int((qtd / maximo) * 100) if maximo else 0
        nome_curto = nome if len(nome) <= 26 else nome[:23] + "..."
        linhas.append(
            '<div class="rank-row"><div class="rank-nome" title="' + html.escape(nome) + '">' + html.escape(nome_curto) + '</div>'
            '<div class="rank-bar-bg"><div class="rank-bar ' + cor_classe + '" style="width:' + str(largura) + '%"></div></div>'
            '<div class="rank-qtd">' + str(qtd) + '</div></div>'
        )
    return "".join(linhas)


def gerar_html(processos):
    total = len(processos)
    status_counter = Counter()
    tipo_acao_counter = Counter()
    cliente_counter = Counter()

    for p in processos:
        status_counter[(p.get("status", "") or "N/A").strip() or "N/A"] += 1
        tipo_acao_counter[(p.get("tipoAcao", "") or "N/A").strip() or "N/A"] += 1
        cliente_counter[(p.get("cliente.nome", "") or "N/A").strip() or "N/A"] += 1

    ativos = sum(1 for p in processos if categoria_status(p.get("status", "")) == "ativo")
    arquivados = sum(1 for p in processos if categoria_status(p.get("status", "")) == "arquivado")
    encerrados = sum(1 for p in processos if categoria_status(p.get("status", "")) == "encerrado")
    trabalhistas = sum(1 for p in processos if categoria_area(p.get("tipoAcao", "")) == "trabalhista")
    civeis = total - trabalhistas

    linhas_tabela = gerar_linhas_tabela(processos)
    ranking_status = gerar_barra_ranking(status_counter, "bar-laranja")
    ranking_tipo_acao = gerar_barra_ranking(tipo_acao_counter, "bar-azul")
    ranking_cliente = gerar_barra_ranking(cliente_counter, "bar-verde")

    clientes_unicos = sorted(cliente_counter.keys())
    opcoes_cliente = "".join('<option value="' + html.escape(c) + '">' + html.escape(c) + '</option>' for c in clientes_unicos)

    css = (
        "*{margin:0;padding:0;box-sizing:border-box;}"
        "body{background:#f1f5f9;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;color:#0f172a;min-height:100vh;}"
        ".topbar{background:linear-gradient(90deg,#0f2942,#0b3a5c);height:10px;width:100%;}"
        ".container{max-width:1400px;margin:0 auto;padding:28px 24px 60px;}"
        "h1{font-size:24px;color:#0f2942;margin-bottom:4px;font-weight:800;}"
        ".subtitulo{color:#64748b;font-size:14px;margin-bottom:22px;}"
        ".pills-row{display:flex;gap:10px;margin-bottom:18px;flex-wrap:wrap;}"
        ".pill{background:#fff;color:#334155;border:1px solid #e2e8f0;padding:11px 26px;border-radius:999px;font-weight:700;font-size:14px;cursor:pointer;transition:all .15s ease;}"
        ".pill:hover{border-color:#0f2942;}"
        ".pill.active{background:#0f2942;color:#fff;border-color:#0f2942;}"
        ".filtros-card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:18px 22px;margin-bottom:22px;display:flex;gap:24px;flex-wrap:wrap;align-items:center;}"
        ".filtro-grupo{display:flex;align-items:center;gap:10px;}"
        ".filtro-grupo label{font-weight:700;color:#0f2942;font-size:14px;}"
        ".filtro-grupo select{padding:9px 14px;border:1px solid #e2e8f0;border-radius:10px;font-size:14px;color:#334155;background:#f8fafc;min-width:220px;}"
        ".status-pills{display:flex;gap:8px;flex-wrap:wrap;}"
        ".status-pill{padding:9px 18px;border-radius:999px;font-size:13px;font-weight:700;cursor:pointer;border:1px solid #e2e8f0;background:#f8fafc;color:#475569;transition:all .15s ease;}"
        ".status-pill.active{color:#fff;}"
        ".status-pill.active[data-status='todos']{background:#e11d48;border-color:#e11d48;}"
        ".status-pill.active[data-status='ativo']{background:#d97706;border-color:#d97706;}"
        ".status-pill.active[data-status='arquivado']{background:#64748b;border-color:#64748b;}"
        ".status-pill.active[data-status='encerrado']{background:#16a34a;border-color:#16a34a;}"
        ".stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-bottom:22px;}"
        "@media (max-width:900px){.stats-grid{grid-template-columns:repeat(2,1fr);}}"
        ".stat-card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:22px;}"
        ".stat-card strong{display:block;font-size:38px;font-weight:800;margin-bottom:6px;}"
        ".stat-card span{color:#64748b;font-size:14px;font-weight:600;}"
        ".stat-total strong{color:#0f2942;} .stat-ativo strong{color:#d97706;} .stat-arquivado strong{color:#64748b;} .stat-encerrado strong{color:#16a34a;}"
        ".paineis-grid{display:grid;grid-template-columns:1fr 1fr 1.4fr;gap:18px;margin-bottom:26px;}"
        "@media (max-width:1100px){.paineis-grid{grid-template-columns:1fr;}}"
        ".painel{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;}"
        ".painel h3{font-size:15px;color:#0f2942;margin-bottom:16px;font-weight:800;}"
        ".rank-row{display:grid;grid-template-columns:100px 1fr auto;align-items:center;gap:10px;margin-bottom:11px;font-size:12px;}"
        ".rank-nome{color:#334155;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600;}"
        ".rank-bar-bg{background:#f1f5f9;border-radius:6px;height:11px;overflow:hidden;}"
        ".rank-bar{height:100%;border-radius:6px;}"
        ".bar-laranja{background:linear-gradient(90deg,#d97706,#f59e0b);} .bar-azul{background:linear-gradient(90deg,#0b3a5c,#0891b2);} .bar-verde{background:linear-gradient(90deg,#16a34a,#4ade80);}"
        ".rank-qtd{color:#0f2942;font-weight:800;text-align:right;min-width:20px;}"
        ".sem-dados{font-size:12px;color:#94a3b8;}"
        ".tabela-card{background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:22px;}"
        ".tabela-card-header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px;margin-bottom:18px;}"
        ".tabela-card-header h3{font-size:17px;color:#0f2942;font-weight:800;}"
        ".busca-box{flex:1;min-width:260px;}"
        ".busca-box input{width:100%;padding:11px 16px;border:1px solid #e2e8f0;border-radius:10px;background:#f8fafc;color:#0f172a;font-size:14px;}"
        ".busca-box input:focus{outline:none;border-color:#0f2942;background:#fff;}"
        ".contagem{font-size:13px;color:#64748b;font-weight:700;white-space:nowrap;}"
        "table{width:100%;border-collapse:collapse;}"
        "th{background:#f8fafc;padding:12px;text-align:left;font-size:11px;font-weight:800;color:#64748b;text-transform:uppercase;letter-spacing:.4px;border-bottom:2px solid #e2e8f0;white-space:nowrap;}"
        "td{padding:12px;border-bottom:1px solid #f1f5f9;font-size:13px;color:#334155;}"
        "tr:hover{background:#f8fafc;}"
        ".pasta-cell{color:#0891b2;font-weight:800;white-space:nowrap;}"
        ".badge{display:inline-block;padding:5px 13px;border-radius:999px;font-size:11px;font-weight:800;white-space:nowrap;}"
        ".badge-ativo{background:#fef3c7;color:#b45309;} .badge-arquivado{background:#f1f5f9;color:#64748b;} .badge-encerrado{background:#dcfce7;color:#15803d;} .badge-outro{background:#cffafe;color:#0e7490;}"
        ".oculto{display:none!important;}"
        ".table-wrapper{overflow-x:auto;}"
    )

    js = (
        "var statusAtivo='todos';"
        "var areaAtiva='todos';"
        "function filtrarArea(area,botao){"
        "areaAtiva=area;"
        "document.querySelectorAll('.pill').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "aplicarFiltros();}"
        "function filtrarStatus(status,botao){"
        "statusAtivo=status;"
        "document.querySelectorAll('.status-pill').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "aplicarFiltros();}"
        "function aplicarFiltros(){"
        "var termo=document.getElementById('busca').value.toLowerCase();"
        "var clienteSel=document.getElementById('clienteSelect').value;"
        "var visiveis=0;"
        "document.querySelectorAll('#tabelaBody tr').forEach(function(linha){"
        "var texto=linha.textContent.toLowerCase();"
        "var statusLinha=linha.getAttribute('data-status');"
        "var areaLinha=linha.getAttribute('data-area');"
        "var passaTexto=texto.includes(termo);"
        "var passaStatus=(statusAtivo==='todos')||(statusLinha===statusAtivo);"
        "var passaArea=(areaAtiva==='todos')||(areaLinha===areaAtiva);"
        "var passaCliente=(clienteSel==='')||(texto.includes(clienteSel.toLowerCase()));"
        "var visivel=passaTexto&&passaStatus&&passaArea&&passaCliente;"
        "linha.classList.toggle('oculto',!visivel);"
        "if(visivel)visiveis++;});"
        "document.getElementById('contagemVisivel').textContent=visiveis+' de ' + " + str(total) + " + ' processo(s)';}"
        "document.getElementById('busca').addEventListener('input',aplicarFiltros);"
        "document.getElementById('clienteSelect').addEventListener('change',aplicarFiltros);"
        "aplicarFiltros();"
    )

    corpo = (
        '<div class="topbar"></div>'
        '<div class="container">'
        '<h1>Processos - Adv. Celso Jose Bonifacio Junior</h1>'
        '<p class="subtitulo">Processos onde ele atua como advogado da parte contraria (Pacaembu Construtora)</p>'
        '<div class="pills-row">'
        '<button class="pill active" onclick="filtrarArea(\'todos\', this)">Todos</button>'
        '<button class="pill" onclick="filtrarArea(\'trabalhista\', this)">Trabalhista</button>'
        '<button class="pill" onclick="filtrarArea(\'civel\', this)">Civel</button>'
        '</div>'
        '<div class="filtros-card">'
        '<div class="filtro-grupo"><label>Cliente:</label>'
        '<select id="clienteSelect"><option value="">Todos</option>' + opcoes_cliente + '</select></div>'
        '<div class="filtro-grupo"><label>Status:</label>'
        '<div class="status-pills">'
        '<button class="status-pill active" data-status="todos" onclick="filtrarStatus(\'todos\', this)">Todos</button>'
        '<button class="status-pill" data-status="ativo" onclick="filtrarStatus(\'ativo\', this)">Ativos</button>'
        '<button class="status-pill" data-status="arquivado" onclick="filtrarStatus(\'arquivado\', this)">Arquivados</button>'
        '<button class="status-pill" data-status="encerrado" onclick="filtrarStatus(\'encerrado\', this)">Encerrados</button>'
        '</div></div>'
        '</div>'
        '<div class="stats-grid">'
        '<div class="stat-card stat-total"><strong>' + str(total) + '</strong><span>Total de processos</span></div>'
        '<div class="stat-card stat-ativo"><strong>' + str(ativos) + '</strong><span>Ativos / pendentes</span></div>'
        '<div class="stat-card stat-arquivado"><strong>' + str(arquivados) + '</strong><span>Arquivados</span></div>'
        '<div class="stat-card stat-encerrado"><strong>' + str(encerrados) + '</strong><span>Encerrados</span></div>'
        '</div>'
        '<div class="paineis-grid">'
        '<div class="painel"><h3>Por Status</h3>' + ranking_status + '</div>'
        '<div class="painel"><h3>Por Tipo de Acao</h3>' + ranking_tipo_acao + '</div>'
        '<div class="painel"><h3>Por Cliente (Pacaembu)</h3>' + ranking_cliente + '</div>'
        '</div>'
        '<div class="tabela-card">'
        '<div class="tabela-card-header">'
        '<h3>Todos os processos</h3>'
        '<div class="busca-box"><input type="text" id="busca" placeholder="Buscar por processo, adverso, cliente, assunto..."></div>'
        '<span class="contagem" id="contagemVisivel"></span>'
        '</div>'
        '<div class="table-wrapper"><table><thead><tr>'
        '<th>Processo (Pasta)</th><th>Cliente</th><th>Adverso</th><th>Advogado Adverso</th><th>Tipo de Acao</th><th>Status</th>'
        '</tr></thead><tbody id="tabelaBody">' + linhas_tabela + '</tbody></table></div>'
        '</div>'
        '</div>'
    )

    html_final = (
        '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Dashboard - Celso Jose Bonifacio Junior</title>'
        '<style>' + css + '</style></head><body>' + corpo +
        '<script>' + js + '</script></body></html>'
    )
    return html_final


if __name__ == "__main__":
    processos = carregar_processos()
    print("Carregados " + str(len(processos)) + " processo(s) do CSV.")
    resultado = gerar_html(processos)
    with open(ARQUIVO_HTML_SAIDA, "w", encoding="utf-8") as f:
        f.write(resultado)
    print("Dashboard salvo em: " + ARQUIVO_HTML_SAIDA)
    print("Abra esse arquivo no navegador para visualizar.")
