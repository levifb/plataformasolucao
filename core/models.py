from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Nivel(models.Model):
    numero = models.PositiveSmallIntegerField('número', unique=True)
    nome = models.CharField('nome', max_length=50)
    descricao = models.CharField('descrição', max_length=100, blank=True)

    class Meta:
        verbose_name = 'nível'
        verbose_name_plural = 'níveis'
        ordering = ['numero']

    def __str__(self):
        return f'{self.nome} ({self.descricao})' if self.descricao else self.nome


class AlunoManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('O email é obrigatório.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, **extra_fields)


class Aluno(AbstractUser):
    username = None
    email = models.EmailField('email', unique=True)
    first_name = models.CharField('nome', max_length=150)
    last_name = models.CharField('sobrenome', max_length=150, blank=True)
    niveis = models.ManyToManyField(
        Nivel, verbose_name='níveis', related_name='alunos', blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = AlunoManager()

    class Meta:
        verbose_name = 'aluno'
        verbose_name_plural = 'alunos'

    def __str__(self):
        return self.get_full_name() or self.email

    def niveis_visiveis(self):
        """Administradores (staff) enxergam todos os níveis; alunos, só os seus."""
        if self.is_staff:
            return Nivel.objects.all()
        return self.niveis.all()


class Aula(models.Model):
    titulo = models.CharField('título', max_length=200)
    data = models.DateField('data da aula')
    nivel = models.ForeignKey(
        Nivel, verbose_name='nível', on_delete=models.PROTECT, related_name='aulas'
    )
    material = models.FileField(
        'material (PDF)', upload_to='materiais/', blank=True, null=True
    )
    resolucao = models.FileField(
        'resolução (PDF)', upload_to='resolucoes/', blank=True, null=True
    )
    link_gravacao = models.URLField(
        'link da gravação (Google Drive)',
        blank=True,
        help_text='Cole o link do arquivo da gravação no Google Drive '
                  '(ex.: https://drive.google.com/file/d/ID/view).',
    )

    class Meta:
        verbose_name = 'aula'
        verbose_name_plural = 'aulas'
        ordering = ['-data']

    def __str__(self):
        return f'{self.titulo} — {self.nivel.nome}'

    @property
    def drive_id(self):
        """Extrai o ID do arquivo de links como drive.google.com/file/d/ID/view."""
        if not self.link_gravacao or '/file/d/' not in self.link_gravacao:
            return None
        return self.link_gravacao.split('/file/d/')[1].split('/')[0].split('?')[0]


class Material(models.Model):
    titulo = models.CharField('título', max_length=200)
    nivel = models.ForeignKey(
        Nivel, verbose_name='nível', on_delete=models.PROTECT, related_name='materiais'
    )
    descricao = models.TextField('descrição', blank=True)
    arquivo = models.FileField('arquivo (PDF)', upload_to='materiais_avulsos/')
    criado_em = models.DateTimeField('postado em', auto_now_add=True)

    class Meta:
        verbose_name = 'material'
        verbose_name_plural = 'materiais'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.titulo} — {self.nivel.nome}'


