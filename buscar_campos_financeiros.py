import os
import requests
import json

BASE_URL = "https://api.datajuri.com.br/v1"
AUTH_URL = "https://api.datajuri.com.br/oauth/token"

BASIC_AUTH = os.getenv("DATAJURI_BASIC_AUTH", "")
USERNAME = os.getenv("DATAJURI_USERNAME", "")
PASSWORD = os.getenv("DATAJURI_PASSWORD", "")

headers_auth = {
    "Authorization": f"Basic {BASIC_AUTH}",
    "Content-Type": "application/x-www-form-urlencoded",
}
data_auth = {
    "grant_type": "password",
    "username": USERNAME,
    "password": PASSWORD,
}

resp_auth = requests.post(AUTH_URL, headers=headers_auth, data=data_auth, timeout=30)
token = resp_auth.json().get("access_token")

headers_api = {"Authorization": f"Bearer {token}"}

# Tenta vários nomes possíveis para os campos financeiros
campos_teste = "id,pasta,valorCausa,valorProvisionado,valorProvisionadoAtualizado,possibilidadePerda,possibilidade_perda,valor_provisiona,risco,contingencia,risco_contingencia"

resp = requests.get(
    BASE_URL + "/entidades/Processo",
    headers=headers_api,
    params={
        "pasta": "4004632-35.2025.8.26.0451",
        "campos": campos_teste
    },
    timeout=30
)

print(f"Status: {resp.status_code}")

if resp.status_code == 200:
    data = resp.json()
    if data.get("rows"):
        print("\n✅ Campos financeiros encontrados:\n")
        for key, value in data["rows"][0].items():
            print(f"  '{key}': {value}")
    else:
        print("Nenhum registro encontrado")
else:
    print(f"Erro: {resp.text[:500]}")
