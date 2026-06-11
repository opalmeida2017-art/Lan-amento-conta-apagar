from calendar import monthrange
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
import smtplib
import tempfile
from urllib.parse import urlparse

import database_setup as db
from ui.relatorio_execucao import salvar_relatorio_excel as salvar_relatorio_notas_excel
from ui.relatorio_itens import salvar_relatorio_excel as salvar_relatorio_itens_excel


FORMATO_BANCO = "%Y-%m-%d %H:%M:%S"


def _agora():
    return datetime.now()


def formatar_data_hora(valor):
    if not valor:
        return ""
    return valor.strftime(FORMATO_BANCO)


def parse_data_hora(valor):
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        return datetime.strptime(texto, FORMATO_BANCO)
    except Exception:
        return None


def normalizar_tipo_agendamento(tipo):
    texto = str(tipo or "").strip().lower()
    mapa = {
        "hora": "hora",
        "horario": "hora",
        "horário": "hora",
        "diario": "diario",
        "diário": "diario",
        "semanal": "semanal",
        "mensal": "mensal",
    }
    return mapa.get(texto, "")


def calcular_proxima_execucao(tipo, intervalo_horas=1, referencia=None):
    agora = referencia or _agora()
    tipo_normalizado = normalizar_tipo_agendamento(tipo)

    if tipo_normalizado == "hora":
        try:
            horas = max(1, int(intervalo_horas or 1))
        except Exception:
            horas = 1
        return agora + timedelta(hours=horas)

    if tipo_normalizado == "diario":
        proxima = agora.replace(hour=23, minute=59, second=0, microsecond=0)
        if proxima <= agora:
            proxima += timedelta(days=1)
        return proxima

    if tipo_normalizado == "semanal":
        proxima = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        dias_ate_segunda = (7 - proxima.weekday()) % 7
        if dias_ate_segunda == 0 and proxima <= agora:
            dias_ate_segunda = 7
        return proxima + timedelta(days=dias_ate_segunda)

    if tipo_normalizado == "mensal":
        ano = agora.year
        mes = agora.month
        ultimo_dia = monthrange(ano, mes)[1]
        proxima = agora.replace(
            day=ultimo_dia, hour=23, minute=59, second=0, microsecond=0,
        )
        if proxima <= agora:
            if mes == 12:
                ano += 1
                mes = 1
            else:
                mes += 1
            ultimo_dia = monthrange(ano, mes)[1]
            proxima = proxima.replace(year=ano, month=mes, day=ultimo_dia)
        return proxima

    return None


def descricao_agendamento(tipo, intervalo_horas=1):
    tipo_normalizado = normalizar_tipo_agendamento(tipo)
    if tipo_normalizado == "hora":
        try:
            horas = max(1, int(intervalo_horas or 1))
        except Exception:
            horas = 1
        return f"A cada {horas} hora(s)"
    if tipo_normalizado == "diario":
        return "Diariamente às 23:59"
    if tipo_normalizado == "semanal":
        return "Semanalmente às segundas às 00:00"
    if tipo_normalizado == "mensal":
        return "Mensalmente no último dia do mês às 23:59"
    return "Desativado"


def resumo_proximo_envio(tipo, intervalo_horas=1, referencia=None):
    proxima = calcular_proxima_execucao(tipo, intervalo_horas, referencia=referencia)
    if not proxima:
        return "Envio automático desativado."
    return (
        f"{descricao_agendamento(tipo, intervalo_horas)}\n\n"
        f"Próximo envio: {proxima.strftime('%d/%m/%Y %H:%M')}"
    )


def agendamento_esta_vencido(configuracao, referencia=None):
    tipo = normalizar_tipo_agendamento((configuracao or {}).get("agendamento_tipo"))
    if not tipo:
        return False
    agora = referencia or _agora()
    proxima = parse_data_hora((configuracao or {}).get("proxima_execucao"))
    if not proxima:
        proxima = calcular_proxima_execucao(
            tipo, (configuracao or {}).get("intervalo_horas") or 1, referencia=agora,
        )
        db.atualizar_agendamento_email(
            tipo=tipo,
            intervalo_horas=(configuracao or {}).get("intervalo_horas") or 1,
            proxima_execucao=formatar_data_hora(proxima),
        )
        return False
    return agora >= proxima


_CABECALHOS_NOTAS = [
    "Inserção",
    "Cód. Interno",
    "Status",
    "Fornecedor",
    "No.Nota",
    "Data Em.",
    "Valor",
    "Sit. NFe",
    "Filial",
    "Usuário Inserção",
    "Erro Importação",
    "Observação NFe",
    "NFe p/ Estoque",
    "Arquiva",
]


def _linha_relatorio_nota(nota):
    estoque = "   [ ☑ ]   " if "☑" in str(nota.get("nfe_estoque") or "") else "   [ ☐ ]   "
    arquiva = "   [ ☑ ]   " if "☑" in str(nota.get("nfe_arquiva") or "") else "   [ ☐ ]   "
    return [
        db.formatar_data_insercao_exibicao(nota.get("data_insercao")),
        str(nota.get("codigo_interno") or ""),
        db.status_exibicao_painel(nota),
        str(nota.get("fornecedor") or ""),
        str(nota.get("num_nota") or ""),
        str(nota.get("data_em") or ""),
        str(nota.get("valor") or ""),
        str(nota.get("sit_nfe") or ""),
        str(nota.get("filial") or ""),
        str(nota.get("user_ins") or ""),
        str(nota.get("erro_importacao") or ""),
        str(nota.get("observacao_nfe") or ""),
        estoque,
        arquiva,
    ]


def _dados_relatorio_notas_erro():
    filtros = {
        "Critério de data": "Data Inserção",
        "Data Inserção Inicial": "Todos",
        "Data Inserção Final": "Todos",
        "Cód. Interno": "Todos",
        "Nº Nota": "Todos",
        "Status": "Erro",
    }
    linhas = [
        _linha_relatorio_nota(nota)
        for nota in db.listar_notas_filtradas(status="Erro", campo_data="insercao")
    ]
    return filtros, list(_CABECALHOS_NOTAS), linhas


def _dados_relatorio_notas_inseridas_na_data(referencia=None):
    agora = referencia or _agora()
    data_ref = agora.strftime("%d/%m/%Y")
    filtros = {
        "Critério de data": "Data Inserção",
        "Data Inserção Inicial": data_ref,
        "Data Inserção Final": data_ref,
        "Cód. Interno": "Todos",
        "Nº Nota": "Todos",
        "Status": "Todos",
    }
    notas, _, _ = db.listar_notas_por_periodo(
        data_ref, data_ref, campo_data="insercao",
    )
    linhas = [_linha_relatorio_nota(nota) for nota in notas]
    return filtros, list(_CABECALHOS_NOTAS), linhas


def _item_do_grupo_indefinido(item):
    grupo = str((item or {}).get("descGrupoImp") or "").strip().upper()
    return "INDEFINIDO" in grupo


def _dados_relatorio_itens():
    filtros = {
        "Código": "Todos",
        "Grupo": "INDEFINIDO",
        "Descrição": "Todos",
    }
    cabecalhos = ["Cód. Item", "Grupo Atual", "Negócio", "Descrição"]
    linhas = []
    for item in db.obter_itens_erp():
        if not _item_do_grupo_indefinido(item):
            continue
        linhas.append([
            str(item.get("codItemD") or ""),
            str(item.get("descGrupoImp") or ""),
            str(item.get("descNegocioImp") or ""),
            str(item.get("descricao") or ""),
        ])
    return filtros, cabecalhos, linhas


def gerar_anexos_relatorios(referencia=None):
    pasta_temp = Path(tempfile.gettempdir())
    agora = referencia or _agora()
    sufixo = agora.strftime("%Y%m%d_%H%M%S")
    data_ref = agora.strftime("%d/%m/%Y")

    filtros_erro, cabecalhos_erro, linhas_erro = _dados_relatorio_notas_erro()
    caminho_notas_erro = pasta_temp / f"relatorio_notas_erro_{sufixo}.xlsx"
    salvar_relatorio_notas_excel(
        filtros_erro, cabecalhos_erro, linhas_erro, caminho_saida=caminho_notas_erro,
    )

    filtros_inseridas, cabecalhos_inseridas, linhas_inseridas = (
        _dados_relatorio_notas_inseridas_na_data(referencia=agora)
    )
    caminho_notas_inseridas = pasta_temp / f"relatorio_notas_inseridas_{sufixo}.xlsx"
    salvar_relatorio_notas_excel(
        filtros_inseridas,
        cabecalhos_inseridas,
        linhas_inseridas,
        caminho_saida=caminho_notas_inseridas,
    )

    filtros_itens, cabecalhos_itens, linhas_itens = _dados_relatorio_itens()
    caminho_itens = pasta_temp / f"relatorio_itens_email_{sufixo}.xlsx"
    salvar_relatorio_itens_excel(
        filtros_itens, cabecalhos_itens, linhas_itens, caminho_saida=caminho_itens,
    )

    return {
        "data_referencia": data_ref,
        "caminho_notas_erro": caminho_notas_erro,
        "total_notas_erro": len(linhas_erro),
        "caminho_notas_inseridas": caminho_notas_inseridas,
        "total_notas_inseridas": len(linhas_inseridas),
        "caminho_itens": caminho_itens,
        "total_itens": len(linhas_itens),
    }


def _criar_cliente_smtp(smtp_host, porta, usar_ssl):
    porta_int = int(porta or 0)
    if porta_int == 465:
        return smtplib.SMTP_SSL(smtp_host, porta_int, timeout=30)

    cliente = smtplib.SMTP(smtp_host, porta_int, timeout=30)
    cliente.ehlo()
    # Porta 587 usa STARTTLS (submissão autenticada padrão).
    if porta_int == 587 or usar_ssl:
        cliente.starttls()
        cliente.ehlo()
    return cliente


def _normalizar_smtp_host_porta(smtp_host, porta):
    host = str(smtp_host or "").strip()
    porta_saida = str(porta or "").strip()
    if not host:
        return "", porta_saida

    if "://" in host:
        parsed = urlparse(host)
        host = parsed.hostname or ""
        if not porta_saida and parsed.port:
            porta_saida = str(parsed.port)

    host = host.split("/")[0].strip()
    if ":" in host and host.count(":") == 1:
        host_parte, porta_embutida = host.rsplit(":", 1)
        if host_parte and porta_embutida.isdigit():
            host = host_parte.strip()
            if not porta_saida:
                porta_saida = porta_embutida

    return host, porta_saida


def _normalizar_destinatarios(destinatarios_texto, remetente):
    destinos = []
    for trecho in str(destinatarios_texto or "").split(","):
        email = trecho.strip()
        if email and email not in destinos:
            destinos.append(email)
    if destinos:
        return destinos
    return [str(remetente or "").strip()]


EMAIL_SUPORTE_LOG = "op.almeida2017@gmail.com"


def enviar_mensagem_smtp(assunto, corpo_texto, anexos=None, destinatarios=None):
    """Envia e-mail usando SMTP configurado em Configurações."""
    cfg = db.carregar_configuracoes() or {}
    smtp_host, porta_normalizada = _normalizar_smtp_host_porta(
        cfg.get("smtp"),
        cfg.get("porta") or "",
    )
    usuario = str(cfg.get("user_email") or "").strip()
    senha = str(cfg.get("senha_email") or "").strip()
    porta = porta_normalizada
    usar_ssl = bool(cfg.get("ssl"))
    destinos = destinatarios or [EMAIL_SUPORTE_LOG]
    if isinstance(destinos, str):
        destinos = [destinos]

    if not smtp_host or not usuario or not senha or not porta:
        raise RuntimeError(
            "Configuração de e-mail incompleta.\n"
            "Preencha SMTP, porta, e-mail e senha em Configurações → Disparo de E-mail."
        )

    mensagem = EmailMessage()
    mensagem["Subject"] = str(assunto or "").strip()
    mensagem["From"] = usuario
    mensagem["To"] = ", ".join(destinos)
    mensagem.set_content(str(corpo_texto or ""))

    for anexo in anexos or []:
        caminho = Path(anexo["path"])
        with open(caminho, "rb") as arquivo:
            mensagem.add_attachment(
                arquivo.read(),
                maintype=anexo.get("maintype", "application"),
                subtype=anexo.get("subtype", "octet-stream"),
                filename=anexo.get("filename") or caminho.name,
            )

    assunto_log = str(assunto or "").strip()
    destinos_log = ", ".join(destinos)
    try:
        with _criar_cliente_smtp(smtp_host, porta, usar_ssl) as cliente:
            cliente.login(usuario, senha)
            cliente.send_message(mensagem)
    except smtplib.SMTPAuthenticationError as exc:
        detalhe = ""
        try:
            detalhe = (exc.smtp_error or b"").decode("utf-8", errors="ignore")
        except Exception:
            detalhe = str(exc)

        if "gmail" in smtp_host.lower():
            erro_msg = (
                "Falha de autenticação no Gmail SMTP.\n"
                "Use senha de app do Google (16 caracteres), não a senha normal da conta.\n"
                "Configuração recomendada: porta 465 com SSL marcado OU porta 587 com SSL desmarcado.\n\n"
                f"Detalhe técnico: {detalhe or exc}"
            )
            db.registrar_log_email("SMTP", assunto_log, destinos_log, "ERRO", detalhe or erro_msg)
            raise RuntimeError(erro_msg) from exc
        erro_msg = f"Falha de autenticação SMTP: {detalhe or exc}"
        db.registrar_log_email("SMTP", assunto_log, destinos_log, "ERRO", erro_msg)
        raise RuntimeError(erro_msg) from exc
    except smtplib.SMTPNotSupportedError as exc:
        erro_msg = (
            "Servidor SMTP não suportou autenticação.\n"
            "Verifique o campo SMTP sem http/https (ex: smtp.gmail.com) "
            "e a combinação porta/SSL (465 com SSL marcado ou 587 com SSL desmarcado).\n\n"
            f"Detalhe técnico: {exc}"
        )
        db.registrar_log_email("SMTP", assunto_log, destinos_log, "ERRO", erro_msg)
        raise RuntimeError(erro_msg) from exc
    except smtplib.SMTPException as exc:
        erro_msg = f"Falha ao enviar e-mail via SMTP: {exc}"
        db.registrar_log_email("SMTP", assunto_log, destinos_log, "ERRO", erro_msg)
        raise RuntimeError(erro_msg) from exc

    db.registrar_log_email("SMTP", assunto_log, destinos_log, "OK", "")
    return {"destinatarios": destinos, "remetente": usuario}


def enviar_relatorios_agendados(configuracao, referencia=None, tipo_log="Agendado"):
    cfg = configuracao or {}
    smtp_host, porta_normalizada = _normalizar_smtp_host_porta(
        cfg.get("smtp"),
        cfg.get("porta") or "",
    )
    usuario = str(cfg.get("user_email") or "").strip()
    senha = str(cfg.get("senha_email") or "").strip()
    porta = porta_normalizada
    usar_ssl = bool(cfg.get("ssl"))
    destinatarios = _normalizar_destinatarios(cfg.get("destinatarios"), usuario)

    if not smtp_host or not usuario or not senha or not porta:
        raise RuntimeError("Configuração de e-mail incompleta para envio automático.")

    agora = referencia or _agora()
    anexos = gerar_anexos_relatorios(referencia=agora)
    proxima = calcular_proxima_execucao(
        cfg.get("agendamento_tipo"), cfg.get("intervalo_horas") or 1, referencia=agora,
    )

    mensagem = EmailMessage()
    mensagem["Subject"] = (
        f"Relatórios automáticos - {agora.strftime('%d/%m/%Y %H:%M')}"
    )
    mensagem["From"] = usuario
    mensagem["To"] = ", ".join(destinatarios)
    mensagem.set_content(
        "\n".join([
            "Envio automático concluído com sucesso.",
            "",
            f"Data de referência (inserção): {anexos['data_referencia']}",
            f"Notas com erro no anexo: {anexos['total_notas_erro']}",
            (
                "Notas inseridas na data no anexo: "
                f"{anexos['total_notas_inseridas']}"
            ),
            f"Itens no anexo: {anexos['total_itens']}",
            f"Destinatários: {', '.join(destinatarios)}",
            "",
            f"Próximo envio previsto: {proxima.strftime('%d/%m/%Y %H:%M') if proxima else 'desativado'}",
        ])
    )

    for caminho in (
        anexos["caminho_notas_erro"],
        anexos["caminho_notas_inseridas"],
        anexos["caminho_itens"],
    ):
        with open(caminho, "rb") as arquivo:
            mensagem.add_attachment(
                arquivo.read(),
                maintype="application",
                subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=caminho.name,
            )

    assunto_log = mensagem["Subject"]
    destinos_log = ", ".join(destinatarios)
    detalhe_ok = (
        f"Erro: {anexos['total_notas_erro']}, "
        f"Inseridas em {anexos['data_referencia']}: {anexos['total_notas_inseridas']}, "
        f"Itens: {anexos['total_itens']}"
    )
    try:
        with _criar_cliente_smtp(smtp_host, porta, usar_ssl) as cliente:
            cliente.login(usuario, senha)
            cliente.send_message(mensagem)
    except smtplib.SMTPAuthenticationError as exc:
        detalhe = ""
        try:
            detalhe = (exc.smtp_error or b"").decode("utf-8", errors="ignore")
        except Exception:
            detalhe = str(exc)

        if "gmail" in smtp_host.lower():
            erro_msg = (
                "Falha de autenticação no Gmail SMTP.\n"
                "Use senha de app do Google (16 caracteres), não a senha normal da conta.\n"
                "Configuração recomendada: porta 465 com SSL marcado OU porta 587 com SSL desmarcado.\n\n"
                f"Detalhe técnico: {detalhe or exc}"
            )
            db.registrar_log_email(tipo_log, assunto_log, destinos_log, "ERRO", detalhe or erro_msg)
            raise RuntimeError(erro_msg) from exc
        erro_msg = f"Falha de autenticação SMTP: {detalhe or exc}"
        db.registrar_log_email(tipo_log, assunto_log, destinos_log, "ERRO", erro_msg)
        raise RuntimeError(erro_msg) from exc
    except smtplib.SMTPNotSupportedError as exc:
        erro_msg = (
            "Servidor SMTP não suportou autenticação.\n"
            "Verifique o campo SMTP sem http/https (ex: smtp.gmail.com) "
            "e a combinação porta/SSL (465 com SSL marcado ou 587 com SSL desmarcado).\n\n"
            f"Detalhe técnico: {exc}"
        )
        db.registrar_log_email(tipo_log, assunto_log, destinos_log, "ERRO", erro_msg)
        raise RuntimeError(erro_msg) from exc
    except smtplib.SMTPException as exc:
        erro_msg = f"Falha ao enviar e-mail via SMTP: {exc}"
        db.registrar_log_email(tipo_log, assunto_log, destinos_log, "ERRO", erro_msg)
        raise RuntimeError(erro_msg) from exc

    db.registrar_log_email(tipo_log, assunto_log, destinos_log, "OK", detalhe_ok)
    return {
        "total_notas_erro": anexos["total_notas_erro"],
        "total_notas_inseridas": anexos["total_notas_inseridas"],
        "total_itens": anexos["total_itens"],
        "proxima_execucao": proxima,
    }
