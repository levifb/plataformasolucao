from django import forms
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.listagem import filtrar_listagem

from .models import Comentario, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['nivel', 'titulo', 'texto', 'imagem', 'arquivo', 'comentarios_habilitados']
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Título do post'}),
            'texto': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Escreva sua dúvida ou mensagem...'}),
        }

    def __init__(self, *args, aluno=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nivel'].queryset = aluno.niveis_visiveis()
        self.fields['nivel'].empty_label = 'Todos os níveis'
        self.fields['nivel'].required = False


@login_required
def lista_posts(request):
    niveis = request.user.niveis_visiveis()
    posts = Post.objects.filter(
        Q(nivel__in=niveis) | Q(nivel__isnull=True)
    ).select_related('autor', 'nivel')

    contexto = filtrar_listagem(request, posts, campos_busca=['titulo', 'texto'])
    contexto.update({'posts': contexto['pagina'], 'niveis': niveis})
    return render(request, 'comunidade/lista_posts.html', contexto)


@login_required
def novo_post(request):
    if not request.user.is_staff:
        return redirect('comunidade')
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, aluno=request.user)
        if form.is_valid():
            post = form.save(commit=False)
            post.autor = request.user
            post.save()
            return redirect('post_detalhe', pk=post.pk)
    else:
        form = PostForm(aluno=request.user)
    return render(request, 'comunidade/novo_post.html', {'form': form})


@login_required
def post_detalhe(request, pk):
    post = get_object_or_404(
        Post.objects.select_related('autor', 'nivel'),
        Q(nivel__in=request.user.niveis_visiveis()) | Q(nivel__isnull=True),
        pk=pk,
    )
    if request.method == 'POST' and post.comentarios_habilitados:
        texto = request.POST.get('texto', '').strip()
        if texto:
            Comentario.objects.create(post=post, autor=request.user, texto=texto)
            return redirect('post_detalhe', pk=post.pk)
    comentarios = post.comentarios.select_related('autor')
    return render(request, 'comunidade/post_detalhe.html', {
        'post': post,
        'comentarios': comentarios,
    })


@login_required
def editar_comentario(request, pk):
    comentario = get_object_or_404(
        Comentario.objects.select_related('post'), pk=pk, autor=request.user
    )
    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        if texto:
            comentario.texto = texto
            comentario.save()
            return redirect('post_detalhe', pk=comentario.post_id)
    return render(request, 'comunidade/editar_comentario.html', {'comentario': comentario})


@login_required
@require_POST
def excluir_comentario(request, pk):
    comentario = get_object_or_404(Comentario, pk=pk)
    if comentario.autor_id != request.user.pk and not request.user.is_staff:
        return HttpResponseForbidden('Você não pode excluir este comentário.')
    comentario.delete()
    return redirect('post_detalhe', pk=comentario.post_id)
