import customtkinter as ctk
from tkinter import ttk, messagebox
import re
import database_setup as db
from ui.combo_busca_grupo import ComboBuscaGrupo
from ui.aba_logs import AbaLogs
from ui.entry_data_calendario import EntryDataComCalendario
from ui.relatorio_execucao import abrir_relatorio_pdf, salvar_relatorio_excel

class AbaExecucao(ctk.CTkFrame):
    # Importado e Processado: sem coluna Arquiva no painel
    STATUS_SEM_ARQUIVA = frozenset({"IMPORTADO", "PROCESSADO"})
    # Importado e Processado: sem checkbox de Estoque
    STATUS_SEM_ESTOQUE = frozenset({"IMPORTADO", "PROCESSADO"})
    COR_LINHA_CLARA = "#3d3d3d"
    COR_LINHA_ESCURA = "#2e2e2e"
    COR_SELECAO = "#3b8ed0"

    @classmethod
    def _normalizar_status(cls, status):
        return str(status or "").strip().upper()

    @classmethod
    def _nota_arquivada_bloqueada(cls, nota_item):
        """Arquivo indisponível: arquivada fixa (☑) sem desmarcar; estoque oculto."""
        return db.nota_erro_arquivo_indisponivel(
            (nota_item or {}).get('erro_importacao'),
        )

    @classmethod
    def _pode_marcar_arquiva(cls, status, nota_item=None):
        if cls._normalizar_status(status) in cls.STATUS_SEM_ARQUIVA:
            return False
        if nota_item and cls._nota_arquivada_bloqueada(nota_item):
            return False
        return True

    @classmethod
    def _mostra_checkbox_estoque(cls, status, nota_item=None):
        if cls._normalizar_status(status) in cls.STATUS_SEM_ESTOQUE:
            return False
        if nota_item and cls._nota_arquivada_bloqueada(nota_item):
            return False
        return True

    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.notas_filtradas_atuais = []
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

    def _obter_limite_linhas(self):
        valor = self.filtro_limite.get().strip() if hasattr(self, 'filtro_limite') else "100"
        if not valor or valor.lower() == "todos":
            return None
        try:
            return max(1, int(valor))
        except Exception:
            if hasattr(self, 'filtro_limite'):
                self.filtro_limite.set("100")
            return 100

    def montar_tela(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Filtros
        self.frame_filtros = ctk.CTkFrame(self)
        self.frame_filtros.grid(row=0, column=0, pady=(10, 0), padx=10, sticky="ew")
        self.frame_filtros.bind("<Configure>", self._reorganizar_filtros)

        self.lbl_filtro_tipo_data = ctk.CTkLabel(self.frame_filtros, text="Filtrar por:")
        self.filtro_tipo_data = ctk.CTkComboBox(
            self.frame_filtros,
            width=150,
            values=["Data Inserção", "Data Emissão NFe"],
        )
        self.filtro_tipo_data.set("Data Inserção")

        self.lbl_filtro_dt_ini = ctk.CTkLabel(self.frame_filtros, text="De:")
        self.filtro_dt_ini = EntryDataComCalendario(self.frame_filtros, width=100)

        self.lbl_filtro_dt_fim = ctk.CTkLabel(self.frame_filtros, text="até")
        self.filtro_dt_fim = EntryDataComCalendario(self.frame_filtros, width=100)

        self.lbl_filtro_cod = ctk.CTkLabel(self.frame_filtros, text="Cód. Int:")
        self.filtro_cod = ctk.CTkEntry(self.frame_filtros, width=70)

        self.lbl_filtro_nota = ctk.CTkLabel(self.frame_filtros, text="Nº Nota:")
        self.filtro_nota = ctk.CTkEntry(self.frame_filtros, width=70)

        self.lbl_filtro_fornecedor = ctk.CTkLabel(self.frame_filtros, text="Fornecedor:")
        self._fornecedores_disponiveis = self.controller.obter_fornecedores_unicos()
        self.filtro_fornecedor = ComboBuscaGrupo(
            self.frame_filtros,
            self._fornecedores_disponiveis,
            width=200,
            valor_inicial="Todos",
            on_buscar_enter=self.controller.buscar_fornecedor_por_nome,
            on_enter_acao=self.buscar_tabela_dashboard,
        )

        self.lbl_filtro_status = ctk.CTkLabel(self.frame_filtros, text="Status:")
        self.filtro_status = ctk.CTkComboBox(
            self.frame_filtros, width=110,
            values=["Erro", "Importado", "Processado", "Processando", "Arquivada", "Todos"],
        )
        self.filtro_status.set("Erro")

        self.lbl_filtro_limite = ctk.CTkLabel(self.frame_filtros, text="Limite:")
        self.filtro_limite = ctk.CTkComboBox(
            self.frame_filtros, width=90, values=["100", "200", "500", "1000", "Todos"],
        )
        self.filtro_limite.set("100")

        self.btn_filtrar = ctk.CTkButton(
            self.frame_filtros, text="🔍 Buscar", width=70, command=self.buscar_tabela_dashboard,
        )
        self.btn_limpar = ctk.CTkButton(
            self.frame_filtros, text="Limpar", width=60, fg_color="gray",
            command=self.limpar_filtros_dashboard,
        )
        self.btn_logs_robo = ctk.CTkButton(
            self.frame_filtros,
            text="📋 Logs NFe",
            width=130,
            fg_color="#1565c0",
            hover_color="#0d47a1",
            command=self._abrir_logs_robo,
        )
        self.btn_lancar_lote = ctk.CTkButton(
            self.frame_filtros,
            text="Lançar nota em lote",
            width=150,
            fg_color="#6a1b9a",
            hover_color="#4a148c",
            command=self._abrir_popup_lancar_lote,
        )
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

        self._reorganizar_filtros()

        # Tabela (linhas alternadas — zebra)
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=self.COR_LINHA_ESCURA,
            foreground="white",
            rowheight=28,
            fieldbackground=self.COR_LINHA_ESCURA,
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", self.COR_SELECAO)],
            foreground=[("selected", "white")],
        )
        style.configure(
            "Treeview.Heading",
            background="#1f538d",
            foreground="white",
            font=("Arial", 10, "bold"),
        )

        frame_tabela = ctk.CTkFrame(self)
        frame_tabela.grid(row=1, column=0, pady=10, padx=10, sticky="nsew")
        frame_tabela.grid_columnconfigure(0, weight=1)
        frame_tabela.grid_rowconfigure(0, weight=1)

        colunas = (
            "insercao", "cod_interno", "status", "forn", "nota", "placa", "km",
            "data", "valor", "sit_nfe", "filial", "user", "erro",
            "observacao", "estoque", "arquiva",
        )
        self.tabela_nf = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=8)
        
        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela_nf.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela_nf.xview)
        self.tabela_nf.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tabela_nf.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.tabela_nf.heading("insercao", text="Inserção")
        self.tabela_nf.heading("cod_interno", text="Cód. Interno")
        self.tabela_nf.heading("status", text="Status")
        self.tabela_nf.heading("forn", text="Fornecedor")
        self.tabela_nf.heading("nota", text="No.Nota")
        self.tabela_nf.heading("placa", text="Placa")
        self.tabela_nf.heading("km", text="KM")
        self.tabela_nf.heading("data", text="Data Em.")
        self.tabela_nf.heading("valor", text="Valor")
        self.tabela_nf.heading("sit_nfe", text="Sit. NFe")
        self.tabela_nf.heading("filial", text="Filial")
        self.tabela_nf.heading("user", text="Usuário Inserção")
        self.tabela_nf.heading("erro", text="Erro Importação")
        self.tabela_nf.heading("observacao", text="Observação NFe")
        self.tabela_nf.heading("estoque", text="NFe p/ Estoque")
        self.tabela_nf.heading("arquiva", text="Arquiva")

        self.tabela_nf.column("insercao", width=155, anchor="center")
        self.tabela_nf.column("cod_interno", width=82, anchor="center")
        self.tabela_nf.column("status", width=84, anchor="center")
        self.tabela_nf.column("forn", width=180, anchor="w")
        self.tabela_nf.column("nota", width=74, anchor="center")
        self.tabela_nf.column("placa", width=88, anchor="center")
        self.tabela_nf.column("km", width=72, anchor="center")
        self.tabela_nf.column("data", width=88, anchor="center")
        self.tabela_nf.column("valor", width=92, anchor="e")
        self.tabela_nf.column("sit_nfe", width=84, anchor="center")
        self.tabela_nf.column("filial", width=64, anchor="center")
        self.tabela_nf.column("user", width=96, anchor="center")
        self.tabela_nf.column("erro", width=210, anchor="w")
        self.tabela_nf.column("observacao", width=210, anchor="w")
        self.tabela_nf.column("estoque", width=60, anchor="center")
        self.tabela_nf.column("arquiva", width=60, anchor="center")

        self.tabela_nf.tag_configure("linha_clara", background=self.COR_LINHA_CLARA)
        self.tabela_nf.tag_configure("linha_escura", background=self.COR_LINHA_ESCURA)

        self.tabela_nf.bind("<ButtonRelease-1>", self.evento_clique_unico)
        self.tabela_nf.bind("<Double-1>", self.evento_duplo_clique_edicao)
        self._popup_detalhe = None

        frame_rodape = ctk.CTkFrame(self, fg_color="transparent")
        frame_rodape.grid(row=2, column=0, pady=(0, 15), padx=10, sticky="ew")
        frame_rodape.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            frame_rodape, text="Status: Aguardando...", font=("Arial", 12), text_color="gray",
        )
        self.status_label.grid(row=0, column=0, sticky="w", pady=(0, 2))

        self.lbl_dica_placa_km = ctk.CTkLabel(
            frame_rodape,
            text="Dica: duplo clique nas colunas Placa e KM para editar (sem ponto, espaço ou traço).",
            font=("Arial", 11),
            text_color="#9ecbff",
        )
        self.lbl_dica_placa_km.grid(row=1, column=0, sticky="w", pady=(0, 5))

        self._cor_botao_verde = "#2e7d32"
        self._cor_botao_verde_hover = "#1b5e20"
        self._cor_botao_vermelho = "#c62828"
        self._cor_botao_vermelho_hover = "#b71c1c"

        self.btn_iniciar_robo = ctk.CTkButton(
            frame_rodape,
            text="▶ INICIAR AUTOMAÇÃO",
            font=("Arial", 16, "bold"),
            fg_color=self._cor_botao_verde,
            hover_color=self._cor_botao_verde_hover,
            height=45,
            command=self.chamar_robo,
        )
        self.btn_iniciar_robo.grid(row=0, column=1, rowspan=2, sticky="e")

        self.after(500, self.atualizar_tabela_dashboard)

    def _grid_filtro(self, label, widget, row, col):
        label.grid(row=row, column=col, padx=(10, 2), pady=8, sticky="w")
        widget.grid(row=row, column=col + 1, padx=2, pady=8, sticky="ew")

    def _reorganizar_filtros(self, event=None):
        largura = 0
        if event is not None:
            largura = event.width
        else:
            try:
                largura = self.frame_filtros.winfo_width()
            except Exception:
                largura = 0

        widgets = [
            self.lbl_filtro_tipo_data, self.filtro_tipo_data,
            self.lbl_filtro_dt_ini, self.filtro_dt_ini,
            self.lbl_filtro_dt_fim, self.filtro_dt_fim,
            self.lbl_filtro_cod, self.filtro_cod,
            self.lbl_filtro_nota, self.filtro_nota,
            self.lbl_filtro_fornecedor, self.filtro_fornecedor,
            self.lbl_filtro_status, self.filtro_status,
            self.lbl_filtro_limite, self.filtro_limite,
            self.btn_filtrar, self.btn_limpar, self.btn_lancar_lote, self.btn_logs_robo,
            self.lbl_imprimir_relatorio,
        ]
        for widget in widgets:
            widget.grid_forget()

        for col in range(16):
            self.frame_filtros.grid_columnconfigure(col, weight=0)

        if largura >= 1240:
            self._grid_filtro(self.lbl_filtro_tipo_data, self.filtro_tipo_data, 0, 0)
            self._grid_filtro(self.lbl_filtro_dt_ini, self.filtro_dt_ini, 0, 2)
            self._grid_filtro(self.lbl_filtro_dt_fim, self.filtro_dt_fim, 0, 4)
            self._grid_filtro(self.lbl_filtro_cod, self.filtro_cod, 0, 6)
            self._grid_filtro(self.lbl_filtro_nota, self.filtro_nota, 0, 8)
            self.lbl_filtro_fornecedor.grid(row=1, column=0, padx=(10, 2), pady=8, sticky="w")
            self.filtro_fornecedor.grid(row=1, column=1, columnspan=3, padx=2, pady=8, sticky="ew")
            self._grid_filtro(self.lbl_filtro_status, self.filtro_status, 1, 4)
            self._grid_filtro(self.lbl_filtro_limite, self.filtro_limite, 1, 6)
            self.btn_filtrar.grid(row=1, column=8, padx=(15, 5), pady=8, sticky="ew")
            self.btn_limpar.grid(row=1, column=9, padx=5, pady=8, sticky="ew")
            self.btn_lancar_lote.grid(row=0, column=10, padx=(10, 5), pady=8, sticky="e")
            self.btn_logs_robo.grid(row=0, column=11, padx=(5, 5), pady=8, sticky="e")
            self.frame_filtros.grid_columnconfigure(10, weight=1)
            self.lbl_imprimir_relatorio.grid(
                row=1, column=11, padx=(10, 10), pady=8, sticky="e",
            )
            return

        if largura >= 840:
            self._grid_filtro(self.lbl_filtro_tipo_data, self.filtro_tipo_data, 0, 0)
            self._grid_filtro(self.lbl_filtro_dt_ini, self.filtro_dt_ini, 0, 2)
            self._grid_filtro(self.lbl_filtro_dt_fim, self.filtro_dt_fim, 0, 4)
            self._grid_filtro(self.lbl_filtro_cod, self.filtro_cod, 1, 0)
            self._grid_filtro(self.lbl_filtro_nota, self.filtro_nota, 1, 2)
            self.lbl_filtro_fornecedor.grid(row=1, column=4, padx=(15, 2), pady=8, sticky="w")
            self.filtro_fornecedor.grid(row=1, column=5, columnspan=2, padx=2, pady=8, sticky="ew")
            self._grid_filtro(self.lbl_filtro_status, self.filtro_status, 2, 0)
            self._grid_filtro(self.lbl_filtro_limite, self.filtro_limite, 2, 2)
            self.btn_filtrar.grid(row=2, column=4, padx=(15, 5), pady=8, sticky="ew")
            self.btn_limpar.grid(row=2, column=5, padx=5, pady=8, sticky="ew")
            self.btn_lancar_lote.grid(row=1, column=6, padx=(10, 5), pady=8, sticky="e")
            self.btn_logs_robo.grid(row=1, column=7, padx=(5, 5), pady=8, sticky="e")
            self.frame_filtros.grid_columnconfigure(6, weight=1)
            self.lbl_imprimir_relatorio.grid(
                row=2, column=7, padx=(10, 10), pady=8, sticky="e",
            )
            return

        self._grid_filtro(self.lbl_filtro_tipo_data, self.filtro_tipo_data, 0, 0)
        self._grid_filtro(self.lbl_filtro_dt_ini, self.filtro_dt_ini, 0, 2)
        self._grid_filtro(self.lbl_filtro_dt_fim, self.filtro_dt_fim, 1, 0)
        self._grid_filtro(self.lbl_filtro_cod, self.filtro_cod, 1, 2)
        self._grid_filtro(self.lbl_filtro_nota, self.filtro_nota, 2, 0)
        self.lbl_filtro_fornecedor.grid(row=2, column=2, padx=(10, 2), pady=8, sticky="w")
        self.filtro_fornecedor.grid(row=2, column=3, columnspan=2, padx=2, pady=8, sticky="ew")
        self._grid_filtro(self.lbl_filtro_status, self.filtro_status, 3, 0)
        self._grid_filtro(self.lbl_filtro_limite, self.filtro_limite, 3, 2)
        self.btn_filtrar.grid(row=4, column=0, padx=(10, 5), pady=8, sticky="ew")
        self.btn_limpar.grid(row=4, column=1, padx=5, pady=8, sticky="ew")
        self.btn_lancar_lote.grid(row=3, column=0, columnspan=2, padx=(10, 5), pady=8, sticky="ew")
        self.btn_logs_robo.grid(row=3, column=2, columnspan=3, padx=(10, 5), pady=8, sticky="e")
        self.frame_filtros.grid_columnconfigure(4, weight=1)
        self.lbl_imprimir_relatorio.grid(
            row=4, column=2, columnspan=3, padx=(10, 10), pady=(0, 8), sticky="e",
        )

    def _abrir_logs_robo(self):
        AbaLogs.abrir_popup(self)

    @staticmethod
    def _parsear_notas_lote(texto):
        partes = re.split(r"[,;\s]+", str(texto or "").strip())
        notas = []
        vistos = set()
        for parte in partes:
            nota = str(parte or "").strip()
            if not nota or nota in vistos:
                continue
            vistos.add(nota)
            notas.append(nota)
        return notas

    def preparar_filtro_nota_lote(self, nota):
        if not hasattr(self, "filtro_nota"):
            return
        self.filtro_nota.delete(0, "end")
        self.filtro_nota.insert(0, str(nota or "").strip())
        self.atualizar_tabela_dashboard(perguntar_lancamento=False)

    def _abrir_popup_lancar_lote(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Lançar nota em lote")
        popup.geometry("520x260")
        popup.resizable(False, False)
        popup.attributes("-topmost", True)
        popup.transient(self.winfo_toplevel())
        popup.grab_set()

        popup.update_idletasks()
        x = self.winfo_rootx() + max((self.winfo_width() - 520) // 2, 0)
        y = self.winfo_rooty() + max((self.winfo_height() - 260) // 2, 0)
        popup.geometry(f"520x260+{x}+{y}")

        ctk.CTkLabel(
            popup,
            text="Lançar notas em lote",
            font=("Arial", 16, "bold"),
            text_color="#6a1b9a",
        ).pack(pady=(16, 6))

        ctk.CTkLabel(
            popup,
            text="Informe os números das notas separados por vírgula.\nExemplo: 1111, 3333, 52566",
            justify="center",
        ).pack(pady=(0, 10))

        entry_notas = ctk.CTkEntry(
            popup,
            width=460,
            placeholder_text="1111, 3333, 52566",
        )
        entry_notas.pack(pady=(0, 8))
        entry_notas.focus_set()

        lbl_status = ctk.CTkLabel(popup, text="", text_color="gray")
        lbl_status.pack(pady=(0, 6))

        frame_botoes = ctk.CTkFrame(popup, fg_color="transparent")
        frame_botoes.pack(pady=8, padx=16, fill="x")
        frame_botoes.grid_columnconfigure((0, 1), weight=1)

        def fechar():
            popup.grab_release()
            popup.destroy()

        def iniciar_lote():
            notas = self._parsear_notas_lote(entry_notas.get())
            if not notas:
                lbl_status.configure(
                    text="Informe ao menos um número de nota.",
                    text_color="#e53935",
                )
                return
            lbl_status.configure(
                text=f"Iniciando lote com {len(notas)} nota(s)...",
                text_color="#3b8ed0",
            )
            popup.update_idletasks()
            fechar()
            self.controller.iniciar_robo_lote(notas)

        ctk.CTkButton(
            frame_botoes,
            text="Iniciar lote",
            fg_color="#6a1b9a",
            hover_color="#4a148c",
            command=iniciar_lote,
        ).grid(row=0, column=0, padx=6, sticky="ew")

        ctk.CTkButton(
            frame_botoes,
            text="Cancelar",
            fg_color="gray",
            command=fechar,
        ).grid(row=0, column=1, padx=6, sticky="ew")

        popup.protocol("WM_DELETE_WINDOW", fechar)
        entry_notas.bind("<Return>", lambda _event: iniciar_lote())

    def chamar_robo(self):
        self.controller.iniciar_robo()

    def buscar_tabela_dashboard(self):
        self.atualizar_tabela_dashboard(perguntar_lancamento=True)

    def _perguntar_compra_estoque(self, nota_filtrada):
        return messagebox.askyesno(
            "Compra para estoque",
            f"A nota {nota_filtrada} é uma compra para estoque?",
        )

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
        frame_botoes.grid_columnconfigure((0, 1, 2), weight=1)

        def fechar(valor):
            resposta["valor"] = valor
            popup.grab_release()
            popup.destroy()

        ctk.CTkButton(
            frame_botoes,
            text="PDF",
            fg_color="#1f538d",
            hover_color="#163d68",
            command=lambda: fechar("pdf"),
        ).grid(row=0, column=0, padx=6, sticky="ew")

        ctk.CTkButton(
            frame_botoes,
            text="XLS",
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            command=lambda: fechar("xls"),
        ).grid(row=0, column=1, padx=6, sticky="ew")

        ctk.CTkButton(
            frame_botoes,
            text="Cancelar",
            fg_color="#c62828",
            hover_color="#b71c1c",
            command=lambda: fechar(None),
        ).grid(row=0, column=2, padx=6, sticky="ew")

        popup.protocol("WM_DELETE_WINDOW", lambda: fechar(None))
        self.wait_window(popup)
        return resposta["valor"]

    def _campo_data_filtro(self):
        escolha = self.filtro_tipo_data.get().strip() if hasattr(self, 'filtro_tipo_data') else ''
        if escolha == 'Data Emissão NFe':
            return 'emissao'
        return 'insercao'

    def _resumo_filtros_relatorio(self):
        return {
            "Critério de data": self.filtro_tipo_data.get().strip(),
            "Data Inicial": self.filtro_dt_ini.get().strip(),
            "Data Final": self.filtro_dt_fim.get().strip(),
            "Cód. Interno": self.filtro_cod.get().strip(),
            "Nº Nota": self.filtro_nota.get().strip(),
            "Fornecedor": self.filtro_fornecedor.get().strip(),
            "Status": self.filtro_status.get().strip(),
            "Limite linhas": self.filtro_limite.get().strip(),
        }

    def _coletar_linhas_tabela(self):
        linhas = []
        for item in self.tabela_nf.get_children():
            linhas.append(list(self.tabela_nf.item(item, "values")))
        return linhas

    def imprimir_relatorio_filtrado(self):
        self.atualizar_tabela_dashboard()
        linhas = self._coletar_linhas_tabela()
        if not linhas:
            messagebox.showwarning(
                "Aviso", "Nenhuma nota está visível na tabela para gerar o relatório.",
            )
            return

        filtros = self._resumo_filtros_relatorio()
        cabecalhos = [
            self.tabela_nf.heading(coluna).get("text", coluna)
            for coluna in self.tabela_nf["columns"]
        ]
        escolha = self._perguntar_formato_relatorio()
        if not escolha:
            return

        if escolha == "pdf":
            caminho = abrir_relatorio_pdf(filtros, cabecalhos, linhas)
            self.status_label.configure(
                text=f"Status: PDF aberto no navegador com botão de impressão A4 ({len(linhas)} notas).",
                text_color="#3b8ed0",
            )
            return

        caminho = salvar_relatorio_excel(filtros, cabecalhos, linhas)
        messagebox.showinfo(
            "Relatório XLSX",
            f"Relatório salvo em:\n{caminho}",
        )
        self.status_label.configure(
            text=f"Status: XLSX salvo em Downloads ({len(linhas)} notas).",
            text_color="#3b8ed0",
        )

    def botao_robo_em_execucao(self):
        """Vermelho: clique de novo para parar e fechar o navegador."""
        try:
            self.btn_iniciar_robo.configure(
                state="normal",
                text="⏹ PARAR — fecha todo o navegador",
                fg_color=self._cor_botao_vermelho,
                hover_color=self._cor_botao_vermelho_hover,
            )
        except Exception:
            pass

    def restaurar_botao_robo(self):
        try:
            self.btn_iniciar_robo.configure(
                state="normal",
                text="▶ INICIAR AUTOMAÇÃO",
                fg_color=self._cor_botao_verde,
                hover_color=self._cor_botao_verde_hover,
            )
        except Exception:
            pass

    def limpar_filtros_dashboard(self):
        if hasattr(self, 'filtro_dt_ini'):
            self.filtro_dt_ini.delete(0, 'end')
            self.filtro_dt_fim.delete(0, 'end')
            self.filtro_cod.delete(0, 'end')
            self.filtro_nota.delete(0, 'end')
            self._fornecedores_disponiveis = self.controller.obter_fornecedores_unicos()
            self.filtro_fornecedor.atualizar_valores(self._fornecedores_disponiveis)
            self.filtro_fornecedor.set("Todos")
            self.filtro_status.set("Erro")
            self.filtro_limite.set("100")
            if hasattr(self, 'filtro_tipo_data'):
                self.filtro_tipo_data.set("Data Inserção")
        self.atualizar_tabela_dashboard()

    def _avaliar_lancamento_nota_filtrada(self, notas, nota_filtrada):
        nota_filtrada = str(nota_filtrada or "").strip()
        if not nota_filtrada:
            return

        if not notas:
            resposta = messagebox.askyesno(
                "Lançar nota",
                f"A nota {nota_filtrada} não foi encontrada no painel do robô.\n\n"
                "Deseja tentar o lançamento agora mesmo assim?",
            )
            if resposta:
                compra_estoque = self._perguntar_compra_estoque(nota_filtrada)
                self.controller.iniciar_robo_para_nota(
                    nota_filtrada, compra_estoque=compra_estoque,
                )
            return

        nota_item = next(
            (
                item for item in notas
                if str((item or {}).get('num_nota') or '').strip() == nota_filtrada
            ),
            None,
        )
        if not nota_item:
            resposta = messagebox.askyesno(
                "Lançar nota",
                f"A nota {nota_filtrada} não apareceu exatamente no painel do robô.\n\n"
                "Deseja tentar o lançamento agora mesmo assim?",
            )
            if resposta:
                compra_estoque = self._perguntar_compra_estoque(nota_filtrada)
                self.controller.iniciar_robo_para_nota(
                    nota_filtrada, compra_estoque=compra_estoque,
                )
            return

        status_atual = self._normalizar_status((nota_item or {}).get('status'))
        if status_atual in ("IMPORTADO", "PROCESSADO"):
            resposta = messagebox.askyesno(
                "Lançar nota",
                f"A nota {nota_filtrada} já consta como "
                f"{status_atual.title()} no painel.\n\n"
                "Deseja tentar o lançamento novamente?",
            )
            if resposta:
                self.controller.iniciar_robo_para_nota(nota_filtrada)
            return

        resposta = messagebox.askyesno(
            "Lançar nota",
            f"A nota {nota_filtrada} está com status "
            f"'{status_atual or 'SEM STATUS'}'.\n\n"
            "Deseja fazer o lançamento agora?",
        )
        if resposta:
            self.controller.iniciar_robo_para_nota(nota_filtrada)

    def atualizar_tabela_dashboard(self, perguntar_lancamento=False):
        if not hasattr(self, 'tabela_nf'): return
        
        try:
            for item in self.tabela_nf.get_children():
                self.tabela_nf.delete(item)
                
            dt_ini = self.filtro_dt_ini.get().strip() if hasattr(self, 'filtro_dt_ini') else ""
            dt_fim = self.filtro_dt_fim.get().strip() if hasattr(self, 'filtro_dt_fim') else ""
            cod = self.filtro_cod.get().strip() if hasattr(self, 'filtro_cod') else ""
            status = self.filtro_status.get() if hasattr(self, 'filtro_status') else "Todos"
            nota = self.filtro_nota.get().strip() if hasattr(self, 'filtro_nota') else ""
            fornecedor = (
                self.filtro_fornecedor.get().strip()
                if hasattr(self, 'filtro_fornecedor') else "Todos"
            )
            limite = self._obter_limite_linhas()

            print(
                f"\\n[DEBUG TELA] 🔍 Clicou em Buscar. Filtros -> "
                f"Status: '{status}', Nota: '{nota}', Fornecedor: '{fornecedor}'"
            )

            notas = self.controller.obter_notas_dashboard(
                dt_ini, dt_fim, cod, status, nota,
                limite=limite,
                campo_data=self._campo_data_filtro(),
                fornecedor=fornecedor,
            )
            self.notas_filtradas_atuais = notas or []
            
            if not notas:
                print("[DEBUG TELA] ⚠️ Nenhuma nota foi retornada pelo banco de dados.")
                self.status_label.configure(text="Status: exibindo 0 linha(s).", text_color="gray")
                if perguntar_lancamento and nota:
                    self._avaliar_lancamento_nota_filtrada(notas, nota)
                return
                
            print(f"[DEBUG TELA] ✅ Injetando {len(notas)} notas na tabela...")

            for idx, nota_item in enumerate(notas):
                def limpa_none(valor): return "" if valor is None else str(valor)
                tag_linha = "linha_clara" if idx % 2 == 0 else "linha_escura"

                try:
                    # Tenta ler os dados com proteção contra formato incorreto (.get)
                    status_atual = limpa_none(nota_item.get('status')).strip().upper()
                    arquivada_fixa = self._nota_arquivada_bloqueada(nota_item)

                    if not self._mostra_checkbox_estoque(status_atual, nota_item):
                        caixa_estoque = ""
                    else:
                        estoque_banco = limpa_none(nota_item.get('nfe_estoque'))
                        caixa_estoque = "☑" if "☑" in estoque_banco else "☐"

                    if arquivada_fixa:
                        caixa_arquiva = "☑"
                    elif self._pode_marcar_arquiva(status_atual, nota_item):
                        arquiva_banco = limpa_none(nota_item.get('nfe_arquiva'))
                        caixa_arquiva = "☑" if "☑" in arquiva_banco else "☐"
                    else:
                        caixa_arquiva = ""

                    self.tabela_nf.insert(
                        "", "end",
                        values=(
                            db.formatar_data_insercao_exibicao(nota_item.get('data_insercao')),
                            limpa_none(nota_item.get('codigo_interno')),
                            db.status_exibicao_painel(nota_item),
                            limpa_none(nota_item.get('fornecedor')),
                            limpa_none(nota_item.get('num_nota')),
                            db.normalizar_placa_painel(nota_item.get('painel_placa')),
                            db.normalizar_km_painel(nota_item.get('painel_km')),
                            limpa_none(nota_item.get('data_em')),
                            limpa_none(nota_item.get('valor')),
                            limpa_none(nota_item.get('sit_nfe')),
                            limpa_none(nota_item.get('filial')),
                            limpa_none(nota_item.get('user_ins')),
                            limpa_none(nota_item.get('erro_importacao')),
                            limpa_none(nota_item.get('observacao_nfe')),
                            caixa_estoque,
                            caixa_arquiva,
                        ),
                        tags=(tag_linha,),
                    )
                except AttributeError as e:
                    print(f"[ERRO DE DADO] ❌ O banco retornou um formato inesperado. Erro: {e}")
                    break # Para a leitura para não flodar o console

            self.status_label.configure(
                text=f"Status: exibindo {len(notas)} linha(s).",
                text_color="#3b8ed0",
            )
            if perguntar_lancamento and nota:
                self._avaliar_lancamento_nota_filtrada(notas, nota)
                    
        except Exception as e:
            print(f"[ERRO CRÍTICO NA TABELA] ❌ Falha ao atualizar: {e}")

    def _indice_coluna(self, nome_coluna):
        try:
            return list(self.tabela_nf["columns"]).index(nome_coluna)
        except ValueError:
            return -1

    def _coluna_tree_id(self, nome_coluna):
        idx = self._indice_coluna(nome_coluna)
        return f"#{idx + 1}" if idx >= 0 else ""

    def _nota_da_linha(self, item_id):
        try:
            idx = self.tabela_nf.index(item_id)
            if 0 <= idx < len(self.notas_filtradas_atuais):
                return self.notas_filtradas_atuais[idx] or {}
        except Exception:
            pass
        return {}

    def _solicitar_texto_painel(self, titulo, texto_inicial='', placeholder=''):
        popup = ctk.CTkToplevel(self)
        popup.title(titulo)
        popup.geometry("360x160")
        popup.attributes("-topmost", True)
        popup.resizable(False, False)
        resultado = {"valor": None}

        ctk.CTkLabel(popup, text=titulo, font=("Arial", 14, "bold")).pack(pady=(14, 8))
        entry = ctk.CTkEntry(popup, width=300, placeholder_text=placeholder)
        entry.pack(pady=4)
        if texto_inicial:
            entry.insert(0, texto_inicial)

        def confirmar():
            resultado["valor"] = entry.get()
            popup.destroy()

        def cancelar():
            popup.destroy()

        frame_btn = ctk.CTkFrame(popup, fg_color="transparent")
        frame_btn.pack(pady=12)
        ctk.CTkButton(frame_btn, text="Salvar", width=90, command=confirmar).pack(side="left", padx=6)
        ctk.CTkButton(
            frame_btn, text="Cancelar", width=90, fg_color="gray", command=cancelar,
        ).pack(side="left", padx=6)

        popup.protocol("WM_DELETE_WINDOW", cancelar)
        entry.focus_set()
        popup.grab_set()
        self.wait_window(popup)
        return resultado["valor"]

    def evento_duplo_clique_edicao(self, event):
        regiao = self.tabela_nf.identify_region(event.x, event.y)
        if regiao != "cell":
            return
        coluna_clicada = self.tabela_nf.identify_column(event.x)
        item_clicado = self.tabela_nf.identify_row(event.y)
        if not item_clicado:
            return

        if coluna_clicada == self._coluna_tree_id("placa"):
            self._editar_placa_painel(item_clicado)
        elif coluna_clicada == self._coluna_tree_id("km"):
            self._editar_km_painel(item_clicado)

    def _editar_placa_painel(self, item_id):
        valores = list(self.tabela_nf.item(item_id, "values"))
        idx_placa = self._indice_coluna("placa")
        if idx_placa < 0:
            return

        atual = valores[idx_placa] if len(valores) > idx_placa else ""
        novo = self._solicitar_texto_painel(
            "Placa (painel)",
            atual,
            "Somente letras e números",
        )
        if novo is None:
            return

        ok, placa_norm = db.validar_placa_painel(novo)
        if not ok:
            messagebox.showwarning("Placa inválida", placa_norm)
            return

        nota_item = self._nota_da_linha(item_id)
        chave = str(nota_item.get('chave_nfe') or '').strip()
        num_nota = str(nota_item.get('num_nota') or '').strip()
        try:
            self.controller.atualizar_painel_placa(chave, num_nota, placa_norm)
        except ValueError as exc:
            messagebox.showwarning("Placa", str(exc))
            return

        valores[idx_placa] = placa_norm
        self.tabela_nf.item(item_id, values=valores)

    def _editar_km_painel(self, item_id):
        valores = list(self.tabela_nf.item(item_id, "values"))
        idx_km = self._indice_coluna("km")
        if idx_km < 0:
            return

        atual = valores[idx_km] if len(valores) > idx_km else ""
        novo = self._solicitar_texto_painel(
            "KM (painel)",
            atual,
            "Somente números",
        )
        if novo is None:
            return

        ok, km_norm = db.validar_km_painel(novo)
        if not ok:
            messagebox.showwarning("KM inválido", km_norm)
            return

        nota_item = self._nota_da_linha(item_id)
        chave = str(nota_item.get('chave_nfe') or '').strip()
        num_nota = str(nota_item.get('num_nota') or '').strip()
        try:
            self.controller.atualizar_painel_km(chave, num_nota, km_norm)
        except ValueError as exc:
            messagebox.showwarning("KM", str(exc))
            return

        valores[idx_km] = km_norm
        self.tabela_nf.item(item_id, values=valores)

    def evento_clique_unico(self, event):
        regiao = self.tabela_nf.identify_region(event.x, event.y)
        if regiao != "cell":
            return
        coluna_clicada = self.tabela_nf.identify_column(event.x)
        item_clicado = self.tabela_nf.identify_row(event.y)
        if not item_clicado:
            return

        valores = list(self.tabela_nf.item(item_clicado, "values"))
        nota_item = self._nota_da_linha(item_clicado)
        status_real = self._normalizar_status(nota_item.get('status'))
        chave_da_nota = str(nota_item.get('chave_nfe') or '').strip()
        erro = str(nota_item.get('erro_importacao') or '').strip()
        observacao = str(nota_item.get('observacao_nfe') or '').strip()
        idx_arquiva = self._indice_coluna("arquiva")
        idx_estoque = self._indice_coluna("estoque")

        if coluna_clicada == self._coluna_tree_id("arquiva"):
            if db.nota_erro_arquivo_indisponivel(erro):
                return
            if not self._pode_marcar_arquiva(status_real, nota_item):
                return
            if not chave_da_nota or idx_arquiva < 0 or not str(valores[idx_arquiva]).strip():
                return
            estado_atual = valores[idx_arquiva]
            if "☑" in estado_atual:
                novo_estado_tela = "☐"
                estado_banco = "☐"
            else:
                novo_estado_tela = "☑"
                estado_banco = "☑"
            self.controller.atualizar_arquiva(chave_da_nota, estado_banco)
            if (
                (estado_banco == "☑" and self.filtro_status.get() != "Arquivada")
                or (estado_banco == "☐" and self.filtro_status.get() == "Arquivada")
            ):
                self.atualizar_tabela_dashboard()
                return
            valores[idx_arquiva] = novo_estado_tela
            idx_status = self._indice_coluna("status")
            if idx_status >= 0:
                if estado_banco == "☑":
                    valores[idx_status] = "Arquivada"
                else:
                    valores[idx_status] = str(nota_item.get('status') or '')
            self.tabela_nf.item(item_clicado, values=valores)
            return

        if coluna_clicada == self._coluna_tree_id("estoque"):
            if db.nota_erro_arquivo_indisponivel(erro):
                return
            if (
                not self._mostra_checkbox_estoque(status_real, nota_item)
                or idx_estoque < 0
                or not str(valores[idx_estoque]).strip()
            ):
                return
            estado_atual = valores[idx_estoque]
            if "☑" in estado_atual:
                novo_estado_tela = "☐"
                estado_banco = "☐"
            else:
                novo_estado_tela = "☑"
                estado_banco = "☑"
            valores[idx_estoque] = novo_estado_tela
            self.tabela_nf.item(item_clicado, values=valores)
            self.controller.atualizar_estoque(chave_da_nota, estado_banco)
            return

        if coluna_clicada == self._coluna_tree_id("observacao"):
            if observacao:
                self.mostrar_popup_texto("Observação da NFe", observacao)
            return

        if coluna_clicada == self._coluna_tree_id("erro"):
            if status_real == "ERRO" and erro:
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