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

campos_teste = "id,pasta,valorCausa,valorProvisionado,valorProvisionadoAtualizado,possibilidadePerda,possibilidade_perda,valor_provisiona,risco,contingencia"

resp = requests.get(
    BASE_URL + "/entidades/Processo",
    headers=headers_api,
    params={
        "pasta": "4004632-35.2025.8.26.0451",
        "campos": campos_teste
    },
    timeout=30
)

if resp.status_code == 200:
    data = resp.json()
    # Salva JSON bruto num arquivo
    with open("debug_resposta.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("✅ JSON salvo em debug_resposta.json")
    
    # Imprime também
    if data.get("rows"):
        print("\nRegistro encontrado:")
        print(json.dumps(data["rows"][0], indent=2, ensure_ascii=False))
