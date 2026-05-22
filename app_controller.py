import threading

import time

import sqlite3

from tkinter import messagebox

import database_setup as db

import licenca_remota

from robo_web import robo_web, modulo_frota

from ui.main_window import MainWindow



# False = sem login/token antigo; licença remota GitHub usa licenca_config.py

REQUER_LOGIN_E_LICENCA = False



class AppController:

    def __init__(self):

        db.inicializar_banco()

        db.gerar_chave_seguranca()

        db.configurar_usuario_master()

        

        self.view_execucao = None 

        self.view = MainWindow(controller=self)

        self.sistema_bloqueado = False

        self._timer_licenca_id = None



    def iniciar(self):

        self.verificar_acesso()

        self.view.after(2000, self.iniciar_thread_frota)

        self.view.mainloop()



    def verificar_acesso(self):

        if not REQUER_LOGIN_E_LICENCA:

            if not self._licenca_remota_liberada():

                self.view.mostrar_tela_bloqueio_licenca()

                return

            self.sistema_bloqueado = False

            self.view.mostrar_menu_principal()

            self.agendar_verificacao_licenca()

            return

        status, dias = db.checar_status_licenca()

        if status == -1 or status == -2:

            self.view.mostrar_tela_token()

        else:

            self.view.mostrar_tela_login()

            if status == 0:

                messagebox.showwarning("Aviso de Licença", f"Sua licença expira em {dias} dias!")



    def _licenca_remota_liberada(self):

        if not licenca_remota.licenca_configurada():

            return True

        iid = db.obter_instalacao_id()

        if not iid:

            return True

        return licenca_remota.arquivo_licenca_existe(iid)



    def agendar_verificacao_licenca(self):

        if self._timer_licenca_id:

            try:

                self.view.after_cancel(self._timer_licenca_id)

            except Exception:

                pass

        if not licenca_remota.licenca_configurada():

            return

        intervalo_ms = licenca_remota.INTERVALO_VERIFICACAO_SEG * 1000

        self._timer_licenca_id = self.view.after(intervalo_ms, self._checar_licenca_periodica)



    def _checar_licenca_periodica(self):
        liberada = self._licenca_remota_liberada()
        if not liberada:
            # Só bloqueia se o GitHub confirmou suspensão (não por queda de internet)
            inst = db.carregar_instalacao_licenca()
            ult = (inst.get('ultimo_ativado_github') or '').lower()
            if ult in ('não', 'nao', 'n', 'no'):
                self.sistema_bloqueado = True
                self.view.after(0, self.view.mostrar_tela_bloqueio_licenca)
        else:
            self.sistema_bloqueado = False
        self.agendar_verificacao_licenca()



    def tentar_revalidar_licenca(self):
        if self._licenca_remota_liberada():
            self.sistema_bloqueado = False
            self.verificar_acesso()
            return
        inst = db.carregar_instalacao_licenca()
        razao = (inst.get('razao_social') or '').strip()
        if razao:
            ok, msg, _ = licenca_remota.registrar_instalacao(razao)
            if not ok:
                messagebox.showwarning("Licença remota", msg)

        if self._licenca_remota_liberada():
            self.sistema_bloqueado = False
            self.verificar_acesso()
        else:
            messagebox.showerror(
                "Licença",
                "Licença suspensa (ativado = não) ou arquivo ausente.\n"
                "Entre em contato com o suporte.",
            )



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



    def carregar_codigos_relatorios(self):

        try: return db.carregar_codigos_relatorios()

        except: return {}



    def salvar_relatorios_e_filtros(self, rel_veiculo, rel_item, cod_grupo_item="", comando_salvar_filtros=None):

        db.salvar_codigos_relatorios(rel_veiculo, rel_item, cod_grupo_item)

        if comando_salvar_filtros:

            try: comando_salvar_filtros()

            except Exception as e: print(f"Erro ao salvar filtros: {e}")

        messagebox.showinfo("Sucesso", "✅ Todas as configurações foram salvas!")



    def carregar_configuracoes_erp(self):

        return db.carregar_configuracoes()



    def salvar_configuracoes_erp(self, campos_erp, campos_email, params):

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



    def iniciar_thread_frota(self):

        thread_frota = threading.Thread(target=self.loop_atualizacao_frota, daemon=True)

        thread_frota.start()



    def loop_atualizacao_frota(self):

        while True:

            if self.sistema_bloqueado:

                time.sleep(60)

                continue

            try:

                print("[Sincronização] Verificando novos Veículos no ERP...")

                modulo_frota.baixar_e_importar_frota()

                self.view.after(0, self.notificar_atualizacao_tabelas)

                

                print("[Sincronização] Verificando novos Itens no ERP...")

                modulo_frota.baixar_e_importar_itens()

                self.view.after(0, self.notificar_atualizacao_tabelas)

            except Exception as e:

                print(f"Erro na Thread de Sincronização Automática: {e}")

            time.sleep(3600)



    def notificar_atualizacao_tabelas(self):

        try:

            for tab in self.view.sub_tabview.winfo_children():

                for component in tab.winfo_children():

                    if hasattr(component, 'atualizar_tabela'):

                        component.atualizar_tabela()

        except: pass



    def iniciar_robo(self):

        if self.sistema_bloqueado or not self._licenca_remota_liberada():

            messagebox.showerror("Bloqueado", "Sistema sem licença ativa. Verifique com o suporte.")

            if self.view_execucao:

                self.view_execucao.restaurar_botao_robo()

            return

        thread_robo = threading.Thread(target=self.executar_robo_playwright, daemon=True)

        thread_robo.start()



    def executar_robo_playwright(self):

        filtros = db.carregar_filtros()

        if not filtros:

            self.view.after(0, lambda: messagebox.showwarning("Aviso", "Selecione o Mês e Ano na aba 'Filtros de Data' antes de iniciar!"))

            if self.view_execucao: self.view.after(0, self.view_execucao.restaurar_botao_robo)

            return



        try:

            mes_completo = filtros['mes'].split("-")[1].strip() 

            mes_formatado = mes_completo[:3].capitalize() 

        except: mes_formatado = "Jan" 

            

        meses_selecionados = [mes_formatado]

        anos_selecionados = [filtros['ano']]



        def atualizar_status_ui(mensagem):

            print(f"[PLAYWRIGHT]: {mensagem}") 

            if self.view_execucao:

                self.view.after(0, lambda: self.view_execucao.status_label.configure(text=f"Status: {mensagem}"))



        config = db.carregar_configuracoes()

        if not config or not config['link']:

            self.view.after(0, lambda: messagebox.showwarning("Aviso", "Configure o link e usuário do ERP na aba Configurações."))

            if self.view_execucao: self.view.after(0, self.view_execucao.restaurar_botao_robo)

            return



        try:

            atualizar_status_ui(f"Iniciando robô para {mes_formatado}/{filtros['ano']}...")

            robo_web.iniciar_automacao(config, meses_selecionados, anos_selecionados, progresso_callback=atualizar_status_ui)

            

            self.view.after(0, lambda: self.view_execucao.atualizar_tabela_dashboard())

            self.view.after(0, lambda: messagebox.showinfo("Sucesso", "Automação concluída com sucesso!"))

        

        except Exception as e:

            msg_erro = str(e)

            atualizar_status_ui("O robô parou devido a um erro.")

            self.view.after(0, lambda: messagebox.showerror("Erro Crítico", f"Falha na automação:\n{msg_erro}"))

        

        finally:

            if self.view_execucao: self.view.after(0, self.view_execucao.restaurar_botao_robo)

