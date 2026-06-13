from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Aluno, Aula, AulaCancelada, AulaExtra, ComentarioAula, HorarioAula,
    Material, Nivel, Professor, Recesso,
)

admin.site.site_header = 'Curso Solução — Administração'
admin.site.site_title = 'Curso Solução'
admin.site.index_title = 'Gerenciamento da plataforma'


@admin.register(Aluno)
class AlunoAdmin(UserAdmin):
    """Alunos: contas comuns, sem acesso ao gerenciamento."""

    list_display = ('email', 'first_name', 'last_name', 'lista_niveis', 'is_active')
    list_filter = ('niveis', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('first_name', 'email')
    filter_horizontal = ('niveis',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados do aluno', {'fields': ('first_name', 'last_name', 'niveis')}),
        ('Acesso', {'fields': ('is_active',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'niveis', 'password1', 'password2'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_staff=False)

    @admin.display(description='níveis')
    def lista_niveis(self, obj):
        return ', '.join(n.nome for n in obj.niveis.all()) or '—'


@admin.register(Professor)
class ProfessorAdmin(UserAdmin):
    """Professores: gerenciam aulas, materiais e calendário via grupo
    Professores. Só superusuários acessam esta tela — para cadastrar
    professores ou promover um professor a superusuário."""

    list_display = ('email', 'first_name', 'last_name', 'is_active', 'is_superuser')
    list_filter = ('is_active',)
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('first_name', 'email')
    filter_horizontal = ()

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados do professor', {'fields': ('first_name', 'last_name')}),
        ('Acesso', {
            'fields': ('is_active', 'is_superuser'),
            'description': 'Superusuários podem tudo, inclusive cadastrar '
                           'professores e promover outros superusuários.',
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_staff=True)


class ComentarioAulaInline(admin.TabularInline):
    model = ComentarioAula
    extra = 0


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'nivel', 'data', 'tem_material', 'tem_gravacao')
    list_filter = ('nivel',)
    search_fields = ('titulo',)
    date_hierarchy = 'data'
    inlines = [ComentarioAulaInline]

    @admin.display(description='material resolvido', boolean=True)
    def tem_material(self, obj):
        return bool(obj.material)

    @admin.display(description='gravação', boolean=True)
    def tem_gravacao(self, obj):
        return bool(obj.link_gravacao)


@admin.register(ComentarioAula)
class ComentarioAulaAdmin(admin.ModelAdmin):
    list_display = ('autor', 'aula', 'criado_em')
    search_fields = ('texto', 'autor__email')


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'nivel', 'criado_em')
    list_filter = ('nivel',)
    search_fields = ('titulo', 'descricao')


@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao')


@admin.register(HorarioAula)
class HorarioAulaAdmin(admin.ModelAdmin):
    list_display = ('nivel', 'dia_semana', 'hora_inicio', 'hora_fim', 'rotulo', 'tem_link')
    list_filter = ('nivel', 'dia_semana')

    @admin.display(description='link do Meet', boolean=True)
    def tem_link(self, obj):
        return bool(obj.link_meet)


@admin.register(AulaExtra)
class AulaExtraAdmin(admin.ModelAdmin):
    list_display = ('nivel', 'data', 'hora_inicio', 'hora_fim', 'rotulo')
    list_filter = ('nivel',)
    date_hierarchy = 'data'


@admin.register(AulaCancelada)
class AulaCanceladaAdmin(admin.ModelAdmin):
    list_display = ('horario', 'data', 'motivo')
    list_filter = ('horario__nivel',)
    date_hierarchy = 'data'


@admin.register(Recesso)
class RecessoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'inicio', 'fim')
