from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .emails import enviar_email
from .models import Aluno


@receiver(post_save, sender=Aluno)
def boas_vindas_ao_aluno(sender, instance, created, **kwargs):
    """Dá as boas-vindas ao aluno recém-cadastrado, com um link para ele
    criar a própria senha (ou trocar a que recebeu)."""
    if not created or instance.is_staff or not instance.email:
        return

    uid = urlsafe_base64_encode(force_bytes(instance.pk))
    token = default_token_generator.make_token(instance)
    link_senha = settings.SITE_URL + reverse(
        'password_reset_confirm', kwargs={'uidb64': uid, 'token': token}
    )
    link_esqueci = settings.SITE_URL + reverse('password_reset')
    dias_validade = settings.PASSWORD_RESET_TIMEOUT // 86400

    corpo = (
        f'Olá, {instance.first_name or instance.email}!\n\n'
        'Sua conta na plataforma do Curso Solução foi criada com este email.\n\n'
        'Para criar a sua senha (ou trocar a que você recebeu), acesse:\n'
        f'{link_senha}\n'
        f'(o link vale por {dias_validade} dias)\n\n'
        'Se o link expirar, é só pedir um novo em "Esqueci minha senha":\n'
        f'{link_esqueci}\n\n'
        f'Depois é só entrar na plataforma: {settings.SITE_URL}\n\n'
        'Bons estudos!\n'
        'Curso Solução — Olimpíadas de Matemática'
    )
    enviar_email(instance.email, 'Bem-vindo(a) ao Curso Solução!', corpo)
