# -*- coding: utf-8 -*-
with open("gerar_dashboard_prazos_v10.py", "r", encoding="utf-8") as f:
    conteudo = f.read()

substituicoes = []

# 1) Loop de periodo: adicionar contadores de assunto/tipo por dia/semana/prox_semana/mes
antigo_loop = '''    qtd_dia = 0
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
            enc_mes[enc] += 1'''

novo_loop = '''    qtd_dia = 0
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
                tipo_mes[tipo_r] += 1'''

substituicoes.append((antigo_loop, novo_loop))

# 2) Geracao dos rankings: adicionar variantes por periodo para assunto e tipo
antigo_rankings = '''    linhas_tabela = gerar_linhas_tabela(registros)
    ranking_dia = gerar_ranking_barras(enc_dia, "bar-azul", truncar=True)
    ranking_semana = gerar_ranking_barras(enc_semana, "bar-azul", truncar=True)
    ranking_prox_semana = gerar_ranking_barras(enc_prox_semana, "bar-azul", truncar=True)
    ranking_mes = gerar_ranking_barras(enc_mes, "bar-azul", truncar=True)
    ranking_todos = gerar_ranking_barras(encarregado_counter_total, "bar-azul", truncar=True)
    ranking_assuntos = gerar_ranking_barras(assunto_counter, "bar-vermelho", limite=8, truncar=False, clicavel=True)
    ranking_tipo_atividade = gerar_ranking_barras(tipo_atividade_counter, "bar-dourado", limite=8, truncar=False, clicavel=True)'''

novo_rankings = '''    linhas_tabela = gerar_linhas_tabela(registros)
    ranking_dia = gerar_ranking_barras(enc_dia, "bar-azul", truncar=True)
    ranking_semana = gerar_ranking_barras(enc_semana, "bar-azul", truncar=True)
    ranking_prox_semana = gerar_ranking_barras(enc_prox_semana, "bar-azul", truncar=True)
    ranking_mes = gerar_ranking_barras(enc_mes, "bar-azul", truncar=True)
    ranking_todos = gerar_ranking_barras(encarregado_counter_total, "bar-azul", truncar=True)

    ranking_assuntos_dia = gerar_ranking_barras(assunto_dia, "bar-vermelho", limite=8, clicavel=True)
    ranking_assuntos_semana = gerar_ranking_barras(assunto_semana, "bar-vermelho", limite=8, clicavel=True)
    ranking_assuntos_prox_semana = gerar_ranking_barras(assunto_prox_semana, "bar-vermelho", limite=8, clicavel=True)
    ranking_assuntos_mes = gerar_ranking_barras(assunto_mes, "bar-vermelho", limite=8, clicavel=True)
    ranking_assuntos_todos = gerar_ranking_barras(assunto_counter, "bar-vermelho", limite=8, clicavel=True)

    ranking_tipo_dia = gerar_ranking_barras(tipo_dia, "bar-dourado", limite=8, clicavel=True)
    ranking_tipo_semana = gerar_ranking_barras(tipo_semana, "bar-dourado", limite=8, clicavel=True)
    ranking_tipo_prox_semana = gerar_ranking_barras(tipo_prox_semana, "bar-dourado", limite=8, clicavel=True)
    ranking_tipo_mes = gerar_ranking_barras(tipo_mes, "bar-dourado", limite=8, clicavel=True)
    ranking_tipo_todos = gerar_ranking_barras(tipo_atividade_counter, "bar-dourado", limite=8, clicavel=True)'''

substituicoes.append((antigo_rankings, novo_rankings))

# 3) JS mostrarRanking: generalizar para aceitar grupo (encarregado/assunto/tipo)
antigo_js = '''"function mostrarRanking(periodo,botao){"
        "document.querySelectorAll('.mini-pill').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "document.querySelectorAll('.rank-panel').forEach(function(el){el.classList.remove('active');});"
        "document.getElementById('rank-'+periodo).classList.add('active');}"'''

novo_js = '''"function mostrarRanking(grupo,periodo,botao){"
        "var painel=botao.closest('.painel');"
        "painel.querySelectorAll('.mini-pill').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "painel.querySelectorAll('.rank-panel').forEach(function(el){el.classList.remove('active');});"
        "document.getElementById('rank-'+grupo+'-'+periodo).classList.add('active');}"'''

substituicoes.append((antigo_js, novo_js))

# 4) HTML dos 3 paineis: adicionar pills nos paineis de assunto/tipo e renomear ids do encarregado
antigo_html = '''        '<div class="paineis-grid">'
        '<div class="painel">'
        '<div class="painel-header">'
        '<div class="painel-header-left"><div class="painel-bar"></div><h3>Prazos por Encarregado</h3></div>'
        '<div class="mini-pills">'
        '<button class="mini-pill" onclick="mostrarRanking(\\'dia\\', this)">Hoje</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'semana\\', this)">Semana</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'proxsemana\\', this)">Próx. Semana</button>'
        '<button class="mini-pill active" onclick="mostrarRanking(\\'mes\\', this)">Mês</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'todos\\', this)">Todos</button>'
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
        '</div>' '''.rstrip()

novo_html = '''        '<div class="paineis-grid">'
        '<div class="painel">'
        '<div class="painel-header">'
        '<div class="painel-header-left"><div class="painel-bar"></div><h3>Prazos por Encarregado</h3></div>'
        '<div class="mini-pills">'
        '<button class="mini-pill" onclick="mostrarRanking(\\'encarregado\\',\\'dia\\', this)">Hoje</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'encarregado\\',\\'semana\\', this)">Semana</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'encarregado\\',\\'proxsemana\\', this)">Próx. Semana</button>'
        '<button class="mini-pill active" onclick="mostrarRanking(\\'encarregado\\',\\'mes\\', this)">Mês</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'encarregado\\',\\'todos\\', this)">Todos</button>'
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
        '<button class="mini-pill" onclick="mostrarRanking(\\'assunto\\',\\'dia\\', this)">Hoje</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'assunto\\',\\'semana\\', this)">Semana</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'assunto\\',\\'proxsemana\\', this)">Próx. Semana</button>'
        '<button class="mini-pill active" onclick="mostrarRanking(\\'assunto\\',\\'mes\\', this)">Mês</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'assunto\\',\\'todos\\', this)">Todos</button>'
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
        '<button class="mini-pill" onclick="mostrarRanking(\\'tipo\\',\\'dia\\', this)">Hoje</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'tipo\\',\\'semana\\', this)">Semana</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'tipo\\',\\'proxsemana\\', this)">Próx. Semana</button>'
        '<button class="mini-pill active" onclick="mostrarRanking(\\'tipo\\',\\'mes\\', this)">Mês</button>'
        '<button class="mini-pill" onclick="mostrarRanking(\\'tipo\\',\\'todos\\', this)">Todos</button>'
        '</div>'
        '</div>'
        '<div class="rank-panel" id="rank-tipo-dia">' + ranking_tipo_dia + '</div>'
        '<div class="rank-panel" id="rank-tipo-semana">' + ranking_tipo_semana + '</div>'
        '<div class="rank-panel" id="rank-tipo-proxsemana">' + ranking_tipo_prox_semana + '</div>'
        '<div class="rank-panel active" id="rank-tipo-mes">' + ranking_tipo_mes + '</div>'
        '<div class="rank-panel" id="rank-tipo-todos">' + ranking_tipo_todos + '</div>'
        '</div>'
        '</div>' '''.rstrip()

substituicoes.append((antigo_html, novo_html))

nao_encontradas = []
for antigo, novo in substituicoes:
    if antigo in conteudo:
        conteudo = conteudo.replace(antigo, novo)
    else:
        nao_encontradas.append(antigo[:60])

with open("gerar_dashboard_prazos_v11.py", "w", encoding="utf-8") as f:
    f.write(conteudo)

print("Arquivo v11 criado com sucesso!")
if nao_encontradas:
    print("ATENCAO - blocos nao encontrados:")
    for n in nao_encontradas:
        print("  - " + n)
