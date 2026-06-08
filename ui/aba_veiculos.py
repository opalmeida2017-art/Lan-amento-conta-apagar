import customtkinter as ctk
from tkinter import ttk

class AbaVeiculos(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self.montar_tela()

    def montar_tela(self):
        lbl_titulo = ctk.CTkLabel(
            self,
            text="Painel de Veículos (Relatório 117)",
            font=("Arial", 16, "bold"),
        )
        lbl_titulo.pack(pady=(10, 5))

        self.lbl_ultima_atualizacao = ctk.CTkLabel(
            self,
            text='',
            text_color='#9ecbff',
            font=('Arial', 11),
        )
        self.lbl_ultima_atualizacao.pack(pady=(0, 6), padx=10)

        frame_topo = ctk.CTkFrame(self, fg_color="transparent")
        frame_topo.pack(fill="x", padx=10, pady=(0, 5))
        ctk.CTkLabel(frame_topo, text="Placa:").pack(side="left", padx=(0, 6))
        self.filtro_placa = ctk.CTkEntry(frame_topo, width=120, placeholder_text="AAA1A11")
        self.filtro_placa.pack(side="left", padx=(0, 8))
        self.filtro_placa.bind("<Return>", lambda _e: self.atualizar_tabela())
        ctk.CTkButton(
            frame_topo, text="Filtrar", width=70,
            command=self.atualizar_tabela,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            frame_topo, text="Limpar", width=70,
            command=self._limpar_filtro_placa,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkLabel(frame_topo, text="Limite:").pack(side="left", padx=(0, 6))
        self.filtro_limite = ctk.CTkComboBox(
            frame_topo, width=90, values=["100", "200", "500", "1000", "Todos"],
        )
        self.filtro_limite.set("100")
        self.filtro_limite.pack(side="left")

        frame_tabela = ctk.CTkFrame(self)
        frame_tabela.pack(pady=10, padx=10, fill="both", expand=True)

        colunas = (
            "codveiculo", "cavalo", "placa", "carreta1", "carreta2", "carreta3",
            "veiculoproprio", "movimentacao", "data_movimentacao",
        )
        self.tabela_veiculos = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=10)

        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela_veiculos.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela_veiculos.xview)
        self.tabela_veiculos.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        self.tabela_veiculos.pack(side="left", fill="both", expand=True)

        self.tabela_veiculos.heading("codveiculo", text="codVeiculo")
        self.tabela_veiculos.heading("cavalo", text="cavalo")
        self.tabela_veiculos.heading("placa", text="placa")
        self.tabela_veiculos.heading("carreta1", text="carreta1")
        self.tabela_veiculos.heading("carreta2", text="carreta2")
        self.tabela_veiculos.heading("carreta3", text="carreta3")
        self.tabela_veiculos.heading("veiculoproprio", text="veiculoProprio")
        self.tabela_veiculos.heading("movimentacao", text="Movimentação carreta")
        self.tabela_veiculos.heading("data_movimentacao", text="Data movimentação")

        self.tabela_veiculos.column("codveiculo", width=80, anchor="center")
        self.tabela_veiculos.column("cavalo", width=55, anchor="center")
        self.tabela_veiculos.column("placa", width=90, anchor="center")
        self.tabela_veiculos.column("carreta1", width=90, anchor="center")
        self.tabela_veiculos.column("carreta2", width=90, anchor="center")
        self.tabela_veiculos.column("carreta3", width=90, anchor="center")
        self.tabela_veiculos.column("veiculoproprio", width=130, anchor="w")
        self.tabela_veiculos.column("movimentacao", width=280, anchor="w")
        self.tabela_veiculos.column("data_movimentacao", width=130, anchor="center")

        self.tabela_veiculos.tag_configure(
            'carreta_duplicada',
            background='#ffcccc',
            foreground='#8b0000',
        )

        self.lbl_aviso_duplicata = ctk.CTkLabel(
            self,
            text='',
            text_color='#e74c3c',
            font=('Arial', 11),
            wraplength=700,
        )
        self.lbl_aviso_duplicata.pack(pady=(0, 4), padx=10)

        self.btn_atualizar = ctk.CTkButton(
            self, text="Atualizar Lista", font=("Arial", 12, "bold"),
            command=self._click_atualizar_lista,
        )
        self.btn_atualizar.pack(pady=10)

        self.status_label = ctk.CTkLabel(self, text="Status: Aguardando...", text_color="gray")
        self.status_label.pack(pady=(0, 10))

        self.atualizar_tabela()

    def _obter_filtro_placa(self):
        if not hasattr(self, 'filtro_placa'):
            return ''
        return self.filtro_placa.get().strip()

    def _limpar_filtro_placa(self):
        if hasattr(self, 'filtro_placa'):
            self.filtro_placa.delete(0, 'end')
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

    def _atualizar_aviso_data_hora(self):
        data_hora = self.controller.obter_ultima_atualizacao_frota()
        if data_hora:
            self.lbl_ultima_atualizacao.configure(
                text=f'⚠️ Painel de veículos atualizado em: {data_hora}',
                text_color='#9ecbff',
            )
        else:
            self.lbl_ultima_atualizacao.configure(
                text='⚠️ Painel de veículos ainda não foi sincronizado com o ERP.',
                text_color='#f39c12',
            )

    def atualizar_tabela(self):
        self._atualizar_aviso_data_hora()
        for item in self.tabela_veiculos.get_children():
            self.tabela_veiculos.delete(item)

        veiculos = self.controller.obter_veiculos_banco(
            limite=self._obter_limite_linhas(),
            placa_filtro=self._obter_filtro_placa(),
        )
        qtd_movimentacoes = 0
        qtd_duplicadas = 0
        for v in veiculos:
            tags = ('carreta_duplicada',) if v.get('carreta_duplicada') else ()
            if tags:
                qtd_duplicadas += 1
            if v.get('movimentacao_carreta'):
                qtd_movimentacoes += 1
            self.tabela_veiculos.insert(
                "", "end",
                values=(
                    v.get("codVeiculo", ""),
                    v.get("cavalo", ""),
                    v.get("placa", ""),
                    v.get("carreta1", ""),
                    v.get("carreta2", ""),
                    v.get("carreta3", ""),
                    v.get("veiculoProprio", ""),
                    v.get("movimentacao_carreta", ""),
                    v.get("data_movimentacao", ""),
                ),
                tags=tags,
            )
        if veiculos:
            texto = f"Status: exibindo {len(veiculos)} linha(s)."
            if qtd_movimentacoes:
                texto += f" {qtd_movimentacoes} com movimentação de carreta."
            if qtd_duplicadas:
                texto += f" {qtd_duplicadas} linha(s) em vermelho (carreta duplicada)."
            cor = "#e74c3c" if qtd_duplicadas else "#3b8ed0"
            if qtd_duplicadas:
                self.lbl_aviso_duplicata.configure(
                    text=(
                        'Linhas vermelhas: a mesma carreta aparece em mais de um cavalo. '
                        'Corrija no ERP e atualize a lista. O lançamento bloqueia essas placas.'
                    ),
                )
            else:
                self.lbl_aviso_duplicata.configure(text='')
        else:
            texto = (
                "Status: nenhum veículo no banco. "
                "Confira o código do relatório em Parâmetros ERP e clique em Atualizar Lista."
            )
            cor = "#f39c12"
            self.lbl_aviso_duplicata.configure(text='')
        self.status_label.configure(text=texto, text_color=cor)
