# Dashboard de Prazos - Pacaembu Construtora

## 📅 Visão Geral

Dashboard interativo que exibe **atividades e prazos judiciais** da semana em tempo real, integrado com a API DataJuri. Permite rastrear todas as atividades com prazo próximo para garantir cumprimento de obrigações processuais.

## 🎯 Objetivo

- ✅ Visualizar prazos da semana em ordem de data
- ✅ Identificar atividades urgentes
- ✅ Rastrear cumprimento de prazos
- ✅ Atualizar automaticamente diariamente

## 📊 Dados Inclusos

| Campo | Descrição | Origem |
|-------|-----------|--------|
| **Data Próxima** | Data do prazo/atividade | API DataJuri |
| **Descrição** | Detalhes da atividade | API DataJuri |
| **Processo** | Número do processo CNJ | API DataJuri |
| **Status** | Status atual da atividade | API DataJuri |
| **Tipo** | Tipo de atividade (audiência, petição, etc) | API DataJuri |

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

### Entrada
- **atividades_datajuri.csv** - Dados brutos extraídos da API (atualizado automaticamente)

### Processamento
- **gerar_dashboard_prazos_v12.py** - Script que processa os dados e gera o HTML

### Saída
- **dashboard_prazos.html** - Dashboard interativo (abrir no navegador)

## 📈 Recursos do Dashboard

### Filtros Interativos
- 🔍 Buscar por texto
- 📅 Filtrar por data
- 🏷️ Filtrar por tipo de atividade

### Visualizações
- 📊 Tabela principal com todas as atividades
- 📈 Gráfico de distribuição por dia
- 📋 Contadores de estatísticas

### Ações
- 📋 Copiar número do processo
- 📌 Ordenar por colunas
- 🖨️ Imprimir/PDF

## ⚙️ Automação com LaunchAgent

### Criar automação para atualizar diariamente

```bash
cat > ~/Library/LaunchAgents/com.pacaembu.dashboardprazos.plist << 'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pacaembu.dashboardprazos</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/victormiranda/Documentos/datajuri/gerar_dashboard_prazos_v12.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/victormiranda/Documentos/datajuri/prazos.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/victormiranda/Documentos/datajuri/prazos_error.log</string>
</dict>
</plist>
XML

launchctl load ~/Library/LaunchAgents/com.pacaembu.dashboardprazos.plist
```

### Verificar se está ativo
```bash
launchctl list | grep prazos
```

### Parar automação
```bash
launchctl unload ~/Library/LaunchAgents/com.pacaembu.dashboardprazos.plist
```

## 📊 Exemplo de Saída
## 🔄 Fluxo de Atualização

1. **08:00 - LaunchAgent Executa** → gerar_dashboard_prazos_v12.py
2. **Script Conecta** → API DataJuri (OAuth)
3. **Extrai Dados** → Todas as atividades com prazo próximo
4. **Processa** → Filtra semana atual, ordena por data
5. **Gera Dashboard** → dashboard_prazos.html
6. **Salva Log** → prazos.log

## 🛠️ Troubleshooting

### Dashboard não atualiza
```bash
# Verificar logs
tail -50 ~/Documentos/datajuri/prazos.log

# Rodar manual
cd ~/Documentos/datajuri/
python3 gerar_dashboard_prazos_v12.py -v
```

### Erro de autenticação
```bash
# Verificar credenciais em ~/.zshrc
echo $DATAJURI_BASIC_AUTH
echo $DATAJURI_USERNAME
```

### Arquivo CSV vazio
```bash
# Forçar atualização
python3 << 'PYEOF'
import requests, os
from dotenv import load_dotenv

load_dotenv(os.path.expanduser('~/.zshrc'))
BASIC_AUTH = os.getenv('DATAJURI_BASIC_AUTH')
USERNAME = os.getenv('DATAJURI_USERNAME')
PASSWORD = os.getenv('DATAJURI_PASSWORD')

AUTH_URL = "https://api.datajuri.com.br/v1/oauth/token"
headers = {"Authorization": f"Basic {BASIC_AUTH}", "Content-Type": "application/x-www-form-urlencoded"}
data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD}
token = requests.post(AUTH_URL, headers=headers, data=data).json().get("access_token")

print(f"✅ Token obtido: {token[:20]}...")
PYEOF
```

## 📅 Sugestões de Uso

### Rotina Diária
- **08:30** - Abrir dashboard para revisar prazos do dia
- **14:00** - Refresh para verificar novos prazos
- **17:00** - Última verificação antes de sair

### Rotina Semanal
- **Segunda** - Planejar semana inteira
- **Sexta** - Revisar o que faltou fazer
- **Sexta à noite** - Preparar para segunda

### Escalação
- **Hoje**: Prazos críticos
- **Amanhã/Depois**: Próximos passos
- **Semana que vem**: Planejamento

## 📝 Integração com Email

### Adicionar notificação por email (futuro)
```bash
# Script para enviar email com prazos do dia
cat > ~/Documentos/datajuri/notificar_prazos_email.py << 'PYEOF'
# Implementar envio de email com top 5 prazos do dia
# Usar smtplib para enviar via Gmail
PYEOF
```

## 🔐 Segurança

- ✅ Credenciais armazenadas em `~/.zshrc` (não sincronizadas)
- ✅ OAuth com token renovado diariamente
- ✅ Dados salvos localmente (não na nuvem)
- ✅ Logs armazenados apenas 30 dias

## 📞 Suporte

Para dúvidas sobre:
- **Dashboard**: Ver README_CONTINGENCIA.md
- **API DataJuri**: https://api.datajuri.com.br/docs
- **Automação**: Contatar DevOps

---

**Última atualização**: 22 de julho de 2026  
**Responsável**: Victor Miranda - Diretor Jurídico  
**Versão**: v12 (dashboard_prazos_v12.py)  
**Próxima revisão**: Conforme necessário
