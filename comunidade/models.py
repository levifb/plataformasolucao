from django.conf import settings
from django.db import models

from core.models import Nivel


class Post(models.Model):
    nivel = models.ForeignKey(
        Nivel, verbose_name='nível', on_delete=models.PROTECT, related_name='posts'
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='autor',
        on_delete=models.CASCADE,
        related_name='posts',
    )
    titulo = models.CharField('título', max_length=200)
    texto = models.TextField('texto')
    criado_em = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'post'
        verbose_name_plural = 'posts'
        ordering = ['-criado_em']

    def __str__(self):
        return self.titulo


class Comentario(models.Model):
    post = models.ForeignKey(
        Post, verbose_name='post', on_delete=models.CASCADE, related_name='comentarios'
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='autor',
        on_delete=models.CASCADE,
        related_name='comentarios',
    )
    texto = models.TextField('texto')
    criado_em = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'comentário'
        verbose_name_plural = 'comentários'
        ordering = ['criado_em']

    def __str__(self):
        return f'Comentário de {self.autor} em "{self.post}"'
