# -*- coding: utf-8 -*-
"""
Ponto de entrada principal do Sistema de Automação NFe.
Arquitetura: MVC (Model-View-Controller)
"""
import os
import shutil
import sys
from pathlib import Path


def _raiz_aplicacao():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _garantir_licenca_config_na_pasta(raiz):
    """Garante licenca_config.py ao lado do .exe (cópia do exemplo se faltar)."""
    destino = Path(raiz) / 'licenca_config.py'
    if destino.is_file():
        return

    for origem in (
        Path(raiz) / 'licenca_config.example.py',
        Path(getattr(sys, '_MEIPASS', '')) / 'licenca_config.example.py',
    ):
        if origem.is_file():
            shutil.copy2(origem, destino)
            print(
                '[AVISO] licenca_config.py criado a partir do exemplo. '
                'Preencha token e repositórios GitHub para licença e atualização.'
            )
            return


def _preparar_pasta_aplicacao():
    raiz = _raiz_aplicacao()
    os.chdir(raiz)
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    if getattr(sys, 'frozen', False):
        _garantir_licenca_config_na_pasta(raiz)


_preparar_pasta_aplicacao()

from app_controller import AppController


def main():
    _preparar_pasta_aplicacao()
    app = AppController()
    app.iniciar()


if __name__ == "__main__":
    main()