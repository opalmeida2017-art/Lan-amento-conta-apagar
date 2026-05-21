import customtkinter as ctk
from tkinter import ttk, messagebox

class AbaItens(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.montar_tela()

    def montar_tela(self):
        lbl_titulo = ctk.CTkLabel(self, text="Relação de Itens Sincronizados do ERP", font=("Arial", 16, "bold"))
        lbl_titulo.pack(pady=(10, 5))

        frame_filtros = ctk.CTkFrame(self)
        frame_filtros.pack(pady=(5, 10), padx=10, fill="x")

        ctk.CTkLabel(frame_filtros, text="Código:").grid(row=0, column=0, padx=(10, 2), pady=8)
        self.filtro_cod = ctk.CTkEntry(frame_filtros, width=80)
        self.filtro_cod.grid(row=0, column=1, padx=2, pady=8)

        ctk.CTkLabel(frame_filtros, text="Grupo:").grid(row=0, column=2, padx=(15, 2), pady=8)
        
        # Carrega os grupos do banco de dados
        grupos_disponiveis = self.controller.obter_grupos_unicos()
        self.filtro_grupo = ctk.CTkComboBox(frame_filtros, width=180, values=grupos_disponiveis)
        self.filtro_grupo.set("Todos")
        self.filtro_grupo.grid(row=0, column=3, padx=2, pady=8)

        # ==========================================================
        # 🟢 CORREÇÃO 1: FILTRO DE TECLADO NA TELA PRINCIPAL
        # ==========================================================
        def filtrar_grupos_tela(event):
            # Ignora teclas de navegação para não atrapalhar o dropdown
            if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Return', 'Tab']:
                return
            
            texto = self.filtro_grupo.get().lower()
            if not texto:
                self.filtro_grupo.configure(values=grupos_disponiveis)
            else:
                filtrados = [g for g in grupos_disponiveis if texto in g.lower()]
                self.filtro_grupo.configure(values=filtrados if filtrados else grupos_disponiveis)

        # Aplica o espião de teclado diretamente na caixa de texto interna do ComboBox
        self.filtro_grupo._entry.bind('<KeyRelease>', filtrar_grupos_tela)

        ctk.CTkLabel(frame_filtros, text="Descrição:").grid(row=0, column=4, padx=(15, 2), pady=8)
        self.filtro_desc = ctk.CTkEntry(frame_filtros, width=200)
        self.filtro_desc.grid(row=0, column=5, padx=2, pady=8)

        btn_filtrar = ctk.CTkButton(frame_filtros, text="🔍 Buscar", width=70, command=self.atualizar_tabela)
        btn_filtrar.grid(row=0, column=6, padx=(20, 5), pady=8)

        btn_limpar = ctk.CTkButton(frame_filtros, text="Limpar", width=60, fg_color="gray", command=self.limpar_filtros)
        btn_limpar.grid(row=0, column=7, padx=5, pady=8)

        # ====== BOTÃO DE MIGRAÇÃO ======
        btn_migrar = ctk.CTkButton(frame_filtros, text="🔄 Alterar Grupo em Lote", width=150, fg_color="#b8860b", hover_color="#8a6508", command=self.abrir_popup_migracao)
        btn_migrar.grid(row=0, column=8, padx=(20, 5), pady=8)

        frame_tabela = ctk.CTkFrame(self)
        frame_tabela.pack(pady=5, padx=10, fill="both", expand=True)

        colunas = ("codItemD", "descGrupoImp", "descNegocioImp", "descricao")
        self.tabela_itens = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=10)
        
        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela_itens.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela_itens.xview)
        self.tabela_itens.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        
        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        self.tabela_itens.pack(side="left", fill="both", expand=True)

        self.tabela_itens.heading("codItemD", text="Cód. Item")
        self.tabela_itens.heading("descGrupoImp", text="Grupo Atual")
        self.tabela_itens.heading("descNegocioImp", text="Negócio")
        self.tabela_itens.heading("descricao", text="Descrição")
        
        self.tabela_itens.column("codItemD", width=90, anchor="center")
        self.tabela_itens.column("descGrupoImp", width=180, anchor="w")
        self.tabela_itens.column("descNegocioImp", width=180, anchor="w")
        self.tabela_itens.column("descricao", width=350, anchor="w")

        self.atualizar_tabela()

    def limpar_filtros(self):
        self.filtro_cod.delete(0, 'end')
        self.filtro_desc.delete(0, 'end')
        self.filtro_grupo.configure(values=self.controller.obter_grupos_unicos())
        self.filtro_grupo.set("Todos")
        self.atualizar_tabela()

    def atualizar_tabela(self):
        for item in self.tabela_itens.get_children():
            self.tabela_itens.delete(item)
            
        itens_db = self.controller.obter_itens_filtrados(
            cod=self.filtro_cod.get(), 
            grupo=self.filtro_grupo.get(), 
            descricao=self.filtro_desc.get()
        )
        
        for i in itens_db:
            self.tabela_itens.insert("", "end", values=(i['codItemD'], i['descGrupoImp'], i['descNegocioImp'], i['descricao']))

    # ==========================================
    # LÓGICA DO POPUP DE MIGRAÇÃO
    # ==========================================
    def abrir_popup_migracao(self):
        grupo_atual = self.filtro_grupo.get()
        if grupo_atual == "Todos" or not grupo_atual:
            messagebox.showwarning("Aviso de Segurança", "Para usar esta função, primeiro filtre a tabela por um GRUPO específico.")
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
        popup.geometry("600x550")
        popup.attributes("-topmost", True)
        
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (600 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (550 // 2)
        popup.geometry(f"+{x}+{y}")

        ctk.CTkLabel(popup, text="Selecione os itens e o Novo Grupo", font=("Arial", 16, "bold")).pack(pady=10)

        frame_destino = ctk.CTkFrame(popup)
        frame_destino.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(frame_destino, text="Mover para o Grupo:").pack(side="left", padx=10)
        
        grupos_sem_todos = [g for g in self.controller.obter_grupos_unicos() if g != "Todos"]
        combo_novo_grupo = ctk.CTkComboBox(frame_destino, width=250, values=grupos_sem_todos)
        combo_novo_grupo.pack(side="left", padx=10, pady=10)

        # ==========================================================
        # 🟢 CORREÇÃO 2: FILTRO DE TECLADO NO POPUP
        # ==========================================================
        def filtrar_grupos_popup(event):
            if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Return', 'Tab']:
                return
                
            texto = combo_novo_grupo.get().lower()
            if not texto:
                combo_novo_grupo.configure(values=grupos_sem_todos)
            else:
                filtrados = [g for g in grupos_sem_todos if texto in g.lower()]
                combo_novo_grupo.configure(values=filtrados if filtrados else grupos_sem_todos)

        combo_novo_grupo._entry.bind('<KeyRelease>', filtrar_grupos_popup)

        ctk.CTkLabel(popup, text=f"Itens encontrados ({len(itens_na_tela)}):").pack(anchor="w", padx=20, pady=(10,0))
        painel_checks = ctk.CTkScrollableFrame(popup, width=500, height=250)
        painel_checks.pack(padx=20, pady=5, fill="both", expand=True)

        check_vars = {}
        for item in itens_na_tela:
            var = ctk.BooleanVar(value=True)
            check_vars[item['codigo']] = var
            texto_chk = f"[{item['codigo']}] {item['descricao'][:50]}..." 
            chk = ctk.CTkCheckBox(painel_checks, text=texto_chk, variable=var)
            chk.pack(anchor="w", pady=2)

        lbl_status = ctk.CTkLabel(popup, text="Aguardando início...", text_color="gray")
        lbl_status.pack(pady=5)

        def disparar_robo():
            novo_grupo = combo_novo_grupo.get()
            if not novo_grupo: return
            
            itens_marcados = [cod for cod, var in check_vars.items() if var.get()]
            
            if not itens_marcados:
                messagebox.showwarning("Aviso", "Nenhum item selecionado.")
                return

            btn_iniciar.configure(state="disabled", text="Robô trabalhando...")
            combo_novo_grupo.configure(state="disabled")
            
            def atualizar_texto_status(msg):
                popup.after(0, lambda: lbl_status.configure(text=msg))

            self.controller.iniciar_migracao_lote(itens_marcados, novo_grupo, atualizar_texto_status, grupo_atual=grupo_atual)

        btn_iniciar = ctk.CTkButton(popup, text="▶ INICIAR MIGRAÇÃO", fg_color="#b8860b", hover_color="#8a6508", font=("Arial", 14, "bold"), height=40, command=disparar_robo)
        btn_iniciar.pack(pady=15)