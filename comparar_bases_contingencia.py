# -*- coding: utf-8 -*-
import pandas as pd
from collections import Counter
import os

ARQUIVO_ANTIGO = "Dashboard - Contingência Civil.xls"
ARQUIVO_NOVO = "contingencia_civel_api.xlsx"
ARQUIVO_RELATORIO = "relatorio_comparacao_bases.txt"

def ler_base_antiga():
    """Lê a base antiga do Excel .xls"""
    try:
        df = pd.read_excel(ARQUIVO_ANTIGO, engine='xlrd')
        print(f"Colunas encontradas: {list(df.columns)}")
        
        colunas_processo = [col for col in df.columns if 'processo' in col.lower() or 'pasta' in col.lower()]
        if colunas_processo:
            col_processo = colunas_processo[0]
        else:
            col_processo = df.columns[0]
        
        df = df[df[col_processo].notna()]
        processos = df[col_processo].astype(str).str.strip().unique()
        print(f"✅ Base antiga: {len(processos)} processos")
        return set(processos), df, col_processo
    except Exception as e:
        print(f"ERRO ao ler base antiga: {e}")
        return set(), None, None

def ler_base_nova():
    """Lê a base nova do Excel .xlsx"""
    try:
        df = pd.read_excel(ARQUIVO_NOVO)
        df = df[df["Processo"].notna()]
        processos = df["Processo"].astype(str).str.strip().unique()
        print(f"✅ Base nova: {len(processos)} processos\n")
        return set(processos), df
    except Exception as e:
        print(f"ERRO ao ler base nova: {e}")
        return set(), None

def analisar_duplicados(df, col_processo):
    """Identifica duplicados em um dataframe"""
    contador = Counter(df[col_processo].astype(str).str.strip())
    duplicados = {proc: qtd for proc, qtd in contador.items() if qtd > 1}
    return duplicados

def gerar_relatorio(base_antiga, base_nova, df_antiga, df_nova, col_processo_antigo):
    """Gera relatório de comparação"""
    
    dup_antigo = analisar_duplicados(df_antiga, col_processo_antigo) if df_antiga is not None else {}
    dup_novo = analisar_duplicados(df_nova, "Processo")
    
    apenas_antigo = base_antiga - base_nova
    apenas_novo = base_nova - base_antiga
    em_ambas = base_antiga & base_nova
    
    relatorio = []
    relatorio.append("=" * 80)
    relatorio.append("RELATÓRIO DE COMPARAÇÃO DE BASES - CONTINGÊNCIA CÍVEL")
    relatorio.append("=" * 80)
    relatorio.append("")
    
    relatorio.append("RESUMO GERAL:")
    relatorio.append(f"  Base Antiga: {len(base_antiga)} processos")
    relatorio.append(f"  Base Nova:  {len(base_nova)} processos")
    relatorio.append(f"  Em ambas:   {len(em_ambas)} processos")
    relatorio.append(f"  Apenas na antiga: {len(apenas_antigo)} processos")
    relatorio.append(f"  Apenas na nova:   {len(apenas_novo)} processos")
    relatorio.append("")
    
    relatorio.append("DUPLICADOS NA BASE ANTIGA:")
    if dup_antigo:
        for proc, qtd in sorted(dup_antigo.items()):
            relatorio.append(f"  {proc}: {qtd}x")
    else:
        relatorio.append("  Nenhum duplicado encontrado ✅")
    relatorio.append("")
    
    relatorio.append("DUPLICADOS NA BASE NOVA:")
    if dup_novo:
        for proc, qtd in sorted(dup_novo.items()):
            relatorio.append(f"  {proc}: {qtd}x")
    else:
        relatorio.append("  Nenhum duplicado encontrado ✅")
    relatorio.append("")
    
    relatorio.append("PROCESSOS FALTANTES (Na base antiga, não na nova):")
    if apenas_antigo:
        relatorio.append(f"  Total: {len(apenas_antigo)}")
        for proc in sorted(apenas_antigo)[:20]:
            relatorio.append(f"    - {proc}")
        if len(apenas_antigo) > 20:
            relatorio.append(f"    ... e mais {len(apenas_antigo) - 20}")
    else:
        relatorio.append("  Nenhum processo faltante ✅")
    relatorio.append("")
    
    relatorio.append("NOVOS PROCESSOS (Na base nova, não na antiga):")
    if apenas_novo:
        relatorio.append(f"  Total: {len(apenas_novo)}")
        for proc in sorted(apenas_novo)[:20]:
            relatorio.append(f"    - {proc}")
        if len(apenas_novo) > 20:
            relatorio.append(f"    ... e mais {len(apenas_novo) - 20}")
    else:
        relatorio.append("  Nenhum processo novo ✅")
    relatorio.append("")
    relatorio.append("=" * 80)
    
    with open(ARQUIVO_RELATORIO, 'w', encoding='utf-8') as f:
        f.write('\n'.join(relatorio))
    
    print('\n'.join(relatorio))
    print(f"\n✅ Relatório salvo em: {ARQUIVO_RELATORIO}")

if __name__ == "__main__":
    print("Comparando bases...\n")
    
    base_antiga, df_antiga, col_antigo = ler_base_antiga()
    base_nova, df_nova = ler_base_nova()
    
    if base_antiga and base_nova:
        gerar_relatorio(base_antiga, base_nova, df_antiga, df_nova, col_antigo)
    else:
        print("ERRO: Não consegui ler as bases")
