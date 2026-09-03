# -*- coding: utf-8 -*-
import csv, html, os, sys, requests, re
from collections import Counter
from datetime import datetime

BASE_URL = "https://api.datajuri.com.br/v1"
AUTH_URL = "https://api.datajuri.com.br/oauth/token"

BASIC_AUTH = os.getenv("DATAJURI_BASIC_AUTH", "")
USERNAME = os.getenv("DATAJURI_USERNAME", "")
PASSWORD = os.getenv("DATAJURI_PASSWORD", "")

ARQUIVO_CSV_SAIDA = "contingencia_civel_api.csv"
ARQUIVO_HTML_SAIDA = "dashboard_contingencia_civel_api.html"
ARQUIVO_BASE_BRUTA = "base_processada_debug.csv"

def eh_processo_judicial(pasta):
    """Valida se é um número de processo judicial CNJ completo"""
    if not pasta:
        return False
    padrao = r'^\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}$'
    return bool(re.match(padrao, pasta.strip()))

def obter_token():
    if not BASIC_AUTH or not USERNAME or not PASSWORD:
        print("ERRO: credenciais incompletas.")
        sys.exit(1)
    headers = {"Authorization": f"Basic {BASIC_AUTH}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=120)
    if resp.status_code != 200:
        sys.exit(1)
    return resp.json().get("access_token")

def eh_status_ativo(status):
    """Verifica se status é ativo"""
    status_lower = (status or "").strip().lower()
    # Exclui esses status
    excluir = ["guardando", "finalizado", "arquivado", "encerrado", "extinto", "cancelado", "baixado"]
    return not any(ex in status_lower for ex in excluir)

def extrair_processos(token):
    headers = {"Authorization": f"Bearer {token}"}
    campos = "id,pasta,cliente.nome,adverso.nome,advogadoCliente.nome,advogadoAdverso.nome,faseAtual.instancia,natureza,assunto,status"
    page, todos_registros, processos_unicos = 0, [], set()
    base_bruta = []
    
    print("Extraindo processos judiciais...")
    while True:
        params = {"campos": campos, "page": page, "pageSize": 100}
        resp = requests.get(BASE_URL + "/entidades/Processo", headers=headers, params=params, timeout=120)
        if resp.status_code != 200:
            break
        data = resp.json()
        linhas = data.get("rows", [])
        if not linhas:
            break
        for reg in linhas:
            pasta = reg.get("pasta", "")
            base_bruta.append(reg)
            
            # Validar se é processo judicial CNJ
            if not eh_processo_judicial(pasta):
                continue
            
            if pasta not in processos_unicos:
                natureza = (reg.get("natureza") or "").strip().lower()
                status = (reg.get("status") or "").strip().lower()
                instancia = (reg.get("faseAtual.instancia") or "").strip().lower()
                assunto = (reg.get("assunto") or "").strip().lower()
                
                # FILTROS RIGOROSOS
                # 1. Apenas Primeira Instância
                if "primeira" not in instancia:
                    continue
                
                # 2. Apenas status ativo
                if not eh_status_ativo(status):
                    continue
                
                # 3. Excluda incidentes
                if "incidente" in assunto or "cumprimento de sentença" in assunto:
                    continue
                
                # 4. Apenas contingência
                if "cível" not in natureza and "civil" not in natureza and "tributário" not in natureza and "trabalhista" not in natureza:
                    continue
                
                todos_registros.append(reg)
                processos_unicos.add(pasta)
        
        print(f"  Página {page}: {len(linhas)} totais | Válidos: {len(processos_unicos)}")
        page += 1
        if len(linhas) < 100:
            break
    
    print(f"✅ {len(todos_registros)} processos válidos\n")
    
    # Salva base bruta para debug
    salvar_base_bruta(base_bruta, ARQUIVO_BASE_BRUTA)
    
    return todos_registros

def salvar_base_bruta(registros, arquivo):
    """Salva a base completa para debug"""
    if not registros:
        return
    campos = ["pasta", "cliente.nome", "adverso.nome", "faseAtual.instancia", "status", "natureza", "assunto"]
    with open(arquivo, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for reg in registros:
            writer.writerow({k: reg.get(k, "") for k in campos})
    print(f"✅ Base bruta salva em: {arquivo}\n")

def normalizar_registro(reg):
    return {
        "Processo": reg.get("pasta", ""),
        "Cliente": reg.get("cliente.nome", ""),
        "Adverso": reg.get("adverso.nome", ""),
        "Instância": reg.get("faseAtual.instancia", ""),
        "Advogado": reg.get("advogadoCliente.nome", ""),
        "Advogado Adverso": reg.get("advogadoAdverso.nome", ""),
        "Assunto": reg.get("assunto", ""),
        "Natureza": reg.get("natureza", ""),
        "Status": reg.get("status", ""),
    }

def salvar_csv(registros, arquivo):
    if not registros:
        return
    campos = ["Processo", "Cliente", "Adverso", "Instância", "Advogado", "Advogado Adverso", "Assunto", "Natureza", "Status"]
    with open(arquivo, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(registros)
    print(f"✅ CSV: {arquivo}\n")

def gerar_linhas_tabela(registros):
    linhas = []
    for r in registros:
        processo = r.get("Processo") or "N/A"
        natureza = (r.get("Natureza") or "").strip().lower()
        status = (r.get("Status") or "").strip().lower()
        aguardando_citacao = "sim" if "aguardando citação" in status or "aguardando citatao" in status else "nao"
        natureza_class = "civel" if ("cível" in natureza or "civil" in natureza) else "trabalhista" if "trabalhista" in natureza else "tributario"
        linhas.append(
            '<tr data-assunto="' + html.escape(str(r.get("Assunto") or "")).lower() + '" data-instancia="' + html.escape(str(r.get("Instância") or "")).lower() + '" data-advogado="' + html.escape(str(r.get("Advogado") or "")).lower() + '" data-advogado-adverso="' + html.escape(str(r.get("Advogado Adverso") or "")).lower() + '" data-natureza="' + natureza_class + '" data-citacao="' + aguardando_citacao + '">'
            '<td class="pasta-cell"><span>' + html.escape(str(processo)) + '</span><button class="btn-copiar" data-pasta="' + html.escape(str(processo)) + '" onclick="copiarPasta(this)">📋</button></td>'
            '<td>' + html.escape(str(r.get("Cliente") or "N/A")) + '</td>'
            '<td>' + html.escape(str(r.get("Adverso") or "N/A")) + '</td>'
            '<td>' + html.escape(str(r.get("Instância") or "N/A")) + '</td>'
            '<td>' + html.escape(str(r.get("Advogado") or "N/A")) + '</td>'
            '<td>' + html.escape(str(r.get("Advogado Adverso") or "N/A")) + '</td>'
            '<td class="assunto-cell">' + html.escape(str(r.get("Assunto") or "N/A")) + '</td></tr>'
        )
    return "".join(linhas)

def gerar_ranking_barras(contador, cor_classe, limite=8, tipo=""):
    itens = contador.most_common(limite)
    if not itens:
        return '<p class="sem-dados">Sem registros</p>'
    maximo = itens[0][1]
    linhas = []
    for nome, qtd in itens:
        largura = int((qtd / maximo) * 100) if maximo else 0
        nome_curto = nome if len(nome) <= 22 else nome[:19] + "..."
        linhas.append(
            '<div class="rank-row" onclick="filtrarPor(\'' + tipo + '\', \'' + html.escape(nome).replace("'", "\\'") + '\')" style="cursor:pointer;">'
            '<div class="rank-nome" title="' + html.escape(nome) + '">' + html.escape(nome_curto) + '</div>'
            '<div class="rank-bar-bg"><div class="rank-bar ' + cor_classe + '" style="width:' + str(largura) + '%"></div></div>'
            '<div class="rank-qtd">' + str(qtd) + '</div></div>'
        )
    return "".join(linhas)

def gerar_html(registros):
    total = len(registros)
    data_hoje = datetime.now().strftime("%d/%m/%Y")

    civel = sum(1 for r in registros if "cível" in (r.get("Natureza") or "").lower() or "civil" in (r.get("Natureza") or "").lower())
    trabalhista = sum(1 for r in registros if "trabalhista" in (r.get("Natureza") or "").lower())
    tributario = sum(1 for r in registros if "tributário" in (r.get("Natureza") or "").lower())
    aguardando_citacao = sum(1 for r in registros if "aguardando citação" in (r.get("Status") or "").lower() or "aguardando citatao" in (r.get("Status") or "").lower())
    sem_citacao = total - aguardando_citacao

    assunto_counter = Counter()
    fase_counter = Counter()
    advogado_counter = Counter()
    advogado_adverso_counter = Counter()

    for r in registros:
        if r.get("Assunto"):
            assunto_counter[str(r["Assunto"])] += 1
        if r.get("Instância"):
            fase_counter[str(r["Instância"])] += 1
        if r.get("Advogado"):
            advogado_counter[str(r["Advogado"])] += 1
        if r.get("Advogado Adverso"):
            advogado_adverso_counter[str(r["Advogado Adverso"])] += 1

    ranking_assuntos = gerar_ranking_barras(assunto_counter, "bar-azul", tipo="assunto")
    ranking_fase = gerar_ranking_barras(fase_counter, "bar-vermelho", tipo="instancia")
    ranking_advogado = gerar_ranking_barras(advogado_counter, "bar-dourado", tipo="advogado")
    ranking_advogado_adverso = gerar_ranking_barras(advogado_adverso_counter, "bar-cinza", tipo="advogado-adverso")
    linhas_tabela = gerar_linhas_tabela(registros)

    css = "* { margin: 0; padding: 0; box-sizing: border-box; } body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f9f7f2; color: #374151; } .header { background: linear-gradient(135deg, #233240 0%, #4a6c86 100%); color: white; padding: 32px 24px; display: flex; justify-content: space-between; align-items: center; gap: 20px; } .logo-texto { font-size: 13px; font-weight: 900; text-transform: uppercase; } .logo-sub { font-size: 9px; opacity: 0.85; } .logo-mark { display: flex; gap: 4px; } .logo-navy { width: 8px; height: 20px; background: white; border-radius: 2px; } .logo-flag { display: flex; gap: 3px; } .logo-arrow-white { width: 3px; height: 20px; background: white; } .logo-arrow-gold { width: 3px; height: 20px; background: #c9a545; } .header-center { flex: 1; } .kicker { font-size: 10px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; margin-bottom: 6px; } .header-center h1 { font-size: 28px; font-weight: 900; } .sub { font-size: 12px; opacity: 0.85; } .header-right { text-align: center; font-size: 28px; font-weight: 900; } .header-right .lbl { font-size: 10px; text-transform: uppercase; opacity: 0.85; margin-top: 4px; } .container { max-width: 1400px; margin: 24px auto; padding: 0 24px; } .filtros-bar { background: white; border: 1px solid #e2ddc9; border-radius: 12px; padding: 16px 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; gap: 20px; } .busca-inline { flex: 1; } .busca-inline input { width: 100%; padding: 8px 12px; border: 1px solid #e2ddc9; border-radius: 6px; font-size: 12px; } .btn-limpar { background: #f3f1ea; border: 1px solid #e2ddc9; color: #8a8471; padding: 8px 16px; border-radius: 6px; font-size: 11px; font-weight: 600; cursor: pointer; } .btn-limpar:hover { background: #ede8dd; } .btn-limpar:disabled { opacity: 0.5; cursor: not-allowed; } .stats-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1fr; gap: 16px; margin-bottom: 24px; } @media (max-width:1200px) { .stats-grid { grid-template-columns: 1fr 1fr 1fr; } } .stat-card { background: white; border-left: 4px solid; border-radius: 12px; padding: 12px 16px; cursor: pointer; transition: background .2s; } .stat-card:hover { background: #faf9f5; } .stat-card .lbl { font-size: 9px; color: #8a8471; font-weight: 800; text-transform: uppercase; margin-bottom: 4px; } .stat-card .num { font-size: 22px; font-weight: 900; color: #233240; } .stat-card .desc { font-size: 10px; color: #9ca3af; } .stat-total { border-left-color: #233240; } .stat-civel { border-left-color: #6b7f66; } .stat-trabalhista { border-left-color: #9c3b3b; } .stat-tributario { border-left-color: #b8860b; } .stat-citacao { border-left-color: #8b5a8b; } .stat-sem-citacao { border-left-color: #228b22; } .paineis-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px; margin-bottom: 24px; } @media (max-width:1400px) { .paineis-grid { grid-template-columns: 1fr 1fr; } } .painel { background: white; border: 1px solid #e2ddc9; border-radius: 12px; padding: 14px; } .painel-header { display: flex; gap: 6px; margin-bottom: 12px; align-items: center; } .painel-bar { width: 3px; height: 12px; background: #9c3b3b; border-radius: 1px; } .painel h3 { font-size: 11px; color: #233240; font-weight: 900; text-transform: uppercase; } .rank-row { display: grid; grid-template-columns: 90px 1fr auto; gap: 6px; margin-bottom: 8px; font-size: 10px; align-items: center; padding: 6px; border-radius: 4px; transition: background .2s; cursor: pointer; } .rank-row:hover { background: #faf9f5; } .rank-nome { color: #374151; white-space: normal; word-wrap: break-word; font-weight: 600; font-size: 10px; line-height: 1.2; } .rank-bar-bg { background: #f3f1ea; border-radius: 4px; height: 8px; } .rank-bar { height: 100%; border-radius: 4px; } .bar-azul { background: linear-gradient(90deg, #233240, #4a6c86); } .bar-vermelho { background: linear-gradient(90deg, #9c3b3b, #c17b7b); } .bar-dourado { background: linear-gradient(90deg, #8a660a, #c9a545); } .bar-cinza { background: linear-gradient(90deg, #6b7f66, #8a9a7e); } .rank-qtd { color: #233240; font-weight: 800; text-align: right; min-width: 25px; font-size: 10px; } .tabela-card { background: white; border: 1px solid #e2ddc9; border-radius: 12px; padding: 20px; margin-bottom: 20px; } .tabela-card h3 { font-size: 13px; color: #233240; font-weight: 900; text-transform: uppercase; margin-bottom: 12px; } .contagem { font-size: 11px; color: #8a8471; font-weight: 700; margin-bottom: 12px; } table { width: 100%; border-collapse: collapse; } th { background: #faf9f5; padding: 8px; text-align: left; font-size: 9px; font-weight: 800; color: #8a8471; text-transform: uppercase; border-bottom: 2px solid #e2ddc9; white-space: nowrap; position: sticky; top: 0; z-index: 2; } td { padding: 8px; border-bottom: 1px solid #f3f1ea; font-size: 11px; } .assunto-cell { min-width: 250px; } tr:hover { background: #faf9f5; } .pasta-cell { color: #233240; font-weight: 800; display: flex; align-items: center; gap: 6px; white-space: nowrap; } .btn-copiar { background: transparent; border: none; cursor: pointer; font-size: 11px; padding: 2px 4px; border-radius: 4px; opacity: 0.55; transition: .15s; } .btn-copiar:hover { opacity: 1; background: #f3f1ea; } .btn-copiar.copiado { opacity: 1; color: #16a34a; } .oculto { display: none !important; } .table-wrapper { overflow: auto; max-height: 700px; border: 1px solid #e2ddc9; border-radius: 10px; }"

    js = "var filtroAtivo = {}; function aplicarFiltros(){var termo=document.getElementById('busca').value.toLowerCase();var visiveis=0;document.querySelectorAll('#tabelaBody tr').forEach(function(linha){var texto=linha.textContent.toLowerCase();var passa=texto.includes(termo);var attrs=['assunto','instancia','advogado','advogado-adverso','natureza','citacao'];attrs.forEach(function(attr){if(filtroAtivo[attr]){var valor=linha.getAttribute('data-'+attr)||'';if(valor.toLowerCase()!==filtroAtivo[attr].toLowerCase()){passa=false;}}});linha.classList.toggle('oculto',!passa);if(!passa)return;visiveis++;});document.getElementById('contagemVisivel').textContent=visiveis+' de '+"+str(total)+"+'processo(s)';document.getElementById('btnLimpar').disabled=Object.keys(filtroAtivo).length===0;}function filtrarPor(tipo,valor){filtroAtivo[tipo]=valor;aplicarFiltros();document.querySelector('.table-wrapper').scrollIntoView({behavior:'smooth'});}function filtrarCitacao(valor){filtroAtivo['citacao']=valor;aplicarFiltros();document.querySelector('.table-wrapper').scrollIntoView({behavior:'smooth'});}function limparFiltros(){filtroAtivo={};document.getElementById('busca').value='';aplicarFiltros();}document.getElementById('busca').addEventListener('input',aplicarFiltros);aplicarFiltros();function copiarPasta(botao){var pasta=botao.getAttribute('data-pasta');navigator.clipboard.writeText(pasta).then(function(){botao.innerHTML='✓';botao.classList.add('copiado');setTimeout(function(){botao.innerHTML='📋';botao.classList.remove('copiado');},1500);});}"

    corpo = '<div class="header"><div><div class="logo-texto"><span>PACAEMBU</span><span class="logo-sub">CONSTRUTORA</span></div><div class="logo-mark"><div class="logo-navy"></div><div class="logo-flag"><div class="logo-arrow-white"></div><div class="logo-arrow-gold"></div></div></div></div><div class="header-center"><div class="kicker">JURÍDICO · CONTINGÊNCIA</div><h1>DASHBOARD DE CONTINGÊNCIA</h1><div class="sub">Processos judiciais ativos (Primeira Instância)</div></div><div class="header-right"><div>'+str(total)+'</div><div class="lbl">TOTAL</div><div>'+data_hoje+'</div></div></div><div class="container"><div class="filtros-bar"><div class="busca-inline"><input type="text" id="busca" placeholder="Buscar..."></div><button id="btnLimpar" class="btn-limpar" onclick="limparFiltros()" disabled>Limpar Filtros</button></div><div class="stats-grid"><div class="stat-card stat-total"><div class="lbl">Total</div><div class="num">'+str(total)+'</div></div><div class="stat-card stat-civel" onclick="filtrarPor(\'natureza\', \'civel\')"><div class="lbl">Cível</div><div class="num">'+str(civel)+'</div></div><div class="stat-card stat-trabalhista" onclick="filtrarPor(\'natureza\', \'trabalhista\')"><div class="lbl">Trabalhista</div><div class="num">'+str(trabalhista)+'</div></div><div class="stat-card stat-tributario" onclick="filtrarPor(\'natureza\', \'tributario\')"><div class="lbl">Tributário</div><div class="num">'+str(tributario)+'</div></div><div class="stat-card stat-citacao" onclick="filtrarCitacao(\'sim\')"><div class="lbl">Aguardando Citação</div><div class="num">'+str(aguardando_citacao)+'</div></div><div class="stat-card stat-sem-citacao" onclick="filtrarCitacao(\'nao\')"><div class="lbl">Sem Citação</div><div class="num">'+str(sem_citacao)+'</div></div></div><div class="paineis-grid"><div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Assuntos</h3></div>'+ranking_assuntos+'</div><div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Instâncias</h3></div>'+ranking_fase+'</div><div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Advogados</h3></div>'+ranking_advogado+'</div><div class="painel"><div class="painel-header"><div class="painel-bar"></div><h3>Adv. Adversos</h3></div>'+ranking_advogado_adverso+'</div></div><div class="tabela-card"><h3>Processos Judiciais Ativos</h3><div class="contagem" id="contagemVisivel"></div><div class="table-wrapper"><table><thead><tr><th>Processo</th><th>Cliente</th><th>Adverso</th><th>Instância</th><th>Advogado</th><th>Adv. Adverso</th><th>Assunto</th></tr></thead><tbody id="tabelaBody">'+linhas_tabela+'</tbody></table></div></div></div>'

    return '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Contingência - Pacaembu</title><style>'+css+'</style></head><body>'+corpo+'<script>'+js+'</script></body></html>'

if __name__ == "__main__":
    token = obter_token()
    print("=" * 70)
    registros_brutos = extrair_processos(token)
    registros_normalizados = [normalizar_registro(r) for r in registros_brutos]
    salvar_csv(registros_normalizados, ARQUIVO_CSV_SAIDA)
    print("=" * 70)
    print("GERANDO DASHBOARD")
    html_resultado = gerar_html(registros_normalizados)
    with open(ARQUIVO_HTML_SAIDA, "w", encoding="utf-8") as f:
        f.write(html_resultado)
    print(f"✅ {ARQUIVO_HTML_SAIDA}\n")
