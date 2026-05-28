import customtkinter as ctk
from tkinter import messagebox
import re
import database_setup as db # Importamos o banco de dados aqui!

class PainelFiltros(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.layout_job = None
        self.secoes = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.lbl_titulo = ctk.CTkLabel(
            self, text="Parâmetros de Importação e ERP", font=("Arial", 16, "bold"),
        )
        self.lbl_titulo.grid(row=0, column=0, sticky="w", pady=(14, 10), padx=10)

        self.cards_container = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_container.grid(row=1, column=0, sticky="nsew")

        # ==========================================
        # COLUNA 1: FILTROS DE DATA
        # ==========================================
        frame_data = ctk.CTkFrame(self.cards_container, fg_color="#2b2b2b")
        self.secoes.append(frame_data)
        ctk.CTkLabel(frame_data, text="📅 Período", font=("Arial", 14, "bold")).pack(pady=(15, 10))

        self.meses_nomes = [
            "01 - Janeiro", "02 - Fevereiro", "03 - Março", "04 - Abril", 
            "05 - Maio", "06 - Junho", "07 - Julho", "08 - Agosto", 
            "09 - Setembro", "10 - Outubro", "11 - Novembro", "12 - Dezembro"
        ]
        ctk.CTkLabel(frame_data, text="Mês:").pack()
        self.combo_mes = ctk.CTkComboBox(frame_data, values=self.meses_nomes, width=200, state="readonly")
        self.combo_mes.pack(pady=5, padx=20)

        self.anos_lista = ["2023", "2024", "2025", "2026", "2027", "2028"]
        ctk.CTkLabel(frame_data, text="Ano:").pack()
        self.combo_ano = ctk.CTkComboBox(frame_data, values=self.anos_lista, width=200, state="readonly")
        self.combo_ano.pack(pady=5, padx=20)

        self.var_ultimos_30_dias = ctk.BooleanVar(value=False)
        self.chk_ultimos_30_dias = ctk.CTkCheckBox(
            frame_data,
            text="Filtrar importações dos últimos 30 dias",
            variable=self.var_ultimos_30_dias,
            command=self._alternar_periodo_30_dias,
        )
        self.chk_ultimos_30_dias.pack(pady=(6, 4), padx=20, anchor="w")

        self.lbl_dica_ultimos_30_dias = ctk.CTkLabel(
            frame_data,
            text="Ao marcar, o robô ignora Mês/Ano e consulta da data atual retroagindo 30 dias.",
            justify="left",
            text_color="#9ecbff",
            font=("Arial", 11),
            wraplength=220,
        )
        self.lbl_dica_ultimos_30_dias.pack(pady=(0, 6), padx=12, anchor="w")

        self.var_hoje_apenas = ctk.BooleanVar(value=False)
        self.chk_hoje_apenas = ctk.CTkCheckBox(
            frame_data,
            text="Consultar e importar somente notas de HOJE",
            variable=self.var_hoje_apenas,
            command=self._alternar_periodo_hoje,
        )
        self.chk_hoje_apenas.pack(pady=(4, 4), padx=20, anchor="w")

        self.lbl_dica_hoje_apenas = ctk.CTkLabel(
            frame_data,
            text="Ao marcar, o robô ignora Mês/Ano e consulta na SEFAZ apenas a data de hoje.",
            justify="left",
            text_color="#9ecbff",
            font=("Arial", 11),
            wraplength=220,
        )
        self.lbl_dica_hoje_apenas.pack(pady=(0, 10), padx=12, anchor="w")

        ctk.CTkLabel(frame_data, text="Cod. Filial:").pack()
        self.entry_cod_filial = ctk.CTkEntry(
            frame_data, width=200, justify="center", placeholder_text="Ex: 1",
        )
        self.entry_cod_filial.pack(pady=5, padx=20)

        ctk.CTkLabel(frame_data, text="Cod. Unid. Embarque:").pack()
        self.entry_cod_unidade_embarque = ctk.CTkEntry(
            frame_data, width=200, justify="center", placeholder_text="Ex: 1",
        )
        self.entry_cod_unidade_embarque.pack(pady=(5, 10), padx=20)

        aviso_filial_ue = (
            '⚠️ Com Cod. Filial e Cod. Unid. Embarque preenchidos e salvos, '
            'TODAS as notas serão lançadas nessa filial e UE (um único CNPJ). '
            'Durante o lançamento o robô altera só a UE do item; '
            'ao abrir a nota ele aplica Filial + UE antes de finalizar. '
            'Deixe em branco para o ERP escolher sozinho.'
        )
        self.lbl_aviso_filial_ue = ctk.CTkLabel(
            frame_data,
            text=aviso_filial_ue,
            justify='left',
            text_color='#f39c12',
            font=('Arial', 11),
            wraplength=220,
        )
        self.lbl_aviso_filial_ue.pack(pady=(0, 12), padx=12, anchor='w')

        # ==========================================
        # COLUNA 2: MODELOS DE LEITURA
        # ==========================================
        frame_leitura = ctk.CTkFrame(self.cards_container, fg_color="#2b2b2b")
        self.secoes.append(frame_leitura)

        ctk.CTkLabel(frame_leitura, text="🔍 Placa e KM", font=("Arial", 14, "bold")).pack(pady=(15, 10))

        ctk.CTkLabel(frame_leitura, text="Modelos de Placa:").pack()
        self.entry_placas = ctk.CTkEntry(frame_leitura, width=220, placeholder_text="Ex: PLACA: AAA-1A11")
        self.entry_placas.pack(pady=5, padx=20)

        ctk.CTkLabel(frame_leitura, text="Modelos de KM:").pack()
        self.entry_km = ctk.CTkEntry(frame_leitura, width=220, placeholder_text="Ex: KM: 1, ODO 1")
        self.entry_km.pack(pady=5, padx=20)

        # ==========================================
        # COLUNA 3: CÓDIGOS ERP (NOVO)
        # ==========================================
        frame_codigos = ctk.CTkFrame(self.cards_container, fg_color="#2b2b2b")
        self.secoes.append(frame_codigos)

        ctk.CTkLabel(frame_codigos, text="⛽ Códigos Combustível", font=("Arial", 14, "bold")).pack(pady=(15, 5))

        self.entry_etanol = ctk.CTkEntry(frame_codigos, width=150, placeholder_text="Cód. Etanol")
        self.entry_etanol.pack(pady=4)
        
        self.entry_gasolina = ctk.CTkEntry(frame_codigos, width=150, placeholder_text="Cód. Gasolina")
        self.entry_gasolina.pack(pady=4)
        
        self.entry_s10 = ctk.CTkEntry(frame_codigos, width=150, placeholder_text="Cód. Diesel S10")
        self.entry_s10.pack(pady=4)
        
        self.entry_s500 = ctk.CTkEntry(frame_codigos, width=150, placeholder_text="Cód. Diesel S500")
        self.entry_s500.pack(pady=4)
        
        self.entry_arla = ctk.CTkEntry(frame_codigos, width=150, placeholder_text="Cód. ARLA 32")
        self.entry_arla.pack(pady=4)

        # ==========================================
        # COLUNA 4: GRUPO ITEM INDEFINIDO (1x5 — um campo editável)
        # ==========================================
        frame_grupo = ctk.CTkFrame(self.cards_container, fg_color="#2b2b2b")
        self.secoes.append(frame_grupo)

        ctk.CTkLabel(frame_grupo, text="📦 Grupo Item", font=("Arial", 14, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(frame_grupo, text="INDEFINIDO (cadastro)", font=("Arial", 11)).pack(pady=(0, 8))
        ctk.CTkLabel(frame_grupo, text="Cód. no ERP:").pack()
        self.entry_cod_grupo_item = ctk.CTkEntry(frame_grupo, width=150, justify="center", placeholder_text="Cód. no ERP")
        self.entry_cod_grupo_item.pack(pady=6, padx=20)

        # ==========================================
        # BOTÃO SALVAR
        # ==========================================
        self.btn_salvar = ctk.CTkButton(self, text="💾 Salvar Configurações", fg_color="green", hover_color="darkgreen", command=self.salvar_filtros_no_banco)
        self.btn_salvar.grid(row=2, column=0, pady=(14, 10))

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
        if largura < 560:
            colunas = 1
        elif largura < 840:
            colunas = 2
        else:
            colunas = 4

        for idx in range(4):
            self.cards_container.grid_columnconfigure(idx, weight=1 if idx < colunas else 0)

        for idx, secao in enumerate(self.secoes):
            secao.grid_forget()
            secao.grid(
                row=idx // colunas,
                column=idx % colunas,
                padx=8,
                pady=5,
                sticky="nsew",
            )

        largura_campo = 170 if colunas >= 4 else 220 if colunas == 2 else 280
        largura_codigo = 140 if colunas >= 4 else 180 if colunas == 2 else 220
        wrap = 220 if colunas >= 4 else 340 if colunas == 2 else 420

        self.combo_mes.configure(width=largura_campo)
        self.combo_ano.configure(width=largura_campo)
        self.entry_cod_filial.configure(width=largura_campo)
        self.entry_cod_unidade_embarque.configure(width=largura_campo)
        self.entry_placas.configure(width=largura_campo)
        self.entry_km.configure(width=largura_campo)
        self.entry_etanol.configure(width=largura_codigo)
        self.entry_gasolina.configure(width=largura_codigo)
        self.entry_s10.configure(width=largura_codigo)
        self.entry_s500.configure(width=largura_codigo)
        self.entry_arla.configure(width=largura_codigo)
        self.entry_cod_grupo_item.configure(width=largura_codigo)
        self.lbl_aviso_filial_ue.configure(wraplength=wrap)
        self.lbl_dica_ultimos_30_dias.configure(wraplength=wrap)
        self.lbl_dica_hoje_apenas.configure(wraplength=wrap)
        self.btn_salvar.configure(width=min(max(largura - 60, 240), 340))

    def _alternar_periodo_30_dias(self):
        if bool(self.var_ultimos_30_dias.get()):
            self.var_hoje_apenas.set(False)
        self._aplicar_estado_combos_periodo()

    def _alternar_periodo_hoje(self):
        if bool(self.var_hoje_apenas.get()):
            self.var_ultimos_30_dias.set(False)
        self._aplicar_estado_combos_periodo()

    def _aplicar_estado_combos_periodo(self):
        periodo_fixo = bool(self.var_ultimos_30_dias.get()) or bool(self.var_hoje_apenas.get())
        estado_combos = "disabled" if periodo_fixo else "readonly"
        self.combo_mes.configure(state=estado_combos)
        self.combo_ano.configure(state=estado_combos)

    # ==========================================
    # FUNÇÕES DE BANCO DE DADOS DA TELA
    # ==========================================
    def carregar_dados_iniciais(self):
        # Carrega Mês e Ano
        dados_salvos = db.carregar_filtros()
        if dados_salvos:
            self.combo_mes.set(dados_salvos['mes'])
            self.combo_ano.set(dados_salvos['ano'])
            
            # Carrega a flag de 30 dias
            if dados_salvos.get('ultimos_30_dias'):
                self.chk_ultimos_30_dias.select()
            else:
                self.chk_ultimos_30_dias.deselect()
                
            if dados_salvos.get('hoje_apenas'):
                self.chk_hoje_apenas.select()
            else:
                self.chk_hoje_apenas.deselect()

            self.entry_cod_filial.delete(0, 'end')
            self.entry_cod_filial.insert(0, dados_salvos.get('cod_filial', ''))
            self.entry_cod_unidade_embarque.delete(0, 'end')
            self.entry_cod_unidade_embarque.insert(0, dados_salvos.get('cod_unidade_embarque', ''))
        
        self._aplicar_estado_combos_periodo()

        # Carrega Modelos de Placa
        modelos_salvos_placa = db.obter_modelos_placa_string()
        if modelos_salvos_placa:
            self.entry_placas.delete(0, "end")
            self.entry_placas.insert(0, modelos_salvos_placa)

        # Carrega Modelos de KM (NOVO)
        modelos_salvos_km = db.obter_modelos_km_string()
        if modelos_salvos_km:
            self.entry_km.delete(0, "end")
            self.entry_km.insert(0, modelos_salvos_km)
        else:
            self.entry_km.insert(0, "KM: 1, KM 1, HIDROMETRO: 1, ODO: 1")
            
        try:
            cods = db.carregar_codigos_combustiveis()
            if cods["etanol"]: self.entry_etanol.insert(0, cods["etanol"])
            if cods["gasolina"]: self.entry_gasolina.insert(0, cods["gasolina"])
            if cods["s10"]: self.entry_s10.insert(0, cods["s10"])
            if cods["s500"]: self.entry_s500.insert(0, cods["s500"])
            if cods["arla"]: self.entry_arla.insert(0, cods["arla"])
        except: pass

        try:
            cfg_rel = db.carregar_codigos_relatorios()
            cod_grupo = str(cfg_rel.get('cod_grupo_item') or '').strip()
            self.entry_cod_grupo_item.delete(0, "end")
            if cod_grupo:
                self.entry_cod_grupo_item.insert(0, cod_grupo)
        except Exception:
            pass

    def salvar_filtros_no_banco(self):
        try:
            modelos_placa_digitados = self.entry_placas.get()
            modelos_km_digitados = self.entry_km.get() # Pega o texto do KM
            
            # =======================================================
            # VALIDAÇÃO DAS PLACAS
            # =======================================================
            modelos_placa = [m.strip().upper() for m in modelos_placa_digitados.split(',') if m.strip()]
            for m in modelos_placa:
                if re.search(r'[02-9]', m):
                    messagebox.showwarning("⚠️ Validação de Placa", f"Você digitou números inválidos no modelo: '{m}'\nUse APENAS o número '1'.")
                    return 
                if not re.search(r'([A1][A1\-\s]{5,}[A1])', m):
                    messagebox.showwarning("⚠️ Validação de Placa", f"Formato inválido no modelo: '{m}'\nExemplo correto: PLAC AAA-1111")
                    return

            # =======================================================
            # VALIDAÇÃO DO KM (NOVO CÃO DE GUARDA)
            # =======================================================
            modelos_km = [m.strip().upper() for m in modelos_km_digitados.split(',') if m.strip()]
            for m in modelos_km:
                # 1. Bloqueia se o usuário digitar uma km real com números de 0, 2 a 9
                if re.search(r'[02-9]', m):
                    messagebox.showwarning(
                        "⚠️ Validação de KM", 
                        f"Você digitou números inválidos no modelo: '{m}'\n\n"
                        "Regra: Use APENAS o número '1' para indicar onde começa a quilometragem.\n"
                        "Exemplo correto: HIDRO: 1"
                    )
                    return
                
                # 2. Verifica se a máscara contém o indicador '1'
                if '1' not in m:
                    messagebox.showwarning(
                        "⚠️ Validação de KM", 
                        f"Faltou o indicador de posição no modelo: '{m}'\n\n"
                        "Regra: Você deve colocar o número '1' para o robô saber onde extrair a numeração.\n"
                        "Exemplo correto: KM 1"
                    )
                    return

            # =======================================================
            # SALVA TUDO NO BANCO
            # =======================================================
            mes_escolhido = self.combo_mes.get()
            ano_escolhido = self.combo_ano.get()
            cod_filial = self.entry_cod_filial.get().strip()
            cod_unidade = self.entry_cod_unidade_embarque.get().strip()
            ultimos_30_dias = bool(self.var_ultimos_30_dias.get())
            hoje_apenas = bool(self.var_hoje_apenas.get())

            sucesso_f, msg_f = db.salvar_filtros(
                mes_escolhido,
                ano_escolhido,
                cod_filial,
                cod_unidade,
                ultimos_30_dias=ultimos_30_dias,
                hoje_apenas=hoje_apenas,
            )
            db.salvar_modelos_placa(modelos_placa_digitados)
            db.salvar_modelos_km(modelos_km_digitados) # Salva os KMs
            
            # Salva os códigos dos combustíveis (NOVO)
            db.salvar_codigos_combustiveis(
                self.entry_etanol.get(), self.entry_gasolina.get(), 
                self.entry_s10.get(), self.entry_s500.get(),self.entry_arla.get()
            )

            cfg_rel = db.carregar_codigos_relatorios()
            db.salvar_codigos_relatorios(
                str(cfg_rel.get('rel_veiculo') or '').strip(),
                str(cfg_rel.get('rel_item') or '').strip(),
                self.entry_cod_grupo_item.get().strip(),
            )
            
            if sucesso_f:
                messagebox.showinfo(
                    "✅ Sucesso",
                    "Configurações salvas (período, hoje/30 dias, filial, unidade, placas e KMs).",
                )
            else:
                messagebox.showerror("❌ Erro", msg_f)
                
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Ocorreu um erro interno:\n{e}")
            
    # ==========================================
    # FUNÇÃO QUE O ROBÔ USA
    # ==========================================
    def obter_selecao(self):
        mes_texto_completo = self.combo_mes.get()
        # "02 - Fevereiro" -> pega "Fevereiro" -> pega "Fev"
        partes = mes_texto_completo.split(" ")
        mes_nome = partes[2] if len(partes) > 2 else partes[0]
        mes_curto = mes_nome[:3].capitalize()
        
        ano_selecionado = self.combo_ano.get()
        return [mes_curto], [ano_selecionado]
    
    