# Copie este arquivo para licenca_config.py e preencha com seus dados.
# NÃO commite licenca_config.py (contém token secreto).

LICENCA_REMOTA_ATIVA = True

# Repositório GitHub PRIVADO onde ficam os arquivos de licença
GITHUB_OWNER = "seu-usuario-github"
GITHUB_REPO = "licencas-clientes"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = "ghp_SEU_TOKEN_AQUI"

# Pasta dentro do repositório
PASTA_LICENCAS = "licencas"

# Verificação periódica (segundos). Recomendado: 3600 = 1 hora
INTERVALO_VERIFICACAO_SEG = 2

# Sem internet: manter liberado por até N horas após última verificação OK
GRACE_OFFLINE_HORAS = 72
