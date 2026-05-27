from calendar import monthrange
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
import smtplib
import tempfile

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


def _dados_relatorio_notas():
    filtros = {
        "Data Emissão Inicial": "Todos",
        "Data Emissão Final": "Todos",
        "Cód. Interno": "Todos",
        "Nº Nota": "Todos",
        "Status": "ERRO",
    }
    cabecalhos = [
        "Inserção",
        "Cód. Interno",
        "Status",
        "Fornecedor",
        "No.Nota",
        "Data Em.",
        "Valor",
        "Sit. NFe",
        "Chave NFe",
        "Filial",
        "Usuário Inserção",
        "Erro Importação",
        "Observação NFe",
        "NFe p/ Estoque",
        "Arquiva",
    ]

    linhas = []
    for nota in db.listar_notas_filtradas(status="Erro"):
        estoque = "   [ ☑ ]   " if "☑" in str(nota.get("nfe_estoque") or "") else "   [ ☐ ]   "
        arquiva = "   [ ☑ ]   " if "☑" in str(nota.get("nfe_arquiva") or "") else "   [ ☐ ]   "
        linhas.append([
            str(nota.get("data_insercao") or ""),
            str(nota.get("codigo_interno") or ""),
            str(nota.get("status") or ""),
            str(nota.get("fornecedor") or ""),
            str(nota.get("num_nota") or ""),
            str(nota.get("data_em") or ""),
            str(nota.get("valor") or ""),
            str(nota.get("sit_nfe") or ""),
            str(nota.get("chave_nfe") or ""),
            str(nota.get("filial") or ""),
            str(nota.get("user_ins") or ""),
            str(nota.get("erro_importacao") or ""),
            str(nota.get("observacao_nfe") or ""),
            estoque,
            arquiva,
        ])
    return filtros, cabecalhos, linhas


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


def gerar_anexos_relatorios():
    pasta_temp = Path(tempfile.gettempdir())
    sufixo = _agora().strftime("%Y%m%d_%H%M%S")

    filtros_notas, cabecalhos_notas, linhas_notas = _dados_relatorio_notas()
    caminho_notas = pasta_temp / f"relatorio_notas_email_{sufixo}.xlsx"
    salvar_relatorio_notas_excel(
        filtros_notas, cabecalhos_notas, linhas_notas, caminho_saida=caminho_notas,
    )

    filtros_itens, cabecalhos_itens, linhas_itens = _dados_relatorio_itens()
    caminho_itens = pasta_temp / f"relatorio_itens_email_{sufixo}.xlsx"
    salvar_relatorio_itens_excel(
        filtros_itens, cabecalhos_itens, linhas_itens, caminho_saida=caminho_itens,
    )

    return {
        "caminho_notas": caminho_notas,
        "total_notas": len(linhas_notas),
        "caminho_itens": caminho_itens,
        "total_itens": len(linhas_itens),
    }


def _criar_cliente_smtp(smtp_host, porta, usar_ssl):
    porta_int = int(porta or 0)
    if usar_ssl and porta_int == 465:
        return smtplib.SMTP_SSL(smtp_host, porta_int, timeout=30)

    cliente = smtplib.SMTP(smtp_host, porta_int, timeout=30)
    cliente.ehlo()
    if usar_ssl:
        cliente.starttls()
        cliente.ehlo()
    return cliente


def _normalizar_destinatarios(destinatarios_texto, remetente):
    destinos = []
    for trecho in str(destinatarios_texto or "").split(","):
        email = trecho.strip()
        if email and email not in destinos:
            destinos.append(email)
    if destinos:
        return destinos
    return [str(remetente or "").strip()]


def enviar_relatorios_agendados(configuracao, referencia=None):
    cfg = configuracao or {}
    smtp_host = str(cfg.get("smtp") or "").strip()
    usuario = str(cfg.get("user_email") or "").strip()
    senha = str(cfg.get("senha_email") or "").strip()
    porta = cfg.get("porta") or ""
    usar_ssl = bool(cfg.get("ssl"))
    destinatarios = _normalizar_destinatarios(cfg.get("destinatarios"), usuario)

    if not smtp_host or not usuario or not senha or not porta:
        raise RuntimeError("Configuração de e-mail incompleta para envio automático.")

    anexos = gerar_anexos_relatorios()
    agora = referencia or _agora()
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
            f"Notas no anexo: {anexos['total_notas']}",
            f"Itens no anexo: {anexos['total_itens']}",
            f"Destinatários: {', '.join(destinatarios)}",
            "",
            f"Próximo envio previsto: {proxima.strftime('%d/%m/%Y %H:%M') if proxima else 'desativado'}",
        ])
    )

    for caminho in (anexos["caminho_notas"], anexos["caminho_itens"]):
        with open(caminho, "rb") as arquivo:
            mensagem.add_attachment(
                arquivo.read(),
                maintype="application",
                subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=caminho.name,
            )

    with _criar_cliente_smtp(smtp_host, porta, usar_ssl) as cliente:
        cliente.login(usuario, senha)
        cliente.send_message(mensagem)

    return {
        "total_notas": anexos["total_notas"],
        "total_itens": anexos["total_itens"],
        "proxima_execucao": proxima,
    }
