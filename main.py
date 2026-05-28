# -*- coding: utf-8 -*-
"""
Ponto de entrada principal do Sistema de Automação NFe.
Arquitetura: MVC (Model-View-Controller)
"""
import os
import sys

from app_controller import AppController


def _raiz_aplicacao():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def main():
    os.chdir(_raiz_aplicacao())
    app = AppController()
    app.iniciar()


if __name__ == "__main__":
    main()