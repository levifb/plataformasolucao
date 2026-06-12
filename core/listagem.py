from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Q

POR_PAGINA = 10


def filtrar_listagem(request, queryset, campos_busca):
    """Aplica às listagens o filtro de nível (?nivel=), a busca (?q=) e a paginação (?pagina=).

    Devolve o contexto com a página atual ('pagina'), os filtros ativos e a
    querystring pronta para preservá-los nos links de paginação.
    """
    nivel_filtro = request.GET.get('nivel')
    nivel_filtro = int(nivel_filtro) if nivel_filtro and nivel_filtro.isdigit() else None
    if nivel_filtro:
        queryset = queryset.filter(nivel__numero=nivel_filtro)

    busca = request.GET.get('q', '').strip()
    if busca:
        condicao = Q()
        for campo in campos_busca:
            condicao |= Q(**{f'{campo}__icontains': busca})
        queryset = queryset.filter(condicao)

    pagina = Paginator(queryset, POR_PAGINA).get_page(request.GET.get('pagina'))

    params = {}
    if nivel_filtro:
        params['nivel'] = nivel_filtro
    if busca:
        params['q'] = busca
    querystring = urlencode(params) + '&' if params else ''

    return {
        'pagina': pagina,
        'nivel_filtro': nivel_filtro,
        'busca': busca,
        'querystring': querystring,
    }
