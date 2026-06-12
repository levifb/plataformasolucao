from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .emails import notificar_alunos_do_nivel
from .models import Aula, Material


@receiver(post_save, sender=Aula)
def avisar_nova_aula(sender, instance, created, **kwargs):
    if not created:
        return
    link = settings.SITE_URL + reverse('aula_detalhe', args=[instance.pk])
    corpo = (
        'Olá!\n\n'
        f'Uma nova aula foi publicada no nível {instance.nivel.nome}:\n\n'
        f'{instance.titulo} — {instance.data.strftime("%d/%m/%Y")}\n\n'
        f'Acesse: {link}\n\n'
        'Curso Solução — Olimpíadas de Matemática'
    )
    notificar_alunos_do_nivel(instance.nivel, f'Nova aula: {instance.titulo}', corpo)


@receiver(post_save, sender=Material)
def avisar_novo_material(sender, instance, created, **kwargs):
    if not created:
        return
    link = settings.SITE_URL + reverse('materiais')
    corpo = (
        'Olá!\n\n'
        f'Um novo material foi publicado no nível {instance.nivel.nome}:\n\n'
        f'{instance.titulo}\n\n'
        f'Acesse: {link}\n\n'
        'Curso Solução — Olimpíadas de Matemática'
    )
    notificar_alunos_do_nivel(instance.nivel, f'Novo material: {instance.titulo}', corpo)
