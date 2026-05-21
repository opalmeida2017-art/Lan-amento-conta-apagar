# -*- coding: utf-8 -*-
"""
Ponto de entrada principal do Sistema de Automação NFe.
Arquitetura: MVC (Model-View-Controller)
"""
from app_controller import AppController

def main():
    # Instancia o controlador principal (O cérebro do projeto)
    app = AppController()
    
    # Inicia o fluxo de verificação de licença, login e interface
    app.iniciar()

if __name__ == "__main__":
    main()