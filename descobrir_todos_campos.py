# -*- coding: utf-8 -*-
import os
import requests
import json

BASIC_AUTH = os.environ.get("DATAJURI_BASIC_AUTH")
USERNAME = os.environ.get("DATAJURI_USERNAME")
PASSWORD = os.environ.get("DATAJURI_PASSWORD")

AUTH_URL = "https://api.datajuri.com.br/oauth/token"
BASE_URL = "https://api.datajuri.com.br/v1"


def obter_token():
    headers = {
        "Authorization": "Basic " + BASIC_AUTH,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    dados = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
    resp = requests.post(AUTH_URL, headers=headers, data=dados)
    resp.raise_for_status()
    return resp.json()["access_token"]


def extrair_linhas(resp):
    if resp.status_code != 200:
        return None
    dados = resp.json()
    if isinstance(dados, dict):
        return dados.get("rows", dados.get("content", []))
    if isinstance(dados, list):
        return dados
    return []


def testar_campo(token, entidade, campo, id_sempre_incluido=True):
    url = BASE_URL + "/entidades/" + entidade
    headers = {"Authorization": "Bearer " + token}
    campos_param = ("id," + campo) if id_sempre_incluido else campo
    params = {"campos": campos_param, "page": 0}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    linhas = extrair_linhas(resp)

    if linhas is None:
        return "ERRO " + str(resp.status_code)
    if not linhas:
        return "VAZIO (sem registros)"

    exemplo = None
    for reg in linhas[:20]:
        if isinstance(reg, dict):
            val = reg.get(campo)
            if val not in (None, "", "N/A"):
                exemplo = val
                break
    if exemplo is not None:
        return "OK -> " + str(exemplo)
    else:
        return "OK* (campo existe mas vazio nos 20 primeiros)"


def rodar_bateria(token, entidade, candidatos):
    print("\n" + "=" * 70)
    print("ENTIDADE: " + entidade)
    print("=" * 70)
    for campo in candidatos:
        resultado = testar_campo(token, entidade, campo)
        print(("  " + campo).ljust(38) + " " + resultado)


if __name__ == "__main__":
    token = obter_token()
    print("Token obtido com sucesso.")

    candidatos_processo = [
        "pasta", "cliente.nome", "adverso.nome", "advogadoCliente.nome",
        "advogadoAdverso.nome", "faseAtual.numero", "tipoAcao", "status", "natureza",
        "dataAbertura", "valorCausa", "valorDaCausa", "valorProvisionado",
        "valorProvisionadoAtualizado", "possibilidadePerda", "posicaoCliente",
        "qualificacaoCliente", "instanciaFaseAtual", "faseAtual.instancia",
        "localidadeFaseAtual", "faseAtual.localidade", "numeroVaraFaseAtual",
        "faseAtual.numeroVara", "varaFaseAtual", "faseAtual.vara",
        "responsavel.nome", "assunto",
        "dataDistribuicao", "dataCadastro", "objeto", "acaoPrincipal",
        "comarca", "vara", "orgaoJulgador", "situacao", "fase.nome",
        "valorAtualizado", "valorCondenacao", "risco", "prognostico",
        "responsavelId", "encarregado.nome", "areaJuridica",
    ]
    rodar_bateria(token, "Processo", candidatos_processo)

    candidatos_atividade = [
        "id", "prazo_do_encarregado", "data", "hora", "encarregado.nome",
        "proprietario.nome", "assunto", "tipoAtividade", "status", "diasPrazo",
        "processo.pasta", "processo.adverso.nome", "processo.natureza",
        "processo.advogadoCliente.nome", "processo.advogadoAdverso.nome",
        "processo.valorCausa", "processo.tipoAcao", "descricao", "observacao",
        "dataConclusao", "usuarioResponsavel.nome", "prioridade",
    ]
    rodar_bateria(token, "Atividade", candidatos_atividade)

    candidatos_pessoa = [
        "id", "nome", "cpfCnpj", "email", "telefone", "endereco",
        "tipo", "dataNascimento", "profissao", "estadoCivil", "nacionalidade",
    ]
    rodar_bateria(token, "Pessoa", candidatos_pessoa)

    candidatos_usuario = [
        "id", "nome", "email", "login", "cargo", "departamento",
        "ativo", "perfil", "escritorio.nome",
    ]
    rodar_bateria(token, "Usuario", candidatos_usuario)

    print("\n\nFIM DOS TESTES. Me manda essa lista completa.")
