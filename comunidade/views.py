from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Comentario, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['nivel', 'titulo', 'texto']
        widgets = {
            'titulo': forms.TextInput(attrs={'placeholder': 'Título do post'}),
            'texto': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Escreva sua dúvida ou mensagem...'}),
        }

    def __init__(self, *args, aluno=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nivel'].queryset = aluno.niveis_visiveis()
        self.fields['nivel'].empty_label = None


@login_required
def lista_posts(request):
    niveis = request.user.niveis_visiveis()
    posts = Post.objects.filter(nivel__in=niveis).select_related('autor', 'nivel')

    nivel_filtro = request.GET.get('nivel')
    nivel_filtro = int(nivel_filtro) if nivel_filtro and nivel_filtro.isdigit() else None
    if nivel_filtro:
        posts = posts.filter(nivel__numero=nivel_filtro)

    return render(request, 'comunidade/lista_posts.html', {
        'posts': posts,
        'niveis': niveis,
        'nivel_filtro': nivel_filtro,
    })


@login_required
def novo_post(request):
    if not request.user.is_staff:
        return redirect('comunidade')
    if request.method == 'POST':
        form = PostForm(request.POST, aluno=request.user)
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
        pk=pk,
        nivel__in=request.user.niveis_visiveis(),
    )
    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        if texto:
            Comentario.objects.create(post=post, autor=request.user, texto=texto)
            return redirect('post_detalhe', pk=post.pk)
    comentarios = post.comentarios.select_related('autor')
    return render(request, 'comunidade/post_detalhe.html', {
        'post': post,
        'comentarios': comentarios,
    })
