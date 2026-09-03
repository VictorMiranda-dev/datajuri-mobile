# -*- coding: utf-8 -*-
with open("gerar_dashboard_prazos_v9.py", "r", encoding="utf-8") as f:
    conteudo = f.read()

substituicoes = []

# 1) gerar_linhas_tabela: adicionar botao de copiar e campo oculto de busca
antigo_tabela = '''def gerar_linhas_tabela(registros):
    linhas = []
    for r in registros:
        cat = categoria_status(campo(r, "status"))
        area = categoria_area(campo(r, "processo.natureza"))
        encarregado = campo(r, "encarregado.nome") or "N/A"
        linhas.append(
            '<tr data-status="' + cat + '" data-area="' + area + '" data-encarregado="' + html.escape(encarregado.lower()) + '">'
            '<td class="pasta-cell">' + html.escape(campo(r, "processo.pasta") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "processo.adverso.nome") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "prazo_do_encarregado") or "N/A") + '</td>'
            '<td>' + html.escape(campo(r, "data") or "N/A") + '</td>'
            '<td>' + html.escape(encarregado) + '</td>'
            '<td>' + html.escape(campo(r, "assunto") or campo(r, "tipoAtividade") or "N/A") + '</td>'
            '<td><select class="status-select status-' + cat + '" data-original="' + cat + '" onchange="mudarStatus(this)">' + opcoes_status_select(cat) + '</select></td>'
            '</tr>'
        )
    return "".join(linhas)'''

novo_tabela = '''def gerar_linhas_tabela(registros):
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

substituicoes.append((antigo_tabela, novo_tabela))

# 2) gerar_ranking_barras: adicionar parametro clicavel
antigo_ranking = '''def gerar_ranking_barras(contador, cor_classe, limite=10, truncar=False):
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
        linhas.append(
            '<div class="rank-row">'
            '<div class="rank-nome" title="' + html.escape(nome) + '">' + html.escape(nome_exibir) + '</div>'
            '<div class="rank-bar-bg"><div class="rank-bar ' + cor_classe + '" style="width:' + str(largura) + '%"></div></div>'
            '<div class="rank-qtd">' + str(qtd) + '</div>'
            '</div>'
        )
    return "".join(linhas)'''

novo_ranking = '''def gerar_ranking_barras(contador, cor_classe, limite=10, truncar=False, clicavel=False):
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

substituicoes.append((antigo_ranking, novo_ranking))

# 3) Ativar clicavel=True nos rankings de assuntos e tipo de atividade
substituicoes.append((
    'ranking_assuntos = gerar_ranking_barras(assunto_counter, "bar-vermelho", limite=8, truncar=False)\n    ranking_tipo_atividade = gerar_ranking_barras(tipo_atividade_counter, "bar-dourado", limite=8, truncar=False)',
    'ranking_assuntos = gerar_ranking_barras(assunto_counter, "bar-vermelho", limite=8, truncar=False, clicavel=True)\n    ranking_tipo_atividade = gerar_ranking_barras(tipo_atividade_counter, "bar-dourado", limite=8, truncar=False, clicavel=True)'
))

# 4) CSS: adicionar estilos do botao copiar e rank-row clicavel
substituicoes.append((
    '        ".oculto{display:none!important;}"\n        ".table-wrapper{overflow-x:auto;}"',
    '        ".oculto{display:none!important;}"\n        ".oculto-busca{display:none;}"\n        ".table-wrapper{overflow-x:auto;}"\n        ".pasta-cell{display:flex;align-items:center;gap:8px;}"\n        ".btn-copiar{background:transparent;border:none;cursor:pointer;font-size:13px;padding:3px 5px;border-radius:5px;opacity:0.55;transition:.15s;}"\n        ".btn-copiar:hover{opacity:1;background:#f3f1ea;}"\n        ".btn-copiar.copiado{opacity:1;color:#16a34a;}"\n        ".rank-row-clicavel{cursor:pointer;padding:4px;margin:-4px -4px 7px -4px;border-radius:8px;transition:.15s;}"\n        ".rank-row-clicavel:hover{background:#f3f1ea;}"'
))

# 5) JS: adicionar filtrarPorTermo e copiarPasta apos atualizarContadorAlteracoes
antigo_js_fim = '''"botao.textContent='Limpar Alterações';"
        "botao.classList.remove('tem-alteracoes');"
        "botao.disabled=true;"
        "}}"
    )'''

novo_js_fim = '''"botao.textContent='Limpar Alterações';"
        "botao.classList.remove('tem-alteracoes');"
        "botao.disabled=true;"
        "}}"
        "function filtrarPorTermo(elemento){"
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
    )'''

substituicoes.append((antigo_js_fim, novo_js_fim))

nao_encontradas = []
for antigo, novo in substituicoes:
    if antigo in conteudo:
        conteudo = conteudo.replace(antigo, novo)
    else:
        nao_encontradas.append(antigo[:60])

with open("gerar_dashboard_prazos_v10.py", "w", encoding="utf-8") as f:
    f.write(conteudo)

print("Arquivo v10 criado com sucesso!")
if nao_encontradas:
    print("ATENCAO - blocos nao encontrados (pode ter mudado algo manualmente):")
    for n in nao_encontradas:
        print("  - " + n)
