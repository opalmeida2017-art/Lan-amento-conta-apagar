import threading
import time
import sqlite3
from tkinter import messagebox
import database_setup as db
from robo_web import robo_web, modulo_frota
from ui.main_window import MainWindow

class AppController:
    def __init__(self):
        # 1. INICIALIZAÇÃO DO AMBIENTE (Banco e Segurança)
        db.inicializar_banco()
        db.gerar_chave_seguranca()
        db.configurar_usuario_master()
        
        # 2. REFERÊNCIAS DE TELA
        # Esta variável guardará a referência da Aba de Execução quando ela for criada
        self.view_execucao = None 
        
        # 3. INSTÂNCIA DA JANELA PRINCIPAL
        # Passamos 'self' (o próprio controller) para a tela poder nos chamar
        self.view = MainWindow(controller=self)

    def iniciar(self):
        """Ponto de entrada que valida acesso e inicia o loop da interface"""
        self.verificar_acesso()
        # Inicia a sincronização de frota 2 segundos após abrir
        self.view.after(2000, self.iniciar_thread_frota)
        self.view.mainloop()

    # ============================================================
    # GESTÃO DE ACESSO E SEGURANÇA
    # ============================================================
    def verificar_acesso(self):
        status, dias = db.checar_status_licenca()
        if status == -1 or status == -2:
            self.view.mostrar_tela_token()
        else:
            self.view.mostrar_tela_login()
            if status == 0:
                messagebox.showwarning("Aviso de Licença", f"Sua licença expira em {dias} dias!")

    def ativar_sistema(self, token):
        if not token:
            messagebox.showwarning("Aviso", "Por favor, insira um token.")
            return
        sucesso, mensagem = db.ativar_token_31_dias(token)
        if sucesso:
            messagebox.showinfo("Sucesso", mensagem)
            self.verificar_acesso()
        else:
            messagebox.showerror("Erro", mensagem)

    def realizar_login(self, email, senha):
        if not email or not senha:
            messagebox.showwarning("Aviso", "Preencha e-mail e senha.")
            return
        sucesso, mensagem = db.validar_login(email, senha)
        if sucesso:
            self.view.mostrar_menu_principal()
        else:
            messagebox.showerror("Erro de Acesso", mensagem)

    def preparar_cadastro(self):
        """Valida se ainda pode cadastrar operadores (Limite de 1)"""
        if db.contar_usuarios_comuns() >= 1:
            messagebox.showerror("Bloqueado", "O limite de operadores já foi atingido (Máximo 1).")
        else:
            self.view.mostrar_tela_cadastro()

    def executar_cadastro(self, nome, email, senha):
        if not nome or not email or not senha:
            messagebox.showwarning("Aviso", "Preencha todos os campos para o cadastro.")
            return
        sucesso, msg = db.cadastrar_usuario(nome, email, senha)
        if sucesso:
            messagebox.showinfo("Sucesso", msg)
            self.view.mostrar_tela_login()
        else:
            messagebox.showerror("Erro", msg)

    # ============================================================
    # LÓGICA DE CONFIGURAÇÕES (PONTE PARA O DB)
    # ============================================================
    def carregar_codigos_relatorios(self):
        try: return db.carregar_codigos_relatorios()
        except: return {}

    def salvar_relatorios_e_filtros(self, rel_veiculo, rel_item, comando_salvar_filtros):
        """Salva as configurações de relatórios e executa o callback do painel de filtros"""
        db.salvar_codigos_relatorios(rel_veiculo, rel_item)
        if comando_salvar_filtros:
            try: comando_salvar_filtros()
            except Exception as e: print(f"Erro ao salvar filtros: {e}")
        messagebox.showinfo("Sucesso", "✅ Todas as configurações foram salvas!")

    def carregar_configuracoes_erp(self):
        return db.carregar_configuracoes()

    def salvar_configuracoes_erp(self, campos_erp, campos_email, params):
        # Validação básica de preenchimento
        if not any(campos_erp) and not any(campos_email):
            messagebox.showwarning("Aviso", "Nenhum dado foi preenchido.")
            return
        if any(campos_erp) and not all(campos_erp):
            messagebox.showwarning("Aviso", "Dados do ERP incompletos!")
            return
        if any(campos_email) and not all(campos_email):
            messagebox.showwarning("Aviso", "Dados de E-mail incompletos!")
            return

        sucesso, msg = db.salvar_configuracoes(*params)
        if sucesso:
            messagebox.showinfo("Sucesso", msg)

    # ============================================================
    # THREADS DE SINCRONIZAÇÃO (FROTA E ITENS)
    # ============================================================
    def iniciar_thread_frota(self):
        thread_frota = threading.Thread(target=self.loop_atualizacao_frota, daemon=True)
        thread_frota.start()

    def loop_atualizacao_frota(self):
        """Roda silenciosamente a cada 1 hora atualizando os dados do ERP"""
        while True:
            try:
                print("[Sincronização] Verificando novos Veículos no ERP...")
                modulo_frota.baixar_e_importar_frota()
                # Se a aba de veículos estiver aberta, manda ela se atualizar
                self.view.after(0, self.notificar_atualizacao_tabelas)
                
                print("[Sincronização] Verificando novos Itens no ERP...")
                modulo_frota.baixar_e_importar_itens()
                self.view.after(0, self.notificar_atualizacao_tabelas)
            except Exception as e:
                print(f"Erro na Thread de Sincronização Automática: {e}")
            time.sleep(3600) # 1 hora

    def notificar_atualizacao_tabelas(self):
        """Varre a interface para atualizar listas que estejam visíveis"""
        try:
            # Tenta encontrar e atualizar as tabelas modulares
            for tab in self.view.sub_tabview.winfo_children():
                for component in tab.winfo_children():
                    if hasattr(component, 'atualizar_tabela'):
                        component.atualizar_tabela()
        except: pass

    # ============================================================
    # ORQUESTRAÇÃO DO ROBÔ PRINCIPAL (PLAYWRIGHT)
    # ============================================================
    def iniciar_robo(self):
        """Dispara a thread da automação principal"""
        thread_robo = threading.Thread(target=self.executar_robo_playwright, daemon=True)
        thread_robo.start()

    def executar_robo_playwright(self):
        # 1. Carrega filtros de data do banco
        filtros = db.carregar_filtros()
        if not filtros:
            self.view.after(0, lambda: messagebox.showwarning("Aviso", "Selecione o Mês e Ano na aba 'Filtros de Data' antes de iniciar!"))
            if self.view_execucao: self.view.after(0, self.view_execucao.restaurar_botao_robo)
            return

        # 2. Prepara as datas para o robô
        try:
            mes_completo = filtros['mes'].split("-")[1].strip() 
            mes_formatado = mes_completo[:3].capitalize() 
        except: mes_formatado = "Jan" 
            
        meses_selecionados = [mes_formatado]
        anos_selecionados = [filtros['ano']]

        # 3. Função de Log que atualiza a UI em tempo real
        def atualizar_status_ui(mensagem):
            print(f"[PLAYWRIGHT]: {mensagem}") 
            if self.view_execucao:
                # O after(0) é obrigatório para mexer na UI de dentro de uma thread
                self.view.after(0, lambda: self.view_execucao.status_label.configure(text=f"Status: {mensagem}"))

        # 4. Carrega credenciais do ERP
        config = db.carregar_configuracoes()
        if not config or not config['link']:
            self.view.after(0, lambda: messagebox.showwarning("Aviso", "Configure o link e usuário do ERP na aba Configurações."))
            if self.view_execucao: self.view.after(0, self.view_execucao.restaurar_botao_robo)
            return

        # 5. EXECUÇÃO
        try:
            atualizar_status_ui(f"Iniciando robô para {mes_formatado}/{filtros['ano']}...")
            robo_web.iniciar_automacao(config, meses_selecionados, anos_selecionados, progresso_callback=atualizar_status_ui)
            
            # Finalização com sucesso
            self.view.after(0, lambda: self.view_execucao.atualizar_tabela_dashboard())
            self.view.after(0, lambda: messagebox.showinfo("Sucesso", "Automação concluída com sucesso!"))
        
        except Exception as e:
            msg_erro = str(e)
            atualizar_status_ui("O robô parou devido a um erro.")
            self.view.after(0, lambda: messagebox.showerror("Erro Crítico", f"Falha na automação:\n{msg_erro}"))
        
        finally:
            # Garante que o botão volte ao normal
            if self.view_execucao: self.view.after(0, self.view_execucao.restaurar_botao_robo)