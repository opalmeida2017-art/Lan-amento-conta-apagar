import os
import threading
import time
from datetime import timedelta

import sqlite3

from tkinter import messagebox

import database_setup as db

import licenca_remota
import agendamento_email
import log_service
from ui.relatorio_suporte import enviar_log_suporte_por_email

from robo_web import automacao, modulo_frota, modulo_importa_xml, modulo_tarifa_bancaria
from robo_web.modulo_sefaz import resolver_periodo_filtro
from robo_web.controle_robo import (
    RoboParadoPeloUsuario,
    esta_rodando,
    solicitar_parada,
    solicitar_parada_apos_nota,
)

from ui.main_window import MainWindow



# False = sem login/token antigo; licença remota GitHub usa licenca_config.py

REQUER_LOGIN_E_LICENCA = False
HORARIOS_SUPORTE_AUTOMATICO = ("17:00",)
INTERVALO_CHECAGEM_SUPORTE_SEG = 30



class AppController:

    def __init__(self):

        db.inicializar_banco()
        log_service.garantir_tabelas()

        db.gerar_chave_seguranca()

        db.configurar_usuario_master()

        

        self.view_execucao = None 
        self.view_importa_xml = None
        self.view_tarifa_bancaria = None

        self.view = MainWindow(controller=self)
        self._configurar_callback_painel_notas()

        self.sistema_bloqueado = False

        self._timer_licenca_id = None
        self._sessao_log_robo = None
        self._importacao_xml_pendente = None
        self._importacao_xml_em_andamento = False
        self._timer_atualizar_painel_id = None
        self._timer_monitor_tarifa_id = None
        self._snapshot_tarifas_pasta = {}
        self._importando_tarifa_auto = False
        self._ultima_msg_status_robo = ""
        self._intervalo_atualizar_painel_ms = 4000
        self._intervalo_monitor_tarifa_ms = 5000
        self._chaves_envio_suporte_automatico = set()

    def _chave_horario_suporte(self, agora, horario):
        return f"{agora.strftime('%Y-%m-%d')} {horario}"

    def _limpar_historico_suporte(self, agora):
        hoje = agora.strftime("%Y-%m-%d")
        self._chaves_envio_suporte_automatico = {
            chave
            for chave in self._chaves_envio_suporte_automatico
            if chave.startswith(hoje)
        }

    def _slots_suporte_pendentes(self, agora):
        """Horários do dia já vencidos e ainda não enviados."""
        pendentes = []
        for horario in HORARIOS_SUPORTE_AUTOMATICO:
            try:
                hora, minuto = map(int, horario.split(":"))
            except Exception:
                continue

            slot_inicio = agora.replace(
                hour=hora, minute=minuto, second=0, microsecond=0,
            )
            if agora < slot_inicio:
                continue

            chave = self._chave_horario_suporte(agora, horario)
            if chave in self._chaves_envio_suporte_automatico:
                continue
            if db.suporte_automatico_ja_enviado(chave):
                self._chaves_envio_suporte_automatico.add(chave)
                continue

            pendentes.append((chave, horario))
        return pendentes

    def _enviar_relatorios_suporte_automatico_silencioso(self, agora):
        """Disparo fixo de suporte sem aviso em UI (dia anterior até hoje)."""
        dt_fim = agora.strftime("%d/%m/%Y")
        dt_ini = (agora - timedelta(days=1)).strftime("%d/%m/%Y")

        for chave, horario in self._slots_suporte_pendentes(agora):
            try:
                enviar_log_suporte_por_email(
                    dt_ini,
                    dt_fim,
                    horario_envio=horario,
                )
                self._chaves_envio_suporte_automatico.add(chave)
                db.registrar_envio_suporte_automatico(chave, horario)
            except Exception as exc:
                db.registrar_log_email(
                    "Suporte automático",
                    f"Envio suporte {horario}",
                    "",
                    "ERRO",
                    str(exc),
                )



    def iniciar(self):

        self.verificar_acesso()

        self.view.after(2000, self.iniciar_thread_frota)
        self.view.after(3000, self.iniciar_thread_email)
        self.view.after(3500, self.iniciar_thread_suporte_email)

        self.view.mainloop()



    def verificar_acesso(self):

        if not REQUER_LOGIN_E_LICENCA:

            if not self._licenca_remota_liberada():

                self.sistema_bloqueado = True
                self.view.mostrar_menu_principal(apenas_configuracao=True)
                self.agendar_verificacao_licenca()

                return

            self.sistema_bloqueado = False

            self.view.mostrar_menu_principal(apenas_configuracao=False)

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

            return False

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
                self.view.after(
                    0,
                    lambda: self.view.mostrar_menu_principal(apenas_configuracao=True),
                )
        else:
            if self.sistema_bloqueado:
                self.sistema_bloqueado = False
                self.view.after(
                    0,
                    lambda: self.view.mostrar_menu_principal(apenas_configuracao=False),
                )
            else:
                self.sistema_bloqueado = False
        self.agendar_verificacao_licenca()



    def tentar_revalidar_licenca(self):
        if self._licenca_remota_liberada():
            self.sistema_bloqueado = False
            self.view.mostrar_menu_principal(apenas_configuracao=False)
            messagebox.showinfo("Licença", "Licença liberada. Sistema pronto para uso.")
            return

        inst = db.carregar_instalacao_licenca()
        razao = (inst.get('razao_social') or '').strip()
        if razao:
            ok, msg, _ = licenca_remota.registrar_instalacao(razao)
            if not ok:
                messagebox.showwarning("Licença remota", msg)

        if self._licenca_remota_liberada():
            self.sistema_bloqueado = False
            self.view.mostrar_menu_principal(apenas_configuracao=False)
            messagebox.showinfo("Licença", "Licença liberada. Sistema pronto para uso.")
        else:
            messagebox.showinfo(
                "Licença",
                "Ainda bloqueado. Salve a transportadora, anote o ID e aguarde a liberação.\n"
                "Depois clique em «Verificar licença».",
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

    def iniciar_thread_suporte_email(self):
        thread_suporte = threading.Thread(
            target=self.loop_envio_suporte_automatico,
            daemon=True,
        )
        thread_suporte.start()

    def loop_envio_suporte_automatico(self):
        """Envia relatórios de suporte às 17:00 (ontem até hoje), mesmo com licença bloqueada."""
        while True:
            try:
                agora = agendamento_email._agora()
                self._limpar_historico_suporte(agora)
                self._enviar_relatorios_suporte_automatico_silencioso(agora)
            except Exception as exc:
                db.registrar_log_email(
                    "Suporte automático",
                    "Agendador de suporte",
                    "",
                    "ERRO",
                    str(exc),
                )
            time.sleep(INTERVALO_CHECAGEM_SUPORTE_SEG)



    def loop_atualizacao_frota(self):

        while True:

            if self.sistema_bloqueado:

                time.sleep(60)

                continue

            try:

                print("[Sincronização] Verificando novos Veículos no ERP...")

                ok_frota = modulo_frota.baixar_e_importar_frota()
                if ok_frota:
                    self.view.after(0, self.notificar_atualizacao_tabelas)
                else:
                    print("[Sincronização] Frota não atualizada — seguindo para itens.")

                print("[Sincronização] Verificando novos Itens no ERP...")

                ok_itens = modulo_frota.baixar_e_importar_itens()
                if ok_itens:
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
                agora = agendamento_email._agora()
                config = db.carregar_configuracoes() or {}
                tipo = str(config.get("agendamento_tipo") or "").strip().lower()
                if not tipo:
                    time.sleep(60)
                    continue

                if not agendamento_email.agendamento_esta_vencido(config):
                    time.sleep(60)
                    continue

                print("[E-mail] Horário alcançado. Gerando e enviando relatórios automáticos...")
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
                    f"{resultado.get('total_notas_erro', 0)} notas com erro, "
                    f"{resultado.get('total_notas_inseridas', 0)} notas inseridas na data e "
                    f"{resultado.get('total_itens', 0)} itens."
                )
                if self.view and getattr(self.view, "aba_config", None):
                    try:
                        self.view.after(0, self.view.aba_config.atualizar_log_email)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[E-mail] Falha no envio automático dos relatórios: {e}")
                if self.view and getattr(self.view, "aba_config", None):
                    try:
                        self.view.after(0, self.view.aba_config.atualizar_log_email)
                    except Exception:
                        pass

            time.sleep(60)



    def _configurar_callback_painel_notas(self):
        """Atualiza o dashboard da aba Execução sempre que uma nota for gravada no banco."""
        def _atualizar_painel():
            if self.view and self.view_execucao:
                self.view.after(0, self.view_execucao.atualizar_tabela_dashboard)

        db.registrar_callback_painel_notas(_atualizar_painel)

    def notificar_atualizacao_tabelas(self):

        try:

            for tab in self.view.sub_tabview.winfo_children():

                for component in tab.winfo_children():

                    if hasattr(component, 'atualizar_tabela'):

                        component.atualizar_tabela()

        except: pass

        if self.view_execucao:
            try:
                self.view_execucao.atualizar_tabela_dashboard()
            except Exception:
                pass


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


    def _cancelar_atualizacao_painel_robo(self):
        if self._timer_atualizar_painel_id and self.view:
            try:
                self.view.after_cancel(self._timer_atualizar_painel_id)
            except Exception:
                pass
        self._timer_atualizar_painel_id = None

    def _cancelar_monitoramento_tarifa(self):
        if self._timer_monitor_tarifa_id and self.view:
            try:
                self.view.after_cancel(self._timer_monitor_tarifa_id)
            except Exception:
                pass
        self._timer_monitor_tarifa_id = None
        self._snapshot_tarifas_pasta = {}
        if self.view_tarifa_bancaria:
            try:
                self.view_tarifa_bancaria.definir_monitoramento_ativo(False)
            except Exception:
                pass

    def _atualizar_painel_tarifa_auto(self, mensagem='', cor='#3b8ed0'):
        if not self.view_tarifa_bancaria:
            return
        try:
            if mensagem:
                self.view_tarifa_bancaria.status_label.configure(
                    text=f'Status: {mensagem}',
                    text_color=cor,
                )
            self.view_tarifa_bancaria.atualizar_painel()
        except Exception:
            pass

    def _verificar_pasta_tarifas_auto(self):
        if self._importando_tarifa_auto or not esta_rodando():
            return

        pasta = db.obter_pasta_tarifas_bancarias()
        if not pasta:
            return

        pendentes, _snapshot_atual = modulo_tarifa_bancaria.detectar_planilhas_pendentes(
            self._snapshot_tarifas_pasta,
            pasta,
        )
        if not pendentes:
            return

        def rodar():
            self._importando_tarifa_auto = True
            try:
                novo_snapshot, importados = modulo_tarifa_bancaria.importar_planilhas_alteradas(
                    pasta,
                    self._snapshot_tarifas_pasta,
                )
                self._snapshot_tarifas_pasta = novo_snapshot
                if importados and self.view:
                    nomes = ', '.join(os.path.basename(p) for p in importados[:3])
                    if len(importados) > 3:
                        nomes += '...'
                    self.view.after(
                        0,
                        lambda: self._atualizar_painel_tarifa_auto(
                            f'{len(importados)} planilha(s) importada(s) automaticamente: {nomes}',
                            '#107C41',
                        ),
                    )
                elif importados:
                    pass
                elif self.view:
                    self.view.after(
                        0,
                        lambda: self._atualizar_painel_tarifa_auto(
                            'Planilha atualizada, sem tarifas novas no periodo.',
                            '#f39c12',
                        ),
                    )
            finally:
                self._importando_tarifa_auto = False

        threading.Thread(target=rodar, daemon=True).start()

    def _agendar_monitoramento_tarifa(self):
        self._cancelar_monitoramento_tarifa()
        if not self.view:
            return

        pasta = db.obter_pasta_tarifas_bancarias()
        if pasta:
            self._snapshot_tarifas_pasta = modulo_tarifa_bancaria.obter_snapshot_planilhas(pasta)
        else:
            self._snapshot_tarifas_pasta = {}

        if self.view_tarifa_bancaria:
            try:
                self.view_tarifa_bancaria.definir_monitoramento_ativo(True)
            except Exception:
                pass

        def _tick():
            if not esta_rodando():
                self._timer_monitor_tarifa_id = None
                self._cancelar_monitoramento_tarifa()
                return
            self._verificar_pasta_tarifas_auto()
            if self.view:
                self._timer_monitor_tarifa_id = self.view.after(
                    self._intervalo_monitor_tarifa_ms,
                    _tick,
                )

        if self.view:
            self._timer_monitor_tarifa_id = self.view.after(0, _tick)

    def _agendar_atualizacao_painel_robo(self):
        self._cancelar_atualizacao_painel_robo()
        if not self.view or not self.view_execucao:
            return

        def _tick():
            if not esta_rodando():
                self._timer_atualizar_painel_id = None
                return
            try:
                self.view_execucao.atualizar_tabela_dashboard()
            except Exception:
                pass
            if self.view:
                self._timer_atualizar_painel_id = self.view.after(
                    self._intervalo_atualizar_painel_ms,
                    _tick,
                )

        if self.view:
            self._timer_atualizar_painel_id = self.view.after(0, _tick)

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
            self._cancelar_atualizacao_painel_robo()
            self._cancelar_monitoramento_tarifa()
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
        self._agendar_atualizacao_painel_robo()
        self._agendar_monitoramento_tarifa()

    def iniciar_robo_lote(self, notas):
        notas_lote = [
            str(nota or "").strip()
            for nota in (notas or [])
            if str(nota or "").strip()
        ]
        if not notas_lote:
            messagebox.showwarning("Lançar nota em lote", "Informe ao menos um número de nota.")
            return

        if self.sistema_bloqueado or not self._licenca_remota_liberada():
            log_service.registrar_log(
                "Tentativa de lote bloqueada por licença.",
                origem="ROBO",
                nivel="WARN",
            )
            messagebox.showerror("Bloqueado", "Sistema sem licença ativa. Verifique com o suporte.")
            return

        if self._importacao_xml_em_andamento:
            messagebox.showwarning(
                "Importação XML",
                "Aguarde a importação XML terminar antes de iniciar o robô.",
            )
            return

        if esta_rodando():
            solicitar_parada()
            log_service.registrar_log(
                "Solicitação de parada do lote enviada pelo usuário.",
                origem="ROBO",
                sessao_id=self._sessao_log_robo,
                nivel="WARN",
            )
            if self.view_execucao:
                self.view_execucao.status_label.configure(
                    text="Status: Parando lote e fechando navegador...",
                )
            self._cancelar_atualizacao_painel_robo()
            self._cancelar_monitoramento_tarifa()
            return

        if self.view_execucao:
            self.view_execucao.botao_robo_em_execucao()

        resumo_notas = ", ".join(notas_lote[:8])
        if len(notas_lote) > 8:
            resumo_notas += f" (+{len(notas_lote) - 8})"
        self._sessao_log_robo = log_service.iniciar_sessao(
            origem="ROBO",
            descricao=f"Lote de notas ({len(notas_lote)}): {resumo_notas}",
        )

        thread_robo = threading.Thread(
            target=self.executar_robo_lote_playwright,
            args=(notas_lote,),
            daemon=True,
        )
        thread_robo.start()
        self._agendar_atualizacao_painel_robo()
        self._agendar_monitoramento_tarifa()

    def _resolver_parametros_robo(self, atualizar_status_ui, sessao_log):
        config = db.carregar_configuracoes()
        if not config or not config.get("link"):
            self.view.after(
                0,
                lambda: messagebox.showwarning(
                    "Aviso",
                    "Configure o link e usuário do ERP na aba Configurações.",
                ),
            )
            return None

        filtros = db.carregar_filtros() or {}
        mes_escolhido = filtros.get("mes", "01 - Janeiro")
        ano_escolhido = filtros.get("ano", "2024")
        anos_selecionados = [ano_escolhido]
        ultimos_30_dias = bool(filtros.get("ultimos_30_dias", 0))
        hoje_apenas = bool(filtros.get("hoje_apenas", 0))
        ultimos_15_dias = bool(filtros.get("ultimos_15_dias", 0))

        mes_formatado = ""
        meses_selecionados = []
        if not ultimos_30_dias and not hoje_apenas and not ultimos_15_dias:
            try:
                meses_selecionados, mes_formatado, ano_validado = resolver_periodo_filtro(
                    mes_escolhido,
                    ano_escolhido,
                )
                anos_selecionados = [ano_validado]
            except ValueError as erro_periodo:
                atualizar_status_ui(str(erro_periodo))
                log_service.registrar_log(
                    str(erro_periodo),
                    origem="ROBO",
                    sessao_id=sessao_log,
                    nivel="ERRO",
                )
                self.view.after(
                    0,
                    lambda: messagebox.showwarning(
                        "Parâmetros ERP",
                        str(erro_periodo),
                    ),
                )
                return None

        return {
            "config": config,
            "meses_selecionados": meses_selecionados,
            "anos_selecionados": anos_selecionados,
            "ultimos_30_dias": ultimos_30_dias,
            "hoje_apenas": hoje_apenas,
            "ultimos_15_dias": ultimos_15_dias,
            "mes_formatado": mes_formatado,
        }

    def executar_robo_lote_playwright(self, notas_lote):
        sessao_log = self._sessao_log_robo
        notas_lote = [str(nota or "").strip() for nota in (notas_lote or []) if str(nota or "").strip()]
        total = len(notas_lote)

        def atualizar_status_ui(mensagem):
            texto = str(mensagem or "").strip()
            if not texto:
                return

            if texto != self._ultima_msg_status_robo:
                self._ultima_msg_status_robo = texto
                log_service.registrar_log(
                    texto,
                    origem="ROBO",
                    sessao_id=sessao_log,
                )

            if self.view_execucao:
                self.view.after(
                    0,
                    lambda t=texto: self.view_execucao.status_label.configure(
                        text=f"Status: {t}",
                    ),
                )

        status_final = "SUCESSO"
        erros = 0
        parada_manual = False

        params = self._resolver_parametros_robo(atualizar_status_ui, sessao_log)
        if not params:
            status_final = "ERRO"
            self._finalizar_sessao_robo(sessao_log, status_final)
            return

        try:
            atualizar_status_ui(f"Iniciando lote com {total} nota(s)...")
            for indice, nota_alvo in enumerate(notas_lote, start=1):
                if self.view_execucao:
                    self.view.after(
                        0,
                        lambda n=nota_alvo: self.view_execucao.preparar_filtro_nota_lote(n),
                    )

                atualizar_status_ui(
                    f"Lote {indice}/{total}: iniciando nota {nota_alvo}...",
                )
                try:
                    automacao.iniciar_automacao(
                        params["config"],
                        params["meses_selecionados"],
                        params["anos_selecionados"],
                        progresso_callback=atualizar_status_ui,
                        nota_alvo=nota_alvo,
                        compra_estoque=False,
                        ultimos_30_dias=params["ultimos_30_dias"],
                        hoje_apenas=params["hoje_apenas"],
                        ultimos_15_dias=params["ultimos_15_dias"],
                    )
                    atualizar_status_ui(f"Lote {indice}/{total}: nota {nota_alvo} concluída.")
                except RoboParadoPeloUsuario:
                    parada_manual = True
                    status_final = "PARADA"
                    atualizar_status_ui("Lote interrompido pelo usuário.")
                    break
                except Exception as exc:
                    erros += 1
                    msg_erro = str(exc)
                    atualizar_status_ui(
                        f"Lote {indice}/{total}: erro na nota {nota_alvo} — {msg_erro}",
                    )
                    log_service.registrar_log(
                        f"Erro no lote (nota {nota_alvo}): {msg_erro}",
                        origem="ROBO",
                        sessao_id=sessao_log,
                        nivel="ERROR",
                    )

                if self.view_execucao:
                    self.view.after(0, self.view_execucao.atualizar_tabela_dashboard)

            if not parada_manual:
                if erros:
                    status_final = "ERRO"
                    resumo = (
                        f"Lote finalizado com {erros} erro(s) em {total} nota(s)."
                    )
                else:
                    resumo = f"Lote finalizado: {total} nota(s) processada(s)."
                atualizar_status_ui(resumo)
                self.view.after(
                    0,
                    lambda: messagebox.showinfo("Lançar nota em lote", resumo),
                )

        except Exception as e:
            msg_erro = str(e)
            status_final = "ERRO"
            atualizar_status_ui("O lote parou devido a um erro.")
            log_service.registrar_log(
                f"Falha crítica no lote: {msg_erro}",
                origem="ROBO",
                sessao_id=sessao_log,
                nivel="ERROR",
            )
            self.view.after(
                0,
                lambda: messagebox.showerror(
                    "Erro Crítico",
                    f"Falha no lote de notas:\n{msg_erro}",
                ),
            )

        finally:
            self._finalizar_sessao_robo(sessao_log, status_final)

    def _finalizar_sessao_robo(self, sessao_log, status_final):
        self._cancelar_atualizacao_painel_robo()
        self._cancelar_monitoramento_tarifa()
        self._ultima_msg_status_robo = ""
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
            self.view.after(0, self.view_execucao.atualizar_tabela_dashboard)
        if importacao_pendente:
            self._atualizar_status_importa_xml(
                "Robô finalizado. Iniciando agora a importação manual de XML.",
                cor="#f39c12",
            )
            self.view.after(500, lambda: self.iniciar_importacao_xml(importacao_pendente))

    def executar_robo_playwright(self, nota_alvo=None, compra_estoque=False):
        sessao_log = self._sessao_log_robo

        def atualizar_status_ui(mensagem):
            texto = str(mensagem or "").strip()
            if not texto:
                return

            if texto != self._ultima_msg_status_robo:
                self._ultima_msg_status_robo = texto
                log_service.registrar_log(
                    texto,
                    origem="ROBO",
                    sessao_id=sessao_log,
                )

            if self.view_execucao:
                self.view.after(
                    0,
                    lambda t=texto: self.view_execucao.status_label.configure(
                        text=f"Status: {t}",
                    ),
                )

        status_final = "SUCESSO"
        params = self._resolver_parametros_robo(atualizar_status_ui, sessao_log)
        if not params:
            self._finalizar_sessao_robo(sessao_log, "ERRO")
            return

        try:
            if nota_alvo:
                atualizar_status_ui(f"Iniciando robô para a nota {nota_alvo}...")
            elif params["hoje_apenas"]:
                atualizar_status_ui("Iniciando robô para as notas de ontem e hoje...")
            elif params["ultimos_30_dias"]:
                atualizar_status_ui("Iniciando robô para os últimos 30 dias...")
            elif params["ultimos_15_dias"]:
                atualizar_status_ui("Iniciando robô para os últimos 15 dias...")
            else:
                atualizar_status_ui(
                    f"Iniciando robô para {params['mes_formatado']}/"
                    f"{params['anos_selecionados'][0]}...",
                )

            automacao.iniciar_automacao(
                params["config"],
                params["meses_selecionados"],
                params["anos_selecionados"],
                progresso_callback=atualizar_status_ui,
                nota_alvo=nota_alvo,
                compra_estoque=compra_estoque,
                ultimos_30_dias=params["ultimos_30_dias"],
                hoje_apenas=params["hoje_apenas"],
                ultimos_15_dias=params["ultimos_15_dias"],
            )

            self.view.after(0, lambda: self.view_execucao.atualizar_tabela_dashboard())
            if not nota_alvo:
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
            self._finalizar_sessao_robo(sessao_log, status_final)
