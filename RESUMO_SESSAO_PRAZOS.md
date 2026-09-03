# Resumo - Projeto Dashboard de Prazos Semanais

## 🎯 OBJETIVO PRINCIPAL
Atualizar **automaticamente os prazos da semana** dos advogados e fazer ajustes no **Dashboard de Prazos** (NOT contingência).

## ✅ O QUE FOI FEITO

### 1. Comparação de Bases de Contingência (Concluído)
- ✅ Comparou base antiga vs base nova (API)
- ✅ 758 processos faltando, 980 novos
- ✅ Criou FALTANDO.csv e NOVOS.csv
- ✅ Criou COMPARATIVO_COMPLETO.xlsx
- ✅ README_COMPARACAO_BASES.md

### 2. Dashboard de Prazos (Em Progresso)
- ✅ Criou README_PRAZOS.md
- ⚠️ Script atualizar_dashboard_prazos_daily.py com erro 401
- ⚠️ Credenciais rejeitadas pela API

## 🔴 PROBLEMA
Erro 401 no script novo. Script de contingência funciona normal.
Solução: Usar estrutura de autenticação do extrair_contingencia_civel_api.py

## 🚀 PRÓXIMOS PASSOS

1. **Adaptar Script de Prazos**
   - Copiar autenticação do script de contingência
   - Buscar endpoint correto para prazos
   - Filtrar apenas semana (segunda a domingo)

2. **Criar Automação**
   - Sem LaunchAgent (preferência do usuário)
   - Alias no zshrc: `alias prazos='cd ~/Documentos/datajuri/ && python3 atualizar_prazos.py && open dashboard_prazos.html'`

3. **Melhorar Dashboard**
   - Filtros por data/tipo
   - Busca em tempo real
   - Destacar prazos de hoje
   - Estatísticas

## 📁 ARQUIVOS

**Funciona**:
- extrair_contingencia_civel_api.py ← USAR COMO REFERÊNCIA

**Precisa Criar**:
- atualizar_prazos.py
- dashboard_prazos.html

## 🔐 Credenciais
- Arquivo: ~/.zshrc
- Auth URL: https://api.datajuri.com.br/v1/oauth/token
- API Base: https://api.datajuri.com.br/v1

## 📊 Dados Prazos
- Campo: dataProxima
- Filtro: Semana atual
- Ordenação: Por data ASC
- Mostrar: Data, Descrição, Processo, Status

## 💡 DICAS TÉCNICAS
1. Usar requests.post() com OAuth headers
2. Paginação: pageSize=100&page={page}
3. Response: resp.json().get("rows", [])
4. Deduplicar por processo
5. pd.to_datetime() para datas

## 🎯 FOCO PRÓXIMO CHAT
1. Só prazos (não contingência)
2. Adaptar autenticação que funciona
3. Dashboard interativo
4. Automação sem LaunchAgent
5. Ajustes no layout

---
**Data**: 22 de julho de 2026  
**Status**: Pronto para continuar  
**Responsável**: Victor Miranda - Diretor Jurídico
