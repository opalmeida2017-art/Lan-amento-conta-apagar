import customtkinter as ctk
from tkinter import ttk, messagebox
from ui.combo_busca_grupo import ComboBuscaGrupo
from ui.relatorio_itens import abrir_relatorio_pdf, salvar_relatorio_excel


class AbaItens(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.itens_filtrados_atuais = []
        self.montar_tela()

    def montar_tela(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        lbl_titulo = ctk.CTkLabel(
            self, text="Relação de Itens Sincronizados do ERP", font=("Arial", 16, "bold"),
        )
        lbl_titulo.grid(row=0, column=0, pady=(10, 5))

        self.frame_filtros = ctk.CTkFrame(self)
        self.frame_filtros.grid(row=1, column=0, pady=(5, 10), padx=10, sticky="ew")
        self.frame_filtros.grid_columnconfigure(5, weight=1)

        self.lbl_filtro_cod = ctk.CTkLabel(self.frame_filtros, text="Código:")
        self.filtro_cod = ctk.CTkEntry(self.frame_filtros, width=80)
        self.lbl_filtro_cod.grid(row=0, column=0, padx=(10, 2), pady=8, sticky="w")
        self.filtro_cod.grid(row=0, column=1, padx=2, pady=8, sticky="ew")

        self.lbl_filtro_grupo = ctk.CTkLabel(self.frame_filtros, text="Grupo:")
        self.lbl_filtro_grupo.grid(row=0, column=2, padx=(15, 2), pady=8, sticky="w")

        self._grupos_disponiveis = self.controller.obter_grupos_unicos()
        self.filtro_grupo = ComboBuscaGrupo(
            self.frame_filtros,
            self._grupos_disponiveis,
            width=180,
            valor_inicial="Todos",
            on_buscar_enter=self.controller.buscar_grupo_por_nome,
            on_enter_acao=self.atualizar_tabela,
        )
        self.filtro_grupo.grid(row=0, column=3, padx=2, pady=8, sticky="ew")

        self.lbl_filtro_desc = ctk.CTkLabel(self.frame_filtros, text="Descrição:")
        self.lbl_filtro_desc.grid(row=0, column=4, padx=(15, 2), pady=8, sticky="w")
        self.filtro_desc = ctk.CTkEntry(self.frame_filtros, width=200)
        self.filtro_desc.grid(row=0, column=5, padx=2, pady=8, sticky="ew")

        self.lbl_filtro_limite = ctk.CTkLabel(self.frame_filtros, text="Limite:")
        self.lbl_filtro_limite.grid(row=0, column=6, padx=(15, 2), pady=8, sticky="w")
        self.filtro_limite = ctk.CTkComboBox(
            self.frame_filtros, width=90, values=["100", "200", "500", "1000", "Todos"],
        )
        self.filtro_limite.set("100")
        self.filtro_limite.grid(row=0, column=7, padx=2, pady=8, sticky="ew")

        self.btn_filtrar = ctk.CTkButton(
            self.frame_filtros, text="🔍 Buscar", width=70, command=self.atualizar_tabela,
        )
        self.btn_filtrar.grid(row=1, column=0, padx=(10, 5), pady=(0, 8), sticky="ew")

        self.btn_limpar = ctk.CTkButton(
            self.frame_filtros, text="Limpar", width=60, fg_color="gray",
            command=self.limpar_filtros,
        )
        self.btn_limpar.grid(row=1, column=1, padx=5, pady=(0, 8), sticky="ew")

        self.btn_migrar = ctk.CTkButton(
            self.frame_filtros, text="🔄 Alterar Grupo em Lote", width=150,
            fg_color="#b8860b", hover_color="#8a6508", command=self.abrir_popup_migracao,
        )
        self.btn_migrar.grid(row=1, column=2, columnspan=3, padx=(16, 5), pady=(0, 8), sticky="ew")
        self.btn_atualizar_lista = ctk.CTkButton(
            self.frame_filtros,
            text="Atualizar Lista",
            width=120,
            font=("Arial", 12, "bold"),
            command=self._click_atualizar_lista,
        )
        self.btn_atualizar_lista.grid(row=1, column=5, padx=(10, 5), pady=(0, 8), sticky="w")
        self.lbl_imprimir_relatorio = ctk.CTkLabel(
            self.frame_filtros,
            text="Imprimir Relatório",
            text_color="#3b8ed0",
            font=("Arial", 12, "underline"),
            cursor="hand2",
        )
        self.lbl_imprimir_relatorio.bind(
            "<Button-1>", lambda _event: self.imprimir_relatorio_filtrado(),
        )
        self.lbl_imprimir_relatorio.bind(
            "<Enter>", lambda _event: self.lbl_imprimir_relatorio.configure(text_color="#6fb6ff"),
        )
        self.lbl_imprimir_relatorio.bind(
            "<Leave>", lambda _event: self.lbl_imprimir_relatorio.configure(text_color="#3b8ed0"),
        )
        self.lbl_imprimir_relatorio.grid(
            row=1, column=7, padx=(10, 10), pady=(0, 8), sticky="e",
        )

        frame_tabela = ctk.CTkFrame(self)
        frame_tabela.grid(row=2, column=0, pady=5, padx=10, sticky="nsew")
        frame_tabela.grid_columnconfigure(0, weight=1)
        frame_tabela.grid_rowconfigure(0, weight=1)

        colunas = ("codItemD", "descGrupoImp", "descNegocioImp", "descricao")
        self.tabela_itens = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=10)

        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela_itens.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela_itens.xview)
        self.tabela_itens.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tabela_itens.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.tabela_itens.heading("codItemD", text="Cód. Item")
        self.tabela_itens.heading("descGrupoImp", text="Grupo Atual")
        self.tabela_itens.heading("descNegocioImp", text="Negócio")
        self.tabela_itens.heading("descricao", text="Descrição")

        self.tabela_itens.column("codItemD", width=82, anchor="center")
        self.tabela_itens.column("descGrupoImp", width=160, anchor="w")
        self.tabela_itens.column("descNegocioImp", width=150, anchor="w")
        self.tabela_itens.column("descricao", width=300, anchor="w")

        self.status_label = ctk.CTkLabel(self, text="Status: Aguardando...", text_color="gray")
        self.status_label.grid(row=3, column=0, pady=(4, 10), padx=10, sticky="w")

        self.atualizar_tabela()

    def limpar_filtros(self):
        self.filtro_cod.delete(0, 'end')
        self.filtro_desc.delete(0, 'end')
        self._grupos_disponiveis = self.controller.obter_grupos_unicos()
        self.filtro_grupo.atualizar_valores(self._grupos_disponiveis)
        self.filtro_grupo.set("Todos")
        self.filtro_limite.set("100")
        self.atualizar_tabela()

    def _obter_limite_linhas(self):
        valor = self.filtro_limite.get().strip() if hasattr(self, 'filtro_limite') else "100"
        if not valor or valor.lower() == "todos":
            return None
        try:
            return max(1, int(valor))
        except Exception:
            self.filtro_limite.set("100")
            return 100

    def _perguntar_formato_relatorio(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Imprimir Relatório")
        popup.geometry("420x180")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        popup.transient(self.winfo_toplevel())
        popup.grab_set()

        popup.update_idletasks()
        x = self.winfo_rootx() + max((self.winfo_width() - 420) // 2, 0)
        y = self.winfo_rooty() + max((self.winfo_height() - 180) // 2, 0)
        popup.geometry(f"420x180+{x}+{y}")

        resposta = {"valor": None}

        ctk.CTkLabel(
            popup,
            text="Escolha o formato do relatório",
            font=("Arial", 16, "bold"),
            text_color="#3b8ed0",
        ).pack(pady=(18, 8))

        ctk.CTkLabel(
            popup,
            text="PDF abre no navegador em A4.\nXLSX salva na pasta Downloads.",
            justify="center",
        ).pack(pady=(0, 14))

        frame_botoes = ctk.CTkFrame(popup, fg_color="transparent")
        frame_botoes.pack(pady=8, padx=12, fill="x")
        for col in range(3):
            frame_botoes.grid_columnconfigure(col, weight=1)

        def fechar(valor):
            resposta["valor"] = valor
            popup.grab_release()
            popup.destroy()

        ctk.CTkButton(
            frame_botoes, text="PDF", fg_color="#1f538d", hover_color="#163d68",
            command=lambda: fechar("pdf"),
        ).grid(row=0, column=0, padx=6, sticky="ew")

        ctk.CTkButton(
            frame_botoes, text="XLS", fg_color="#2e7d32", hover_color="#1b5e20",
            command=lambda: fechar("xls"),
        ).grid(row=0, column=1, padx=6, sticky="ew")

        ctk.CTkButton(
            frame_botoes, text="Cancelar", fg_color="#c62828", hover_color="#b71c1c",
            command=lambda: fechar(None),
        ).grid(row=0, column=2, padx=6, sticky="ew")

        popup.protocol("WM_DELETE_WINDOW", lambda: fechar(None))
        self.wait_window(popup)
        return resposta["valor"]

    def _resumo_filtros_relatorio(self):
        return {
            "Código": self.filtro_cod.get().strip(),
            "Grupo": self.filtro_grupo.get().strip(),
            "Descrição": self.filtro_desc.get().strip(),
            "Limite linhas": self.filtro_limite.get().strip(),
        }

    def _coletar_linhas_tabela(self):
        linhas = []
        for item in self.tabela_itens.get_children():
            linhas.append(list(self.tabela_itens.item(item, "values")))
        return linhas

    def imprimir_relatorio_filtrado(self):
        self.atualizar_tabela()
        linhas = self._coletar_linhas_tabela()
        if not linhas:
            messagebox.showwarning("Aviso", "Nenhum item está visível na tabela para gerar o relatório.")
            return

        filtros = self._resumo_filtros_relatorio()
        cabecalhos = [
            self.tabela_itens.heading(coluna).get("text", coluna)
            for coluna in self.tabela_itens["columns"]
        ]
        escolha = self._perguntar_formato_relatorio()
        if not escolha:
            return

        if escolha == "pdf":
            abrir_relatorio_pdf(filtros, cabecalhos, linhas)
            self.status_label.configure(
                text=f"Status: PDF de itens aberto no navegador ({len(linhas)} itens).",
                text_color="#3b8ed0",
            )
            return

        caminho = salvar_relatorio_excel(filtros, cabecalhos, linhas)
        messagebox.showinfo("Relatório XLSX", f"Relatório salvo em:\n{caminho}")
        self.status_label.configure(
            text=f"Status: XLSX de itens salvo em Downloads ({len(linhas)} itens).",
            text_color="#3b8ed0",
        )

    def _click_atualizar_lista(self):
        self.btn_atualizar_lista.configure(state="disabled")
        self.status_label.configure(
            text="Status: sincronizando itens com o ERP...",
            text_color="#f39c12",
        )
        iniciado = self.controller.sincronizar_itens_erp(ao_finalizar=self._finalizar_atualizacao)
        if not iniciado:
            self.status_label.configure(
                text="Status: sincronização de itens já está em andamento.",
                text_color="#f39c12",
            )
            self.btn_atualizar_lista.configure(state="normal")

    def _finalizar_atualizacao(self):
        self.atualizar_tabela()
        self.btn_atualizar_lista.configure(state="normal")

    def atualizar_tabela(self):
        for item in self.tabela_itens.get_children():
            self.tabela_itens.delete(item)

        itens_db = self.controller.obter_itens_filtrados(
            cod=self.filtro_cod.get(),
            grupo=self.filtro_grupo.get(),
            descricao=self.filtro_desc.get(),
            limite=self._obter_limite_linhas(),
        )
        self.itens_filtrados_atuais = itens_db

        for i in itens_db:
            self.tabela_itens.insert(
                "", "end",
                values=(
                    i.get('codItemD', ''),
                    i.get('descGrupoImp', ''),
                    i.get('descNegocioImp', ''),
                    i.get('descricao', ''),
                ),
            )
        if itens_db:
            texto = f"Status: exibindo {len(itens_db)} linha(s)."
            cor = "#3b8ed0"
        else:
            texto = (
                "Status: nenhum item no banco. "
                "Confira o código do relatório em Parâmetros ERP e clique em Atualizar Lista."
            )
            cor = "#f39c12"
        self.status_label.configure(text=texto, text_color=cor)

    def abrir_popup_migracao(self):
        grupo_atual = self.filtro_grupo.get().strip()
        if grupo_atual == "Todos" or not grupo_atual:
            messagebox.showwarning(
                "Aviso de Segurança",
                "Para usar esta função, primeiro filtre a tabela por um GRUPO específico.",
            )
            return

        itens_na_tela = []
        for item in self.tabela_itens.get_children():
            valores = self.tabela_itens.item(item, "values")
            itens_na_tela.append({"codigo": valores[0], "descricao": valores[3]})

        if not itens_na_tela:
            messagebox.showwarning("Aviso", "Nenhum item filtrado na tabela.")
            return

        popup = ctk.CTkToplevel(self)
        popup.title(f"Migrar itens do grupo: {grupo_atual}")
        popup.geometry("600x520")
        popup.minsize(500, 420)
        popup.attributes("-topmost", True)

        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 300
        y = self.winfo_y() + (self.winfo_height() // 2) - 260
        popup.geometry(f"600x520+{x}+{y}")

        ctk.CTkLabel(
            popup, text="Selecione os itens e o Novo Grupo", font=("Arial", 16, "bold"),
        ).pack(pady=10)

        frame_destino = ctk.CTkFrame(popup)
        frame_destino.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(frame_destino, text="Mover para o Grupo:").pack(side="left", padx=10)

        grupos_sem_todos = [g for g in self.controller.obter_grupos_unicos() if g != "Todos"]
        combo_novo_grupo = ComboBuscaGrupo(
            frame_destino,
            grupos_sem_todos,
            width=250,
            valor_inicial=grupos_sem_todos[0] if grupos_sem_todos else "",
            on_buscar_enter=self.controller.buscar_grupo_por_nome,
        )
        combo_novo_grupo.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(
            popup, text=f"Itens encontrados ({len(itens_na_tela)}):",
        ).pack(anchor="w", padx=20, pady=(10, 0))

        painel_checks = ctk.CTkScrollableFrame(popup, width=500, height=200)
        painel_checks.pack(padx=20, pady=5, fill="x")

        check_vars = {}
        for item in itens_na_tela:
            var = ctk.BooleanVar(value=True)
            check_vars[item['codigo']] = var
            texto_chk = f"[{item['codigo']}] {item['descricao'][:50]}..."
            chk = ctk.CTkCheckBox(painel_checks, text=texto_chk, variable=var)
            chk.pack(anchor="w", pady=2)

        frame_rodape = ctk.CTkFrame(popup, fg_color="transparent")
        frame_rodape.pack(side="bottom", fill="x", padx=20, pady=(5, 15))

        lbl_status = ctk.CTkLabel(frame_rodape, text="Aguardando início...", text_color="gray")
        lbl_status.pack(pady=(0, 8))

        def disparar_robo():
            novo_grupo = combo_novo_grupo.get().strip()
            if not novo_grupo:
                return
            if novo_grupo.lower() == grupo_atual.lower():
                messagebox.showwarning(
                    "Aviso", "O grupo de destino deve ser diferente do grupo atual.",
                )
                return

            itens_marcados = [cod for cod, var in check_vars.items() if var.get()]
            if not itens_marcados:
                messagebox.showwarning("Aviso", "Nenhum item selecionado.")
                return

            btn_iniciar.configure(state="disabled", text="Robô trabalhando...")
            combo_novo_grupo.configure(state="disabled")

            def atualizar_texto_status(msg):
                def _atualizar(m=msg):
                    if popup.winfo_exists():
                        lbl_status.configure(text=m)
                popup.after(0, _atualizar)

            def reabilitar_popup():
                def _reabilitar():
                    if not popup.winfo_exists():
                        return
                    try:
                        btn_iniciar.configure(state="normal", text="▶ INICIAR MIGRAÇÃO")
                        combo_novo_grupo.configure(state="normal")
                    except Exception:
                        pass
                popup.after(0, _reabilitar)

            self.controller.iniciar_migracao_lote(
                itens_marcados, novo_grupo, atualizar_texto_status,
                grupo_atual=grupo_atual, on_finalizado=reabilitar_popup,
            )

        btn_iniciar = ctk.CTkButton(
            frame_rodape,
            text="▶ INICIAR MIGRAÇÃO",
            fg_color="#b8860b",
            hover_color="#8a6508",
            font=("Arial", 14, "bold"),
            height=40,
            command=disparar_robo,
        )
        btn_iniciar.pack(fill="x")