from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Aula


@login_required
def home(request):
    niveis = request.user.niveis.all()
    aulas = Aula.objects.filter(nivel__in=niveis).select_related('nivel')

    nivel_filtro = request.GET.get('nivel')
    nivel_filtro = int(nivel_filtro) if nivel_filtro and nivel_filtro.isdigit() else None
    if nivel_filtro:
        aulas = aulas.filter(nivel__numero=nivel_filtro)

    return render(request, 'core/home.html', {
        'aulas': aulas,
        'niveis': niveis,
        'nivel_filtro': nivel_filtro,
    })


@login_required
def aula_detalhe(request, pk):
    aula = get_object_or_404(
        Aula.objects.select_related('nivel'),
        pk=pk,
        nivel__in=request.user.niveis.all(),
    )
    return render(request, 'core/aula_detalhe.html', {'aula': aula})
