# -*- coding: utf-8 -*-
"""
Ponto de entrada principal do Sistema de Automação NFe.
Arquitetura: MVC (Model-View-Controller)
"""
from app_controller import AppController

def main():
    # Instancia o controlador principal (O cérebro do projeto)
    app = AppController()
    
    # Inicia a interface (login/licença desativados em app_controller.REQUER_LOGIN_E_LICENCA)
    app.iniciar()

if __name__ == "__main__":
    main()