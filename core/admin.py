from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Aluno, Aula, Material, Nivel

admin.site.site_header = 'Curso Solução — Administração'
admin.site.site_title = 'Curso Solução'
admin.site.index_title = 'Gerenciamento da plataforma'


@admin.register(Aluno)
class AlunoAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'lista_niveis', 'is_active')
    list_filter = ('niveis', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('first_name', 'email')
    filter_horizontal = ('niveis', 'groups', 'user_permissions')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados do aluno', {'fields': ('first_name', 'last_name', 'niveis')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'niveis', 'password1', 'password2'),
        }),
    )

    @admin.display(description='níveis')
    def lista_niveis(self, obj):
        return ', '.join(n.nome for n in obj.niveis.all()) or '—'


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'nivel', 'data', 'tem_material', 'tem_resolucao', 'tem_gravacao')
    list_filter = ('nivel',)
    search_fields = ('titulo',)
    date_hierarchy = 'data'

    @admin.display(description='material', boolean=True)
    def tem_material(self, obj):
        return bool(obj.material)

    @admin.display(description='resolução', boolean=True)
    def tem_resolucao(self, obj):
        return bool(obj.resolucao)

    @admin.display(description='gravação', boolean=True)
    def tem_gravacao(self, obj):
        return bool(obj.link_gravacao)


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'nivel', 'criado_em')
    list_filter = ('nivel',)
    search_fields = ('titulo', 'descricao')


@admin.register(Nivel)
class NivelAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao')
