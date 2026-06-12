from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .listagem import filtrar_listagem
from .models import Aula, ComentarioAula, Material


@login_required
def home(request):
    niveis = request.user.niveis_visiveis()
    aulas = Aula.objects.filter(nivel__in=niveis).select_related('nivel')

    contexto = filtrar_listagem(request, aulas, campos_busca=['titulo'])
    contexto.update({'aulas': contexto['pagina'], 'niveis': niveis})
    return render(request, 'core/home.html', contexto)


@login_required
def materiais(request):
    niveis = request.user.niveis_visiveis()
    lista = Material.objects.filter(nivel__in=niveis).select_related('nivel')

    contexto = filtrar_listagem(request, lista, campos_busca=['titulo', 'descricao'])
    contexto.update({'materiais': contexto['pagina'], 'niveis': niveis})
    return render(request, 'core/materiais.html', contexto)


@login_required
def aula_detalhe(request, pk):
    aula = get_object_or_404(
        Aula.objects.select_related('nivel'),
        pk=pk,
        nivel__in=request.user.niveis_visiveis(),
    )
    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        if texto:
            ComentarioAula.objects.create(aula=aula, autor=request.user, texto=texto)
            return redirect('aula_detalhe', pk=aula.pk)
    comentarios = aula.comentarios.select_related('autor')
    return render(request, 'core/aula_detalhe.html', {
        'aula': aula,
        'comentarios': comentarios,
    })


@login_required
def editar_comentario_aula(request, pk):
    comentario = get_object_or_404(
        ComentarioAula.objects.select_related('aula'), pk=pk, autor=request.user
    )
    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        if texto:
            comentario.texto = texto
            comentario.save()
            return redirect('aula_detalhe', pk=comentario.aula_id)
    return render(request, 'core/editar_comentario_aula.html', {'comentario': comentario})


@login_required
@require_POST
def excluir_comentario_aula(request, pk):
    comentario = get_object_or_404(ComentarioAula, pk=pk)
    if comentario.autor_id != request.user.pk and not request.user.is_staff:
        return HttpResponseForbidden('Você não pode excluir este comentário.')
    comentario.delete()
    return redirect('aula_detalhe', pk=comentario.aula_id)
