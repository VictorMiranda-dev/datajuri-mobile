#!/bin/bash
cd "/Users/victormiranda/Documentos/datajuri" || exit 1
source "/Users/victormiranda/.zshrc" 2>/dev/null

echo "=== $(date '+%d/%m/%Y %H:%M') - Iniciando atualizacao automatica ===" >> atualizacao_automatica.log

# 1. Gera o dashboard com os dados mais recentes da API DataJuri
python3 gerar_dashboard_prazos_v13.py >> atualizacao_automatica.log 2>&1

# 2. Atualiza a pasta web_app automaticamente com o index.html gerado
if [ -f "dashboard_prazos.html" ]; then
    mkdir -p web_app
    cp dashboard_prazos.html web_app/index.html
    echo "[OK] Arquivo web_app/index.html sincronizado com sucesso." >> atualizacao_automatica.log
fi

echo "=== $(date '+%d/%m/%Y %H:%M') - Concluido ===" >> atualizacao_automatica.log
