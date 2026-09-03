# -*- coding: utf-8 -*-
"""
Le o arquivo processos_celso_bonifacio.csv e cria um dashboard HTML
com tema claro, filtros por status (incluindo Encerrado) e busca.
"""

import csv
import html
import os
import sys
from collections import Counter

ARQUIVO_CSV = "processos_celso_bonifacio.csv"
ARQUIVO_HTML_SAIDA = "dashboard_celso_bonifacio.html"


def carregar_processos():
    if not os.path.exists(ARQUIVO_CSV):
        print("ERRO: arquivo '" + ARQUIVO_CSV + "' nao encontrado.")
        print("Rode primeiro o buscar_celso.py")
        sys.exit(1)

    processos = []
    with open(ARQUIVO_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for linha in reader:
            processos.append(linha)
    return processos


def categoria_status(status):
    status_lower = (status or "").strip().lower()
    if "ativo" in status_lower or "pendente" in status_lower:
        return "ativo"
    if "arquivado" in status_lower:
        return "arquivado"
    if "encerrado" in status_lower:
        return "encerrado"
    return "outro"


def badge_status(status):
    cat = categoria_status(status)
    return '<span class="badge badge-' + cat + '">' + html.escape(status or "N/A") + '</span>'


def gerar_linhas_tabela(processos):
    linhas = []
    for p in processos:
        cat = categoria_status(p.get("status", ""))
        linhas.append("""
        <tr data-status="{cat}">
            <td class="pasta-cell">{pasta}</td>
            <td>{cliente}</td>
            <td>{adverso}</td>
            <td>{advogado_adverso}</td>
            <td>{tipo_acao}</td>
            <td>{status}</td>
        </tr>
        """.format(
            cat=cat,
            pasta=html.escape(p.get("pasta", "") or "N/A"),
            cliente=html.escape(p.get("cliente.nome", "") or "N/A"),
            adverso=html.escape(p.get("adverso.nome", "") or "N/A"),
            advogado_adverso=html.escape(p.get("advogadoAdverso.nome", "") or "N/A"),
            tipo_acao=html.escape(p.get("tipoAcao", "") or "N/A"),
            status=badge_status(p.get("status", "")),
        ))
    return "".join(linhas)


def gerar_cards_processos(processos):
    cards = []
    for p in processos:
        cat = categoria_status(p.get("status", ""))
        cards.append("""
        <div class="card-processo" data-status="{cat}">
            <div class="card-header">
                <span class="card-pasta">{pasta}</span>
                {status}
            </div>
            <div class="card-body">
                <div class="card-linha">
                    <span class="card-label">Cliente</span>
                    <span class="card-valor">{cliente}</span>
                </div>
                <div class="card-linha">
                    <span class="card-label">Adverso</span>
                    <span class="card-valor">{adverso}</span>
                </div>
                <div class="card-linha">
                    <span class="card-label">Advogado Adverso</span>
                    <span class="card-valor destaque">{advogado_adverso}</span>
                </div>
                <div class="card-linha">
                    <span class="card-label">Tipo de Acao</span>
                    <span class="card-valor">{tipo_acao}</span>
                </div>
            </div>
        </div>
        """.format(
            cat=cat,
            pasta=html.escape(p.get("pasta", "") or "N/A"),
            cliente=html.escape(p.get("cliente.nome", "") or "N/A"),
            adverso=html.escape(p.get("adverso.nome", "") or "N/A"),
            advogado_adverso=html.escape(p.get("advogadoAdverso.nome", "") or "N/A"),
            tipo_acao=html.escape(p.get("tipoAcao", "") or "N/A"),
            status=badge_status(p.get("status", "")),
        ))
    return "".join(cards)


def gerar_barra_ranking(contador, cor_classe, limite=10):
    itens = contador.most_common(limite)
    if not itens:
        return '<p class="sem-dados">Sem registros</p>'
    maximo = itens[0][1]
    linhas = []
    for nome, qtd in itens:
        largura = int((qtd / maximo) * 100) if maximo else 0
        linhas.append("""
        <div class="rank-row">
            <div class="rank-nome" title="{nome_full}">{nome}</div>
            <div class="rank-bar-bg"><div class="rank-bar {cor}" style="width:{largura}%"></div></div>
            <div class="rank-qtd">{qtd}</div>
        </div>
        """.format(
            nome_full=html.escape(nome),
            nome=html.escape(nome if len(nome) <= 40 else nome[:37] + "..."),
            cor=cor_classe,
            largura=largura,
            qtd=qtd,
        ))
    return "".join(linhas)


def gerar_html(processos):
    total = len(processos)

    status_counter = Counter()
    tipo_acao_counter = Counter()
    cliente_counter = Counter()

    for p in processos:
        status = (p.get("status", "") or "N/A").strip() or "N/A"
        status_counter[status] += 1
        tipo_acao = (p.get("tipoAcao", "") or "N/A").strip() or "N/A"
        tipo_acao_counter[tipo_acao] += 1
        cliente = (p.get("cliente.nome", "") or "N/A").strip() or "N/A"
        cliente_counter[cliente] += 1

    ativos = sum(1 for p in processos if categoria_status(p.get("status", "")) == "ativo")
    arquivados = sum(1 for p in processos if categoria_status(p.get("status", "")) == "arquivado")
    encerrados = sum(1 for p in processos if categoria_status(p.get("status", "")) == "encerrado")

    linhas_tabela = gerar_linhas_tabela(processos)
    cards_processos = gerar_cards_processos(processos)
    ranking_status = gerar_barra_ranking(status_counter, "bar-status")
    ranking_tipo_acao = gerar_barra_ranking(tipo_acao_counter, "bar-tipo")
    ranking_cliente = gerar_barra_ranking(cliente_counter, "bar-cliente")

    template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard - Celso Jose Bonifacio Junior</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    background: #f3f4f6;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #1f2937;
    min-height: 100vh;
    padding: 24px;
}

.container { max-width: 1400px; margin: 0 auto; }

header {
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 2px solid #d1fae5;
}

h1 {
    font-size: 26px;
    color: #0f766e;
    margin-bottom: 6px;
    font-weight: 700;
}

.subtitulo { color: #6b7280; font-size: 14px; }

.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin: 24px 0;
}

@media (max-width: 900px) {
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

.stat-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 18px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.stat-card small {
    display: block;
    color: #6b7280;
    font-size: 11px;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

.stat-card strong { display: block; font-size: 26px; }

.stat-total strong { color: #0891b2; }
.stat-ativo strong { color: #d97706; }
.stat-arquivado strong { color: #6b7280; }
.stat-encerrado strong { color: #16a34a; }

.paineis-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}

@media (max-width: 1100px) {
    .paineis-grid { grid-template-columns: 1fr; }
}

.painel {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.painel h3 {
    font-size: 13px;
    color: #374151;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 14px;
    font-weight: 700;
}

.rank-row {
    display: grid;
    grid-template-columns: 1fr 2fr auto;
    align-items: center;
    gap: 10px;
    margin-bottom: 9px;
    font-size: 12px;
}

.rank-nome { color: #374151; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.rank-bar-bg {
    background: #f3f4f6;
    border-radius: 6px;
    height: 10px;
    overflow: hidden;
}

.rank-bar { height: 100%; border-radius: 6px; }
.bar-status { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.bar-tipo { background: linear-gradient(90deg, #0891b2, #22d3ee); }
.bar-cliente { background: linear-gradient(90deg, #16a34a, #4ade80); }

.rank-qtd { color: #6b7280; font-weight: 700; text-align: right; }

.sem-dados { font-size: 12px; color: #9ca3af; }

.filtros-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
    margin-bottom: 20px;
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 14px 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.filtro-label {
    font-size: 12px;
    color: #6b7280;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-right: 4px;
}

.filtro-chip {
    background: #f3f4f6;
    color: #4b5563;
    border: 1px solid #e5e7eb;
    padding: 7px 16px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
}

.filtro-chip:hover { background: #e5e7eb; }

.filtro-chip.active {
    background: #0f766e;
    color: #ffffff;
    border-color: #0f766e;
}

.filtro-chip.active[data-status="encerrado"] { background: #16a34a; border-color: #16a34a; }
.filtro-chip.active[data-status="ativo"] { background: #d97706; border-color: #d97706; }
.filtro-chip.active[data-status="arquivado"] { background: #6b7280; border-color: #6b7280; }

.busca-box { flex: 1; min-width: 220px; }

.busca-box input {
    width: 100%;
    padding: 10px 14px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #f9fafb;
    color: #1f2937;
    font-size: 14px;
}

.busca-box input:focus { outline: none; border-color: #0f766e; background: #ffffff; }

.tab-buttons {
    display: flex;
    gap: 6px;
    margin: 20px 0 16px;
    border-bottom: 2px solid #e5e7eb;
}

.tab-btn {
    background: transparent;
    color: #6b7280;
    border: none;
    padding: 10px 18px;
    cursor: pointer;
    font-weight: 600;
    font-size: 14px;
    border-bottom: 2px solid transparent;
    transition: all 0.2s ease;
}

.tab-btn.active { color: #0f766e; border-bottom-color: #0f766e; }
.tab-content { display: none; }
.tab-content.active { display: block; }

.contagem-visivel {
    font-size: 13px;
    color: #6b7280;
    margin-bottom: 14px;
}

.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
}

.card-processo {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.card-header {
    background: #f9fafb;
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #f3f4f6;
}

.card-pasta { font-weight: 700; color: #0891b2; font-size: 13px; }

.card-body { padding: 14px 16px; }

.card-linha {
    display: flex;
    justify-content: space-between;
    padding: 7px 0;
    border-bottom: 1px solid #f3f4f6;
    gap: 10px;
}

.card-linha:last-child { border-bottom: none; }

.card-label {
    color: #9ca3af;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    flex-shrink: 0;
    font-weight: 600;
}

.card-valor { text-align: right; font-size: 12px; color: #374151; }
.card-valor.destaque { color: #d97706; font-weight: 700; }

.table-wrapper {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    overflow-x: auto;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

table { width: 100%; border-collapse: collapse; }

th {
    background: #f9fafb;
    padding: 12px;
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    border-bottom: 2px solid #e5e7eb;
    white-space: nowrap;
}

td {
    padding: 11px 12px;
    border-bottom: 1px solid #f3f4f6;
    font-size: 13px;
    color: #374151;
}

tr:hover { background: #f9fafb; }

.pasta-cell { color: #0891b2; font-weight: 700; white-space: nowrap; }

.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
}

.badge-ativo { background: #fef3c7; color: #b45309; }
.badge-arquivado { background: #f3f4f6; color: #6b7280; }
.badge-encerrado { background: #dcfce7; color: #15803d; }
.badge-outro { background: #cffafe; color: #0e7490; }

.oculto { display: none !important; }
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>Processos - Adv. Celso Jose Bonifacio Junior</h1>
        <p class="subtitulo">Processos onde ele atua como advogado da parte contraria</p>
    </header>

    <div class="stats-grid">
        <div class="stat-card stat-total">
            <small>Total de Processos</small>
            <strong>TOTAL_VAL</strong>
        </div>
        <div class="stat-card stat-ativo">
            <small>Ativos / Pendentes</small>
            <strong>ATIVOS_VAL</strong>
        </div>
        <div class="stat-card stat-arquivado">
            <small>Arquivados</small>
            <strong>ARQUIVADOS_VAL</strong>
        </div>
        <div class="stat-card stat-encerrado">
            <small>Encerrados</small>
            <strong>ENCERRADOS_VAL</strong>
        </div>
    </div>

    <div class="paineis-grid">
        <div class="painel">
            <h3>Por Status</h3>
            RANKING_STATUS
        </div>
        <div class="painel">
            <h3>Por Tipo de Acao</h3>
            RANKING_TIPO_ACAO
        </div>
        <div class="painel">
            <h3>Por Cliente (Pacaembu)</h3>
            RANKING_CLIENTE
        </div>
    </div>

    <div class="filtros-bar">
        <span class="filtro-label">Status:</span>
        <button class="filtro-chip active" data-status="todos" onclick="filtrarStatus('todos', this)">Todos</button>
        <button class="filtro-chip" data-status="ativo" onclick="filtrarStatus('ativo', this)">Ativos</button>
        <button class="filtro-chip" data-status="arquivado" onclick="filtrarStatus('arquivado', this)">Arquivados</button>
        <button class="filtro-chip" data-status="encerrado" onclick="filtrarStatus('encerrado', this)">Encerrados</button>
        <div class="busca-box">
            <input type="text" id="busca" placeholder="Buscar por pasta, cliente, adverso...">
        </div>
    </div>

    <div class="tab-buttons">
        <button class="tab-btn active" onclick="mostrarAba('cards')">Cartoes</button>
        <button class="tab-btn" onclick="mostrarAba('tabela')">Tabela</button>
    </div>

    <p class="contagem-visivel" id="contagemVisivel"></p>

    <div id="cards" class="tab-content active">
        <div class="cards-grid" id="cardsGrid">
            CARDS_PROCESSOS
        </div>
    </div>

    <div id="tabela" class="tab-content">
        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Pasta</th>
                        <th>Cliente</th>
                        <th>Adverso</th>
                        <th>Advogado Adverso</th>
                        <th>Tipo de Acao</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="tabelaBody">
                    LINHAS_TABELA
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
var statusAtivo = 'todos';

function mostrarAba(aba) {
    document.querySelectorAll('.tab-content').forEach(function(el) { el.classList.remove('active'); });
    document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });
    document.getElementById(aba).classList.add('active');
    event.target.classList.add('active');
    aplicarFiltros();
}

function filtrarStatus(status, botao) {
    statusAtivo = status;
    document.querySelectorAll('.filtro-chip').forEach(function(el) { el.classList.remove('active'); });
    botao.classList.add('active');
    aplicarFiltros();
}

function aplicarFiltros() {
    var termo = document.getElementById('busca').value.toLowerCase();
    var visiveisCards = 0;
    var visiveisTabela = 0;

    document.querySelectorAll('#cardsGrid .card-processo').forEach(function(card) {
        var texto = card.textContent.toLowerCase();
        var statusCard = card.getAttribute('data-status');
        var passaTexto = texto.includes(termo);
        var passaStatus = (statusAtivo === 'todos') || (statusCard === statusAtivo);
        var visivel = passaTexto && passaStatus;
        card.classList.toggle('oculto', !visivel);
        if (visivel) visiveisCards++;
    });

    document.querySelectorAll('#tabelaBody tr').forEach(function(linha) {
        var texto = linha.textContent.toLowerCase();
        var statusLinha = linha.getAttribute('data-status');
        var passaTexto = texto.includes(termo);
        var passaStatus = (statusAtivo === 'todos') || (statusLinha === statusAtivo);
        var visivel = passaTexto && passaStatus;
        linha.classList.toggle('oculto', !visivel);
        if (visivel) visiveisTabela++;
    });

    var abaCardsAtiva = document.getElementById('cards').classList.contains('active');
    var contagem = abaCardsAtiva ? visiveisCards : visiveisTabela;
    document.getElementById('contagemVisivel').textContent = contagem + ' processo(s) exibido(s)';
}

document.getElementById('busca').addEventListener('input', aplicarFiltros);

aplicarFiltros();
</script>
</body>
</html>
"""

    resultado = template.replace("TOTAL_VAL", str(total))
    resultado = resultado.replace("ATIVOS_VAL", str(ativos))
    resultado = resultado.replace("ARQUIVADOS_VAL", str(arquivados))
    resultado = resultado.replace("ENCERRADOS_VAL", str(encerrados))
    resultado = resultado.replace("RANKING_STATUS", ranking_status)
    resultado = resultado.replace("RANKING_TIPO_ACAO", ranking_tipo_acao)
    resultado = resultado.replace("RANKING_CLIENTE", ranking_cliente)
    resultado = resultado.replace("CARDS_PROCESSOS", cards_processos)
    resultado = resultado.replace("LINHAS_TABELA", linhas_tabela)

    return resultado


if __name__ == "__main__":
    processos = carregar_processos()
    print("Carregados " + str(len(processos)) + " processo(s) do CSV.")

    html_final = gerar_html(processos)

    with open(ARQUIVO_HTML_SAIDA, "w", encoding="utf-8") as f:
        f.write(html_final)

    print("Dashboard salvo em: " + ARQUIVO_HTML_SAIDA)
    print("Abra esse arquivo no navegador para visualizar.")
