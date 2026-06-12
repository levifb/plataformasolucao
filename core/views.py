import calendar
from datetime import date

from django import forms
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .listagem import filtrar_listagem
from .models import (
    Aula, AulaCancelada, AulaExtra, ComentarioAula, HorarioAula, Material, Recesso,
)

MESES = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
]


def montar_mes(ano, mes, horarios, extras, cancelamentos, recessos, hoje):
    """Monta as semanas de um mês para o calendário, marcando as próximas
    aulas (de hoje em diante). Dias de recesso ficam sem as aulas da grade
    semanal; aulas avulsas aparecem normalmente; ocorrências canceladas da
    grade aparecem riscadas."""
    semanas = []
    for semana in calendar.Calendar(firstweekday=6).monthdatescalendar(ano, mes):
        dias = []
        for dia in semana:
            em_recesso = any(r.inicio <= dia <= r.fim for r in recessos)
            aulas, canceladas = [], []
            if dia.month == mes and dia >= hoje:
                if not em_recesso:
                    for h in horarios:
                        if h.dia_semana != dia.weekday():
                            continue
                        cancelamento = next(
                            (c for c in cancelamentos
                             if c.horario_id == h.pk and c.data == dia),
                            None,
                        )
                        if cancelamento:
                            canceladas.append(cancelamento)
                        else:
                            aulas.append(h)
                aulas.extend(e for e in extras if e.data == dia)
                aulas.sort(key=lambda a: a.hora_inicio)
            dias.append({
                'data': dia,
                'aulas': aulas,
                'canceladas': canceladas,
                'outro_mes': dia.month != mes,
                'hoje': dia == hoje,
                'passado': dia < hoje,
            })
        semanas.append(dias)
    ultimo_dia = date(ano, mes, calendar.monthrange(ano, mes)[1])
    recessos_do_mes = [
        r for r in recessos if r.inicio <= ultimo_dia and r.fim >= date(ano, mes, 1)
    ]
    return {
        'nome': f'{MESES[mes - 1]} de {ano}',
        'semanas': semanas,
        'recessos': recessos_do_mes,
    }


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


class AulaExtraForm(forms.ModelForm):
    class Meta:
        model = AulaExtra
        fields = ['nivel', 'data', 'hora_inicio', 'hora_fim', 'link_meet']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nivel'].empty_label = None
        self.fields['link_meet'].required = False

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get('hora_inicio'), dados.get('hora_fim')
        if inicio and fim and fim <= inicio:
            self.add_error('hora_fim', 'O horário de fim deve ser depois do horário de início.')
        return dados


@login_required
def nova_aula_calendario(request):
    if not request.user.is_staff:
        return redirect('calendario')
    if request.method == 'POST':
        form = AulaExtraForm(request.POST)
        if form.is_valid():
            aula = form.save(commit=False)
            if not aula.link_meet:
                horario = aula.nivel.horarios.exclude(link_meet='').first()
                if horario:
                    aula.link_meet = horario.link_meet
            aula.save()
            return redirect('calendario')
    else:
        form = AulaExtraForm()
    return render(request, 'core/nova_aula_calendario.html', {'form': form})


class CancelarAulaForm(forms.ModelForm):
    class Meta:
        model = AulaCancelada
        fields = ['horario', 'data', 'motivo']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'motivo': forms.TextInput(attrs={'placeholder': 'Ex.: feriado, professor doente...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['horario'].empty_label = None
        self.fields['motivo'].required = False

    def clean(self):
        dados = super().clean()
        horario, dia = dados.get('horario'), dados.get('data')
        if horario and dia and dia.weekday() != horario.dia_semana:
            self.add_error(
                'data',
                f'A data não corresponde ao dia dessa aula ({horario.get_dia_semana_display()}).',
            )
        return dados


@login_required
def cancelar_aula_calendario(request):
    if not request.user.is_staff:
        return redirect('calendario')
    if request.method == 'POST':
        form = CancelarAulaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('calendario')
    else:
        form = CancelarAulaForm()
    return render(request, 'core/cancelar_aula.html', {'form': form})


@login_required
@require_POST
def desfazer_cancelamento(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden('Apenas professores podem desfazer um cancelamento.')
    cancelamento = get_object_or_404(AulaCancelada, pk=pk)
    cancelamento.delete()
    return redirect('calendario')


@login_required
def calendario(request):
    hoje = date.today()
    niveis = request.user.niveis_visiveis()

    # Links de todos os níveis, agrupados; calendário só com os níveis do aluno.
    todos_horarios = list(HorarioAula.objects.select_related('nivel'))
    meus_horarios = [h for h in todos_horarios if h.nivel in niveis]
    extras = list(AulaExtra.objects.filter(nivel__in=niveis).select_related('nivel'))
    cancelamentos = list(
        AulaCancelada.objects.filter(horario__nivel__in=niveis)
        .select_related('horario', 'horario__nivel')
    )
    recessos = list(Recesso.objects.all())

    meses = []
    ano, mes = hoje.year, hoje.month
    for _ in range(2):
        meses.append(
            montar_mes(ano, mes, meus_horarios, extras, cancelamentos, recessos, hoje)
        )
        ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)

    return render(request, 'core/calendario.html', {
        'horarios': todos_horarios,
        'meses': meses,
        'proximos_cancelamentos': [c for c in cancelamentos if c.data >= hoje],
    })


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
