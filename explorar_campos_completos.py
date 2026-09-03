import os
import requests
import json

BASE_URL = "https://api.datajuri.com.br/v1"
AUTH_URL = "https://api.datajuri.com.br/oauth/token"

BASIC_AUTH = os.getenv("DATAJURI_BASIC_AUTH", "")
USERNAME = os.getenv("DATAJURI_USERNAME", "")
PASSWORD = os.getenv("DATAJURI_PASSWORD", "")

print(f"BASIC_AUTH: {'***' if BASIC_AUTH else 'VAZIO'}")
print(f"USERNAME: {USERNAME}")

# Step 1: Autenticar e obter token
headers_auth = {
    "Authorization": f"Basic {BASIC_AUTH}",
    "Content-Type": "application/x-www-form-urlencoded",
}
data_auth = {
    "grant_type": "password",
    "username": USERNAME,
    "password": PASSWORD,
}

print("\nAutenticando...")
resp_auth = requests.post(AUTH_URL, headers=headers_auth, data=data_auth, timeout=30)

print(f"OAuth Status: {resp_auth.status_code}")

if resp_auth.status_code != 200:
    print(f"Erro: {resp_auth.text}")
    exit(1)

token = resp_auth.json().get("access_token")
print(f"✅ Token obtido: {token[:20]}...")

# Step 2: Usar o token pra buscar o processo
headers_api = {"Authorization": f"Bearer {token}"}

resp = requests.get(
    BASE_URL + "/entidades/Processo",
    headers=headers_api,
    params={"pasta": "4004632-35.2025.8.26.0451"},
    timeout=30
)

print(f"\nAPI Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    print("✅ JSON válido!")
    
    if data.get("rows"):
        print("\n🔍 CAMPOS ENCONTRADOS NESTE PROCESSO:\n")
        print("Todos os campos:")
        for key in sorted(data["rows"][0].keys()):
            value = data["rows"][0][key]
            print(f"  '{key}': {value}")
    else:
        print("Nenhum registro encontrado")
else:
    print(f"Erro: {resp.text[:500]}")
