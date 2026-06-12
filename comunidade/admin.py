from django.contrib import admin

from .models import Comentario, Post


class ComentarioInline(admin.TabularInline):
    model = Comentario
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'nivel', 'criado_em')
    list_filter = ('nivel',)
    search_fields = ('titulo', 'texto', 'autor__email')
    inlines = [ComentarioInline]


@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('autor', 'post', 'criado_em')
    search_fields = ('texto', 'autor__email')
