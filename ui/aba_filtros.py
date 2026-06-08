import customtkinter as ctk

from ui import ui_filtros


class AbaFiltros(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.layout_job = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.montar_tela()

    def montar_tela(self):
        self.frame_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.frame_scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=(0, 6))
        self.frame_scroll.grid_columnconfigure(0, weight=1)

        self.painel_de_filtros = ui_filtros.PainelFiltros(self.frame_scroll)
        self.painel_de_filtros.grid(row=0, column=0, sticky="ew", pady=(0, 8), padx=8)

        self.comando_salvar_filtros = None

        def roubar_botao(widget_pai):
            for widget in widget_pai.winfo_children():
                if isinstance(widget, ctk.CTkButton) and "Salvar" in str(widget.cget("text")):
                    self.comando_salvar_filtros = widget.cget("command")
                    widget.pack_forget()
                    widget.grid_forget()
                    return True
                if roubar_botao(widget):
                    return True
            return False

        roubar_botao(self.painel_de_filtros)

        frame_relatorios = ctk.CTkFrame(self.frame_scroll)
        frame_relatorios.grid(row=1, column=0, sticky="ew", pady=(0, 4), padx=8)

        ctk.CTkLabel(
            frame_relatorios,
            text="Relatórios e Cadastros do ERP",
            font=("Arial", 15, "bold"),
        ).pack(pady=(12, 5))

        self.frame_grid = ctk.CTkFrame(frame_relatorios, fg_color="transparent")
        self.frame_grid.pack(fill="x", pady=(4, 4), padx=10)

        self.lbl_rel_veic = ctk.CTkLabel(
            self.frame_grid, text="Cód. Relatório Veículos:", font=("Arial", 12, "bold"),
        )
        self.entry_rel_veiculo = ctk.CTkEntry(self.frame_grid, width=100, justify="center")

        self.lbl_rel_item = ctk.CTkLabel(
            self.frame_grid, text="Cód. Relatório Itens:", font=("Arial", 12, "bold"),
        )
        self.entry_rel_item = ctk.CTkEntry(self.frame_grid, width=100, justify="center")

        instrucoes = (
            "⚠️ INSTRUÇÕES PARA EXPORTAÇÃO NO ERP:\n\n"
            "🚛 VEÍCULOS: As colunas do relatório 117 devem conter estes nomes:\n"
            " codVeiculo | cavalo | placa | carreta1 | carreta2 | carreta3 | veiculoProprio\n"
            " (veiculoProprio define Próprio/Agregado/Terceiro na importação NFe)\n\n"
            "📦 ITENS: As colunas devem estar EXATAMENTE nesta ordem e com os nomes originais:\n"
            " 1º codItemD   |   2º descGrupoImp   |   3º descNegocioImp   |   4º descricao\n\n"
            "📦 GRUPO INDEFINIDO (cadastro de item): Cadastre o grupo no ERP em:\n"
            "   Tabelas\\Despesas/Receitas\\Grupos\n"
            "   Informe o código no campo «Grupo Item / Cód. no ERP» (coluna à direita)."
        )

        self.btn_salvar_tudo = ctk.CTkButton(
            self,
            text="💾 Salvar Parâmetros",
            command=self._click_salvar_tudo,
            width=260,
            height=42,
            font=("Arial", 15, "bold"),
            fg_color="#107C41",
            hover_color="#0A532B",
        )
        self.btn_salvar_tudo.grid(row=1, column=0, padx=12, pady=(4, 10), sticky="ew")

        self.lbl_instrucoes = ctk.CTkLabel(
            frame_relatorios,
            text=instrucoes,
            justify="left",
            text_color="#f39c12",
            font=("Arial", 11),
        )
        self.lbl_instrucoes.pack(pady=(4, 12), padx=20, anchor="w")

        self.bind("<Configure>", self._agendar_layout_responsivo)
        self.after(0, self._aplicar_layout_responsivo)
        self.carregar_dados_iniciais()

    def _agendar_layout_responsivo(self, _event=None):
        if self.layout_job:
            self.after_cancel(self.layout_job)
        self.layout_job = self.after(80, self._aplicar_layout_responsivo)

    def _aplicar_layout_responsivo(self):
        self.layout_job = None
        largura = max(self.winfo_width(), 1)

        for widget in (
            self.lbl_rel_veic,
            self.entry_rel_veiculo,
            self.lbl_rel_item,
            self.entry_rel_item,
        ):
            widget.grid_forget()

        if largura < 760:
            self.lbl_rel_veic.grid(row=0, column=0, padx=(10, 5), pady=3, sticky="e")
            self.entry_rel_veiculo.grid(row=0, column=1, padx=(0, 10), pady=3, sticky="w")
            self.lbl_rel_item.grid(row=1, column=0, padx=(10, 5), pady=3, sticky="e")
            self.entry_rel_item.grid(row=1, column=1, padx=(0, 10), pady=3, sticky="w")
        else:
            self.lbl_rel_veic.grid(row=0, column=0, padx=(10, 5), pady=3, sticky="e")
            self.entry_rel_veiculo.grid(row=0, column=1, padx=(0, 30), pady=3, sticky="w")
            self.lbl_rel_item.grid(row=0, column=2, padx=(20, 5), pady=3, sticky="e")
            self.entry_rel_item.grid(row=0, column=3, padx=(0, 10), pady=3, sticky="w")

        self.lbl_instrucoes.configure(wraplength=max(420, largura - 80))
        self.btn_salvar_tudo.configure(width=240 if largura < 760 else 280)

    def _entry_cod_grupo(self):
        return self.painel_de_filtros.entry_cod_grupo_item

    def carregar_dados_iniciais(self):
        cfg = self.controller.carregar_codigos_relatorios()

        self.entry_rel_veiculo.delete(0, 'end')
        rel_veiculo = str(cfg.get('rel_veiculo') or '').strip()
        if rel_veiculo:
            self.entry_rel_veiculo.insert(0, rel_veiculo)

        self.entry_rel_item.delete(0, 'end')
        rel_item = str(cfg.get('rel_item') or '').strip()
        if rel_item:
            self.entry_rel_item.insert(0, rel_item)

        entry_grupo = self._entry_cod_grupo()
        entry_grupo.delete(0, 'end')

        cod = cfg.get('cod_grupo_item', '')
        if cod:
            entry_grupo.insert(0, cod)

    def _click_salvar_tudo(self):
        from tkinter import messagebox

        rel_veiculo = self.entry_rel_veiculo.get().strip()
        rel_item = self.entry_rel_item.get().strip()
        cod_grupo = self._entry_cod_grupo().get().strip()

        if not rel_veiculo or not rel_item:
            messagebox.showwarning(
                "Códigos de relatórios",
                "Informe os códigos dos relatórios de Veículos e Itens conforme o ERP desta empresa.",
            )
            return

        if not cod_grupo:
            messagebox.showwarning(
                "Código do grupo",
                "Informe o código ERP do grupo INDEFINIDO no campo «Grupo Item / Cód. no ERP».",
            )
            return

        self.controller.salvar_tudo(rel_veiculo, rel_item, cod_grupo, self.comando_salvar_filtros)

