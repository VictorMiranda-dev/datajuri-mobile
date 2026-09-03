# 📊 Dashboard Prazos v12 Melhorado

Versão aprimorada do v12 com 3 funcionalidades novas:

## ✨ O que Mudou

### 1️⃣ Atualiza Prazos da Semana (API Integrada)

**Antes:**
```python
def carregar_registros():
    # Lia CSV local
    # ❌ Precisava de arquivo atividades_datajuri.csv
```

**Agora:**
```python
def carregar_registros():
    # Lê credenciais do ~/.zshrc
    # Autentica na API
    # Busca atividades
    # Filtra apenas semana atual
    # ✅ Sem arquivo intermediário
```

**Resultado:**
- 📥 Busca direto da API DataJuri
- 📅 Filtra automaticamente prazos da semana (segunda a domingo)
- 🔄 Paginação automática (100 registros por página)
- ⏱️ Sem dependências extras (python3 + curl)

---

### 2️⃣ Separação Trabalhista x Cível

**No Header:**
```
[Todos os Processos 47] [🏛️ Cível 32] [⚖️ Trabalhista 15]
```

**Nos Filtros:**
- Pill "Cível" com ícone 🏛️
- Pill "Trabalhista" com ícone ⚖️
- Contagem dinâmica de cada tipo

**Na Tabela:**
- Coluna `data-area` identifica cada processo
- Filtro rápido por área jurídica

**Estatística:**
- Card "Processos Cíveis" mostra total
- Card "Processos Trabalhistas" mostra total

---

### 3️⃣ Destaque de Prazos do Dia + Responsável

**Visual:**
- 🔴 **Prazos de HOJE** destacados com fundo amarelo/gold
- Linha da tabela inteira com `background-color: rgba(156,59,59,0.08)`
- Coluna de data (**Prazo Encarregado**) com fundo `#fff3cd` 
- Coluna **Encarregado** com fundo `#fff3cd` e **negrito**

**Filtros:**
- Botão `🔴 Hoje` nos filtros de período (destacado)
- Card `🔴 Prazos HOJE` mostra quantidade de prazos do dia

**Ranking:**
- Rankings mostram "Hoje", "Semana", "Todos"
- Padrão abre "Todos" (pode mudar)

---

## 🚀 Como Usar

### Setup (Primeira Vez)

Copie o arquivo para sua pasta:
```bash
cp gerar_dashboard_prazos_v12_melhorado.py ~/Documentos/datajuri/
```

### Executar

```bash
cd ~/Documentos/datajuri/
python3 gerar_dashboard_prazos_v12_melhorado.py
```

**Saída:**
```
==================================================
🔄 Carregando Prazos da Semana
==================================================

🔐 Autenticando...
✅ Autenticado

📥 Buscando atividades da API...
   Página 1: 100 registros
   Página 2: 87 registros
   ✅ Total: 187 atividades

📅 Filtrando prazos de 22/07 a 28/07

✅ 47 prazos da semana carregados

==================================================
🎨 Gerando Dashboard...
==================================================

✅ Dashboard salvo em: dashboard_prazos.html

==================================================
✅ Processo concluído!
==================================================
```

### Abre Automaticamente

Se não abrir sozinho:
```bash
open dashboard_prazos.html
```

---

## 🎯 Funcionalidades Principais

### Filtros

**Por Área:**
- 🏛️ Cível
- ⚖️ Trabalhista
- Todos

**Por Status:**
- Todos
- Não iniciados
- Em andamento
- Finalizados

**Por Período:**
- 🔴 Hoje (destaque especial)
- Semana

**Por Encarregado:**
- Select dropdown com todos os nomes

**Busca Livre:**
- Procura em processo, adverso, assunto

---

## 📊 Dashboard Widgets

### Stats Grid (Topo)
- Total da Semana
- Não Iniciados
- Em Andamento
- Finalizados

### Período Grid (Cards)
- 🔴 Prazos HOJE (mostra quantidade + data)
- Prazos Esta Semana
- Processos Cíveis (estatística)
- Processos Trabalhistas (estatística)

### Painéis (Gráficos)
- Prazos por Encarregado
- Principais Assuntos
- Tipos de Atividade

Cada painel com abas: Hoje | Semana | Todos

### Tabela Completa
- Processo (Pasta)
- Adverso
- Prazo Encarregado (destaque se hoje)
- Data Fatal
- Encarregado (destaque se hoje)
- Assunto
- Status (editável em tempo real)

---

## 🎨 Visual

### Cores & Destaque

**Prazos de Hoje:**
- Background: `#fff3cd` (amarelo claro)
- Cor de texto: `#8a660a` (ouro escuro)
- Fonte: **negrito** (weight: 800)

**Linha da Tabela (Hoje):**
- Background: `rgba(156,59,59,0.08)` (vermelho bem claro)
- Font-weight: 600

**Branding Pacaembu:**
- Navy: #233240 (headers)
- Brick Red: #9c3b3b (destaque vermelho)
- Gold: #b8860b (destaque ouro)
- Beige: #f3f1ea (background)

---

## 📋 Dados Capturados da API

O script captura e formata:
- `dataProxima` → prazo do encarregado
- `dataRegistro` → data de registro
- `status` → categorizado (naoiniciado, andamento, finalizado)
- `encarregado.nome` → responsável
- `natureza` → categorizado (cível, trabalhista)
- `numeroProcesso` → número do processo
- `descricao` → assunto
- `tipo` → tipo de atividade
- `adverso` → nome da outra parte

---

## 🔧 Customizações Fáceis

### Mudar Cores

No CSS (linha ~260):
```python
css = """
...
.prazo-hoje{background:#fff3cd;color:#8a660a;}
.encarregado-hoje{background:#fff3cd;color:#8a660a;}
...
"""
```

### Mudar Período Padrão

Rankings abrem "Todos" por padrão. Para mudar para "Semana":
```python
'<button class="mini-pill active" data-periodo="semana"...'
```

### Adicionar Mais Filtros

Edite a seção `filtros-bar` no HTML gerado.

---

## 📝 Notas Técnicas

- ✅ Sem dependências Python extras (só subprocess)
- ✅ Usa `curl` (builtin no macOS)
- ✅ Lê `.zshrc` com bash puro
- ✅ Paginação automática (100 por página)
- ✅ Trata 4 formatos de data diferentes
- ✅ Categoria automatica de status/área
- ✅ Compatível com v12 (mesmo HTML/CSS/JS)

---

## 🐛 Troubleshooting

### "Credenciais não encontradas"

```bash
grep DATAJURI ~/.zshrc
```

Deve listar 3 variáveis.

### "Nenhum prazo encontrado para esta semana"

Significa que não há atividades com `dataProxima` entre hoje e domingo.

### Dashboard não atualiza

Sempre roda o script novamente:
```bash
python3 gerar_dashboard_prazos_v12_melhorado.py
```

---

## ✅ Checklist

- [ ] Credenciais no ~/.zshrc (BASIC_AUTH, USERNAME, PASSWORD)
- [ ] Copiar arquivo para ~/Documentos/datajuri/
- [ ] Testar: `python3 gerar_dashboard_prazos_v12_melhorado.py`
- [ ] Verificar dashboard em browser
- [ ] Testar filtros (área, período, status)
- [ ] Testar busca
- [ ] Pronto!

---

**Versão:** v12 Melhorado  
**Data:** 22 de julho de 2026  
**Status:** Pronto para uso ✅
