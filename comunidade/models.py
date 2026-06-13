from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from core.models import Nivel, validar_pdf

# Mesma lógica do validar_pdf: só formatos de imagem, para impedir que um
# arquivo executável seja servido a partir do domínio do site.
validar_imagem = FileExtensionValidator(
    allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp']
)


class Post(models.Model):
    """Post da comunidade. Sem nível definido (nivel nulo), o post é para
    todos os níveis e aparece para qualquer aluno."""

    nivel = models.ForeignKey(
        Nivel,
        verbose_name='nível',
        on_delete=models.PROTECT,
        related_name='posts',
        null=True,
        blank=True,
        help_text='Em branco, o post aparece para alunos de todos os níveis.',
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='autor',
        on_delete=models.CASCADE,
        related_name='posts',
    )
    titulo = models.CharField('título', max_length=200)
    texto = models.TextField('texto')
    imagem = models.FileField(
        'imagem',
        upload_to='comunidade/imagens/',
        blank=True,
        null=True,
        validators=[validar_imagem],
        help_text='Opcional. JPG, PNG, GIF ou WebP.',
    )
    arquivo = models.FileField(
        'anexo (PDF)',
        upload_to='comunidade/anexos/',
        blank=True,
        null=True,
        validators=[validar_pdf],
        help_text='Opcional.',
    )
    comentarios_habilitados = models.BooleanField(
        'comentários habilitados',
        default=True,
        help_text='Desmarque para publicar um aviso sem espaço para comentários.',
    )
    criado_em = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'post'
        verbose_name_plural = 'posts'
        ordering = ['-criado_em']

    def __str__(self):
        return self.titulo

    def nome_do_nivel(self):
        return self.nivel.nome if self.nivel else 'Todos os níveis'


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
