# -*- coding: utf-8 -*-
import html
import os
import sys
from collections import Counter
from datetime import datetime
import xlrd

ARQUIVO_XLS = "contingencia_civel.xls"
ARQUIVO_HTML_SAIDA = "dashboard_contingencia_civel.html"


def carregar_registros():
    if not os.path.exists(ARQUIVO_XLS):
        print("ERRO: arquivo '" + ARQUIVO_XLS + "' nao encontrado.")
        print("Exporte o relatorio no DataJuri e salve com esse nome nesta pasta.")
        sys.exit(1)

    livro = xlrd.open_workbook(ARQUIVO_XLS)
    planilha = livro.sheet_by_index(0)

    cabecalho = [str(planilha.cell_value(0, c)).strip() for c in range(planilha.ncols)]

    registros = []
    for linha_idx in range(1, planilha.nrows):
        registro = {}
        for col_idx, nome_campo in enumerate(cabecalho):
            celula = planilha.cell(linha_idx, col_idx)
            tipo = celula.ctype
            valor = celula.value
            if tipo == 3:  # data
                try:
                    dt = xlrd.xldate_as_datetime(valor, livro.datemode)
                    valor = dt.strftime("%d/%m/%Y")
                except Exception:
                    valor = ""
            elif tipo == 2:  # numero
                pass  # mantem como float
            else:
                valor = str(valor).strip()
            registro[nome_campo] = valor
        if registro.get("Processo"):
            registros.append(registro)
    return registros


def campo(reg, chave, padrao=""):
    val = reg.get(chave, padrao)
    if val is None:
        return padrao
    return val


def moeda(valor):
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "R$ 0,00"
    texto = "{:,.2f}".format(v)
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return "R$ " + texto


def moeda_compacta(valor):
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "R$ 0"
    if v >= 1000000:
        return "R$ " + "{:.2f}".format(v / 1000000).replace(".", ",") + " Mi"
    if v >= 1000:
        return "R$ " + "{:.0f}".format(v / 1000) + " mil"
    return moeda(v)


def categoria_perda(valor):
    v = (valor or "").strip().lower()
    if "poss" in v and "prov" not in v:
        return "possivel"
    if "prov" in v:
        return "provavel"
    if "remot" in v:
        return "remota"
    return "outro"


def gerar_linhas_tabela(registros):
    linhas = []
    for r in registros:
        cat = categoria_perda(campo(r, "Possibilidade de Perda"))
        processo = campo(r, "Processo") or "N/A"
        linhas.append(
            '<tr data-perda="' + cat + '">'
            '<td class="pasta-cell"><span class="pasta-texto">' + html.escape(str(processo)) + '</span>'
            '<button type="button" class="btn-copiar" data-pasta="' + html.escape(str(processo)) + '" onclick="copiarPasta(this)" title="Copiar numero do processo">&#128203;</button></td>'
            '<td>' + html.escape(str(campo(r, "Cliente") or "N/A")) + '</td>'
            '<td>' + html.escape(str(campo(r, "Adverso") or "N/A")) + '</td>'
            '<td class="num-cell">' + moeda(campo(r, "Valor da Causa", 0)) + '</td>'
            '<td class="num-cell">' + moeda(campo(r, "Valor Provisionado - Atualizado", 0)) + '</td>'
            '<td><span class="badge badge-' + cat + '">' + html.escape(str(campo(r, "Possibilidade de Perda") or "N/A")) + '</span></td>'
            '<td>' + html.escape(str(campo(r, "Instância da fase atual") or "N/A")) + '</td>'
            '<td>' + html.escape(str(campo(r, "Advogado do cliente") or "N/A")) + '</td>'
            '<td>' + html.escape(str(campo(r, "Assunto") or "N/A")) + '</td>'
            '<td>' + html.escape(str(campo(r, "Responsável") or "N/A")) + '</td>'
            '</tr>'
        )
    return "".join(linhas)


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
    valor_total_causa = sum(float(campo(r, "Valor da Causa", 0) or 0) for r in registros)
    valor_total_provisao = sum(float(campo(r, "Valor Provisionado - Atualizado", 0) or 0) for r in registros)
    total_provaveis = sum(1 for r in registros if categoria_perda(campo(r, "Possibilidade de Perda")) == "provavel")
    total_possiveis = sum(1 for r in registros if categoria_perda(campo(r, "Possibilidade de Perda")) == "possivel")
    total_remotas = sum(1 for r in registros if categoria_perda(campo(r, "Possibilidade de Perda")) == "remota")

    assunto_counter = Counter()
    fase_counter = Counter()
    escritorio_counter = Counter()
    responsavel_counter = Counter()

    for r in registros:
        assunto = campo(r, "Assunto")
        if assunto:
            assunto_counter[str(assunto)] += 1
        fase = campo(r, "Instância da fase atual")
        if fase:
            fase_counter[str(fase)] += 1
        escritorio = campo(r, "Advogado do cliente")
        if escritorio:
            escritorio_counter[str(escritorio)] += 1
        responsavel = campo(r, "Responsável")
        if responsavel:
            responsavel_counter[str(responsavel)] += 1

    linhas_tabela = gerar_linhas_tabela(registros)
    ranking_assuntos = gerar_ranking_barras(assunto_counter, "bar-vermelho")
    ranking_fase = gerar_ranking_barras(fase_counter, "bar-azul")
    ranking_escritorio = gerar_ranking_barras(escritorio_counter, "bar-dourado")
    ranking_responsavel = gerar_ranking_barras(responsavel_counter, "bar-azul")

    data_hoje = datetime.now().strftime("%d/%m/%Y")

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
        ".header-right{text-align:center;}"
        ".header-right .num{font-size:22px;font-weight:900;color:#233240;}"
        ".header-right .lbl{font-size:10px;color:#8a8471;font-weight:700;letter-spacing:.5px;}"
        ".header-right .data{font-size:11px;color:#9ca3af;margin-top:6px;}"
        ".container{max-width:1500px;margin:0 auto;padding:24px 32px 60px;}"
        ".filtros-bar{display:flex;align-items:center;gap:20px;flex-wrap:wrap;background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:14px 20px;margin-bottom:22px;}"
        ".filtro-grupo{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}"
        ".filtro-titulo{font-size:11px;font-weight:800;color:#8a8471;letter-spacing:1px;text-transform:uppercase;margin-right:2px;}"
        ".pill{background:#fff;color:#4b5563;border:1.5px solid #e2ddc9;padding:8px 16px;border-radius:999px;font-weight:700;font-size:12.5px;cursor:pointer;transition:.15s;}"
        ".pill:hover{border-color:#233240;}"
        ".pill.active{background:#233240;color:#fff;border-color:#233240;}"
        ".pill.active[data-perda='provavel']{background:#9c3b3b;border-color:#9c3b3b;}"
        ".pill.active[data-perda='possivel']{background:#b8860b;border-color:#b8860b;}"
        ".pill.active[data-perda='remota']{background:#3f6b4f;border-color:#3f6b4f;}"
        ".busca-inline{flex:1;min-width:220px;}"
        ".busca-inline input{width:100%;padding:9px 14px;border:1.5px solid #e2ddc9;border-radius:8px;font-size:13px;background:#faf9f5;}"
        ".busca-inline input:focus{outline:none;border-color:#233240;background:#fff;}"
        ".stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:22px;}"
        "@media (max-width:900px){.stats-grid{grid-template-columns:repeat(2,1fr);}}"
        ".stat-card{background:#fff;border:1px solid #e2ddc9;border-left:6px solid #233240;border-radius:10px;padding:18px 20px;}"
        ".stat-card .lbl{font-size:10.5px;color:#8a8471;font-weight:800;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;}"
        ".stat-card .num{font-size:26px;font-weight:900;color:#233240;margin-bottom:4px;}"
        ".stat-card .desc{font-size:11.5px;color:#9ca3af;}"
        ".stat-total{border-left-color:#233240;} .stat-total .num{color:#233240;}"
        ".stat-causa{border-left-color:#6b7f66;} .stat-causa .num{color:#4f6b4a;}"
        ".stat-provaveis{border-left-color:#9c3b3b;} .stat-provaveis .num{color:#9c3b3b;}"
        ".stat-provisao{border-left-color:#b8860b;} .stat-provisao .num{color:#8a660a;}"
        ".paineis-grid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:16px;margin-bottom:24px;}"
        "@media (max-width:1250px){.paineis-grid{grid-template-columns:1fr 1fr;}}"
        "@media (max-width:650px){.paineis-grid{grid-template-columns:1fr;}}"
        ".painel{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:20px;}"
        ".painel-header{display:flex;align-items:center;gap:8px;margin-bottom:18px;}"
        ".painel-bar{width:4px;height:15px;background:#9c3b3b;border-radius:2px;}"
        ".painel h3{font-size:12.5px;color:#233240;font-weight:900;letter-spacing:.4px;text-transform:uppercase;}"
        ".rank-row{display:grid;grid-template-columns:100px 1fr auto;align-items:center;gap:8px;margin-bottom:11px;font-size:11.5px;}"
        ".rank-nome{color:#374151;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600;}"
        ".rank-bar-bg{background:#f3f1ea;border-radius:6px;height:10px;overflow:hidden;}"
        ".rank-bar{height:100%;border-radius:6px;}"
        ".bar-azul{background:linear-gradient(90deg,#233240,#4a6c86);}"
        ".bar-vermelho{background:linear-gradient(90deg,#9c3b3b,#c17b7b);}"
        ".bar-dourado{background:linear-gradient(90deg,#8a660a,#c9a545);}"
        ".rank-qtd{color:#233240;font-weight:800;text-align:right;min-width:24px;font-size:11px;}"
        ".sem-dados{font-size:12px;color:#9ca3af;}"
        ".tabela-card{background:#fff;border:1px solid #e2ddc9;border-radius:12px;padding:22px;}"
        ".tabela-card h3{font-size:13px;color:#233240;font-weight:900;letter-spacing:.4px;text-transform:uppercase;margin-bottom:14px;}"
        ".contagem{font-size:12px;color:#8a8471;font-weight:700;margin-bottom:12px;}"
        "table{width:100%;border-collapse:collapse;}"
        "th{background:#faf9f5;padding:10px;text-align:left;font-size:9.5px;font-weight:800;color:#8a8471;text-transform:uppercase;letter-spacing:.4px;border-bottom:2px solid #e2ddc9;white-space:nowrap;position:sticky;top:0;z-index:2;}"
        "td{padding:10px;border-bottom:1px solid #f3f1ea;font-size:12px;color:#374151;}"
        "tr:hover{background:#faf9f5;}"
        ".pasta-cell{color:#233240;font-weight:800;white-space:nowrap;display:flex;align-items:center;gap:6px;}"
        ".num-cell{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}"
        ".btn-copiar{background:transparent;border:none;cursor:pointer;font-size:12px;padding:3px 5px;border-radius:5px;opacity:0.55;transition:.15s;}"
        ".btn-copiar:hover{opacity:1;background:#f3f1ea;}"
        ".btn-copiar.copiado{opacity:1;color:#16a34a;}"
        ".badge{display:inline-block;padding:4px 12px;border-radius:999px;font-size:10px;font-weight:800;white-space:nowrap;}"
        ".badge-possivel{background:#f3e6c4;color:#7a5c08;} .badge-provavel{background:#f3dede;color:#8a2e2e;} .badge-remota{background:#dcece1;color:#2f5a3d;} .badge-outro{background:#e5e7eb;color:#4b5563;}"
        ".oculto{display:none!important;}"
        ".table-wrapper{overflow:auto;max-height:620px;border:1px solid #e2ddc9;border-radius:10px;}"
    )

    js = (
        "var perdaAtiva='todos';"
        "function filtrarPerda(perda,botao){"
        "perdaAtiva=perda;"
        "document.querySelectorAll('.pill[data-perda]').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "aplicarFiltros();}"
        "function aplicarFiltros(){"
        "var termo=document.getElementById('busca').value.toLowerCase();"
        "var visiveis=0;"
        "document.querySelectorAll('#tabelaBody tr').forEach(function(linha){"
        "var texto=linha.textContent.toLowerCase();"
        "var perdaLinha=linha.getAttribute('data-perda');"
        "var passaTexto=texto.includes(termo);"
        "var passaPerda=(perdaAtiva==='todos')||(perdaLinha===perdaAtiva);"
        "var visivel=passaTexto&&passaPerda;"
        "linha.classList.toggle('oculto',!visivel);"
        "if(visivel)visiveis++;});"
        "document.getElementById('contagemVisivel').textContent=visiveis+' de ' + " + str(total) + " + ' processo(s)';}"
        "document.getElementById('busca').addEventListener('input',aplicarFiltros);"
        "aplicarFiltros();"
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
        "}else{copiarFallback(pasta,marcarCopiado);}"
        "}"
        "function copiarFallback(texto,callback){"
        "var temp=document.createElement('textarea');"
        "temp.value=texto;temp.style.position='fixed';temp.style.opacity='0';"
        "document.body.appendChild(temp);temp.focus();temp.select();"
        "try{document.execCommand('copy');callback();}catch(e){}"
        "document.body.removeChild(temp);"
        "}"
    )

    corpo = (
        '<div class="header">'
        '<div class="header-left">'
        '<div class="logo-texto"><span class="logo-nome">PACAEMBU</span><span class="logo-sub">CONSTRUTORA</span></div>'
        '<div class="logo-mark"><div class="logo-navy"></div><div class="logo-flag"><div class="logo-arrow-white"></div><div class="logo-arrow-gold"></div></div></div>'
        '</div>'
        '<div class="header-center">'
        '<div class="kicker">JURÍDICO &middot; CONTINGÊNCIA CÍVEL</div>'
        '<h1>DASHBOARD DE CONTINGÊNCIA CÍVEL</h1>'
        '<div class="sub">Processos, valores de causa e provisão</div>'
        '</div>'
        '<div class="header-right">'
        '<div class="num">' + str(total) + '</div><div class="lbl">PROCESSOS</div><div class="data">' + data_hoje + '</div>'
        '</div>'
        '</div>'
        '<div class="container">'
        '<div class="filtros-bar">'
        '<div class="filtro-grupo">'
        '<span class="filtro-titulo">Possibilidade de Perda</span>'
        '<button class="pill active" data-perda="todos" onclick="filtrarPerda(\'todos\', this)">Todos</button>'
        '<button class="pill" data-perda="possivel" onclick="filtrarPerda(\'possivel\', this)">Possível</button>'
        '<button class="pill" data-perda="provavel" onclick="filtrarPerda(\'provavel\', this)">Provável</button>'
        '<button class="pill" data-perda="remota" onclick="filtrarPerda(\'remota\', this)">Remota</button>'
        '</div>'
        '<div class="busca-inline"><input type="text" id="busca" placeholder="Buscar por processo, cliente, adverso, assunto..."></div>'
        '</div>'
        '<div class="stats-grid">'
        '<div class="stat-card stat-total"><div class="lbl">Total de Processos</div><div class="num">' + str(total) + '</div><div class="desc">Contingência cível</div></div>'
        '<div class="stat-card stat-causa"><div class="lbl">Total da Causa</div><div class="num">' + moeda_compacta(valor_total_causa) + '</div><div class="desc">Soma de todos os processos</div></div>'
        '<div class="stat-card stat-provaveis"><div class="lbl">Processos Prováveis</div><div class="num">' + str(total_provaveis) + '</div><div class="desc">Possível: ' + str(total_possiveis) + ' &middot; Remota: ' + str(total_remotas) + '</div></div>'
        '<div class="stat-card stat-provisao"><div class="lbl">Valor da Provisão</div><div class="num">' + moeda_compacta(valor_total_provisao) + '</div><div class="desc">Total provisionado atualizado</div></div>'
        '</div>'
        '<div class="paineis-grid">'
        '<div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Principais Assuntos</h3></div>' + ranking_assuntos + '</div>'
        '<div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Processos por Fase</h3></div>' + ranking_fase + '</div>'
        '<div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Principais Escritórios</h3></div>' + ranking_escritorio + '</div>'
        '<div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Por Responsável</h3></div>' + ranking_responsavel + '</div>'
        '</div>'
        '<div class="tabela-card">'
        '<h3>Todos os Processos</h3>'
        '<div class="contagem" id="contagemVisivel"></div>'
        '<div class="table-wrapper"><table><thead><tr>'
        '<th>Processo</th><th>Cliente</th><th>Adverso</th><th>Valor da Causa</th><th>Valor Provisionado</th><th>Poss. de Perda</th><th>Instância</th><th>Advogado Cliente</th><th>Assunto</th><th>Responsável</th>'
        '</tr></thead><tbody id="tabelaBody">' + linhas_tabela + '</tbody></table></div>'
        '</div>'
        '</div>'
    )

    return (
        '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<title>Contingência Cível - Pacaembu</title>'
        '<style>' + css + '</style></head><body>' + corpo +
        '<script>' + js + '</script></body></html>'
    )


if __name__ == "__main__":
    registros = carregar_registros()
    print("Carregados " + str(len(registros)) + " processo(s) do arquivo.")
    resultado = gerar_html(registros)
    with open(ARQUIVO_HTML_SAIDA, "w", encoding="utf-8") as f:
        f.write(resultado)
    print("Dashboard salvo em: " + ARQUIVO_HTML_SAIDA)
    print("Abra esse arquivo no navegador para visualizar.")
