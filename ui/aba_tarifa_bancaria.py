import os

import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from ui.entry_data_calendario import EntryDataComCalendario


class AbaTarifaBancaria(ctk.CTkFrame):
    COR_CARD_CNPJ = "#2b2b2b"
    COR_CARD_CONTA = "#363636"
    COR_LINHA_CLARA = "#3d3d3d"
    COR_LINHA_ESCURA = "#2e2e2e"

    def __init__(self, master, controller):
        super().__init__(master, fg_color="transparent")
        self.controller = controller
        self.controller.view = self
        self._treeviews = []
        self.pasta_planilhas = self.controller.obter_pasta_planilhas()
        self.montar_tela()
        db = __import__('database_setup')
        db.registrar_callback_painel_tarifas(self._atualizar_painel_seguro)

    def _atualizar_painel_seguro(self):
        try:
            self.after(0, self.atualizar_painel)
        except Exception:
            pass

    def formatar_data_teclado(self, event):
        entry = event.widget
        texto = "".join(c for c in entry.get() if c.isdigit())
        if event.keysym == "BackSpace":
            return
        if len(texto) <= 2:
            novo_texto = texto
        elif len(texto) <= 4:
            novo_texto = f"{texto[:2]}/{texto[2:]}"
        else:
            novo_texto = f"{texto[:2]}/{texto[2:4]}/{texto[4:8]}"
        entry.delete(0, 'end')
        entry.insert(0, novo_texto)

    def montar_tela(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        frame_topo = ctk.CTkFrame(self, fg_color="transparent")
        frame_topo.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        frame_topo.grid_columnconfigure(0, weight=1)

        lbl_titulo = ctk.CTkLabel(
            frame_topo,
            text="Automação Tarifa Bancária",
            font=("Arial", 16, "bold"),
        )
        lbl_titulo.grid(row=0, column=0, sticky="w", pady=(0, 8))

        frame_pasta = ctk.CTkFrame(frame_topo, fg_color="transparent")
        frame_pasta.grid(row=1, column=0, sticky="ew")
        frame_pasta.grid_columnconfigure(1, weight=1)

        self.btn_pasta = ctk.CTkButton(
            frame_pasta,
            text="Pasta XLS",
            width=120,
            command=self.selecionar_pasta_planilhas,
        )
        self.btn_pasta.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.lbl_pasta = ctk.CTkLabel(
            frame_pasta,
            text=self._texto_pasta_atual(),
            justify="left",
            anchor="w",
            text_color="gray",
            wraplength=700,
        )
        self.lbl_pasta.grid(row=0, column=1, sticky="ew")

        self.lbl_instrucao = ctk.CTkLabel(
            frame_topo,
            text=(
                "Arquivos no padrao agencia_conta.xls (ex.: 0821_26058-4.xls). "
                "Com o robo ativo, planilhas novas ou atualizadas na pasta sao importadas automaticamente."
            ),
            text_color="#888888",
            font=("Arial", 10),
            justify="left",
            anchor="w",
            wraplength=900,
        )
        self.lbl_instrucao.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        frame_erp = ctk.CTkFrame(frame_topo, fg_color="#2b2b2b")
        frame_erp.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        frame_erp.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(
            frame_erp,
            text="Parametros ERP (tarifa)",
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky="w", padx=12, pady=(10, 6))

        cfg = self.controller.obter_config_erp()
        ctk.CTkLabel(frame_erp, text="Cod. Fornecedor Sicredi:").grid(
            row=1, column=0, sticky="w", padx=(12, 6), pady=4,
        )
        self.entry_cod_fornecedor = ctk.CTkEntry(frame_erp, width=80)
        self.entry_cod_fornecedor.grid(row=1, column=1, sticky="w", pady=4)
        self.entry_cod_fornecedor.insert(0, cfg.get('cod_fornecedor_sicredi', '640'))

        ctk.CTkLabel(frame_erp, text="Grupo item:").grid(
            row=1, column=2, sticky="w", padx=(12, 6), pady=4,
        )
        self.entry_cod_grupo = ctk.CTkEntry(frame_erp, width=60)
        self.entry_cod_grupo.grid(row=1, column=3, sticky="w", pady=4)
        self.entry_cod_grupo.insert(0, cfg.get('cod_grupo_item_tarifa', '44'))

        ctk.CTkLabel(frame_erp, text="Item fallback:").grid(
            row=1, column=4, sticky="w", padx=(12, 6), pady=4,
        )
        self.entry_nome_item = ctk.CTkEntry(
            frame_erp, width=220, placeholder_text="Usa descricao da planilha",
        )
        self.entry_nome_item.grid(row=1, column=5, sticky="ew", padx=(0, 12), pady=4)
        fallback = cfg.get('nome_item_tarifa_padrao', '')
        if fallback:
            self.entry_nome_item.insert(0, fallback)

        self.lbl_mapa_filial = ctk.CTkLabel(
            frame_erp,
            text=(
                "No mapa_contas.csv use colunas cod_filial e cod_conta_erp "
                "(filial por CNPJ, conta ERP por agencia/conta)."
            ),
            text_color="#9ecbff",
            font=("Arial", 10),
            justify="left",
            anchor="w",
            wraplength=820,
        )
        self.lbl_mapa_filial.grid(
            row=2, column=0, columnspan=6, sticky="ew", padx=12, pady=(0, 10),
        )

        self.lbl_ultima_atualizacao = ctk.CTkLabel(
            self,
            text='',
            text_color='#9ecbff',
            font=('Arial', 11),
            anchor="w",
        )
        self.lbl_ultima_atualizacao.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 2))

        self.lbl_monitor = ctk.CTkLabel(
            self,
            text='Monitoramento automatico: inativo (inicie o robo para ativar)',
            text_color='#888888',
            font=('Arial', 10),
            anchor="w",
        )
        self.lbl_monitor.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))

        frame_filtros = ctk.CTkFrame(self, fg_color="transparent")
        frame_filtros.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 4))

        ctk.CTkLabel(frame_filtros, text="CNPJ:").pack(side="left", padx=(0, 6))
        self._cnpjs_disponiveis = self.controller.obter_cnpjs_disponiveis()
        self.filtro_cnpj = ctk.CTkComboBox(
            frame_filtros,
            width=220,
            values=self._cnpjs_disponiveis,
        )
        self.filtro_cnpj.set("Todos")
        self.filtro_cnpj.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(frame_filtros, text="Data:").pack(side="left", padx=(0, 6))
        self.filtro_dt_ini = EntryDataComCalendario(frame_filtros, width=100)
        self.filtro_dt_ini.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(frame_filtros, text="ate").pack(side="left", padx=(0, 4))
        self.filtro_dt_fim = EntryDataComCalendario(frame_filtros, width=100)
        self.filtro_dt_fim.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(frame_filtros, text="Status:").pack(side="left", padx=(0, 6))
        self.filtro_status = ctk.CTkComboBox(
            frame_filtros,
            width=120,
            values=["Todos", "Pendente", "Processado", "Erro"],
        )
        self.filtro_status.set("Todos")
        self.filtro_status.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            frame_filtros, text="Filtrar", width=70,
            command=self.atualizar_painel,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            frame_filtros, text="Limpar", width=70,
            command=self._limpar_filtros,
        ).pack(side="left")

        self.frame_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.frame_scroll.grid(row=5, column=0, sticky="nsew", padx=10, pady=(4, 4))
        self.frame_scroll.grid_columnconfigure(0, weight=1)

        frame_rodape = ctk.CTkFrame(self, fg_color="transparent")
        frame_rodape.grid(row=6, column=0, sticky="ew", padx=10, pady=(4, 10))

        self.btn_importar = ctk.CTkButton(
            frame_rodape,
            text="Importar Planilhas",
            font=("Arial", 12, "bold"),
            fg_color="#107C41",
            hover_color="#0A532B",
            command=self._click_importar_planilhas,
        )
        self.btn_importar.pack(side="left", padx=(0, 12))

        self.btn_lancar = ctk.CTkButton(
            frame_rodape,
            text="Lancar Pendentes no ERP",
            font=("Arial", 12, "bold"),
            fg_color="#1f538d",
            hover_color="#163d66",
            command=self._click_lancar_tarifas,
        )
        self.btn_lancar.pack(side="left", padx=(0, 12))

        self.status_label = ctk.CTkLabel(
            frame_rodape,
            text="Status: selecione a pasta XLS e cadastre o mapa CNPJ/conta.",
            text_color="gray",
        )
        self.status_label.pack(side="left")

        self.bind("<Configure>", self._ajustar_quebra_texto)
        self.atualizar_painel()

    def definir_monitoramento_ativo(self, ativo):
        if not hasattr(self, 'lbl_monitor'):
            return
        if ativo:
            self.lbl_monitor.configure(
                text='Monitoramento automatico da pasta XLS: ATIVO (robo em execucao)',
                text_color='#107C41',
            )
        else:
            self.lbl_monitor.configure(
                text='Monitoramento automatico: inativo (inicie o robo para ativar)',
                text_color='#888888',
            )

    def _ajustar_quebra_texto(self, event=None):
        if event and event.widget is not self:
            return
        largura = max(320, self.winfo_width() - 160)
        if hasattr(self, 'lbl_pasta'):
            self.lbl_pasta.configure(wraplength=largura)
        if hasattr(self, 'lbl_instrucao'):
            self.lbl_instrucao.configure(wraplength=max(400, self.winfo_width() - 40))

    def _texto_pasta_atual(self):
        if self.pasta_planilhas:
            return self.pasta_planilhas
        return "Nenhuma pasta selecionada."

    def selecionar_pasta_planilhas(self):
        pasta = filedialog.askdirectory(
            title="Selecione a pasta com os extratos XLS do Sicredi",
            initialdir=self.pasta_planilhas or os.getcwd(),
        )
        if not pasta:
            return
        self.pasta_planilhas = pasta
        self.controller.salvar_pasta_planilhas(pasta)
        self.lbl_pasta.configure(text=pasta, text_color="#9ecbff")
        self.status_label.configure(
            text="Status: pasta definida. Coloque mapa_contas.csv e clique em Importar Planilhas.",
            text_color="#3b8ed0",
        )

    def _atualizar_combo_cnpj(self):
        selecionado = self.filtro_cnpj.get().strip() if hasattr(self, 'filtro_cnpj') else 'Todos'
        self._cnpjs_disponiveis = self.controller.obter_cnpjs_disponiveis()
        self.filtro_cnpj.configure(values=self._cnpjs_disponiveis)
        if selecionado in self._cnpjs_disponiveis:
            self.filtro_cnpj.set(selecionado)
        else:
            self.filtro_cnpj.set("Todos")

    def _limpar_filtros(self):
        self.filtro_cnpj.set("Todos")
        self.filtro_dt_ini.delete(0, 'end')
        self.filtro_dt_fim.delete(0, 'end')
        self.filtro_status.set("Todos")
        self.atualizar_painel()

    def _obter_filtros(self):
        cnpj = self.filtro_cnpj.get().strip()
        if cnpj == 'Todos':
            cnpj = ''
        return {
            'cnpj_filtro': cnpj,
            'data_ini': self.filtro_dt_ini.get().strip(),
            'data_fim': self.filtro_dt_fim.get().strip(),
            'status': self.filtro_status.get().strip(),
        }

    def _atualizar_aviso_data_hora(self):
        data_hora = self.controller.obter_ultima_atualizacao()
        if data_hora:
            self.lbl_ultima_atualizacao.configure(
                text=f'⚠️ Última importação de planilhas: {data_hora}',
                text_color='#9ecbff',
            )
        else:
            self.lbl_ultima_atualizacao.configure(
                text='⚠️ Nenhuma planilha importada ainda.',
                text_color='#f39c12',
            )

    def _configurar_estilo_treeview(self, tree):
        tree.tag_configure('linha_clara', background=self.COR_LINHA_CLARA)
        tree.tag_configure('linha_escura', background=self.COR_LINHA_ESCURA)
        tree.tag_configure('erro', background='#5c2b2b', foreground='#ffb3b3')
        tree.tag_configure('processado', background='#2b4a2b', foreground='#b8e6b8')

    def _criar_treeview_conta(self, parent, tarifas):
        frame_tabela = ctk.CTkFrame(parent, fg_color="transparent")
        frame_tabela.pack(fill="x", padx=8, pady=(0, 8))

        if not tarifas:
            ctk.CTkLabel(
                frame_tabela,
                text="Sem tarifas no período importado (conta pode ter movimentação em outro dia).",
                text_color="#888888",
                font=("Arial", 10),
                anchor="w",
            ).pack(fill="x", padx=4, pady=(0, 6))
            return None

        colunas = ("data", "descricao", "valor", "status")
        altura = min(10, max(3, len(tarifas) + 1))
        tree = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=altura)

        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll_y.set)

        scroll_y.pack(side="right", fill="y")
        tree.pack(side="left", fill="x", expand=True)

        tree.heading("data", text="Data")
        tree.heading("descricao", text="Descrição")
        tree.heading("valor", text="Valor")
        tree.heading("status", text="Status")

        tree.column("data", width=100, anchor="center", stretch=False)
        tree.column("descricao", width=420, anchor="w", stretch=True)
        tree.column("valor", width=110, anchor="e", stretch=False)
        tree.column("status", width=100, anchor="center", stretch=False)

        self._configurar_estilo_treeview(tree)

        for idx, tarifa in enumerate(tarifas):
            status = str(tarifa.get('status') or '').strip()
            status_upper = status.upper()
            if status_upper == 'ERRO':
                tag = 'erro'
            elif status_upper == 'PROCESSADO':
                tag = 'processado'
            else:
                tag = 'linha_clara' if idx % 2 == 0 else 'linha_escura'

            tree.insert(
                "", "end",
                values=(
                    tarifa.get('data_movimento', ''),
                    tarifa.get('descricao', ''),
                    tarifa.get('valor', ''),
                    status,
                ),
                tags=(tag,),
            )

        self._treeviews.append(tree)
        return tree

    def _limpar_painel(self):
        for widget in self.frame_scroll.winfo_children():
            widget.destroy()
        self._treeviews = []

    def atualizar_painel(self):
        self._atualizar_combo_cnpj()
        self._atualizar_aviso_data_hora()
        self._limpar_painel()

        filtros = self._obter_filtros()
        grupos = self.controller.obter_tarifas_agrupadas(**filtros)

        if not grupos:
            ctk.CTkLabel(
                self.frame_scroll,
                text=(
                    "Nenhuma conta/tarifa encontrada.\n"
                    "Selecione a pasta dos extratos XLS, cadastre mapa_contas.csv "
                    "(cnpj;agencia;conta;razao_social) e clique em Importar Planilhas."
                ),
                text_color="#f39c12",
                font=("Arial", 12),
                justify="left",
            ).pack(anchor="w", padx=8, pady=12)
            self.status_label.configure(
                text="Status: painel vazio.",
                text_color="#f39c12",
            )
            return

        total_tarifas = 0
        for grupo in grupos:
            card_cnpj = ctk.CTkFrame(self.frame_scroll, fg_color=self.COR_CARD_CNPJ)
            card_cnpj.pack(fill="x", padx=4, pady=(0, 12))

            titulo = f"CNPJ: {grupo.get('cnpj', '—')}"
            razao = str(grupo.get('razao_social') or '').strip()
            if razao:
                titulo += f"  —  {razao}"

            ctk.CTkLabel(
                card_cnpj,
                text=titulo,
                font=("Arial", 13, "bold"),
                text_color="#3b8ed0",
                anchor="w",
            ).pack(fill="x", padx=12, pady=(10, 6))

            for conta in grupo.get('contas', []):
                frame_conta = ctk.CTkFrame(card_cnpj, fg_color=self.COR_CARD_CONTA)
                frame_conta.pack(fill="x", padx=12, pady=(0, 8))

                agencia = str(conta.get('agencia') or '').strip()
                numero_conta = str(conta.get('conta') or '').strip()
                if agencia and numero_conta:
                    rotulo_conta = f"Conta: Ag. {agencia} / {numero_conta}"
                elif numero_conta:
                    rotulo_conta = f"Conta: {numero_conta}"
                else:
                    rotulo_conta = "Conta: —"

                tarifas = conta.get('tarifas', [])
                total_tarifas += len(tarifas)

                data_arquivo = str(conta.get('data_arquivo_xls') or '').strip()

                frame_cabecalho = ctk.CTkFrame(frame_conta, fg_color="transparent")
                frame_cabecalho.pack(fill="x", padx=10, pady=(8, 4))

                ctk.CTkLabel(
                    frame_cabecalho,
                    text=f"{rotulo_conta}  ({len(tarifas)} tarifa(s))",
                    font=("Arial", 11, "bold"),
                    anchor="w",
                ).pack(fill="x")

                if data_arquivo:
                    ctk.CTkLabel(
                        frame_cabecalho,
                        text=f"Arquivo XLS atualizado em: {data_arquivo}",
                        font=("Arial", 10),
                        text_color="#9ecbff",
                        anchor="w",
                    ).pack(fill="x", pady=(2, 0))
                else:
                    ctk.CTkLabel(
                        frame_cabecalho,
                        text="Arquivo XLS: aguardando primeira atualizacao",
                        font=("Arial", 10),
                        text_color="#888888",
                        anchor="w",
                    ).pack(fill="x", pady=(2, 0))

                self._criar_treeview_conta(frame_conta, tarifas)

        self.status_label.configure(
            text=(
                f"Status: {len(grupos)} CNPJ(s), "
                f"{total_tarifas} tarifa(s) exibida(s)."
            ),
            text_color="#3b8ed0",
        )

    def _salvar_config_erp_tela(self):
        cod_forn = self.entry_cod_fornecedor.get().strip()
        cod_grupo = self.entry_cod_grupo.get().strip()
        nome_item = self.entry_nome_item.get().strip()
        self.controller.salvar_config_erp(cod_forn, cod_grupo, nome_item)

    def _click_lancar_tarifas(self):
        self._salvar_config_erp_tela()
        self.btn_lancar.configure(state="disabled")
        self.status_label.configure(
            text="Status: lancando tarifas pendentes no ERP...",
            text_color="#f39c12",
        )
        self.controller.lancar_tarifas_pendentes(
            ao_finalizar=self._finalizar_lancamento,
            log_callback=self._log_lancamento,
        )

    def _log_lancamento(self, msg):
        try:
            self.after(0, lambda: self.status_label.configure(
                text=f"Status: {msg}",
                text_color="#9ecbff",
            ))
        except Exception:
            pass

    def _finalizar_lancamento(self):
        self.atualizar_painel()
        self.btn_lancar.configure(state="normal")
        self.status_label.configure(
            text="Status: lancamento ERP concluido. Verifique status no painel.",
            text_color="#3b8ed0",
        )

    def _click_importar_planilhas(self):
        if not self.pasta_planilhas:
            messagebox.showwarning(
                "Pasta XLS",
                "Selecione primeiro a pasta onde o Sicredi salva os extratos.",
            )
            return

        self.btn_importar.configure(state="disabled")
        self.status_label.configure(
            text="Status: importando planilhas XLS...",
            text_color="#f39c12",
        )
        self.controller.importar_planilhas_pasta(
            self.pasta_planilhas,
            ao_finalizar=self._finalizar_importacao,
        )

    def _finalizar_importacao(self):
        self.atualizar_painel()
        self.btn_importar.configure(state="normal")
