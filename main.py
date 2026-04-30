import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk  
import threading         
import time              
import database_setup as db
import robo_web.robo_web as robo_web          
import ui_filtros
from robo_web import modulo_frota

# Configuração visual do sistema
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Automação NFe")
        self.geometry("400x550")
        self.eval('tk::PlaceWindow . center') 
        
        import database_setup as db
        db.inicializar_banco()
        db.gerar_chave_seguranca()
        db.configurar_usuario_master() 
        
        self.verificar_acesso()
        self.atualizar_tabela_dashboard()
        
        # CHAMA O ROBÔ DE FROTA DEPOIS QUE A TELA JÁ ESTIVER ABERTA (Delay de 2 segundos)
        self.after(2000, self.iniciar_thread_frota)

    def iniciar_thread_frota(self):
        # ATENÇÃO: NÃO coloque () depois de loop_atualizacao_frota aqui embaixo!
        thread_frota = threading.Thread(target=loop_atualizacao_frota, daemon=True)
        thread_frota.start()

    def verificar_acesso(self):
        status, dias = db.checar_status_licenca()
        if status == -1 or status == -2:
            self.mostrar_tela_token()
        else:
            self.mostrar_tela_login()
            if status == 0:
                messagebox.showwarning("Aviso de Licença", f"Sua licença expira em {dias} dias!")

    def limpar_tela(self):
        for widget in self.winfo_children():
            widget.destroy()

    # ==========================================
    # TELA 1: BLOQUEIO / TOKEN
    # ==========================================
    def mostrar_tela_token(self):
        self.limpar_tela()
        lbl_titulo = ctk.CTkLabel(self, text="Sistema Bloqueado", font=("Arial", 24, "bold"), text_color="red")
        lbl_titulo.pack(pady=(50, 10))
        lbl_sub = ctk.CTkLabel(self, text="Insira uma licença válida de 31 dias.")
        lbl_sub.pack(pady=(0, 30))
        self.entry_token = ctk.CTkEntry(self, placeholder_text="Digite o Token", width=250)
        self.entry_token.pack(pady=10)
        btn_ativar = ctk.CTkButton(self, text="Ativar Sistema", command=self.ativar_sistema)
        btn_ativar.pack(pady=20)

    def ativar_sistema(self):
        token = self.entry_token.get().strip()
        sucesso, mensagem = db.ativar_token_31_dias(token)
        if sucesso:
            messagebox.showinfo("Sucesso", mensagem)
            self.verificar_acesso() 
        else:
            messagebox.showerror("Erro", mensagem)

    # ==========================================
    # TELA 2: LOGIN E CADASTRO
    # ==========================================
    def mostrar_tela_login(self):
        self.limpar_tela()
        self.geometry("400x550")
        
        lbl_titulo = ctk.CTkLabel(self, text="Acesso ao Sistema", font=("Arial", 24, "bold"))
        lbl_titulo.pack(pady=(60, 30))
        
        self.entry_email = ctk.CTkEntry(self, placeholder_text="E-mail", width=250)
        self.entry_email.pack(pady=10)
        
        self.entry_senha = ctk.CTkEntry(self, placeholder_text="Senha", show="*", width=250)
        self.entry_senha.pack(pady=10)
        
        btn_login = ctk.CTkButton(self, text="Entrar", command=self.realizar_login)
        btn_login.pack(pady=15)
        
        btn_cadastrar = ctk.CTkButton(self, text="Novo Operador", fg_color="transparent", border_width=1, command=self.mostrar_tela_cadastro)
        btn_cadastrar.pack(pady=10)

    def realizar_login(self):
        email = self.entry_email.get().strip()
        senha = self.entry_senha.get().strip()
        sucesso, mensagem = db.validar_login(email, senha)
        if sucesso:
            self.mostrar_menu_principal()
        else:
            messagebox.showerror("Erro de Acesso", mensagem)

    def mostrar_tela_cadastro(self):
        if db.contar_usuarios_comuns() >= 1:
            messagebox.showerror("Bloqueado", "O limite de operadores já foi atingido (Máximo 1).")
            return

        self.limpar_tela()
        lbl_titulo = ctk.CTkLabel(self, text="Cadastrar Operador", font=("Arial", 24, "bold"))
        lbl_titulo.pack(pady=(40, 20))
        self.reg_nome = ctk.CTkEntry(self, placeholder_text="Nome Completo", width=250)
        self.reg_nome.pack(pady=10)
        self.reg_email = ctk.CTkEntry(self, placeholder_text="E-mail", width=250)
        self.reg_email.pack(pady=10)
        self.reg_senha = ctk.CTkEntry(self, placeholder_text="Senha", show="*", width=250)
        self.reg_senha.pack(pady=10)
        btn_confirmar = ctk.CTkButton(self, text="Confirmar Cadastro", command=self.executar_cadastro)
        btn_confirmar.pack(pady=20)
        btn_voltar = ctk.CTkButton(self, text="Voltar", fg_color="gray", command=self.mostrar_tela_login)
        btn_voltar.pack()

    def executar_cadastro(self):
        nome = self.reg_nome.get().strip()
        email = self.reg_email.get().strip()
        senha = self.reg_senha.get().strip()
        if not nome or not email or not senha:
            messagebox.showwarning("Aviso", "Preencha todos os campos.")
            return
        sucesso, msg = db.cadastrar_usuario(nome, email, senha)
        if sucesso:
            messagebox.showinfo("Sucesso", msg)
            self.mostrar_tela_login()
        else:
            messagebox.showerror("Erro", msg)

    # ==========================================
    # TELA 3: MENU PRINCIPAL E SUB-ABAS
    # ==========================================
    def mostrar_menu_principal(self):
        self.limpar_tela()
        self.geometry("850x650") 
        self.eval('tk::PlaceWindow . center')
        
        self.tabview = ctk.CTkTabview(self, width=800, height=600)
        self.tabview.pack(pady=20, padx=20)
        
        self.tabview.add("Painel do Robô")
        self.tabview.add("Configurações do Sistema")
        
        self.montar_aba_robo()
        self.montar_aba_configuracoes()

    def montar_aba_robo(self):
        aba_principal = self.tabview.tab("Painel do Robô")
        
        lbl_titulo = ctk.CTkLabel(aba_principal, text="Dashboard da Automação", font=("Arial", 22, "bold"), text_color="#3b8ed0")
        lbl_titulo.pack(pady=(10, 5))

        self.sub_tabview = ctk.CTkTabview(aba_principal, width=760, height=450)
        self.sub_tabview.pack(pady=5, padx=10, fill="both", expand=True)
        
        self.sub_tabview.add("Execução e Notas")
        self.sub_tabview.add("Filtros de Data")
        self.sub_tabview.add("Veículos Ativos")

        self.montar_sub_aba_execucao()
        self.montar_sub_aba_filtros()
        self.montar_sub_aba_veiculos()

    def montar_sub_aba_execucao(self):
        aba_exec = self.sub_tabview.tab("Execução e Notas")

        # --- Estilizando a Tabela ---
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=25, fieldbackground="#2b2b2b", borderwidth=0)
        style.map('Treeview', background=[('selected', '#3b8ed0')])
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", font=('Arial', 10, 'bold'))

        frame_tabela = ctk.CTkFrame(aba_exec)
        frame_tabela.pack(pady=10, padx=10, fill="both", expand=True)

        # 1. ATUALIZAMOS A LISTA DE COLUNAS (cod_interno no início e erro no fim)
        colunas = ("cod_interno", "status", "forn", "nota", "data", "valor", "sit_nfe", "chave", "filial", "user", "erro")
        self.tabela_nf = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=8)
        
        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela_nf.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela_nf.xview)
        self.tabela_nf.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        self.tabela_nf.pack(side="left", fill="both", expand=True)

        # 2. DEFINIMOS OS CABEÇALHOS
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
        
        # 3. AJUSTAMOS O LARGURA DE CADA COLUNA (Deixei o Fornecedor e Chave um pouco menores para caber o Erro)
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
        self.tabela_nf.column("erro", width=380, anchor="w") # Aumentado para 380px para caber o texto

        self.atualizar_tabela_dashboard()
        
        # LIGA O EVENTO DE DUPLO CLIQUE DO MOUSE NA TABELA
        self.tabela_nf.bind("<Double-1>", self.evento_clique_tabela)
        # --- BOTÃO INICIAR ---
        self.btn_iniciar_robo = ctk.CTkButton(aba_exec, text="▶ INICIAR AUTOMAÇÃO", font=("Arial", 16, "bold"), 
                                              fg_color="#8b0000", hover_color="#ff0000", height=45,
                                              command=self.chamar_robo_em_background)
        self.btn_iniciar_robo.pack(pady=15)
        
    def montar_sub_aba_filtros(self):
        aba_filt = self.sub_tabview.tab("Filtros de Data")
        self.painel_de_filtros = ui_filtros.PainelFiltros(aba_filt)
        self.painel_de_filtros.pack(fill="both", expand=True)
        
 
    # ==========================================
    # NOVA ABA: VEÍCULOS ATIVOS
    # ==========================================
    def montar_sub_aba_veiculos(self):
        aba_veic = self.sub_tabview.tab("Veículos Ativos")

        lbl_titulo = ctk.CTkLabel(aba_veic, text="Relação de Veículos Cadastrados no Banco", font=("Arial", 16, "bold"))
        lbl_titulo.pack(pady=(10, 5))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="#2b2b2b", foreground="white", rowheight=25, fieldbackground="#2b2b2b", borderwidth=0)
        style.map('Treeview', background=[('selected', '#3b8ed0')])
        style.configure("Treeview.Heading", background="#1f538d", foreground="white", font=('Arial', 10, 'bold'))

        frame_tabela = ctk.CTkFrame(aba_veic)
        frame_tabela.pack(pady=10, padx=10, fill="both", expand=True)

        # 1. NOMES INTERNOS DAS COLUNAS AJUSTADOS
        colunas = ("codigo", "placa", "tipo", "atualizacao")
        self.tabela_veiculos = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=10)
        
        scroll_y = ttk.Scrollbar(frame_tabela, orient="vertical", command=self.tabela_veiculos.yview)
        scroll_x = ttk.Scrollbar(frame_tabela, orient="horizontal", command=self.tabela_veiculos.xview)
        self.tabela_veiculos.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_x.pack(side="bottom", fill="x")
        scroll_y.pack(side="right", fill="y")
        self.tabela_veiculos.pack(side="left", fill="both", expand=True)

        # 2. CABEÇALHOS (O texto que aparece em azul na tela)
        self.tabela_veiculos.heading("codigo", text="Cód. Veículo")
        self.tabela_veiculos.heading("placa", text="Placa")
        self.tabela_veiculos.heading("tipo", text="Tipo (Vínculo)")
        self.tabela_veiculos.heading("atualizacao", text="Última Atualização")
        
        # 3. LARGURA DAS COLUNAS
        self.tabela_veiculos.column("codigo", width=100, anchor="center")
        self.tabela_veiculos.column("placa", width=120, anchor="center")
        self.tabela_veiculos.column("tipo", width=200, anchor="w")
        self.tabela_veiculos.column("atualizacao", width=160, anchor="center")

        btn_atualizar = ctk.CTkButton(aba_veic, text="Atualizar Lista", font=("Arial", 12, "bold"), 
                                      command=self.atualizar_tabela_veiculos)
        btn_atualizar.pack(pady=10)

        self.atualizar_tabela_veiculos()

    def atualizar_tabela_veiculos(self):
        """Busca os veículos no banco de dados da frota e preenche a tabela visual"""
        for item in self.tabela_veiculos.get_children():
            self.tabela_veiculos.delete(item)
            
        import sqlite3
        try:
            conn = sqlite3.connect('sistema_automacao.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 4. ORDEM DA BUSCA CORRIGIDA (Primeiro o Código, depois a Placa...)
            cursor.execute("SELECT codVeiculo, placa, veiculoProprio, ultima_atualizacao FROM frota_erp ORDER BY codVeiculo ASC")
            veiculos_db = cursor.fetchall()
            
            # 5. INSERINDO OS DADOS NA ORDEM CORRETA DA TABELA
            for v in veiculos_db:
                self.tabela_veiculos.insert("", "end", values=(
                    v['codVeiculo'],        # Aparece na 1ª coluna (Cód. Veículo)
                    v['placa'],             # Aparece na 2ª coluna (Placa)
                    v['veiculoProprio'],    # Aparece na 3ª coluna (Tipo)
                    v['ultima_atualizacao'] # Aparece na 4ª coluna (Atualização)
                ))
            conn.close()
        except Exception as e:
            print(f"Aguardando primeira leitura de frota... ({e})")
    # ==========================================
    # ABA DE CONFIGURAÇÕES (Com Validação)
    # ==========================================
    def montar_aba_configuracoes(self):
        aba = self.tabview.tab("Configurações do Sistema")
        
        frame_erp = ctk.CTkFrame(aba)
        frame_erp.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_erp, text="Dados do Sistema ERP (Web)", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        self.conf_link = ctk.CTkEntry(frame_erp, placeholder_text="Link do Sistema (URL)", width=350)
        self.conf_link.grid(row=1, column=0, padx=10, pady=10)
        self.conf_user_erp = ctk.CTkEntry(frame_erp, placeholder_text="Usuário do ERP", width=170)
        self.conf_user_erp.grid(row=1, column=1, padx=10, pady=10)
        self.conf_senha_erp = ctk.CTkEntry(frame_erp, placeholder_text="Senha do ERP", show="*", width=170)
        self.conf_senha_erp.grid(row=1, column=2, padx=10, pady=10)

        frame_email = ctk.CTkFrame(aba)
        frame_email.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(frame_email, text="Configurações de Disparo de E-mail", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=4, pady=10)
        self.conf_smtp = ctk.CTkEntry(frame_email, placeholder_text="Servidor SMTP (ex: smtp.gmail.com)", width=250)
        self.conf_smtp.grid(row=1, column=0, padx=10, pady=10)
        self.conf_porta = ctk.CTkEntry(frame_email, placeholder_text="Porta (ex: 587)", width=100)
        self.conf_porta.grid(row=1, column=1, padx=10, pady=10)
        self.conf_ssl = ctk.CTkCheckBox(frame_email, text="Usar SSL/TLS")
        self.conf_ssl.grid(row=1, column=2, padx=10, pady=10)
        self.conf_ssl.select()
        self.conf_user_email = ctk.CTkEntry(frame_email, placeholder_text="E-mail de Disparo", width=250)
        self.conf_user_email.grid(row=2, column=0, padx=10, pady=10)
        self.conf_senha_email = ctk.CTkEntry(frame_email, placeholder_text="Senha do E-mail", show="*", width=250)
        self.conf_senha_email.grid(row=2, column=1, columnspan=2, padx=10, pady=10)

        btn_salvar = ctk.CTkButton(aba, text="Salvar Configurações", command=self.salvar_configs, fg_color="green", hover_color="darkgreen")
        btn_salvar.pack(pady=20)
        self.carregar_dados_config()

    def salvar_configs(self):
        link = self.conf_link.get().strip()
        user_erp = self.conf_user_erp.get().strip()
        senha_erp = self.conf_senha_erp.get().strip()
        smtp = self.conf_smtp.get().strip()
        porta = self.conf_porta.get().strip()
        ssl = 1 if self.conf_ssl.get() else 0
        user_email = self.conf_user_email.get().strip()
        senha_email = self.conf_senha_email.get().strip()
        
        campos_erp = [link, user_erp, senha_erp]
        campos_email = [smtp, porta, user_email, senha_email]
        
        if not any(campos_erp) and not any(campos_email):
            messagebox.showwarning("Aviso", "Nenhum dado foi preenchido.")
            return
        if any(campos_erp) and not all(campos_erp):
            messagebox.showwarning("Aviso", "Dados do ERP incompletos!")
            return
        if any(campos_email) and not all(campos_email):
            messagebox.showwarning("Aviso", "Dados de E-mail incompletos!")
            return

        sucesso, msg = db.salvar_configuracoes(link, user_erp, senha_erp, smtp, user_email, senha_email, ssl, porta)
        if sucesso:
            messagebox.showinfo("Sucesso", msg)

    def carregar_dados_config(self):
        dados = db.carregar_configuracoes()
        if dados:
            self.conf_link.insert(0, dados["link"])
            self.conf_user_erp.insert(0, dados["user_sis"])
            self.conf_senha_erp.insert(0, dados["senha_sis"])
            self.conf_smtp.insert(0, dados["smtp"])
            self.conf_porta.insert(0, str(dados["porta"]))
            self.conf_user_email.insert(0, dados["user_email"])
            self.conf_senha_email.insert(0, dados["senha_email"])
            if dados["ssl"] == 1: self.conf_ssl.select()
            else: self.conf_ssl.deselect()

    # ==========================================
    # GATILHOS DO ROBÔ (Thread)
    # ==========================================
    def chamar_robo_em_background(self):
        self.btn_iniciar_robo.configure(state="disabled", text="Robô Trabalhando... Aguarde.", fg_color="gray")
        thread_robo = threading.Thread(target=self.executar_robo_playwright, daemon=True)
        thread_robo.start()
    
    def atualizar_tabela_dashboard(self):
        if not hasattr(self, 'tabela_nf'):
            return

        for item in self.tabela_nf.get_children():
            self.tabela_nf.delete(item)
            
        import database_setup as db
        notas = db.listar_todas_notas()
        
        # 4. INSERIMOS OS VALORES NA ORDEM CORRETA
        for nota in notas:
            # Função auxiliar para garantir que valores None virem string vazia
            def limpa_none(valor):
                return "" if valor is None else str(valor)

            self.tabela_nf.insert("", "end", values=(
                limpa_none(nota.get('codigo_interno')),   
                limpa_none(nota.get('status')), 
                limpa_none(nota.get('fornecedor')), 
                limpa_none(nota.get('num_nota')), 
                limpa_none(nota.get('data_em')), 
                limpa_none(nota.get('valor')), 
                limpa_none(nota.get('sit_nfe')), 
                limpa_none(nota.get('chave_nfe')), 
                limpa_none(nota.get('filial')), 
                limpa_none(nota.get('user_ins')),
                limpa_none(nota.get('erro_importacao'))   
            ))
            
    def evento_clique_tabela(self, event):
        """Função disparada quando o usuário dá um duplo clique na tabela"""
        # Identifica a linha e a coluna clicada
        item_id = self.tabela_nf.identify_row(event.y)
        coluna_id = self.tabela_nf.identify_column(event.x)
        
        if not item_id:
            return

        # Pega todos os valores da linha clicada
        valores = self.tabela_nf.item(item_id, "values")
        cod_interno = valores[0]
        erro_msg = valores[10]
        
        # SE CLICOU NA COLUNA 1 (Código Interno) "#1"
        if coluna_id == "#1" and cod_interno:
            # Copia o código para a área de transferência do Windows
            self.clipboard_clear()
            self.clipboard_append(cod_interno)
            messagebox.showinfo("Copiado!", f"O Código Interno '{cod_interno}' foi copiado!\n\nVocê pode apertar CTRL+V no sistema ERP para pesquisar a conta a pagar.")
            
            # NOTA: Se você souber a URL fixa do sistema, você poderia importar a biblioteca 'webbrowser' 
            # e fazer o Python abrir o link direto assim:
            # import webbrowser
            # webbrowser.open(f"https://sat1b.intersite.com.br/sua_pagina_conta_pagar?id={cod_interno}")

        # SE CLICOU NA COLUNA 11 (Erro) "#11"
        elif coluna_id == "#11" and erro_msg:
            # Abre um popup mostrando o texto completo do erro
            messagebox.showwarning("Detalhes do Erro", f"Mensagem completa registrada:\n\n{erro_msg}")        
    
    def executar_robo_playwright(self):
        # 1. LÊ OS FILTROS SALVOS NO BANCO DE DADOS ANTES DE INICIAR
        filtros = db.carregar_filtros()
        if not filtros:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "Por favor, vá na aba 'Filtros de Data', selecione o Mês e Ano e salve antes de iniciar!")
            robo_web.iniciar_automacao(config, meses, anos, progresso_callback=atualizar_status)
            return

        # 2. CONVERTE O MÊS DO FORMATO DA TELA PARA O FORMATO DO ROBÔ
        try:
            mes_completo = filtros['mes'].split("-")[1].strip() 
            mes_formatado = mes_completo[:3].capitalize() 
        except:
            mes_formatado = "Jan" 
            
        meses_selecionados = [mes_formatado]
        anos_selecionados = [filtros['ano']]

        # 3. CORREÇÃO CIRÚRGICA: FUNÇÃO BLINDADA PARA ATUALIZAR STATUS
        def atualizar_status(mensagem):
            print(f"Status: {mensagem}") # Garante que você sempre veja o status no terminal
            try:
                # Tenta atualizar a tela apenas se a label existir, sem travar o programa
                if hasattr(self, 'status_label'):
                    self.status_label.configure(text=f"Status: {mensagem}")
                elif hasattr(self, 'lbl_status'):
                    self.lbl_status.configure(text=f"Status: {mensagem}")
                self.update_idletasks()
            except:
                pass # Ignora o erro visual silenciosamente e deixa o robô seguir a vida

        # 4. CARREGA AS CONFIGURAÇÕES DE LOGIN
        config = db.carregar_configuracoes()
        if not config or not config['link']:
            from tkinter import messagebox
            messagebox.showwarning("Aviso", "Configure o acesso ao sistema antes de iniciar.")
            atualizar_status("Operação cancelada.")
            return

        atualizar_status(f"Iniciando robô para o período de {mes_formatado}/{filtros['ano']}...")

        # 5. CHAMA O ROBÔ PASSANDO AS DATAS CORRETAS
        try:
            import robo_web.robo_web as robo_web
            from tkinter import messagebox
            
            # Chama o robô com as datas dinâmicas extraídas do banco
            robo_web.iniciar_automacao(config, meses_selecionados, anos_selecionados, progresso_callback=atualizar_status)
            
            # Quando o robô terminar, atualiza a tabela na tela
            self.after(0, self.atualizar_tabela_dashboard)
            
            messagebox.showinfo("Sucesso", "Automação finalizada! Verifique o painel para ver as notas importadas.")
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Erro Crítico", str(e))
            atualizar_status(f"Erro: {str(e)}")
            
    def restaurar_botao_robo(self):
        self.btn_iniciar_robo.configure(state="normal", text="▶ INICIAR AUTOMAÇÃO", fg_color="#8b0000")
import threading
import time
from robo_web import modulo_frota
        
def loop_atualizacao_frota():
    """Roda invisível a cada 1 hora sem travar a tela"""
    while True:
        try:
            modulo_frota.baixar_e_importar_frota()
        except Exception as e:
            print(f"Erro na Thread de Frota: {e}")
        time.sleep(3600) # Dorme por 1 hora

if __name__ == "__main__":
    app = App()
    app.mainloop()