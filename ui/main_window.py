import customtkinter as ctk
from tkinter import messagebox

# ========================================================
# IMPORTAÇÃO DOS COMPONENTES MODULARES (As peças de Lego)
# ========================================================
from ui.aba_config import AbaConfig
from controllers.ctrl_config import ConfigController
from ui.aba_veiculos import AbaVeiculos
from controllers.ctrl_veiculos import VeiculosController
from ui.aba_itens import AbaItens
from controllers.ctrl_itens import ItensController
from ui.aba_execucao import AbaExecucao
from controllers.ctrl_execucao import ExecucaoController
from ui.aba_filtros import AbaFiltros
from controllers.ctrl_filtros import FiltrosController

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MainWindow(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller # Referência ao AppController (O Cérebro)
        
        self.title("Sistema de Automação NFe - Enterprise")
        self.geometry("400x550")
        self.eval('tk::PlaceWindow . center') 

    def limpar_tela(self):
        """Remove todos os widgets da janela para trocar de tela."""
        for widget in self.winfo_children():
            widget.destroy()

    # ============================================================
    # TELAS DE ACESSO (TOKEN / LOGIN / CADASTRO)
    # ============================================================
    
    def mostrar_tela_token(self):
        self.limpar_tela()
        self.geometry("400x550")
        
        lbl_titulo = ctk.CTkLabel(self, text="Sistema Bloqueado", font=("Arial", 24, "bold"), text_color="red")
        lbl_titulo.pack(pady=(50, 10))
        
        lbl_sub = ctk.CTkLabel(self, text="Insira uma licença válida para continuar.")
        lbl_sub.pack(pady=(0, 30))
        
        self.entry_token = ctk.CTkEntry(self, placeholder_text="Digite o Token", width=250)
        self.entry_token.pack(pady=10)
        
        btn_ativar = ctk.CTkButton(self, text="Ativar Sistema", 
                                   command=lambda: self.controller.ativar_sistema(self.entry_token.get().strip()))
        btn_ativar.pack(pady=20)

    def mostrar_tela_bloqueio_licenca(self):
        import database_setup as db
        self.limpar_tela()
        self.geometry("480x420")
        ctk.CTkLabel(self, text="Sistema Bloqueado", font=("Arial", 24, "bold"), text_color="red").pack(pady=(40, 10))
        ctk.CTkLabel(
            self,
            text="Licença suspensa (ativado = não) ou arquivo ausente no servidor.",
            font=("Arial", 13),
        ).pack(pady=(0, 15))
        iid = db.obter_instalacao_id() or "— ainda não registrado —"
        ctk.CTkLabel(self, text="ID desta instalação:", font=("Arial", 12, "bold")).pack()
        ctk.CTkLabel(self, text=iid, font=("Consolas", 11), text_color="#3b8ed0", wraplength=420).pack(pady=(4, 20))
        ctk.CTkButton(self, text="Tentar novamente", command=self.controller.tentar_revalidar_licenca).pack(pady=8)

    def mostrar_tela_login(self):
        self.limpar_tela()
        self.geometry("400x550")
        
        lbl_titulo = ctk.CTkLabel(self, text="Acesso ao Sistema", font=("Arial", 24, "bold"))
        lbl_titulo.pack(pady=(60, 30))
        
        self.entry_email = ctk.CTkEntry(self, placeholder_text="E-mail", width=250)
        self.entry_email.pack(pady=10)
        
        self.entry_senha = ctk.CTkEntry(self, placeholder_text="Senha", show="*", width=250)
        self.entry_senha.pack(pady=10)
        
        btn_login = ctk.CTkButton(self, text="Entrar", 
                                  command=lambda: self.controller.realizar_login(self.entry_email.get().strip(), self.entry_senha.get().strip()))
        btn_login.pack(pady=15)
        
        btn_cadastrar = ctk.CTkButton(self, text="Novo Operador", fg_color="transparent", border_width=1, 
                                      command=self.controller.preparar_cadastro)
        btn_cadastrar.pack(pady=10)

    def mostrar_tela_cadastro(self):
        self.limpar_tela()
        lbl_titulo = ctk.CTkLabel(self, text="Cadastrar Operador", font=("Arial", 24, "bold"))
        lbl_titulo.pack(pady=(40, 20))
        
        self.reg_nome = ctk.CTkEntry(self, placeholder_text="Nome Completo", width=250)
        self.reg_nome.pack(pady=10)
        
        self.reg_email = ctk.CTkEntry(self, placeholder_text="E-mail", width=250)
        self.reg_email.pack(pady=10)
        
        self.reg_senha = ctk.CTkEntry(self, placeholder_text="Senha", show="*", width=250)
        self.reg_senha.pack(pady=10)
        
        btn_confirmar = ctk.CTkButton(self, text="Confirmar Cadastro", 
                                      command=lambda: self.controller.executar_cadastro(
                                          self.reg_nome.get().strip(), 
                                          self.reg_email.get().strip(), 
                                          self.reg_senha.get().strip()
                                      ))
        btn_confirmar.pack(pady=20)
        
        btn_voltar = ctk.CTkButton(self, text="Voltar", fg_color="gray", command=self.mostrar_tela_login)
        btn_voltar.pack()

    # ============================================================
    # MENU PRINCIPAL (ORQUESTRAÇÃO DAS ABAS)
    # ============================================================

    def mostrar_menu_principal(self):
        self.limpar_tela()
        self.geometry("980x880") 
        self.eval('tk::PlaceWindow . center')
        
        # Criar a Tabview Principal
        self.tabview = ctk.CTkTabview(self, width=920, height=800)
        self.tabview.pack(pady=20, padx=20)
        
        # Adicionar as Abas de Nível Superior
        aba_painel_robo = self.tabview.add("Painel do Robô")
        aba_configuracoes = self.tabview.add("Configurações do Sistema")
        
        # 1. MONTAR ABA DE CONFIGURAÇÕES (Componentizada)
        ctrl_config = ConfigController()
        self.aba_config = AbaConfig(master=aba_configuracoes, controller=ctrl_config)
        self.aba_config.pack(fill="both", expand=True)

        # 2. MONTAR O PAINEL DO ROBÔ (Que contém as sub-abas)
        self.montar_painel_do_robo(aba_painel_robo)

    def montar_painel_do_robo(self, container):
        """Cria as sub-abas dentro do Painel do Robô."""
        lbl_titulo = ctk.CTkLabel(container, text="Dashboard da Automação", font=("Arial", 22, "bold"), text_color="#3b8ed0")
        lbl_titulo.pack(pady=(10, 5))

        self.sub_tabview = ctk.CTkTabview(container, width=900, height=680)
        self.sub_tabview.pack(pady=5, padx=10, fill="both", expand=True)
        
        # Criar as áreas para cada sub-aba
        tab_exec = self.sub_tabview.add("Execução e Notas")
        tab_filtros = self.sub_tabview.add("Filtros de Data")
        tab_veiculos = self.sub_tabview.add("Veículos Ativos")
        tab_itens = self.sub_tabview.add("Itens")
        
        # --- PLUGAR ABA EXECUÇÃO ---
        ctrl_exec = ExecucaoController(app_controller=self.controller)
        self.aba_execucao = AbaExecucao(master=tab_exec, controller=ctrl_exec)
        self.aba_execucao.pack(fill="both", expand=True)
        # Notifica o cérebro principal onde está a tela de execução para logs do Robô
        self.controller.view_execucao = self.aba_execucao

        # --- PLUGAR ABA FILTROS ---
        ctrl_filtros = FiltrosController()
        self.aba_filtros = AbaFiltros(master=tab_filtros, controller=ctrl_filtros)
        self.aba_filtros.pack(fill="both", expand=True)

        # --- PLUGAR ABA VEÍCULOS ---
        ctrl_veic = VeiculosController()
        self.aba_veiculos = AbaVeiculos(master=tab_veiculos, controller=ctrl_veic)
        self.aba_veiculos.pack(fill="both", expand=True)

        # --- PLUGAR ABA ITENS ---
        ctrl_itens = ItensController()
        self.aba_itens = AbaItens(master=tab_itens, controller=ctrl_itens)
        self.aba_itens.pack(fill="both", expand=True)