# Dashboard de Prazos - Pacaembu Construtora

## 📅 Visão Geral

Dashboard interativo que exibe atividades e prazos judiciais da semana em tempo real, integrado com a API DataJuri.

## 🎯 Objetivo

- ✅ Visualizar prazos da semana em ordem de data
- ✅ Identificar atividades urgentes
- ✅ Rastrear cumprimento de prazos
- ✅ Atualizar automaticamente diariamente

## 📊 Dados Inclusos

- Data Próxima: Data do prazo/atividade
- Descrição: Detalhes da atividade
- Processo: Número do processo CNJ
- Status: Status atual da atividade
- Tipo: Tipo de atividade (audiência, petição, etc)

## 🚀 Como Usar

### 1. Abrir Dashboard
```bash
open ~/Documentos/datajuri/dashboard_prazos.html
```

### 2. Atualizar Manualmente
```bash
cd ~/Documentos/datajuri/
python3 gerar_dashboard_prazos_v12.py
```

### 3. Ver Dados em CSV
```bash
open ~/Documentos/datajuri/atividades_datajuri.csv
```

## 🔧 Estrutura dos Arquivos

- **atividades_datajuri.csv** - Dados brutos da API
- **gerar_dashboard_prazos_v12.py** - Script de processamento
- **dashboard_prazos.html** - Dashboard interativo

## 📈 Recursos do Dashboard

- 🔍 Buscar por texto
- 📅 Filtrar por data
- 🏷️ Filtrar por tipo de atividade
- 📊 Gráfico de distribuição
- 📋 Contadores

## ⚙️ Automação

Executa automaticamente às 8h da manhã via LaunchAgent.

Verificar status:
```bash
launchctl list | grep prazos
```

## 📞 Suporte

Contatar: Victor Miranda - Diretor Jurídico

---
**Última atualização**: 22 de julho de 2026
**Versão**: v12 (dashboard_prazos_v12.py)
