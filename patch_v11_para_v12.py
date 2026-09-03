# -*- coding: utf-8 -*-
import re

with open("gerar_dashboard_prazos_v11.py", "r", encoding="utf-8") as f:
    conteudo = f.read()

substituicoes = []

# 1) gerar_linhas_tabela: adicionar parametros de periodo e data-periodos por linha
antigo_1 = '''def gerar_linhas_tabela(registros):
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
        linhas.append(
            '<tr data-status="' + cat + '" data-area="' + area + '" data-encarregado="' + html.escape(encarregado.lower()) + '">'
            '<td class="pasta-cell"><span class="pasta-texto">' + html.escape(pasta) + '</span>'
            '<button type="button" class="btn-copiar" data-pasta="' + html.escape(pasta) + '" onclick="copiarPasta(this)" title="Copiar numero do processo">&#128203;</button></td>'
            '<td>' + html.escape(campo(r, "processo.adverso.nome") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "prazo_do_encarregado") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "data") or "N/A") + '</td>'
            '<td>' + html.escape(encarregado) + '</td>'
            '<td>' + html.escape(assunto_exibir) + span_oculto + '</td>'
            '<td><select class="status-select status-' + cat + '" data-original="' + cat + '" onchange="mudarStatus(this)">' + opcoes_status_select(cat) + '</select></td>'
            '</tr>'
        )
    return "".join(linhas)'''

novo_1 = '''def gerar_linhas_tabela(registros, hoje, semana_inicio, semana_fim, prox_semana_inicio, prox_semana_fim, mes_inicio, mes_fim):
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
        if d:
            if d == hoje:
                periodos_row.append("dia")
            if semana_inicio <= d <= semana_fim:
                periodos_row.append("semana")
            if prox_semana_inicio <= d <= prox_semana_fim:
                periodos_row.append("proxsemana")
            if mes_inicio <= d <= mes_fim:
                periodos_row.append("mes")
        periodos_attr = " ".join(periodos_row)

        linhas.append(
            '<tr data-status="' + cat + '" data-area="' + area + '" data-encarregado="' + html.escape(encarregado.lower()) + '" data-periodos="' + periodos_attr + '">'
            '<td class="pasta-cell"><span class="pasta-texto">' + html.escape(pasta) + '</span>'
            '<button type="button" class="btn-copiar" data-pasta="' + html.escape(pasta) + '" onclick="copiarPasta(this)" title="Copiar numero do processo">&#128203;</button></td>'
            '<td>' + html.escape(campo(r, "processo.adverso.nome") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "prazo_do_encarregado") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "data") or "N/A") + '</td>'
            '<td>' + html.escape(encarregado) + '</td>'
            '<td>' + html.escape(assunto_exibir) + span_oculto + '</td>'
            '<td><select class="status-select status-' + cat + '" data-original="' + cat + '" onchange="mudarStatus(this)">' + opcoes_status_select(cat) + '</select></td>'
            '</tr>'
        )
    return "".join(linhas)'''

substituicoes.append((antigo_1, novo_1))

# 2) chamada de gerar_linhas_tabela: passar as janelas de periodo
substituicoes.append((
    'linhas_tabela = gerar_linhas_tabela(registros)',
    'linhas_tabela = gerar_linhas_tabela(registros, hoje, semana_inicio, semana_fim, prox_semana_inicio, prox_semana_fim, mes_inicio, mes_fim)'
))

# 3) gerar_ranking_barras: adicionar parametro grupo
antigo_3 = '''def gerar_ranking_barras(contador, cor_classe, limite=10, truncar=False, clicavel=False):
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
        atributos = ' data-termo="' + html.escape(nome) + '" onclick="filtrarPorTermo(this)"' if clicavel else ""
        linhas.append(
            '<div class="rank-row' + classe_extra + '"' + atributos + '>'
            '<div class="rank-nome" title="' + html.escape(nome) + '">' + html.escape(nome_exibir) + '</div>'
            '<div class="rank-bar-bg"><div class="rank-bar ' + cor_classe + '" style="width:' + str(largura) + '%"></div></div>'
            '<div class="rank-qtd">' + str(qtd) + '</div>'
            '</div>'
        )
    return "".join(linhas)'''

novo_3 = '''def gerar_ranking_barras(contador, cor_classe, limite=10, truncar=False, clicavel=False, grupo=""):
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
    return "".join(linhas)'''

substituicoes.append((antigo_3, novo_3))

# 4) chamadas dos rankings: ativar clicavel+grupo no encarregado tambem, e grupo nos demais
antigo_4 = '''    ranking_dia = gerar_ranking_barras(enc_dia, "bar-azul", truncar=True)
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

novo_4 = '''    ranking_dia = gerar_ranking_barras(enc_dia, "bar-azul", truncar=True, clicavel=True, grupo="encarregado")
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
    ranking_tipo_todos = gerar_ranking_barras(tipo_atividade_counter, "bar-dourado", limite=8, clicavel=True, grupo="tipo")'''

substituicoes.append((antigo_4, novo_4))

# 5) CSS: adicionar periodo-pill e tabela com scroll proprio
substituicoes.append((
    '        ".table-wrapper{overflow-x:auto;}"',
    '        ".periodo-pill{background:#f3f1ea;color:#4b5563;border:1.5px solid #e2ddc9;padding:8px 14px;border-radius:999px;font-weight:700;font-size:12.5px;cursor:pointer;transition:.15s;}"\n'
    '        ".periodo-pill:hover{border-color:#233240;}"\n'
    '        ".periodo-pill.active{background:#6b7f66;color:#fff;border-color:#6b7f66;}"\n'
    '        ".table-wrapper{overflow:auto;max-height:620px;border:1px solid #e2ddc9;border-radius:10px;}"\n'
    '        "th{position:sticky;top:0;z-index:2;}"'
))

# 6) HTML: adicionar grupo de filtro global de periodo na barra de filtros
substituicoes.append((
    '''        '<div class="busca-inline"><input type="text" id="busca" placeholder="Buscar por processo, adverso, assunto..."></div>' ''' .rstrip(),
    '''        '<div class="filtro-grupo">'
        '<span class="filtro-titulo">Per\u00edodo</span>'
        '<button class="periodo-pill active" data-periodo="todos" onclick="filtrarPeriodo(\\'todos\\', this)">Todos</button>'
        '<button class="periodo-pill" data-periodo="dia" onclick="filtrarPeriodo(\\'dia\\', this)">Hoje</button>'
        '<button class="periodo-pill" data-periodo="semana" onclick="filtrarPeriodo(\\'semana\\', this)">Semana</button>'
        '<button class="periodo-pill" data-periodo="proxsemana" onclick="filtrarPeriodo(\\'proxsemana\\', this)">Pr\u00f3x. Semana</button>'
        '<button class="periodo-pill" data-periodo="mes" onclick="filtrarPeriodo(\\'mes\\', this)">M\u00eas</button>'
        '</div>'
        '<div class="busca-inline"><input type="text" id="busca" placeholder="Buscar por processo, adverso, assunto..."></div>' '''.rstrip()
))

# 7) JS: adicionar periodoAtivo + filtrarPeriodo
substituicoes.append((
    '''"var statusAtivo='todos';"
        "var areaAtiva='todos';"''',
    '''"var statusAtivo='todos';"
        "var areaAtiva='todos';"
        "var periodoAtivo='todos';"
        "function filtrarPeriodo(periodo,botao){"
        "periodoAtivo=periodo;"
        "document.querySelectorAll('.periodo-pill').forEach(function(el){el.classList.remove('active');});"
        "botao.classList.add('active');"
        "aplicarFiltros();}"'''
))

# 8) JS: aplicarFiltros com checagem de periodo
antigo_8 = '''"function aplicarFiltros(){"
        "var termo=document.getElementById('busca').value.toLowerCase();"
        "var encarregadoSel=document.getElementById('encarregadoSelect').value;"
        "var visiveis=0;"
        "document.querySelectorAll('#tabelaBody tr').forEach(function(linha){"
        "var texto=linha.textContent.toLowerCase();"
        "var statusLinha=linha.getAttribute('data-status');"
        "var areaLinha=linha.getAttribute('data-area');"
        "var encarregadoLinha=linha.getAttribute('data-encarregado');"
        "var passaTexto=texto.includes(termo);"
        "var passaStatus=(statusAtivo==='todos')||(statusLinha===statusAtivo);"
        "var passaArea=(areaAtiva==='todos')||(areaLinha===areaAtiva);"
        "var passaEncarregado=(encarregadoSel==='')||(encarregadoLinha===encarregadoSel);"
        "var visivel=passaTexto&&passaStatus&&passaArea&&passaEncarregado;"
        "linha.classList.toggle('oculto',!visivel);"
        "if(visivel)visiveis++;});"
        "document.getElementById('contagemVisivel').textContent=visiveis+' registro(s) exibido(s)';}"'''

novo_8 = '''"function aplicarFiltros(){"
        "var termo=document.getElementById('busca').value.toLowerCase();"
        "var encarregadoSel=document.getElementById('encarregadoSelect').value;"
        "var visiveis=0;"
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
        "var visivel=passaTexto&&passaStatus&&passaArea&&passaEncarregado&&passaPeriodo;"
        "linha.classList.toggle('oculto',!visivel);"
        "if(visivel)visiveis++;});"
        "document.getElementById('contagemVisivel').textContent=visiveis+' registro(s) exibido(s)';}"'''

substituicoes.append((antigo_8, novo_8))

# 9) JS: reescrever filtrarPorTermo
antigo_9 = '''"function filtrarPorTermo(elemento){"
        "var termo=elemento.getAttribute('data-termo');"
        "document.getElementById('busca').value=termo;"
        "statusAtivo='todos';"
        "areaAtiva='todos';"
        "document.querySelectorAll('.pill[data-status]').forEach(function(el){el.classList.remove('active');});"
        "document.querySelector('.pill[data-status=\\"todos\\"]').classList.add('active');"
        "document.querySelectorAll('.pill-area').forEach(function(el){el.classList.remove('active');});"
        "document.querySelector('.pill-area').classList.add('active');"
        "document.getElementById('encarregadoSelect').value='';"
        "aplicarFiltros();"
        "document.querySelector('.tabela-card').scrollIntoView({behavior:'smooth',block:'start'});"
        "}"'''

novo_9 = '''"function filtrarPorTermo(elemento){"
        "var termo=elemento.getAttribute('data-termo');"
        "var grupo=elemento.getAttribute('data-grupo');"
        "var painel=elemento.closest('.painel');"
        "var pillAtivo=painel.querySelector('.mini-pill.active');"
        "var periodoDoPainel=pillAtivo?pillAtivo.getAttribute('data-periodo'):'todos';"
        "statusAtivo='todos';"
        "areaAtiva='todos';"
        "periodoAtivo=periodoDoPainel;"
        "document.querySelectorAll('.pill[data-status]').forEach(function(el){el.classList.remove('active');});"
        "document.querySelector('.pill[data-status=\\"todos\\"]').classList.add('active');"
        "document.querySelectorAll('.pill-area').forEach(function(el){el.classList.remove('active');});"
        "document.querySelector('.pill-area').classList.add('active');"
        "document.querySelectorAll('.periodo-pill').forEach(function(el){el.classList.remove('active');});"
        "var periodoPillGlobal=document.querySelector('.periodo-pill[data-periodo=\\"'+periodoDoPainel+'\\"]');"
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
        "}"'''

substituicoes.append((antigo_9, novo_9))

nao_encontradas = []
for antigo, novo in substituicoes:
    if antigo in conteudo:
        conteudo = conteudo.replace(antigo, novo)
    else:
        nao_encontradas.append(antigo[:60])

# 10) adicionar data-periodo="X" em cada botao mini-pill (via regex, ja que o texto do botao varia por grupo)
pattern = re.compile(
    r"(<button class=\"mini-pill[^\"]*\" onclick=\"mostrarRanking\(\\'(\w+)\\',\\'(\w+)\\', this\)\">)"
)

def replacer(m):
    tag_completa = m.group(1)
    periodo = m.group(3)
    return tag_completa.replace(
        'onclick="mostrarRanking',
        'data-periodo="' + periodo + '" onclick="mostrarRanking'
    )

conteudo, n_pills = pattern.subn(replacer, conteudo)

with open("gerar_dashboard_prazos_v12.py", "w", encoding="utf-8") as f:
    f.write(conteudo)

print("Arquivo v12 criado com sucesso!")
print("Botoes mini-pill com data-periodo adicionados: " + str(n_pills) + " (esperado: 15)")
if nao_encontradas:
    print("ATENCAO - blocos nao encontrados:")
    for n in nao_encontradas:
        print("  - " + n)
