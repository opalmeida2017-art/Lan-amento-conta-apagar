import customtkinter as ctk
from tkinter import messagebox
import re
import database_setup as db # Importamos o banco de dados aqui!

class PainelFiltros(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        ctk.CTkLabel(self, text="Configurações de Busca e Importação:", font=("Arial", 16, "bold")).pack(pady=(20, 20))

        # ==========================================
        # SEÇÃO DE MÊS (COMBOBOX)
        # ==========================================
        frame_mes = ctk.CTkFrame(self, fg_color="transparent")
        frame_mes.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(frame_mes, text="📅 Mês:", font=("Arial", 14, "bold"), width=100, anchor="e").pack(side="left", padx=(10, 20))
        
        self.meses_nomes = [
            "01 - Janeiro", "02 - Fevereiro", "03 - Março", "04 - Abril", 
            "05 - Maio", "06 - Junho", "07 - Julho", "08 - Agosto", 
            "09 - Setembro", "10 - Outubro", "11 - Novembro", "12 - Dezembro"
        ]
        
        self.combo_mes = ctk.CTkComboBox(frame_mes, values=self.meses_nomes, width=250, state="readonly")
        self.combo_mes.pack(side="left")

        # ==========================================
        # SEÇÃO DE ANO (COMBOBOX)
        # ==========================================
        frame_ano = ctk.CTkFrame(self, fg_color="transparent")
        frame_ano.pack(pady=5, padx=20, fill="x")
        
        ctk.CTkLabel(frame_ano, text="📆 Ano:", font=("Arial", 14, "bold"), width=100, anchor="e").pack(side="left", padx=(10, 20))
        
        self.anos_lista = ["2023", "2024", "2025", "2026", "2027", "2028"]
        
        self.combo_ano = ctk.CTkComboBox(frame_ano, values=self.anos_lista, width=150, state="readonly")
        self.combo_ano.pack(side="left")

        # ==========================================
        # SEÇÃO DE MODELOS DE PLACA (NOVO)
        # ==========================================
        frame_placa = ctk.CTkFrame(self, fg_color="transparent")
        frame_placa.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(frame_placa, text="🚗 Placas:", font=("Arial", 14, "bold"), width=100, anchor="e").pack(side="left", padx=(10, 20))

        # Campo de entrada para os modelos separados por vírgula
        self.entry_placas = ctk.CTkEntry(frame_placa, width=450, placeholder_text="Ex: PLACA: AAA-1A11, PLAC: AAA 1A11, PLACA: AAA1A11")
        self.entry_placas.pack(side="left")
        
        # ==========================================
        # SEÇÃO DE MODELOS DE KM (NOVO)
        # ==========================================
        frame_km = ctk.CTkFrame(self, fg_color="transparent")
        frame_km.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(frame_km, text="🛣️ KM:", font=("Arial", 14, "bold"), width=100, anchor="e").pack(side="left", padx=(10, 20))

        # Campo de entrada para os modelos de KM separados por vírgula
        self.entry_km = ctk.CTkEntry(frame_km, width=450, placeholder_text="Ex: KM: 1, HIDRO: 1, ODO 1")
        self.entry_km.pack(side="left")

        # ==========================================
        # BOTÃO SALVAR
        # ==========================================
        self.btn_salvar = ctk.CTkButton(self, text="💾 Salvar Configurações", fg_color="green", hover_color="darkgreen", command=self.salvar_filtros_no_banco)
        self.btn_salvar.pack(pady=30)

        # Ao iniciar a tela, tenta carregar do banco os últimos que foram salvos!
        self.carregar_dados_iniciais()

    # ==========================================
    # FUNÇÕES DE BANCO DE DADOS DA TELA
    # ==========================================
    def carregar_dados_iniciais(self):
        # Carrega Mês e Ano
        dados_salvos = db.carregar_filtros()
        if dados_salvos:
            self.combo_mes.set(dados_salvos["mes"])
            self.combo_ano.set(dados_salvos["ano"])

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
            
            sucesso_f, msg_f = db.salvar_filtros(mes_escolhido, ano_escolhido)
            db.salvar_modelos_placa(modelos_placa_digitados)
            db.salvar_modelos_km(modelos_km_digitados) # Salva os KMs
            
            if sucesso_f:
                messagebox.showinfo("✅ Sucesso", "Configurações, Placas e KMs salvos com sucesso!")
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
    
    