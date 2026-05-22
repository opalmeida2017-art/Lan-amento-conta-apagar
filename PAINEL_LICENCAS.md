# Painel local de licenças

Aplicação no seu PC para **ativar** e **desativar** clientes no GitHub (repositório pode ficar **privado**).

## Como abrir

**Forma mais fácil (Windows):** duplo clique em:

`rodar_painel_licencas.bat`

**Ou no terminal:**

```bash
cd "c:\python\Lançamento conta apagar"
python painel_licencas.py
```

## Antes de usar (uma vez)

1. Arquivo `licenca_config.py` preenchido:
   - `GITHUB_OWNER` = seu usuário (ex: `opalmeida2017-art`)
   - `GITHUB_REPO` = `licencas-clientes`
   - `GITHUB_BRANCH` = `principal`
   - `GITHUB_TOKEN` = token com permissão **repo**

2. Pasta `licencas/` no GitHub com arquivos `.json` (cliente salva em Configurações do sistema).

## Uso

1. Abra o painel
2. **Atualizar lista**
3. **Ativar** = cliente liberado (`"ativado": "sim"`)
4. **Desativar** = cliente bloqueado (`"ativado": "não"`)

Não é necessário apagar o arquivo no GitHub.
