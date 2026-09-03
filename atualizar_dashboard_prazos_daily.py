import pandas as pd
import requests
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

print(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] Iniciando...")

# Carrega .zshrc
zshrc_path = os.path.expanduser('~/.zshrc')
if os.path.exists(zshrc_path):
    with open(zshrc_path, 'r') as f:
        for line in f:
            if 'DATAJURI_BASIC_AUTH=' in line:
                exec(line.strip().replace('export ', ''))
            elif 'DATAJURI_USERNAME=' in line:
                exec(line.strip().replace('export ', ''))
            elif 'DATAJURI_PASSWORD=' in line:
                exec(line.strip().replace('export ', ''))

BASIC_AUTH = os.getenv('DATAJURI_BASIC_AUTH')
USERNAME = os.getenv('DATAJURI_USERNAME')
PASSWORD = os.getenv('DATAJURI_PASSWORD')

if not all([BASIC_AUTH, USERNAME, PASSWORD]):
    print("❌ Credenciais não encontradas")
    print(f"  BASIC_AUTH: {bool(BASIC_AUTH)}")
    print(f"  USERNAME: {bool(USERNAME)}")
    print(f"  PASSWORD: {bool(PASSWORD)}")
    sys.exit(1)

AUTH_URL = "https://api.datajuri.com.br/v1/oauth/token"
API_URL = "https://api.datajuri.com.br/v1"

try:
    # Obter token
    print("🔐 Obtendo token...")
    headers_auth = {
        "Authorization": f"Basic {BASIC_AUTH}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data_auth = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
    }
    
    resp_auth = requests.post(AUTH_URL, headers=headers_auth, data=data_auth, timeout=10)
    
    if resp_auth.status_code != 200:
        print(f"❌ Erro ao obter token: {resp_auth.status_code}")
        print(f"   Resposta: {resp_auth.text}")
        sys.exit(1)
    
    token = resp_auth.json().get("access_token")
    if not token:
        print("❌ Token não obtido na resposta")
        sys.exit(1)
    
    print("✅ Token obtido")
    
    # Buscar atividades
    print("📥 Buscando atividades...")
    headers_api = {"Authorization": f"Bearer {token}"}
    
    page = 1
    atividades = []
    
    while True:
        url = f"{API_URL}/atividades?pageSize=100&page={page}"
        resp = requests.get(url, headers=headers_api, timeout=10)
        
        if resp.status_code != 200:
            print(f"⚠️  Página {page}: status {resp.status_code}")
            break
        
        linhas = resp.json().get("rows", [])
        if not linhas:
            break
        
        atividades.extend(linhas)
        print(f"  ✓ Página {page}: {len(linhas)} atividades")
        page += 1
    
    print(f"✅ Total extraído: {len(atividades)}")
    
    if not atividades:
        print("⚠️  Nenhuma atividade encontrada")
        sys.exit(0)
    
    # Processa dados
    df = pd.DataFrame(atividades)
    hoje = datetime.now()
    fim_semana = hoje + timedelta(days=(6 - hoje.weekday()))
    
    if 'dataProxima' not in df.columns:
        print("❌ Campo 'dataProxima' não encontrado")
        sys.exit(1)
    
    df['dataProxima'] = pd.to_datetime(df['dataProxima'], errors='coerce')
    df_semana = df[(df['dataProxima'] >= hoje) & (df['dataProxima'] <= fim_semana)].copy()
    df_semana = df_semana.sort_values('dataProxima')
    
    print(f"✅ Prazos da semana: {len(df_semana)}")
    
    # Gera HTML
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Prazos da Semana</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #233240; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .header h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 14px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: white; padding: 15px; border-radius: 8px; border-left: 4px solid #9c3b3b; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 28px; font-weight: bold; color: #233240; }}
        .stat-label {{ font-size: 12px; color: #666; margin-top: 5px; }}
        table {{ width: 100%; background: white; border-collapse: collapse; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        th {{ background: #233240; color: white; padding: 12px; text-align: left; font-weight: 600; }}
        td {{ padding: 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f9f9f9; }}
        .today {{ background: #FFE6E6 !important; font-weight: bold; }}
        input {{ padding: 10px; border: 1px solid #ddd; border-radius: 4px; width: 100%; margin-bottom: 20px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📅 Prazos da Semana</h1>
            <p>De {hoje.strftime('%d/%m/%Y')} a {fim_semana.strftime('%d/%m/%Y')}</p>
            <p>Atualizado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{len(df_semana)}</div>
                <div class="stat-label">Total de Atividades</div>
            </div>
        </div>
        
        <input type="text" id="busca" placeholder="🔍 Buscar por descrição, processo...">
        
        <table>
            <thead>
                <tr>
                    <th>📅 Data</th>
                    <th>📌 Descrição</th>
                    <th>📋 Processo</th>
                    <th>🏷️ Status</th>
                </tr>
            </thead>
            <tbody id="corpo">
"""
    
    for idx, row in df_semana.iterrows():
        data = row['dataProxima']
        data_str = data.strftime('%a, %d/%m') if pd.notna(data) else 'S/data'
        descricao = str(row.get('descricao', 'S/descrição'))[:60]
        processo = str(row.get('pasta', row.get('processo', 'S/processo')))
        status = str(row.get('status', 'Ativo'))
        
        classe = 'today' if data.date() == hoje.date() else ''
        
        html += f"<tr class='{classe}'><td>{data_str}</td><td>{descricao}</td><td>{processo}</td><td>{status}</td></tr>\n"
    
    html += """
            </tbody>
        </table>
    </div>
    <script>
        document.getElementById('busca').addEventListener('keyup', function(e) {
            const filtro = e.target.value.toLowerCase();
            document.querySelectorAll('#corpo tr').forEach(linha => {
                linha.style.display = linha.textContent.toLowerCase().includes(filtro) ? '' : 'none';
            });
        });
    </script>
</body>
</html>"""
    
    # Salva
    with open('dashboard_prazos_semana.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✅ Dashboard criado: dashboard_prazos_semana.html")
    
except Exception as e:
    print(f"❌ Erro: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
