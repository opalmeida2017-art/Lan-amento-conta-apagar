import customtkinter as ctk
from ui import ui_filtros

class AbaFiltros(ctk.CTkScrollableFrame):
    def __init__(self, master, controller):
        # Transforma a aba inteira em um frame rolável
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.montar_tela()

    def montar_tela(self):
        # =======================================================
        # 1. PAINEL ORIGINAL (Mês, Ano e Combustíveis)
        # =======================================================
        self.painel_de_filtros = ui_filtros.PainelFiltros(self)
        self.painel_de_filtros.pack(fill="x", pady=(0, 10))

        # =======================================================
        # 2. HACK INVISÍVEL: ROUBAR O BOTÃO VERDE DO PAINEL
        # =======================================================
        self.comando_salvar_filtros = None
        
        def roubar_botao(widget_pai):
            for widget in widget_pai.winfo_children():
                if isinstance(widget, ctk.CTkButton) and "Salvar" in str(widget.cget("text")):
                    self.comando_salvar_filtros = widget.cget("command")
                    widget.pack_forget() 
                    widget.grid_forget()
                    return True
                else:
                    if roubar_botao(widget): return True
            return False
            
        roubar_botao(self.painel_de_filtros)

        # =======================================================
        # 3. NOSSO NOVO PAINEL DE RELATÓRIOS
        # =======================================================
        frame_relatorios = ctk.CTkFrame(self)
        frame_relatorios.pack(fill="x", pady=5)

        ctk.CTkLabel(frame_relatorios, text="Configuração dos Relatórios do ERP", font=("Arial", 15, "bold")).pack(pady=(15, 5))

        frame_grid = ctk.CTkFrame(frame_relatorios, fg_color="transparent")
        frame_grid.pack(pady=5)

        ctk.CTkLabel(frame_grid, text="Cód. Relatório Veículos:", font=("Arial", 12, "bold")).grid(row=0, column=0, padx=(10, 5), sticky="e")
        self.entry_rel_veiculo = ctk.CTkEntry(frame_grid, width=100, justify="center")
        self.entry_rel_veiculo.grid(row=0, column=1, padx=(0, 30), sticky="w")

        ctk.CTkLabel(frame_grid, text="Cód. Relatório Itens:", font=("Arial", 12, "bold")).grid(row=0, column=2, padx=(30, 5), sticky="e")
        self.entry_rel_item = ctk.CTkEntry(frame_grid, width=100, justify="center")
        self.entry_rel_item.grid(row=0, column=3, padx=(0, 10), sticky="w")

        instrucoes = (
            "⚠️ INSTRUÇÕES PARA EXPORTAÇÃO NO ERP:\n\n"
            "🚛 VEÍCULOS: As colunas devem conter EXATAMENTE estes nomes originais:\n"
            " 1º codVeiculo   |   2º placa   |   3º veiculoProprio\n\n"
            "📦 ITENS: As colunas devem estar EXATAMENTE nesta ordem e com os nomes originais:\n"
            " 1º codItemD   |   2º descGrupoImp   |   3º descNegocioImp   |   4º descricao"
        )
        ctk.CTkLabel(frame_relatorios, text=instrucoes, justify="left", text_color="#f39c12", font=("Arial", 12)).pack(pady=(10, 15), padx=20, anchor="w")

        # =======================================================
        # 4. BOTÃO ÚNICO PARA SALVAR TUDO
        # =======================================================
        btn_salvar_tudo = ctk.CTkButton(self, text="💾 Salvar Todas as Configurações", 
                                        command=self._click_salvar_tudo,
                                        width=300, height=45, font=("Arial", 15, "bold"), 
                                        fg_color="#107C41", hover_color="#0A532B")
        btn_salvar_tudo.pack(pady=20)

        self.carregar_dados_iniciais()

    def carregar_dados_iniciais(self):
        cfg = self.controller.carregar_codigos_relatorios()
        self.entry_rel_veiculo.delete(0, 'end')
        self.entry_rel_veiculo.insert(0, cfg.get('rel_veiculo', '117'))
        self.entry_rel_item.delete(0, 'end')
        self.entry_rel_item.insert(0, cfg.get('rel_item', '118'))

    def _click_salvar_tudo(self):
        rel_veiculo = self.entry_rel_veiculo.get()
        rel_item = self.entry_rel_item.get()
        # Envia a função roubada e os textos para o controlador salvar!
        self.controller.salvar_tudo(rel_veiculo, rel_item, self.comando_salvar_filtros)