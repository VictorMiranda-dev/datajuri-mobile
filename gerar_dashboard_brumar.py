# -*- coding: utf-8 -*-
"""
Le o arquivo processos_brumar_marilia.csv (gerado pelo buscar_brumar_final.py)
e cria um dashboard HTML bonito para visualizar os processos.
"""

import csv
import html
import os
import sys

ARQUIVO_CSV = "processos_brumar_marilia.csv"
ARQUIVO_HTML_SAIDA = "dashboard_brumar_marilia.html"


def carregar_processos():
    if not os.path.exists(ARQUIVO_CSV):
        print("ERRO: arquivo '" + ARQUIVO_CSV + "' nao encontrado.")
        print("Rode primeiro o buscar_brumar_final.py")
        sys.exit(1)

    processos = []
    with open(ARQUIVO_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for linha in reader:
            processos.append(linha)
    return processos


def badge_status(status):
    status = (status or "").strip()
    status_lower = status.lower()
    if "pendente" in status_lower or "ativo" in status_lower:
        classe = "badge-pendente"
    elif "encerrado" in status_lower or "arquivado" in status_lower:
        classe = "badge-encerrado"
    else:
        classe = "badge-outro"
    return '<span class="badge ' + classe + '">' + html.escape(status or "N/A") + '</span>'


def gerar_linhas_tabela(processos):
    linhas = []
    for p in processos:
        linhas.append("""
        <tr>
            <td class="pasta-cell">{pasta}</td>
            <td>{cliente}</td>
            <td>{adverso}</td>
            <td>{correu}</td>
            <td>{empreiteiro}</td>
            <td>{tipo_acao}</td>
            <td>{status}</td>
        </tr>
        """.format(
            pasta=html.escape(p.get("pasta", "") or "N/A"),
            cliente=html.escape(p.get("cliente.nome", "") or "N/A"),
            adverso=html.escape(p.get("adverso.nome", "") or "N/A"),
            correu=html.escape(p.get("correu", "") or "-"),
            empreiteiro=html.escape(p.get("empreiteiro", "") or "-"),
            tipo_acao=html.escape(p.get("tipoAcao", "") or "N/A"),
            status=badge_status(p.get("status", "")),
        ))
    return "".join(linhas)


def gerar_cards_processos(processos):
    cards = []
    for p in processos:
        cards.append("""
        <div class="card-processo">
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
                    <span class="card-label">Correu</span>
                    <span class="card-valor">{correu}</span>
                </div>
                <div class="card-linha">
                    <span class="card-label">Empreiteiro</span>
                    <span class="card-valor destaque">{empreiteiro}</span>
                </div>
                <div class="card-linha">
                    <span class="card-label">Tipo de Acao</span>
                    <span class="card-valor">{tipo_acao}</span>
                </div>
            </div>
        </div>
        """.format(
            pasta=html.escape(p.get("pasta", "") or "N/A"),
            cliente=html.escape(p.get("cliente.nome", "") or "N/A"),
            adverso=html.escape(p.get("adverso.nome", "") or "N/A"),
            correu=html.escape(p.get("correu", "") or "-"),
            empreiteiro=html.escape(p.get("empreiteiro", "") or "-"),
            tipo_acao=html.escape(p.get("tipoAcao", "") or "N/A"),
            status=badge_status(p.get("status", "")),
        ))
    return "".join(cards)


def gerar_html(processos):
    total = len(processos)
    pendentes = sum(1 for p in processos if "pendente" in (p.get("status", "") or "").lower())
    encerrados = sum(1 for p in processos if "encerrado" in (p.get("status", "") or "").lower())
    outros = total - pendentes - encerrados

    linhas_tabela = gerar_linhas_tabela(processos)
    cards_processos = gerar_cards_processos(processos)

    template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Dashboard - Brumar de Marilia</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    background: linear-gradient(135deg, #0f172a 0%, #1a1f3a 100%);
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    color: #e5e7eb;
    min-height: 100vh;
    padding: 20px;
}

.container { max-width: 1400px; margin: 0 auto; }

header {
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 2px solid rgba(34, 197, 94, 0.3);
}

h1 {
    font-size: 28px;
    background: linear-gradient(135deg, #22c55e 0%, #06b6d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
}

.subtitulo { color: #9ca3af; font-size: 14px; }

.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin: 30px 0;
}

@media (max-width: 900px) {
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
}

.stat-card {
    background: rgba(17, 24, 39, 0.8);
    border: 1px solid rgba(75, 85, 99, 0.5);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}

.stat-card small {
    display: block;
    color: #9ca3af;
    font-size: 12px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.stat-card strong { display: block; font-size: 28px; }

.stat-total strong { color: #06b6d4; }
.stat-pendente strong { color: #f59e0b; }
.stat-encerrado strong { color: #22c55e; }
.stat-outro strong { color: #9ca3af; }

.tab-buttons {
    display: flex;
    gap: 10px;
    margin: 30px 0 20px;
    border-bottom: 2px solid rgba(75, 85, 99, 0.3);
}

.tab-btn {
    background: transparent;
    color: #9ca3af;
    border: none;
    padding: 12px 20px;
    cursor: pointer;
    font-weight: 500;
    font-size: 14px;
    border-bottom: 2px solid transparent;
    transition: all 0.3s ease;
}

.tab-btn.active { color: #22c55e; border-bottom-color: #22c55e; }
.tab-content { display: none; }
.tab-content.active { display: block; }

.cards-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 20px;
}

.card-processo {
    background: rgba(17, 24, 39, 0.8);
    border: 1px solid rgba(75, 85, 99, 0.5);
    border-radius: 12px;
    overflow: hidden;
}

.card-header {
    background: rgba(31, 41, 55, 0.6);
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.card-pasta { font-weight: 700; color: #06b6d4; font-size: 14px; }

.card-body { padding: 16px 18px; }

.card-linha {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid rgba(75, 85, 99, 0.2);
    gap: 10px;
}

.card-linha:last-child { border-bottom: none; }

.card-label {
    color: #9ca3af;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    flex-shrink: 0;
}

.card-valor {
    text-align: right;
    font-size: 13px;
    color: #e5e7eb;
}

.card-valor.destaque {
    color: #f59e0b;
    font-weight: 600;
}

.table-wrapper {
    background: rgba(17, 24, 39, 0.8);
    border: 1px solid rgba(75, 85, 99, 0.5);
    border-radius: 12px;
    overflow-x: auto;
}

table { width: 100%; border-collapse: collapse; }

th {
    background: rgba(31, 41, 55, 0.8);
    padding: 14px 12px;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    border-bottom: 2px solid rgba(75, 85, 99, 0.3);
    white-space: nowrap;
}

td {
    padding: 12px;
    border-bottom: 1px solid rgba(75, 85, 99, 0.2);
    font-size: 13px;
}

tr:hover { background: rgba(31, 41, 55, 0.4); }

.pasta-cell { color: #06b6d4; font-weight: 600; white-space: nowrap; }

.badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    white-space: nowrap;
}

.badge-pendente { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
.badge-encerrado { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
.badge-outro { background: rgba(156, 163, 175, 0.2); color: #9ca3af; }

.busca-box {
    margin-bottom: 20px;
}

.busca-box input {
    width: 100%;
    padding: 12px 16px;
    border: 1px solid rgba(75, 85, 99, 0.5);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.9);
    color: #e5e7eb;
    font-size: 14px;
}

.busca-box input:focus {
    outline: none;
    border-color: #22c55e;
}

.empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #9ca3af;
}
</style>
</head>
<body>
<div class="container">
    <header>
        <h1>Processos - Brumar de Marilia Portaria e Limpeza Ltda</h1>
        <p class="subtitulo">Processos onde a empresa aparece como Correu ou Empreiteiro</p>
    </header>

    <div class="stats-grid">
        <div class="stat-card stat-total">
            <small>Total de Processos</small>
            <strong>TOTAL_VAL</strong>
        </div>
        <div class="stat-card stat-pendente">
            <small>Pendentes</small>
            <strong>PENDENTES_VAL</strong>
        </div>
        <div class="stat-card stat-encerrado">
            <small>Encerrados</small>
            <strong>ENCERRADOS_VAL</strong>
        </div>
        <div class="stat-card stat-outro">
            <small>Outros Status</small>
            <strong>OUTROS_VAL</strong>
        </div>
    </div>

    <div class="busca-box">
        <input type="text" id="busca" placeholder="Buscar por pasta, cliente, adverso...">
    </div>

    <div class="tab-buttons">
        <button class="tab-btn active" onclick="mostrarAba('cards')">Cartoes</button>
        <button class="tab-btn" onclick="mostrarAba('tabela')">Tabela</button>
    </div>

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
                        <th>Correu</th>
                        <th>Empreiteiro</th>
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
function mostrarAba(aba) {
    document.querySelectorAll('.tab-content').forEach(function(el) { el.classList.remove('active'); });
    document.querySelectorAll('.tab-btn').forEach(function(el) { el.classList.remove('active'); });
    document.getElementById(aba).classList.add('active');
    event.target.classList.add('active');
}

document.getElementById('busca').addEventListener('input', function(e) {
    var termo = e.target.value.toLowerCase();

    document.querySelectorAll('#cardsGrid .card-processo').forEach(function(card) {
        var texto = card.textContent.toLowerCase();
        card.style.display = texto.includes(termo) ? '' : 'none';
    });

    document.querySelectorAll('#tabelaBody tr').forEach(function(linha) {
        var texto = linha.textContent.toLowerCase();
        linha.style.display = texto.includes(termo) ? '' : 'none';
    });
});
</script>
</body>
</html>
"""

    resultado = template.replace("TOTAL_VAL", str(total))
    resultado = resultado.replace("PENDENTES_VAL", str(pendentes))
    resultado = resultado.replace("ENCERRADOS_VAL", str(encerrados))
    resultado = resultado.replace("OUTROS_VAL", str(outros))
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
