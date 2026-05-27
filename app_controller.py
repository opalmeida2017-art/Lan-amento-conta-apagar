import threading

import time

import sqlite3

from tkinter import messagebox

import database_setup as db

import licenca_remota
import agendamento_email
import log_service

from robo_web import robo_web, modulo_frota, modulo_importa_xml
from robo_web.controle_robo import (
    RoboParadoPeloUsuario,
    esta_rodando,
    solicitar_parada,
    solicitar_parada_apos_nota,
)

from ui.main_window import MainWindow



# False = sem login/token antigo; licença remota GitHub usa licenca_config.py

REQUER_LOGIN_E_LICENCA = False



class AppController:

    def __init__(self):

        db.inicializar_banco()
        log_service.garantir_tabelas()

        db.gerar_chave_seguranca()

        db.configurar_usuario_master()

        

        self.view_execucao = None 
        self.view_importa_xml = None

        self.view = MainWindow(controller=self)

        self.sistema_bloqueado = False

        self._timer_licenca_id = None
        self._sessao_log_robo = None
        self._importacao_xml_pendente = None
        self._importacao_xml_em_andamento = False



    def iniciar(self):

        self.verificar_acesso()

        self.view.after(2000, self.iniciar_thread_frota)
        self.view.after(3000, self.iniciar_thread_email)

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

        try:
            licenca_remota.garantir_registro_inicial_bloqueado()
        except Exception:
            pass

        iid = db.obter_ou_criar_instalacao_id()

        if not iid:

            return False

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


    def iniciar_thread_email(self):
        thread_email = threading.Thread(target=self.loop_envio_email_agendado, daemon=True)
        thread_email.start()



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


    def loop_envio_email_agendado(self):
        while True:
            if self.sistema_bloqueado:
                time.sleep(60)
                continue

            try:
                config = db.carregar_configuracoes() or {}
                tipo = str(config.get("agendamento_tipo") or "").strip().lower()
                if not tipo:
                    time.sleep(60)
                    continue

                if not agendamento_email.agendamento_esta_vencido(config):
                    time.sleep(60)
                    continue

                print("[E-mail] Horário alcançado. Gerando e enviando relatórios automáticos...")
                agora = agendamento_email._agora()
                resultado = agendamento_email.enviar_relatorios_agendados(config, referencia=agora)
                proxima = resultado.get("proxima_execucao")
                db.atualizar_agendamento_email(
                    tipo=tipo,
                    intervalo_horas=config.get("intervalo_horas") or 1,
                    proxima_execucao=agendamento_email.formatar_data_hora(proxima),
                    ultima_execucao=agendamento_email.formatar_data_hora(agora),
                )
                print(
                    "[E-mail] Relatórios enviados com sucesso: "
                    f"{resultado.get('total_notas', 0)} notas e {resultado.get('total_itens', 0)} itens."
                )
            except Exception as e:
                print(f"[E-mail] Falha no envio automático dos relatórios: {e}")

            time.sleep(60)



    def notificar_atualizacao_tabelas(self):

        try:

            for tab in self.view.sub_tabview.winfo_children():

                for component in tab.winfo_children():

                    if hasattr(component, 'atualizar_tabela'):

                        component.atualizar_tabela()

        except: pass


    def _atualizar_status_importa_xml(self, mensagem, cor="gray"):
        if self.view_importa_xml:
            self.view.after(
                0,
                lambda: self.view_importa_xml.atualizar_status_geral(mensagem, cor),
            )


    def _atualizar_item_importa_xml(self, item, status, mensagem=""):
        if self.view_importa_xml:
            self.view.after(
                0,
                lambda item=item, status=status, mensagem=mensagem: (
                    self.view_importa_xml.atualizar_item(item, status, mensagem)
                ),
            )


    def _definir_estado_importa_xml(self, executando):
        if self.view_importa_xml:
            self.view.after(
                0,
                lambda: self.view_importa_xml.definir_estado_execucao(executando),
            )


    def solicitar_importacao_xml(self, itens_xml):
        itens = [dict(item) for item in (itens_xml or []) if item.get("caminho")]
        if not itens:
            messagebox.showwarning("Importação XML", "Nenhum XML foi carregado para importação.")
            return

        if self._importacao_xml_em_andamento:
            messagebox.showwarning(
                "Importação XML",
                "Já existe uma importação XML em andamento. Aguarde terminar.",
            )
            return

        if self._importacao_xml_pendente:
            messagebox.showwarning(
                "Importação XML",
                "Já existe uma importação XML agendada aguardando o robô finalizar a nota atual.",
            )
            return

        if self.sistema_bloqueado or not self._licenca_remota_liberada():
            messagebox.showerror("Bloqueado", "Sistema sem licença ativa. Verifique com o suporte.")
            return

        if esta_rodando():
            self._importacao_xml_pendente = itens
            self._definir_estado_importa_xml(True)
            self._atualizar_status_importa_xml(
                "Importação XML agendada. O robô vai parar após concluir a nota atual.",
                "#f39c12",
            )
            for item in itens:
                self._atualizar_item_importa_xml(
                    item,
                    "AGUARDANDO ROBÔ",
                    "Aguardando o robô concluir a nota atual para iniciar a importação XML.",
                )
            solicitar_parada_apos_nota()
            if self.view_execucao:
                self.view.after(
                    0,
                    lambda: self.view_execucao.status_label.configure(
                        text="Status: Robô vai parar após a nota atual para iniciar a importação XML.",
                    ),
                )
            return

        self._iniciar_thread_importacao_xml(itens)


    def _iniciar_thread_importacao_xml(self, itens_xml):
        itens = [dict(item) for item in (itens_xml or []) if item.get("caminho")]
        if not itens or self._importacao_xml_em_andamento:
            return

        self._importacao_xml_pendente = None
        self._importacao_xml_em_andamento = True
        self._definir_estado_importa_xml(True)
        self._atualizar_status_importa_xml(
            f"Preparando importação manual de {len(itens)} XML(s)...",
            "#3b8ed0",
        )
        thread_xml = threading.Thread(
            target=self.executar_importacao_xml,
            args=(itens,),
            daemon=True,
        )
        thread_xml.start()


    def executar_importacao_xml(self, itens_xml):
        sessao_log = log_service.iniciar_sessao(
            origem="XML",
            descricao=f"Importação manual de {len(itens_xml)} XML(s)",
        )

        def log_xml(mensagem):
            print(f"[XML]: {mensagem}")
            log_service.registrar_log(
                mensagem,
                origem="XML",
                sessao_id=sessao_log,
            )
            self._atualizar_status_importa_xml(mensagem, "#3b8ed0")

        def atualizar_item_xml(item, status, mensagem=""):
            self._atualizar_item_importa_xml(item, status, mensagem)

        status_final = "CONCLUIDA"
        try:
            config = db.carregar_configuracoes()
            if (
                not config
                or not config.get("link")
                or not config.get("user_sis")
                or not config.get("senha_sis")
            ):
                status_final = "CANCELADA"
                for item in itens_xml:
                    atualizar_item_xml(
                        item,
                        "ERRO",
                        "Configure o link, usuário e senha do ERP antes de importar XML.",
                    )
                self.view.after(
                    0,
                    lambda: messagebox.showwarning(
                        "Importação XML",
                        "Configure o link, usuário e senha do ERP antes de importar XML.",
                    ),
                )
                return

            resultado = modulo_importa_xml.iniciar_importacao_xml(
                config,
                itens_xml,
                log_callback=log_xml,
                status_callback=atualizar_item_xml,
            )
            self._atualizar_status_importa_xml(
                f"Importação XML concluída: {resultado.get('ok', 0)} sucesso(s), "
                f"{resultado.get('erro', 0)} erro(s).",
                "#3b8ed0",
            )
            self.view.after(
                0,
                lambda: messagebox.showinfo(
                    "Importação XML",
                    "Importação manual de XML concluída.",
                ),
            )
        except Exception as e:
            status_final = "ERRO"
            msg_erro = str(e)
            log_service.registrar_log(
                f"Falha na importação XML: {msg_erro}",
                origem="XML",
                sessao_id=sessao_log,
                nivel="ERROR",
            )
            self._atualizar_status_importa_xml(
                f"Falha na importação XML: {msg_erro}",
                "#e57373",
            )
            self.view.after(
                0,
                lambda: messagebox.showerror(
                    "Importação XML",
                    f"Falha na importação XML:\n{msg_erro}",
                ),
            )
        finally:
            log_service.finalizar_sessao(
                sessao_log,
                origem="XML",
                status=status_final,
            )
            self._importacao_xml_em_andamento = False
            self._definir_estado_importa_xml(False)


    def iniciar_robo(self, nota_alvo=None, compra_estoque=False):
        if self.sistema_bloqueado or not self._licenca_remota_liberada():
            log_service.registrar_log(
                "Tentativa de iniciar o robô bloqueada por licença.",
                origem="ROBO",
                nivel="WARN",
            )
            messagebox.showerror("Bloqueado", "Sistema sem licença ativa. Verifique com o suporte.")
            if self.view_execucao:
                self.view_execucao.restaurar_botao_robo()
            return

        if self._importacao_xml_em_andamento:
            messagebox.showwarning(
                "Importação XML",
                "Aguarde a importação XML terminar antes de iniciar o robô.",
            )
            if self.view_execucao:
                self.view_execucao.restaurar_botao_robo()
            return

        if esta_rodando():
            solicitar_parada()
            log_service.registrar_log(
                "Solicitação de parada do robô enviada pelo usuário.",
                origem="ROBO",
                sessao_id=self._sessao_log_robo,
                nivel="WARN",
            )
            if self.view_execucao:
                self.view_execucao.status_label.configure(
                    text="Status: Parando robô e fechando navegador...",
                )
            return

        if self.view_execucao:
            self.view_execucao.botao_robo_em_execucao()

        descricao = (
            f"Nota alvo {nota_alvo}" if nota_alvo else "Processamento completo do robô"
        )
        self._sessao_log_robo = log_service.iniciar_sessao(
            origem="ROBO",
            descricao=descricao,
        )

        thread_robo = threading.Thread(
            target=self.executar_robo_playwright,
            args=(nota_alvo, compra_estoque),
            daemon=True,
        )
        thread_robo.start()



    def executar_robo_playwright(self, nota_alvo=None, compra_estoque=False):
        sessao_log = self._sessao_log_robo
        status_final = "CONCLUIDA"

        filtros = db.carregar_filtros()

        if not filtros:
            log_service.registrar_log(
                "Execução cancelada: mês/ano não configurados.",
                origem="ROBO",
                sessao_id=sessao_log,
                nivel="WARN",
            )

            self.view.after(
                0,
                lambda: messagebox.showwarning(
                    "Aviso",
                    "Selecione o Mês e Ano na aba 'Parâmetros ERP' antes de iniciar!",
                ),
            )

            if self.view_execucao: self.view.after(0, self.view_execucao.restaurar_botao_robo)
            log_service.finalizar_sessao(
                sessao_log,
                origem="ROBO",
                status="CANCELADA",
            )
            self._sessao_log_robo = None

            return



        ultimos_30_dias = bool((filtros or {}).get('ultimos_30_dias'))

        try:
            mes_completo = filtros['mes'].split("-")[1].strip()
            mes_formatado = mes_completo[:3].capitalize()
        except Exception:
            mes_formatado = "Jan"

        meses_selecionados = [mes_formatado]
        anos_selecionados = [filtros['ano']]
        descricao_periodo = (
            "últimos 30 dias"
            if ultimos_30_dias
            else f"{mes_formatado}/{filtros['ano']}"
        )



        def atualizar_status_ui(mensagem):

            print(f"[PLAYWRIGHT]: {mensagem}") 
            log_service.registrar_log(
                mensagem,
                origem="ROBO",
                sessao_id=sessao_log,
            )

            if self.view_execucao:

                self.view.after(0, lambda: self.view_execucao.status_label.configure(text=f"Status: {mensagem}"))



        config = db.carregar_configuracoes()

        if not config or not config['link']:
            log_service.registrar_log(
                "Execução cancelada: configurações do ERP ausentes.",
                origem="ROBO",
                sessao_id=sessao_log,
                nivel="WARN",
            )

            self.view.after(0, lambda: messagebox.showwarning("Aviso", "Configure o link e usuário do ERP na aba Configurações."))

            if self.view_execucao: self.view.after(0, self.view_execucao.restaurar_botao_robo)
            log_service.finalizar_sessao(
                sessao_log,
                origem="ROBO",
                status="CANCELADA",
            )
            self._sessao_log_robo = None

            return



        try:
            if nota_alvo:
                atualizar_status_ui(
                    f"Iniciando lançamento da nota {nota_alvo} para "
                    f"{descricao_periodo}...",
                )
            else:
                atualizar_status_ui(f"Iniciando robô para {descricao_periodo}...")
            robo_web.iniciar_automacao(
                config,
                meses_selecionados,
                anos_selecionados,
                progresso_callback=atualizar_status_ui,
                nota_alvo=nota_alvo,
                compra_estoque=compra_estoque,
                ultimos_30_dias=ultimos_30_dias,
            )
            self.view.after(0, lambda: self.view_execucao.atualizar_tabela_dashboard())
            if not self._importacao_xml_pendente:
                self.view.after(0, lambda: messagebox.showinfo("Sucesso", "Automação concluída com sucesso!"))

        except RoboParadoPeloUsuario:
            status_final = "PARADA"
            atualizar_status_ui("Robô parado. Navegador fechado.")
            self.view.after(0, lambda: self.view_execucao.atualizar_tabela_dashboard())

        except Exception as e:
            msg_erro = str(e)
            status_final = "ERRO"
            atualizar_status_ui("O robô parou devido a um erro.")
            log_service.registrar_log(
                f"Falha crítica: {msg_erro}",
                origem="ROBO",
                sessao_id=sessao_log,
                nivel="ERROR",
            )
            self.view.after(0, lambda: messagebox.showerror("Erro Crítico", f"Falha na automação:\n{msg_erro}"))

        finally:
            log_service.finalizar_sessao(
                sessao_log,
                origem="ROBO",
                status=status_final,
            )
            importacao_pendente = self._importacao_xml_pendente
            self._importacao_xml_pendente = None
            self._sessao_log_robo = None
            if self.view_execucao:
                self.view.after(0, self.view_execucao.restaurar_botao_robo)
            if importacao_pendente:
                self._atualizar_status_importa_xml(
                    "Robô finalizado. Iniciando agora a importação manual de XML.",
                    "#3b8ed0",
                )
                self._iniciar_thread_importacao_xml(importacao_pendente)

