from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .listagem import filtrar_listagem
from .models import Aula, Material


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
    return render(request, 'core/aula_detalhe.html', {'aula': aula})
