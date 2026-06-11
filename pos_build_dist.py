"""Copia arquivos de configuração para dist/ após pyinstaller."""
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DIST = RAIZ / 'dist'


def main():
    DIST.mkdir(parents=True, exist_ok=True)
    exe = DIST / 'lancamento-conta-apagar.exe'
    if not exe.is_file():
        print(f'AVISO: {exe} não encontrado. Rode pyinstaller antes.')
        sys.exit(1)

    cfg = RAIZ / 'licenca_config.py'
    exemplo = RAIZ / 'licenca_config.example.py'

    if cfg.is_file():
        shutil.copy2(cfg, DIST / 'licenca_config.py')
        print('OK: licenca_config.py copiado para dist/')
    else:
        print(
            'AVISO: licenca_config.py não existe na raiz do projeto. '
            'Crie a partir de licenca_config.example.py antes do build.',
        )

    if exemplo.is_file():
        shutil.copy2(exemplo, DIST / 'licenca_config.example.py')
        print('OK: licenca_config.example.py copiado para dist/')

    print('')
    print('Pasta pronta para distribuir:')
    print(f'  {DIST}')
    print('  - lancamento-conta-apagar.exe')
    if (DIST / 'licenca_config.py').is_file():
        print('  - licenca_config.py')
    print('')
    print('Copie a pasta dist inteira (ou exe + licenca_config.py) para o cliente.')


if __name__ == '__main__':
    main()
