from django.conf import settings
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


class ProfessorManager(AlunoManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_staff=True)


class Professor(Aluno):
    """Conta de administrador. Professores enxergam todos os níveis,
    publicam aulas e materiais e podem cadastrar outros professores."""

    objects = ProfessorManager()

    class Meta:
        proxy = True
        verbose_name = 'professor'
        verbose_name_plural = 'professores'

    def save(self, *args, **kwargs):
        self.is_staff = True
        self.is_superuser = True
        super().save(*args, **kwargs)


class HorarioAula(models.Model):
    """Horário semanal fixo de aula de um nível, com o link do Meet."""

    DIAS_SEMANA = [
        (0, 'segunda-feira'),
        (1, 'terça-feira'),
        (2, 'quarta-feira'),
        (3, 'quinta-feira'),
        (4, 'sexta-feira'),
        (5, 'sábado'),
        (6, 'domingo'),
    ]

    nivel = models.ForeignKey(
        Nivel, verbose_name='nível', on_delete=models.CASCADE, related_name='horarios'
    )
    dia_semana = models.PositiveSmallIntegerField('dia da semana', choices=DIAS_SEMANA)
    hora_inicio = models.TimeField('início')
    hora_fim = models.TimeField('fim')
    rotulo = models.CharField(
        'rótulo', max_length=100, blank=True,
        help_text='Ex.: Nível 1 avançado. Aparece no calendário e na lista de links.',
    )
    link_meet = models.URLField('link do Meet', blank=True)

    class Meta:
        verbose_name = 'horário de aula'
        verbose_name_plural = 'horários de aula'
        ordering = ['nivel__numero', 'dia_semana', 'hora_inicio']

    def __str__(self):
        return f'{self.nivel.nome} — {self.get_dia_semana_display()} {self.hora_inicio:%H:%M}'


class AulaCancelada(models.Model):
    """Cancela uma ocorrência específica da grade semanal (ex.: só o sábado 20/06).
    A aula aparece riscada no calendário dos alunos do nível."""

    horario = models.ForeignKey(
        HorarioAula, verbose_name='horário', on_delete=models.CASCADE,
        related_name='cancelamentos',
    )
    data = models.DateField('data')
    motivo = models.CharField(
        'motivo', max_length=200, blank=True,
        help_text='Opcional. Aparece para os alunos ao passar o mouse sobre a aula cancelada.',
    )

    class Meta:
        verbose_name = 'aula cancelada'
        verbose_name_plural = 'aulas canceladas'
        ordering = ['data']
        constraints = [
            models.UniqueConstraint(fields=['horario', 'data'], name='cancelamento_unico'),
        ]

    def __str__(self):
        return f'{self.horario} cancelada em {self.data:%d/%m/%Y}'


class AulaExtra(models.Model):
    """Aula em data específica, fora da grade semanal (ex.: intensivo de férias).
    Aparece no calendário mesmo durante um recesso."""

    nivel = models.ForeignKey(
        Nivel, verbose_name='nível', on_delete=models.CASCADE, related_name='aulas_extras'
    )
    data = models.DateField('data')
    hora_inicio = models.TimeField('início')
    hora_fim = models.TimeField('fim')
    rotulo = models.CharField('rótulo', max_length=100, blank=True)
    link_meet = models.URLField('link do Meet', blank=True)

    class Meta:
        verbose_name = 'aula avulsa'
        verbose_name_plural = 'aulas avulsas'
        ordering = ['data', 'hora_inicio']

    def __str__(self):
        return f'{self.nivel.nome} — {self.data:%d/%m/%Y} {self.hora_inicio:%H:%M}'


class Recesso(models.Model):
    """Período sem aulas (férias, feriados). O calendário fica vazio nesses dias."""

    descricao = models.CharField('descrição', max_length=100)
    inicio = models.DateField('início')
    fim = models.DateField('fim')

    class Meta:
        verbose_name = 'recesso'
        verbose_name_plural = 'recessos'
        ordering = ['inicio']

    def __str__(self):
        return f'{self.descricao} ({self.inicio:%d/%m/%Y} a {self.fim:%d/%m/%Y})'


class Aula(models.Model):
    titulo = models.CharField('título', max_length=200)
    data = models.DateField('data da aula')
    nivel = models.ForeignKey(
        Nivel, verbose_name='nível', on_delete=models.PROTECT, related_name='aulas'
    )
    material = models.FileField(
        'material resolvido (PDF)',
        upload_to='materiais/',
        blank=True,
        null=True,
        help_text='Versão resolvida do material, publicada após a aula. '
                  'O material puro fica na aba Materiais.',
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


class ComentarioAula(models.Model):
    aula = models.ForeignKey(
        Aula, verbose_name='aula', on_delete=models.CASCADE, related_name='comentarios'
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='autor',
        on_delete=models.CASCADE,
        related_name='comentarios_aula',
    )
    texto = models.TextField('texto')
    criado_em = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'comentário de aula'
        verbose_name_plural = 'comentários de aula'
        ordering = ['criado_em']

    def __str__(self):
        return f'Comentário de {self.autor} em "{self.aula}"'


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


