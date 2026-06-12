from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import Aluno, Aula, Material, Nivel


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
            link_gravacao='https://www.youtube.com/watch?v=abc123XYZ',
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

    def test_youtube_embed_na_pagina_da_aula(self):
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('aula_detalhe', args=[self.aula_n1.pk]))
        self.assertContains(resp, 'youtube.com/embed/abc123XYZ')

    def test_materiais_mostra_so_do_nivel(self):
        Material.objects.create(titulo='Lista N1', nivel=self.n1, arquivo='materiais_avulsos/a.pdf')
        Material.objects.create(titulo='Lista N2', nivel=self.n2, arquivo='materiais_avulsos/b.pdf')
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('materiais'))
        self.assertContains(resp, 'Lista N1')
        self.assertNotContains(resp, 'Lista N2')

    def test_extracao_youtube_id(self):
        aula = self.aula_n1
        aula.link_gravacao = 'https://youtu.be/xyz789'
        self.assertEqual(aula.youtube_id, 'xyz789')
        aula.link_gravacao = 'https://www.youtube.com/live/live123?feature=share'
        self.assertEqual(aula.youtube_id, 'live123')
        aula.link_gravacao = ''
        self.assertIsNone(aula.youtube_id)
