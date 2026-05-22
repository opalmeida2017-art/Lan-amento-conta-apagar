# Licenciamento remoto — o que VOCÊ precisa fazer

## 1. Criar repositório no GitHub

1. Crie um repositório **privado** (ex.: `licencas-clientes`).
2. Dentro dele, crie a pasta `licencas/` (pode estar vazia no início).

## 2. Gerar token de acesso (PAT)

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
2. Gere um token com permissão **`repo`** (acesso a repositórios privados).
3. Copie o token (começa com `ghp_...`). **Não compartilhe.**

## 3. Configurar o aplicativo

1. Copie o arquivo de exemplo:
   ```
   copiar licenca_config.example.py → licenca_config.py
   ```
2. Edite `licenca_config.py`:
   ```python
   LICENCA_REMOTA_ATIVA = True
   GITHUB_OWNER = "seu-usuario"
   GITHUB_REPO = "licencas-clientes"
   GITHUB_BRANCH = "main"
   GITHUB_TOKEN = "ghp_SEU_TOKEN"
   PASTA_LICENCAS = "licencas"
   INTERVALO_VERIFICACAO_SEG = 3600
   ```
3. O arquivo `licenca_config.py` **não** deve ir para o Git (já está no `.gitignore`).

## 4. Distribuir o sistema aos clientes

- Envie o programa **com** `licenca_config.py` já preenchido **dentro do instalador** (ou compile em `.exe` incluindo esse arquivo).
- O token ficará no PC do cliente — use um token só para uploads na pasta `licencas/` ou aceite o risco.

## 5. Fluxo no cliente

1. Cliente abre o sistema → entra direto (sem login antigo).
2. Vai em **Configurações do Sistema** → preenche link, usuário e senha do ERP → **Salvar**.
3. O sistema gera um **ID único** e envia o arquivo `licencas/{ID}.json` para o seu GitHub.
4. A cada **1 hora** o sistema verifica o campo **`ativado`** no arquivo (`sim` = liberado, `não` = bloqueado).

## 6. Bloquear ou reativar (painel local)

1. Duplo clique em **`rodar_painel_licencas.bat`** (ou `python painel_licencas.py`).
2. **Desativar** = bloqueia o cliente; **Ativar** = libera.
3. O cliente reflete na próxima verificação (até 1 h) ou ao reabrir o app.

Detalhes: veja **`PAINEL_LICENCAS.md`**.

## 8. Identificar o cliente

- Na tela **Configurações** aparece o **ID desta instalação**.
- Anote: `ID` → nome da empresa (planilha).

## Modo teste (sem GitHub)

Deixe `LICENCA_REMOTA_ATIVA = False` em `licenca_config.py` (ou não crie o arquivo): o sistema funciona sem bloqueio remoto, mas ainda gera ID local ao salvar.

## Arquivos implementados

| Arquivo | Função |
|---------|--------|
| `licenca_remota.py` | Upload e verificação no GitHub |
| `licenca_config.example.py` | Modelo de configuração |
| `database_setup.py` | Tabela `instalacao_licenca` |
| `controllers/ctrl_config.py` | Registro ao salvar ERP |
| `ui/aba_config.py` | Exibe ID da instalação |
| `app_controller.py` | Bloqueio e checagem horária |
| `ui/main_window.py` | Tela de bloqueio |
| `painel_licencas.py` | Painel local ativar/desativar |
| `rodar_painel_licencas.bat` | Atalho para abrir o painel |
