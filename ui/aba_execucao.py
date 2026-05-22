import customtkinter as ctk
from tkinter import ttk

class AbaExecucao(ctk.CTkFrame):
    # Importado e Processado: sem coluna Arquiva no painel
    STATUS_SEM_ARQUIVA = frozenset({"IMPORTADO", "PROCESSADO"})
    # Importado e Processado: sem checkbox de Estoque
    STATUS_SEM_ESTOQUE = frozenset({"IMPORTADO", "PROCESSADO"})

    @classmethod
    def _normalizar_status(cls, status):
        return str(status or "").strip().upper()

    @classmethod
    def _pode_marcar_arquiva(cls, status):
        return cls._normalizar_status(status) not in cls.STATUS_SEM_ARQUIVA

    @classmethod
    def _mostra_checkbox_estoque(cls, status):
        return cls._normalizar_status(status) not in cls.STATUS_SEM_ESTOQUE

    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.montar_tela()

    def formatar_data_teclado(self, event):
        entry = event.widget
        texto = "".join([c for c in entry.get() if c.isdigit()])
        if event.keysym == "BackSpace": return
        novo_texto = ""
        if len(texto) <= 2: novo_texto = texto
        elif len(texto) <= 4: novo_texto = f"{texto[:2]}/{texto[2:]}"
        else: novo_texto = f"{texto[:2]}/{texto[2:4]}/{texto[4:8]}"
        entry.delete(0, 'end')
        entry.insert(0, novo_texto)

    def montar_tela(self):
        # Filtros
        frame_filtros = ctk.CTkFrame(self)
        frame_filtros.pack(pady=(10, 0), padx=10, fill="x")

        ctk.CTkLabel(frame_filtros, text="Data Emissão:").grid(row=0, column=0, padx=(10,2), pady=8)
        self.filtro_dt_ini = ctk.CTkEntry(frame_filtros, width=100, placeholder_text="DD/MM/YYYY")
        self.filtro_dt_ini.grid(row=0, column=1, padx=2, pady=8)
        self.filtro_dt_ini.bind("<KeyRelease>", self.formatar_data_teclado)
        
        ctk.CTkLabel(frame_filtros, text="até").grid(row=0, column=2, padx=2)
        self.filtro_dt_fim = ctk.CTkEntry(frame_filtros, width=100, placeholder_text="DD/MM/YYYY")
        self.filtro_dt_fim.grid(row=0, column=3, padx=2, pady=8)
        self.filtro_dt_fim.bind("<KeyRelease>", self.formatar_data_teclado)

        ctk.CTkLabel(frame_filtros, text="Cód. Int:").grid(row=0, column=4, padx=(10,2))
        self.filtro_cod = ctk.CTkEntry(frame_filtros, width=70)
        self.filtro_cod.grid(row=0, column=5, padx=2, pady=8)

        ctk.CTkLabel(frame_filtros, text="Nº Nota:").grid(row=0, column=6, padx=(10,2))
        self.filtro_nota = ctk.CTkEntry(frame_filtros, width=70)
        self.filtro_nota.grid(row=0, column=7, padx=2, pady=8)

        ctk.CTkLabel(frame_filtros, text="Status:").grid(row=0, column=8, padx=(10,2))
        self.filtro_status = ctk.CTkComboBox(
            frame_filtros, width=110,
            values=["Todos", "Importado", "Processado", "Erro", "Processando"],
        )
        self.filtro_status.set("Todos")
        self.filtro_status.grid(row=0, column=9, padx=2, pady=8)

        btn_filtrar = ctk.CTkButton(frame_filtros, text="🔍 Buscar", width=70, command=self.atualizar_tabela_dashboard)
        btn_filtrar.grid(row=0, column=10, padx=(15, 5), pady=8)
        btn_limpar = ctk.CTkButton(frame_filtros, text="Limpar", width=60, fg_color="gray", command=self.limpar_filtros_dashboard)
        btn_limpar.grid(row=0, column=11, padx=5, pady=8)

        # Tabela
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=25, fieldbackground="#2b2b2b", borderwidth=0)
        style.map('Treeview', background=[('selected', '#3b8ed0')])
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", font=('Arial', 10, 'bold'))

        frame_tabela = ctk.CTkFrame(self)
        frame_tabela.pack(pady=10, padx=10, fill="both", expand=True)

        colunas = ("cod_interno", "status", "forn", "nota", "data", "valor", "sit_nfe", "chave", "filial", "user", "erro", "observacao", "estoque", "arquiva")
        self.tabela_nf = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=8)
        
        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela_nf.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela_nf.xview)
        self.tabela_nf.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        self.tabela_nf.pack(side="left", fill="both", expand=True)

        self.tabela_nf.heading("cod_interno", text="Cód. Interno")
        self.tabela_nf.heading("status", text="Status")
        self.tabela_nf.heading("forn", text="Fornecedor")
        self.tabela_nf.heading("nota", text="No.Nota")
        self.tabela_nf.heading("data", text="Data Em.")
        self.tabela_nf.heading("valor", text="Valor")
        self.tabela_nf.heading("sit_nfe", text="Sit. NFe")
        self.tabela_nf.heading("chave", text="Chave NFe")
        self.tabela_nf.heading("filial", text="Filial")
        self.tabela_nf.heading("user", text="Usuário Inserção")
        self.tabela_nf.heading("erro", text="Erro Importação")
        self.tabela_nf.heading("observacao", text="Observação NFe")
        self.tabela_nf.heading("estoque", text="NFe p/ Estoque")
        self.tabela_nf.heading("arquiva", text="Arquiva")

        self.tabela_nf.column("cod_interno", width=90, anchor="center")
        self.tabela_nf.column("status", width=90, anchor="center")
        self.tabela_nf.column("forn", width=200, anchor="w") 
        self.tabela_nf.column("nota", width=80, anchor="center")
        self.tabela_nf.column("data", width=90, anchor="center")
        self.tabela_nf.column("valor", width=100, anchor="e") 
        self.tabela_nf.column("sit_nfe", width=100, anchor="center")
        self.tabela_nf.column("chave", width=260, anchor="center")
        self.tabela_nf.column("filial", width=80, anchor="center")
        self.tabela_nf.column("user", width=110, anchor="center")
        self.tabela_nf.column("erro", width=250, anchor="w")
        self.tabela_nf.column("observacao", width=250, anchor="w")
        self.tabela_nf.column("estoque", width=110, anchor="center")
        self.tabela_nf.column("arquiva", width=90, anchor="center")

        self.tabela_nf.bind("<ButtonRelease-1>", self.evento_clique_unico)
        self._popup_detalhe = None

        self.status_label = ctk.CTkLabel(self, text="Status: Aguardando...", font=("Arial", 12), text_color="gray")
        self.status_label.pack(pady=(0, 5))

        self.btn_iniciar_robo = ctk.CTkButton(self, text="▶ INICIAR AUTOMAÇÃO", font=("Arial", 16, "bold"), 
                                              fg_color="#8b0000", hover_color="#ff0000", height=45,
                                              command=self.chamar_robo)
        self.btn_iniciar_robo.pack(pady=(0, 15))
        
        self.after(500, self.atualizar_tabela_dashboard)

    def chamar_robo(self):
        self.btn_iniciar_robo.configure(state="disabled", text="Robô Trabalhando... Aguarde.", fg_color="gray")
        self.controller.iniciar_robo()

    def restaurar_botao_robo(self):
        try: self.btn_iniciar_robo.configure(state="normal", text="▶ INICIAR AUTOMAÇÃO", fg_color="#8b0000")
        except: pass

    def limpar_filtros_dashboard(self):
        if hasattr(self, 'filtro_dt_ini'):
            self.filtro_dt_ini.delete(0, 'end')
            self.filtro_dt_fim.delete(0, 'end')
            self.filtro_cod.delete(0, 'end')
            self.filtro_nota.delete(0, 'end')
            self.filtro_status.set("Todos")
        self.atualizar_tabela_dashboard()

    def atualizar_tabela_dashboard(self):
        if not hasattr(self, 'tabela_nf'): return
        
        try:
            for item in self.tabela_nf.get_children():
                self.tabela_nf.delete(item)
                
            dt_ini = self.filtro_dt_ini.get().strip() if hasattr(self, 'filtro_dt_ini') else ""
            dt_fim = self.filtro_dt_fim.get().strip() if hasattr(self, 'filtro_dt_fim') else ""
            cod = self.filtro_cod.get().strip() if hasattr(self, 'filtro_cod') else ""
            status = self.filtro_status.get() if hasattr(self, 'filtro_status') else "Todos"
            nota = self.filtro_nota.get().strip() if hasattr(self, 'filtro_nota') else ""

            print(f"\\n[DEBUG TELA] 🔍 Clicou em Buscar. Filtros -> Status: '{status}', Nota: '{nota}'")

            notas = self.controller.obter_notas_dashboard(dt_ini, dt_fim, cod, status, nota)
            
            if not notas:
                print("[DEBUG TELA] ⚠️ Nenhuma nota foi retornada pelo banco de dados.")
                return
                
            print(f"[DEBUG TELA] ✅ Injetando {len(notas)} notas na tabela...")

            for nota_item in notas:
                def limpa_none(valor): return "" if valor is None else str(valor)
                
                try:
                    # Tenta ler os dados com proteção contra formato incorreto (.get)
                    status_atual = limpa_none(nota_item.get('status')).strip().upper()
                    
                    if not self._mostra_checkbox_estoque(status_atual):
                        caixa_estoque = ""
                    else:
                        estoque_banco = limpa_none(nota_item.get('nfe_estoque'))
                        caixa_estoque = "   [ ☑ ]   " if "☑" in estoque_banco else "   [ ☐ ]   "

                    if self._pode_marcar_arquiva(status_atual):
                        arquiva_banco = limpa_none(nota_item.get('nfe_arquiva'))
                        caixa_arquiva = "   [ ☑ ]   " if "☑" in arquiva_banco else "   [ ☐ ]   "
                    else:
                        caixa_arquiva = ""

                    self.tabela_nf.insert("", "end", values=(
                        limpa_none(nota_item.get('codigo_interno')), 
                        limpa_none(nota_item.get('status')), 
                        limpa_none(nota_item.get('fornecedor')), 
                        limpa_none(nota_item.get('num_nota')), 
                        limpa_none(nota_item.get('data_em')), 
                        limpa_none(nota_item.get('valor')), 
                        limpa_none(nota_item.get('sit_nfe')), 
                        limpa_none(nota_item.get('chave_nfe')), 
                        limpa_none(nota_item.get('filial')), 
                        limpa_none(nota_item.get('user_ins')),
                        limpa_none(nota_item.get('erro_importacao')), 
                        limpa_none(nota_item.get('observacao_nfe')),
                        caixa_estoque,
                        caixa_arquiva,
                    ))
                except AttributeError as e:
                    print(f"[ERRO DE DADO] ❌ O banco retornou um formato inesperado. Erro: {e}")
                    break # Para a leitura para não flodar o console
                    
        except Exception as e:
            print(f"[ERRO CRÍTICO NA TABELA] ❌ Falha ao atualizar: {e}")

    def evento_clique_unico(self, event):
        regiao = self.tabela_nf.identify_region(event.x, event.y)
        if regiao != "cell":
            return
        coluna_clicada = self.tabela_nf.identify_column(event.x)
        item_clicado = self.tabela_nf.identify_row(event.y)
        if not item_clicado:
            return

        valores = list(self.tabela_nf.item(item_clicado, "values"))
        status = str(valores[1]).strip().upper() if len(valores) > 1 and valores[1] else ""
        chave_da_nota = str(valores[7]).strip() if len(valores) > 7 else ""
        erro = str(valores[10]).strip() if len(valores) > 10 else ""
        observacao = str(valores[11]).strip() if len(valores) > 11 else ""

        # Coluna Arquiva (#14) — só Erro ou Importado
        if coluna_clicada == "#14":
            if not self._pode_marcar_arquiva(status):
                return
            if not chave_da_nota or len(valores) < 14 or not str(valores[13]).strip():
                return
            estado_atual = valores[13]
            if "☑" in estado_atual:
                novo_estado_tela = "   [ ☐ ]   "
                estado_banco = "☐"
            else:
                novo_estado_tela = "   [ ☑ ]   "
                estado_banco = "☑"
            valores[13] = novo_estado_tela
            self.tabela_nf.item(item_clicado, values=valores)
            self.controller.atualizar_arquiva(chave_da_nota, estado_banco)
            return

        # Coluna NFe p/ Estoque (#13) — alternar checkbox
        if coluna_clicada == "#13":
            if not self._mostra_checkbox_estoque(status) or len(valores) < 13 or not str(valores[12]).strip():
                return
            estado_atual = valores[12]
            if "☑" in estado_atual:
                novo_estado_tela = "   [ ☐ ]   "
                estado_banco = "☐"
            else:
                novo_estado_tela = "   [ ☑ ]   "
                estado_banco = "☑"
            valores[12] = novo_estado_tela
            self.tabela_nf.item(item_clicado, values=valores)
            self.controller.atualizar_estoque(chave_da_nota, estado_banco)
            return

        # Só abre popup ao clicar na coluna Observação (#12)
        if coluna_clicada == "#12":
            if observacao:
                self.mostrar_popup_texto("Observação da NFe", observacao)
            return

        # Só abre popup ao clicar na coluna Erro Importação (#11), se houver erro
        if coluna_clicada == "#11":
            if status == "ERRO" and erro:
                self.mostrar_popup_texto("Motivo do Erro", erro)
            return

    def mostrar_popup_texto(self, titulo, texto):
        if self._popup_detalhe and self._popup_detalhe.winfo_exists():
            self._popup_detalhe.destroy()
        popup = ctk.CTkToplevel(self)
        self._popup_detalhe = popup
        popup.title(titulo)
        popup.geometry("600x350")
        popup.attributes("-topmost", True)
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (600 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (350 // 2)
        popup.geometry(f"+{x}+{y}")
        
        lbl = ctk.CTkLabel(popup, text=titulo, font=("Arial", 16, "bold"), text_color="#3b8ed0")
        lbl.pack(pady=(15, 5))
        caixa_texto = ctk.CTkTextbox(popup, width=550, height=220, wrap="word", font=("Arial", 14))
        caixa_texto.pack(pady=10, padx=20)
        caixa_texto.insert("0.0", texto)
        caixa_texto.configure(state="disabled")
        def fechar():
            if popup.winfo_exists():
                popup.destroy()
            self._popup_detalhe = None

        btn_fechar = ctk.CTkButton(popup, text="Fechar", command=fechar, fg_color="gray", width=120)
        btn_fechar.pack(pady=5)
        popup.protocol("WM_DELETE_WINDOW", fechar)