from django.test import TestCase
from django.urls import reverse

from core.models import Aluno, Nivel

from .models import Comentario, Post


class ComunidadeTests(TestCase):
    def setUp(self):
        self.n1 = Nivel.objects.get(numero=1)
        self.n2 = Nivel.objects.get(numero=2)
        self.aluno = Aluno.objects.create_user(
            email='aluno@teste.com', password='senha123', first_name='Ana'
        )
        self.aluno.niveis.add(self.n1)
        self.outro = Aluno.objects.create_user(
            email='outro@teste.com', password='senha123', first_name='Beto'
        )
        self.outro.niveis.add(self.n2)
        self.post_n2 = Post.objects.create(
            nivel=self.n2, autor=self.outro, titulo='Post nível 2', texto='Oi'
        )
        self.client.login(username='aluno@teste.com', password='senha123')

    def test_admin_pode_criar_post(self):
        admin = Aluno.objects.create_superuser('admin@teste.com', 'senha123', first_name='Admin')
        self.client.login(username='admin@teste.com', password='senha123')
        resp = self.client.post(reverse('novo_post'), {
            'nivel': self.n1.pk, 'titulo': 'Aviso da semana', 'texto': 'Aula confirmada!',
        })
        post = Post.objects.get(titulo='Aviso da semana')
        self.assertRedirects(resp, reverse('post_detalhe', args=[post.pk]))
        self.assertEqual(post.autor, admin)

    def test_aluno_nao_pode_criar_post(self):
        resp = self.client.post(reverse('novo_post'), {
            'nivel': self.n1.pk, 'titulo': 'Tentativa', 'texto': 'x',
        })
        self.assertRedirects(resp, reverse('comunidade'))
        self.assertFalse(Post.objects.filter(titulo='Tentativa').exists())

    def test_lista_so_mostra_posts_do_nivel(self):
        resp = self.client.get(reverse('comunidade'))
        self.assertNotContains(resp, 'Post nível 2')

    def test_post_de_outro_nivel_da_404(self):
        resp = self.client.get(reverse('post_detalhe', args=[self.post_n2.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_comentar(self):
        post = Post.objects.create(
            nivel=self.n1, autor=self.aluno, titulo='Meu post', texto='Texto'
        )
        self.client.post(reverse('post_detalhe', args=[post.pk]), {'texto': 'Boa pergunta!'})
        comentario = Comentario.objects.get(post=post)
        self.assertEqual(comentario.texto, 'Boa pergunta!')
        self.assertEqual(comentario.autor, self.aluno)

    def _criar_comentario(self, autor, texto='Comentário'):
        post = Post.objects.create(
            nivel=self.n1, autor=self.aluno, titulo='Post', texto='Texto'
        )
        return Comentario.objects.create(post=post, autor=autor, texto=texto)

    def test_autor_edita_proprio_comentario(self):
        comentario = self._criar_comentario(self.aluno, 'Original')
        resp = self.client.post(
            reverse('editar_comentario', args=[comentario.pk]), {'texto': 'Corrigido'}
        )
        self.assertRedirects(resp, reverse('post_detalhe', args=[comentario.post.pk]))
        comentario.refresh_from_db()
        self.assertEqual(comentario.texto, 'Corrigido')

    def test_nao_edita_comentario_de_outro(self):
        comentario = self._criar_comentario(self.outro, 'De outra pessoa')
        resp = self.client.post(
            reverse('editar_comentario', args=[comentario.pk]), {'texto': 'Invadido'}
        )
        self.assertEqual(resp.status_code, 404)
        comentario.refresh_from_db()
        self.assertEqual(comentario.texto, 'De outra pessoa')

    def test_autor_exclui_proprio_comentario(self):
        comentario = self._criar_comentario(self.aluno)
        resp = self.client.post(reverse('excluir_comentario', args=[comentario.pk]))
        self.assertRedirects(resp, reverse('post_detalhe', args=[comentario.post.pk]))
        self.assertFalse(Comentario.objects.filter(pk=comentario.pk).exists())

    def test_nao_exclui_comentario_de_outro(self):
        comentario = self._criar_comentario(self.outro)
        resp = self.client.post(reverse('excluir_comentario', args=[comentario.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Comentario.objects.filter(pk=comentario.pk).exists())

    def test_staff_exclui_qualquer_comentario(self):
        comentario = self._criar_comentario(self.aluno)
        Aluno.objects.create_superuser('admin@teste.com', 'senha123', first_name='Admin')
        self.client.login(username='admin@teste.com', password='senha123')
        self.client.post(reverse('excluir_comentario', args=[comentario.pk]))
        self.assertFalse(Comentario.objects.filter(pk=comentario.pk).exists())

    def test_excluir_exige_post(self):
        comentario = self._criar_comentario(self.aluno)
        resp = self.client.get(reverse('excluir_comentario', args=[comentario.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Comentario.objects.filter(pk=comentario.pk).exists())
