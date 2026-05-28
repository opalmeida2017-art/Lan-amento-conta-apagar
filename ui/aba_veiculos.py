import customtkinter as ctk
from tkinter import ttk

class AbaVeiculos(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.montar_tela()

    def montar_tela(self):
        lbl_titulo = ctk.CTkLabel(self, text="Relação de Veículos Cadastrados no Banco", font=("Arial", 16, "bold"))
        lbl_titulo.pack(pady=(10, 5))

        frame_topo = ctk.CTkFrame(self, fg_color="transparent")
        frame_topo.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(frame_topo, text="Limite:").pack(side="left", padx=(0, 6))
        self.filtro_limite = ctk.CTkComboBox(
            frame_topo, width=90, values=["100", "200", "500", "1000", "Todos"],
        )
        self.filtro_limite.set("100")
        self.filtro_limite.pack(side="left")

        frame_tabela = ctk.CTkFrame(self)
        frame_tabela.pack(pady=10, padx=10, fill="both", expand=True)

        colunas = ("codigo", "placa", "tipo", "atualizacao")
        self.tabela_veiculos = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=10)
        
        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela_veiculos.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela_veiculos.xview)
        self.tabela_veiculos.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        self.tabela_veiculos.pack(side="left", fill="both", expand=True)

        self.tabela_veiculos.heading("codigo", text="Cód. Veículo")
        self.tabela_veiculos.heading("placa", text="Placa")
        self.tabela_veiculos.heading("tipo", text="Tipo (Vínculo)")
        self.tabela_veiculos.heading("atualizacao", text="Última Atualização")
        
        self.tabela_veiculos.column("codigo", width=90, anchor="center")
        self.tabela_veiculos.column("placa", width=100, anchor="center")
        self.tabela_veiculos.column("tipo", width=180, anchor="w")
        self.tabela_veiculos.column("atualizacao", width=150, anchor="center")

        self.btn_atualizar = ctk.CTkButton(
            self, text="Atualizar Lista", font=("Arial", 12, "bold"),
            command=self._click_atualizar_lista,
        )
        self.btn_atualizar.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="Status: Aguardando...", text_color="gray")
        self.status_label.pack(pady=(0, 10))

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

    def _click_atualizar_lista(self):
        self.btn_atualizar.configure(state="disabled")
        self.status_label.configure(
            text="Status: sincronizando frota com o ERP...",
            text_color="#f39c12",
        )
        self.controller.sincronizar_frota_erp(ao_finalizar=self._finalizar_atualizacao)

    def _finalizar_atualizacao(self):
        self.atualizar_tabela()
        self.btn_atualizar.configure(state="normal")

    def atualizar_tabela(self):
        for item in self.tabela_veiculos.get_children():
            self.tabela_veiculos.delete(item)

        veiculos = self.controller.obter_veiculos_banco(limite=self._obter_limite_linhas())
        for v in veiculos:
            self.tabela_veiculos.insert(
                "", "end",
                values=(
                    v.get("codVeiculo", ""),
                    v.get("placa", ""),
                    v.get("veiculoProprio", ""),
                    v.get("ultima_atualizacao", ""),
                ),
            )
        if veiculos:
            texto = f"Status: exibindo {len(veiculos)} linha(s)."
            cor = "#3b8ed0"
        else:
            texto = (
                "Status: nenhum veículo no banco. "
                "Confira o código do relatório em Parâmetros ERP e clique em Atualizar Lista."
            )
            cor = "#f39c12"
        self.status_label.configure(text=texto, text_color=cor)