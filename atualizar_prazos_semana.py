import pandas as pd
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carrega credenciais
load_dotenv(os.path.expanduser('~/.zshrc'))
BASIC_AUTH = os.getenv('DATAJURI_BASIC_AUTH')
USERNAME = os.getenv('DATAJURI_USERNAME')
PASSWORD = os.getenv('DATAJURI_PASSWORD')

AUTH_URL = "https://api.datajuri.com.br/v1/oauth/token"
API_URL = "https://api.datajuri.com.br/v1"

# Obter token
headers_auth = {"Authorization": f"Basic {BASIC_AUTH}", "Content-Type": "application/x-www-form-urlencoded"}
data_auth = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
token = requests.post(AUTH_URL, headers=headers_auth, data=data_auth).json().get("access_token")

headers_api = {"Authorization": f"Bearer {token}"}

# Data de hoje e fim da semana
hoje = datetime.now()
fim_semana = hoje + timedelta(days=(6 - hoje.weekday()))

print(f"📅 Prazos de {hoje.strftime('%d/%m')} a {fim_semana.strftime('%d/%m')}\n")

# Extrai atividades
page = 1
atividades = []

while True:
    url = f"{API_URL}/atividades?pageSize=100&page={page}"
    resp = requests.get(url, headers=headers_api).json()
    
    linhas = resp.get("rows", [])
    if not linhas:
        break
    
    atividades.extend(linhas)
    page += 1

# Filtra prazos da semana
df = pd.DataFrame(atividades)

if 'dataProxima' in df.columns:
    df['dataProxima'] = pd.to_datetime(df['dataProxima'], errors='coerce')
    df_semana = df[(df['dataProxima'] >= hoje) & (df['dataProxima'] <= fim_semana)].copy()
    
    df_semana = df_semana.sort_values('dataProxima')
    
    print(f"✅ Total: {len(df_semana)} atividades\n")
    
    for idx, row in df_semana.iterrows():
        data = row['dataProxima'].strftime('%a, %d/%m') if pd.notna(row['dataProxima']) else 'S/data'
        descricao = row.get('descricao', 'S/descrição')
        print(f"  {data} - {descricao}")
    
    # Salva CSV
    df_semana.to_csv('prazos_semana.csv', index=False)
    print(f"\n✅ Salvo em: prazos_semana.csv")
else:
    print("❌ Campo 'dataProxima' não encontrado")

