import logging

from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def notificar_alunos_do_nivel(nivel, assunto, corpo):
    """Envia um email aos alunos ativos do nível, em cópia oculta.

    Uma falha no envio (ex.: servidor de email fora do ar) é registrada no log,
    mas não impede o salvamento da aula ou do material.
    """
    destinatarios = list(
        nivel.alunos.filter(is_active=True).values_list('email', flat=True)
    )
    if not destinatarios:
        return
    email = EmailMessage(subject=assunto, body=corpo, bcc=destinatarios)
    try:
        email.send()
    except Exception:
        logger.exception('Falha ao enviar aviso aos alunos do nível %s', nivel)
