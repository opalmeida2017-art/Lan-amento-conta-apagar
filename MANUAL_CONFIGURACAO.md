# Manual do Usuário — Sistema de Automação NFe

Guia passo a passo para configurar e usar o sistema no dia a dia.

---

## Índice

1. [Antes de começar](#1-antes-de-começar)
2. [Primeira vez no sistema](#2-primeira-vez-no-sistema)
3. [Configurações do Sistema](#3-configurações-do-sistema)
4. [Parâmetros ERP](#4-parâmetros-erp)
5. [Painel Execução e Notas (robô)](#5-painel-execução-e-notas-robô)
6. [Importação manual de XML](#6-importação-manual-de-xml)
7. [Logs do Robô](#7-logs-do-robô)
8. [Veículos e Itens](#8-veículos-e-itens)
9. [Dúvidas frequentes](#9-dúvidas-frequentes)

---

## 1. Antes de começar

### O que você precisa

| Item | Descrição |
|------|-----------|
| **Programa** | `lancamento-conta-apagar.exe` |
| **Acesso ao ERP** | URL de login, usuário e senha com permissão para NFe e relatórios |
| **Internet** | Para consulta SEFAZ e sincronização |
| **E-mail (opcional)** | Conta SMTP para envio automático de relatórios |

### Abas do sistema

Após o acesso liberado:

- **Painel do Robô** — notas, parâmetros, veículos, itens e importação XML  
- **Configurações do Sistema** — ERP, e-mail e transportadora  
- **Logs do Robô** — acompanhamento das execuções  

Sub-abas do **Painel do Robô**:

| Sub-aba | Função |
|---------|--------|
| Execução e Notas | Painel das notas e **INICIAR AUTOMAÇÃO** |
| Parâmetros ERP | Período, filial/UE, placas, combustíveis e relatórios |
| Veículos Ativos | Frota sincronizada do ERP |
| Itens | Itens e grupo indefinido |
| Importa XML | Envio manual de XMLs |

---

## 2. Primeira vez no sistema

### Passo 1 — Abrir o programa

Execute `lancamento-conta-apagar.exe`. A janela abre maximizada.

### Passo 2 — Se aparecer “Sistema bloqueado”

1. Vá em **Configurações do Sistema**.  
2. Preencha **Razão social (transportadora)** (ex.: `Transportes Silva Ltda`).  
3. Clique em **Salvar transportadora e gerar ID**.  
4. Anote o **ID desta instalação** que aparece na tela.  
5. Envie o ID para o suporte/aguardar liberação.  
6. Depois da liberação, clique em **Verificar licença** no topo da tela.

### Passo 3 — Uso normal

Com o sistema liberado, aparecem todas as abas. Siga a ordem do [checklist](#ordem-recomendada-de-configuração-checklist) no final deste manual.

---

## 3. Configurações do Sistema

Acesse **Configurações do Sistema**.

### 3.1 Dados do ERP (Web)

| Campo | O que preencher |
|-------|-----------------|
| **Link do Sistema** | URL da tela de login do ERP |
| **Usuário** | Login no ERP |
| **Senha** | Senha do usuário |

1. Preencha os três campos.  
2. Teste o login manualmente no ERP com os mesmos dados.  
3. Se preencher um campo do ERP, preencha todos.

### 3.2 Disparo de e-mail (opcional)

| Campo | O que preencher |
|-------|-----------------|
| **SMTP** | Ex.: `smtp.gmail.com` ou `smtp.office365.com` |
| **Porta** | `465` com SSL **ou** `587` sem SSL |
| **Usar SSL/TLS** | Conforme o provedor |
| **E-mail** | Conta remetente |
| **Senha E-mail** | Senha ou senha de aplicativo |
| **Destinos** | E-mails separados por vírgula |

**Agendamento** — marque apenas uma opção:

| Opção | Quando envia |
|-------|----------------|
| Por hora | A cada X hora(s) informadas |
| Diário às 23:59 | Todo dia às 23:59 |
| Semanal | Segunda-feira às 00:00 |
| Mensal | Último dia do mês às 23:59 |

Os relatórios automáticos enviam **notas com erro** e **itens com grupo INDEFINIDO**.

### 3.3 Transportadora

| Campo | Uso |
|-------|-----|
| **Razão social** | Nome da empresa |
| **ID desta instalação** | Código único do seu computador — anote para o suporte |

### 3.4 Salvar

1. Revise os campos preenchidos.  
2. Clique em **Salvar Configurações** (ou **Salvar transportadora e gerar ID** se ainda estiver bloqueado).  
3. Confira a mensagem de confirmação.

---

## 4. Parâmetros ERP

Acesse **Painel do Robô** → **Parâmetros ERP**. O botão **Salvar Parâmetros** fica na parte inferior.

### 4.1 Período

| Campo | Uso |
|-------|-----|
| **Mês / Ano** | Período da consulta SEFAZ |
| **Últimos 30 dias** | Ignora mês/ano e usa os últimos 30 dias a partir de hoje |

### 4.2 Filial e UE (opcional)

| Campo | Uso |
|-------|-----|
| **Cod. Filial** | Código da filial no ERP |
| **Cod. Unid. Embarque** | Código da UE no ERP |

Com os dois preenchidos, todas as notas usam essa filial/UE. Deixe em branco para o ERP decidir.

### 4.3 Placa e KM

**Placa** — use `1` na posição dos números da placa (ex.: `PLACA: AAA-1A11`). Vários modelos separados por vírgula.

**KM** — use `1` onde começa a quilometragem (ex.: `KM: 1`, `ODO: 1`).

### 4.4 Combustíveis

Preencha os códigos de item no ERP: Etanol, Gasolina, Diesel S10, Diesel S500 e ARLA 32.

### 4.5 Grupo INDEFINIDO

Informe o código do grupo INDEFINIDO cadastrado em `Tabelas → Despesas/Receitas → Grupos`.

### 4.6 Relatórios ERP

| Campo | Obrigatório |
|-------|-------------|
| Cód. Relatório Veículos | Sim |
| Cód. Relatório Itens | Sim |

**Colunas do relatório de veículos:** `codVeiculo`, `placa`, `veiculoProprio`

**Colunas do relatório de itens:** `codItemD`, `descGrupoImp`, `descNegocioImp`, `descricao`

### 4.7 Salvar

Clique em **Salvar Parâmetros** e aguarde a confirmação.

---

## 5. Painel Execução e Notas (robô)

### 5.1 Painel

A coluna **Inserção** mostra quando a nota entrou no painel. Use **Limite linhas** (padrão 100) e os filtros de data, código, nota e status.

### 5.2 Iniciar automação

1. Confirme **Configurações** e **Parâmetros ERP** salvos.  
2. Clique em **▶ INICIAR AUTOMAÇÃO**.  
3. Para parar, clique em **⏹ PARAR**.  
4. Acompanhe em **Logs do Robô** e no status na parte inferior.

O robô consulta o SEFAZ, processa as notas e, ao terminar um ciclo, aguarda **2 minutos** e retoma sozinho.

### 5.3 Lançar uma nota pelo filtro

1. Filtre pelo **N° nota**.  
2. Se não estiver **Importado**, confirme **Sim** para lançar.  
3. Se a nota não aparecer, o sistema pode perguntar se é **compra para estoque**.

### 5.4 Relatório

**Imprimir Relatório** → **PDF** (navegador) ou **XLS** (pasta Downloads), respeitando os filtros ativos.

---

## 6. Importação manual de XML

1. **Importa XML** → **📁 Pasta XML**.  
2. **Recarregar** se adicionar arquivos.  
3. **▶ Iniciar Importação** (lotes de até 250 XMLs).

Não inicie o robô principal durante uma importação XML em andamento.

---

## 7. Logs do Robô

Filtre por data/hora e número da nota para localizar erros.

| Campo | Exemplo |
|-------|---------|
| Data/Hora | `26/05/2026 08:00` |
| Nº Nota | `1441` |

Clique em **Filtrar**. Use **Limpar Filtros** ou **Limpar Logs** quando necessário.

---

## 8. Veículos e Itens

**Veículos Ativos** — lista da frota; atualiza ao abrir a aba.

**Itens** — filtre, imprima relatórios e migre itens INDEFINIDO quando disponível na tela.

---

## 9. Dúvidas frequentes

### O sistema abre bloqueado

Normal na primeira vez. Salve a transportadora, anote o ID, aguarde liberação e clique em **Verificar licença**.

### O robô não inicia

Verifique: acesso liberado, ERP configurado, parâmetros ERP salvos e códigos dos relatórios preenchidos.

### E-mail automático não chega

Confira SMTP, porta, SSL, senha (ou senha de app) e destinatários. Todos os campos de e-mail devem estar preenchidos.

### Relatório de veículos/itens vazio

Confira os códigos dos relatórios no ERP e se as colunas têm os nomes exatos indicados na seção 4.6.

### Filial/UE não aplicou

Salve novamente os códigos em **Parâmetros ERP**.

---

## Ordem recomendada de configuração (checklist)

- [ ] 1. Salvar **transportadora** e anotar o **ID** (se bloqueado)  
- [ ] 2. **Verificar licença** após liberação  
- [ ] 3. **Configurações** → ERP (link, usuário, senha) → **Salvar**  
- [ ] 4. **Parâmetros ERP** → período (ou últimos 30 dias)  
- [ ] 5. Códigos dos relatórios de veículos e itens + grupo INDEFINIDO  
- [ ] 6. Placa, KM e combustíveis (se usar)  
- [ ] 7. Filial/UE (se usar lançamento fixo) → **Salvar Parâmetros**  
- [ ] 8. (Opcional) E-mail e agendamento → **Salvar Configurações**  
- [ ] 9. **Execução e Notas** → **INICIAR AUTOMAÇÃO**  
- [ ] 10. Acompanhar em **Logs do Robô**

---

*Manual do usuário — Automação NFe.*
