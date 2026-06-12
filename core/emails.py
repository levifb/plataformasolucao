import logging

from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def enviar_email(destinatario, assunto, corpo):
    """Envia um email a um destinatário.

    Uma falha no envio (ex.: servidor de email fora do ar) é registrada no log,
    mas não interrompe a operação que disparou o envio.
    """
    email = EmailMessage(subject=assunto, body=corpo, to=[destinatario])
    try:
        email.send()
    except Exception:
        logger.exception('Falha ao enviar email "%s" para %s', assunto, destinatario)
