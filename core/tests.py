import re
from datetime import date

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import Aluno, Aula, ComentarioAula, Material, Nivel


class PlataformaTests(TestCase):
    def setUp(self):
        self.n1 = Nivel.objects.get(numero=1)
        self.n2 = Nivel.objects.get(numero=2)
        self.aluno = Aluno.objects.create_user(
            email='aluno@teste.com', password='senha123', first_name='Ana'
        )
        self.aluno.niveis.add(self.n1)
        self.aula_n1 = Aula.objects.create(
            titulo='Contagem', data=date(2026, 6, 1), nivel=self.n1,
            link_gravacao='https://drive.google.com/file/d/abc123XYZ/view?pli=1',
        )
        self.aula_n2 = Aula.objects.create(
            titulo='Indução', data=date(2026, 6, 2), nivel=self.n2
        )

    def test_login_por_email(self):
        ok = self.client.login(username='aluno@teste.com', password='senha123')
        self.assertTrue(ok)

    def test_home_exige_login(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/entrar/', resp.url)

    def test_home_mostra_so_aulas_do_nivel(self):
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'Contagem')
        self.assertNotContains(resp, 'Indução')

    def test_aula_de_outro_nivel_da_404(self):
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('aula_detalhe', args=[self.aula_n2.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_drive_embed_na_pagina_da_aula(self):
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('aula_detalhe', args=[self.aula_n1.pk]))
        self.assertContains(resp, 'drive.google.com/file/d/abc123XYZ/preview')
        self.assertContains(resp, self.aula_n1.link_gravacao)

    def test_materiais_mostra_so_do_nivel(self):
        Material.objects.create(titulo='Lista N1', nivel=self.n1, arquivo='materiais_avulsos/a.pdf')
        Material.objects.create(titulo='Lista N2', nivel=self.n2, arquivo='materiais_avulsos/b.pdf')
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('materiais'))
        self.assertContains(resp, 'Lista N1')
        self.assertNotContains(resp, 'Lista N2')

    def test_admin_ve_aulas_de_todos_os_niveis(self):
        Aluno.objects.create_superuser('admin@teste.com', 'senha123', first_name='Admin')
        self.client.login(username='admin@teste.com', password='senha123')
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'Contagem')
        self.assertContains(resp, 'Indução')

    def test_busca_por_titulo(self):
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('home'), {'q': 'conta'})
        self.assertContains(resp, 'Contagem')
        resp = self.client.get(reverse('home'), {'q': 'inexistente'})
        self.assertNotContains(resp, 'Contagem')
        self.assertContains(resp, 'Nenhuma aula encontrada')

    def test_paginacao_de_aulas(self):
        # Com a aula do setUp, o aluno passa a ver 13 aulas: 10 na página 1 e 3 na 2.
        for i in range(12):
            Aula.objects.create(titulo=f'Aula extra {i}', data=date(2026, 7, 1), nivel=self.n1)
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('home'))
        self.assertEqual(len(resp.context['pagina'].object_list), 10)
        self.assertContains(resp, 'Página 1 de 2')
        resp = self.client.get(reverse('home'), {'pagina': 2})
        self.assertEqual(len(resp.context['pagina'].object_list), 3)

    def test_paginacao_preserva_filtros(self):
        for i in range(12):
            Aula.objects.create(titulo=f'Aula extra {i}', data=date(2026, 7, 1), nivel=self.n1)
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('home'), {'nivel': 1, 'q': 'extra'})
        self.assertContains(resp, 'nivel=1&amp;q=extra&amp;pagina=2')

    def test_recuperacao_de_senha(self):
        mail.outbox.clear()
        resp = self.client.post(reverse('password_reset'), {'email': 'aluno@teste.com'})
        self.assertRedirects(resp, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['aluno@teste.com'])

        link = re.search(r'http://testserver(/senha/redefinir/\S+)', mail.outbox[0].body)
        self.assertIsNotNone(link)
        # O GET no link redireciona para a URL com token de sessão, onde fica o formulário.
        resp = self.client.get(link.group(1), follow=True)
        self.assertContains(resp, 'Criar nova senha')

        url_form = resp.request['PATH_INFO']
        resp = self.client.post(url_form, {
            'new_password1': 'NovaSenha#2026',
            'new_password2': 'NovaSenha#2026',
        })
        self.assertRedirects(resp, reverse('password_reset_complete'))
        self.assertTrue(self.client.login(username='aluno@teste.com', password='NovaSenha#2026'))

    def test_email_desconhecido_nao_revela_cadastro(self):
        mail.outbox.clear()
        resp = self.client.post(reverse('password_reset'), {'email': 'naoexiste@teste.com'})
        self.assertRedirects(resp, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_nova_aula_avisa_alunos_do_nivel(self):
        mail.outbox.clear()
        aula = Aula.objects.create(titulo='Grafos', data=date(2026, 6, 15), nivel=self.n1)
        self.assertEqual(len(mail.outbox), 1)
        aviso = mail.outbox[0]
        self.assertEqual(aviso.subject, 'Nova aula: Grafos')
        self.assertEqual(aviso.bcc, ['aluno@teste.com'])
        self.assertIn(reverse('aula_detalhe', args=[aula.pk]), aviso.body)
        # Editar a aula não dispara novo aviso.
        aula.titulo = 'Grafos e árvores'
        aula.save()
        self.assertEqual(len(mail.outbox), 1)

    def test_nova_aula_sem_alunos_no_nivel_nao_envia_email(self):
        mail.outbox.clear()
        Aula.objects.create(titulo='Funções', data=date(2026, 6, 16), nivel=self.n2)
        self.assertEqual(len(mail.outbox), 0)

    def test_novo_material_avisa_alunos_do_nivel(self):
        mail.outbox.clear()
        Material.objects.create(titulo='Lista 5', nivel=self.n1, arquivo='materiais_avulsos/l5.pdf')
        self.assertEqual(len(mail.outbox), 1)
        aviso = mail.outbox[0]
        self.assertEqual(aviso.subject, 'Novo material: Lista 5')
        self.assertEqual(aviso.bcc, ['aluno@teste.com'])

    def test_material_resolvido_na_pagina_da_aula(self):
        self.aula_n1.material = 'materiais/lista-resolvida.pdf'
        self.aula_n1.save()
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('aula_detalhe', args=[self.aula_n1.pk]))
        self.assertContains(resp, 'Baixar material resolvido')

    def test_aula_sem_material_mostra_aviso(self):
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('aula_detalhe', args=[self.aula_n1.pk]))
        self.assertContains(resp, 'O material resolvido desta aula ainda não foi publicado.')

    def test_extracao_drive_id(self):
        aula = self.aula_n1
        self.assertEqual(aula.drive_id, 'abc123XYZ')
        aula.link_gravacao = 'https://drive.google.com/file/d/xyz789/view'
        self.assertEqual(aula.drive_id, 'xyz789')
        aula.link_gravacao = ''
        self.assertIsNone(aula.drive_id)
        aula.link_gravacao = 'https://drive.google.com/drive/folders/pasta'
        self.assertIsNone(aula.drive_id)


class ComentarioAulaTests(TestCase):
    def setUp(self):
        self.n1 = Nivel.objects.get(numero=1)
        self.aluno = Aluno.objects.create_user(
            email='aluno@teste.com', password='senha123', first_name='Ana'
        )
        self.aluno.niveis.add(self.n1)
        self.outro = Aluno.objects.create_user(
            email='outro@teste.com', password='senha123', first_name='Beto'
        )
        self.outro.niveis.add(self.n1)
        self.aula = Aula.objects.create(
            titulo='Contagem', data=date(2026, 6, 1), nivel=self.n1
        )
        self.client.login(username='aluno@teste.com', password='senha123')

    def test_comentar_na_aula(self):
        self.client.post(
            reverse('aula_detalhe', args=[self.aula.pk]), {'texto': 'Não entendi o exemplo 3.'}
        )
        comentario = ComentarioAula.objects.get(aula=self.aula)
        self.assertEqual(comentario.texto, 'Não entendi o exemplo 3.')
        self.assertEqual(comentario.autor, self.aluno)

    def test_comentario_aparece_na_pagina(self):
        ComentarioAula.objects.create(aula=self.aula, autor=self.aluno, texto='Ótima aula!')
        resp = self.client.get(reverse('aula_detalhe', args=[self.aula.pk]))
        self.assertContains(resp, 'Ótima aula!')
        self.assertContains(resp, 'Comentários (1)')

    def test_autor_edita_proprio_comentario(self):
        comentario = ComentarioAula.objects.create(
            aula=self.aula, autor=self.aluno, texto='Original'
        )
        resp = self.client.post(
            reverse('editar_comentario_aula', args=[comentario.pk]), {'texto': 'Corrigido'}
        )
        self.assertRedirects(resp, reverse('aula_detalhe', args=[self.aula.pk]))
        comentario.refresh_from_db()
        self.assertEqual(comentario.texto, 'Corrigido')

    def test_nao_edita_comentario_de_outro(self):
        comentario = ComentarioAula.objects.create(
            aula=self.aula, autor=self.outro, texto='De outra pessoa'
        )
        resp = self.client.post(
            reverse('editar_comentario_aula', args=[comentario.pk]), {'texto': 'Invadido'}
        )
        self.assertEqual(resp.status_code, 404)
        comentario.refresh_from_db()
        self.assertEqual(comentario.texto, 'De outra pessoa')

    def test_autor_exclui_proprio_comentario(self):
        comentario = ComentarioAula.objects.create(
            aula=self.aula, autor=self.aluno, texto='Apagável'
        )
        resp = self.client.post(reverse('excluir_comentario_aula', args=[comentario.pk]))
        self.assertRedirects(resp, reverse('aula_detalhe', args=[self.aula.pk]))
        self.assertFalse(ComentarioAula.objects.filter(pk=comentario.pk).exists())

    def test_nao_exclui_comentario_de_outro(self):
        comentario = ComentarioAula.objects.create(
            aula=self.aula, autor=self.outro, texto='De outra pessoa'
        )
        resp = self.client.post(reverse('excluir_comentario_aula', args=[comentario.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(ComentarioAula.objects.filter(pk=comentario.pk).exists())

    def test_staff_exclui_qualquer_comentario(self):
        comentario = ComentarioAula.objects.create(
            aula=self.aula, autor=self.aluno, texto='Comentário'
        )
        Aluno.objects.create_superuser('admin@teste.com', 'senha123', first_name='Admin')
        self.client.login(username='admin@teste.com', password='senha123')
        self.client.post(reverse('excluir_comentario_aula', args=[comentario.pk]))
        self.assertFalse(ComentarioAula.objects.filter(pk=comentario.pk).exists())

    def test_excluir_exige_post(self):
        comentario = ComentarioAula.objects.create(
            aula=self.aula, autor=self.aluno, texto='Comentário'
        )
        resp = self.client.get(reverse('excluir_comentario_aula', args=[comentario.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(ComentarioAula.objects.filter(pk=comentario.pk).exists())
