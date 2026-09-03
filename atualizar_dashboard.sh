#!/bin/bash
cd ~/Documentos/datajuri/ || exit 1

echo "=== $(date) - Iniciando atualizacao ===" >> atualizacao.log

/usr/bin/python3 extrair_dashboard_completo.py >> atualizacao.log 2>&1

/usr/bin/python3 gerar_dashboard_prazos_v12.py >> atualizacao.log 2>&1

echo "=== $(date) - Atualizacao concluida ===" >> atualizacao.log
