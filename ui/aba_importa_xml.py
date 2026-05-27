import os
import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from robo_web.modulo_importa_xml import listar_xmls_da_pasta


class AbaImportaXML(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.pasta_xml = ""
        self.itens_xml = []
        self._iid_por_caminho = {}
        self._montar_tela()

    def _montar_tela(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        topo = ctk.CTkFrame(self)
        topo.grid(row=0, column=0, padx=10, pady=(10, 8), sticky="ew")
        topo.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            topo,
            text="Importação Manual de XML",
            font=("Arial", 16, "bold"),
            text_color="#3b8ed0",
        ).grid(row=0, column=0, columnspan=4, padx=12, pady=(10, 6), sticky="w")

        self.btn_pasta = ctk.CTkButton(
            topo, text="📁 Pasta XML", width=120, command=self.selecionar_pasta_xml,
        )
        self.btn_pasta.grid(row=1, column=0, padx=(12, 8), pady=(0, 10), sticky="w")

        self.lbl_pasta = ctk.CTkLabel(
            topo,
            text="Nenhuma pasta selecionada.",
            justify="left",
            anchor="w",
            text_color="gray",
        )
        self.lbl_pasta.grid(row=1, column=1, padx=4, pady=(0, 10), sticky="ew")

        self.btn_recarregar = ctk.CTkButton(
            topo, text="Recarregar", width=100, command=self.recarregar_pasta,
        )
        self.btn_recarregar.grid(row=1, column=2, padx=8, pady=(0, 10), sticky="e")

        self.btn_iniciar = ctk.CTkButton(
            topo,
            text="▶ Iniciar Importação",
            width=160,
            fg_color="#107C41",
            hover_color="#0A532B",
            command=self.iniciar_importacao,
        )
        self.btn_iniciar.grid(row=1, column=3, padx=(8, 12), pady=(0, 10), sticky="e")

        frame_tabela = ctk.CTkFrame(self)
        frame_tabela.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="nsew")
        frame_tabela.grid_columnconfigure(0, weight=1)
        frame_tabela.grid_rowconfigure(0, weight=1)

        colunas = ("nota", "arquivo", "status", "mensagem")
        self.tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=12)
        self.tabela.heading("nota", text="Nº Nota")
        self.tabela.heading("arquivo", text="Arquivo XML")
        self.tabela.heading("status", text="Status")
        self.tabela.heading("mensagem", text="Mensagem")
        self.tabela.column("nota", width=95, anchor="center")
        self.tabela.column("arquivo", width=260, anchor="w")
        self.tabela.column("status", width=120, anchor="center")
        self.tabela.column("mensagem", width=430, anchor="w")

        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tabela.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.lbl_status = ctk.CTkLabel(
            self,
            text="Status: selecione uma pasta com XMLs para carregar o painel.",
            text_color="gray",
        )
        self.lbl_status.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="w")

    def selecionar_pasta_xml(self):
        pasta = filedialog.askdirectory(
            title="Selecione a pasta com os XMLs",
            initialdir=self.pasta_xml or os.getcwd(),
        )
        if not pasta:
            return
        self.carregar_pasta(pasta)

    def recarregar_pasta(self):
        if not self.pasta_xml:
            messagebox.showwarning("Pasta XML", "Selecione primeiro uma pasta com XMLs.")
            return
        self.carregar_pasta(self.pasta_xml)

    def carregar_pasta(self, pasta):
        itens = listar_xmls_da_pasta(pasta)
        self.pasta_xml = pasta
        self.itens_xml = itens
        self._iid_por_caminho = {}

        for iid in self.tabela.get_children():
            self.tabela.delete(iid)

        for indice, item in enumerate(itens, 1):
            iid = str(indice)
            self._iid_por_caminho[item["caminho"]] = iid
            self.tabela.insert(
                "",
                "end",
                iid=iid,
                values=(
                    item.get("numero_nota") or "-",
                    item.get("arquivo") or "",
                    "PENDENTE",
                    item.get("mensagem") or "",
                ),
            )

        self.lbl_pasta.configure(text=pasta, text_color="white")
        self.lbl_status.configure(
            text=f"Status: {len(itens)} XML(s) carregado(s) na pasta.",
            text_color="#3b8ed0" if itens else "gray",
        )
        if not itens:
            messagebox.showwarning(
                "Pasta XML",
                "Nenhum arquivo .xml foi encontrado na pasta selecionada.",
            )

    def obter_itens_para_importacao(self):
        return [dict(item) for item in self.itens_xml]

    def iniciar_importacao(self):
        itens = self.obter_itens_para_importacao()
        if not itens:
            messagebox.showwarning("Importação XML", "Nenhum XML foi carregado no painel.")
            return
        self.controller.iniciar_importacao(itens)

    def atualizar_status_geral(self, texto, cor="gray"):
        self.lbl_status.configure(text=f"Status: {texto}", text_color=cor)

    def atualizar_item(self, item, status, mensagem=""):
        caminho = str(item.get("caminho") or "")
        iid = self._iid_por_caminho.get(caminho)
        if not iid:
            return
        valores = list(self.tabela.item(iid, "values"))
        if len(valores) < 4:
            return
        valores[0] = item.get("numero_nota") or valores[0] or "-"
        valores[1] = item.get("arquivo") or valores[1]
        valores[2] = status
        valores[3] = mensagem
        self.tabela.item(iid, values=valores)

    def marcar_lote(self, itens, status, mensagem):
        for item in itens:
            self.atualizar_item(item, status, mensagem)

    def definir_estado_execucao(self, executando):
        estado = "disabled" if executando else "normal"
        self.btn_pasta.configure(state=estado)
        self.btn_recarregar.configure(state=estado)
        self.btn_iniciar.configure(state=estado)
