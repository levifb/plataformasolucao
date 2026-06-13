import re
from datetime import date

from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .auth import MAX_TENTATIVAS
from .models import (
    Aluno, Aula, AulaCancelada, AulaExtra, ComentarioAula, HorarioAula,
    Material, Nivel, Professor, Recesso,
)
from .views import montar_mes


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

    def test_nova_aula_nao_dispara_email(self):
        mail.outbox.clear()
        Aula.objects.create(titulo='Grafos', data=date(2026, 6, 15), nivel=self.n1)
        self.assertEqual(len(mail.outbox), 0)

    def test_novo_material_nao_dispara_email(self):
        mail.outbox.clear()
        Material.objects.create(titulo='Lista 5', nivel=self.n1, arquivo='materiais_avulsos/l5.pdf')
        self.assertEqual(len(mail.outbox), 0)

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

    def test_comentario_de_professor_ganha_selo(self):
        professor = Professor.objects.create_user(
            email='prof@teste.com', password='senha123', first_name='Levi'
        )
        ComentarioAula.objects.create(aula=self.aula, autor=professor, texto='Boa pergunta!')
        resp = self.client.get(reverse('aula_detalhe', args=[self.aula.pk]))
        self.assertContains(resp, 'Professor')


class BoasVindasTests(TestCase):
    def test_aluno_novo_recebe_boas_vindas(self):
        mail.outbox.clear()
        Aluno.objects.create_user(
            email='novo@teste.com', password='senha123', first_name='Ana'
        )
        self.assertEqual(len(mail.outbox), 1)
        aviso = mail.outbox[0]
        self.assertEqual(aviso.to, ['novo@teste.com'])
        self.assertEqual(aviso.subject, 'Bem-vindo(a) ao Curso Solução!')
        self.assertIn('Olá, Ana!', aviso.body)
        self.assertIn('/senha/redefinir/', aviso.body)
        self.assertIn('/senha/esqueci/', aviso.body)

    def test_link_de_boas_vindas_cria_senha(self):
        mail.outbox.clear()
        Aluno.objects.create_user(
            email='novo@teste.com', password='senha-inicial', first_name='Ana'
        )
        link = re.search(r'(/senha/redefinir/\S+)', mail.outbox[0].body)
        self.assertIsNotNone(link)
        resp = self.client.get(link.group(1), follow=True)
        self.assertContains(resp, 'Criar nova senha')
        resp = self.client.post(resp.request['PATH_INFO'], {
            'new_password1': 'MinhaSenha#2026',
            'new_password2': 'MinhaSenha#2026',
        })
        self.assertRedirects(resp, reverse('password_reset_complete'))
        self.assertTrue(self.client.login(username='novo@teste.com', password='MinhaSenha#2026'))

    def test_professor_nao_recebe_boas_vindas(self):
        mail.outbox.clear()
        Professor.objects.create_user(
            email='prof@teste.com', password='senha123', first_name='Levi'
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_superuser_nao_recebe_boas_vindas(self):
        mail.outbox.clear()
        Aluno.objects.create_superuser('admin@teste.com', 'senha123', first_name='Admin')
        self.assertEqual(len(mail.outbox), 0)

    def test_editar_aluno_nao_reenvia_boas_vindas(self):
        aluno = Aluno.objects.create_user(
            email='novo@teste.com', password='senha123', first_name='Ana'
        )
        mail.outbox.clear()
        aluno.first_name = 'Ana Clara'
        aluno.save()
        self.assertEqual(len(mail.outbox), 0)


class ProfessorTests(TestCase):
    def setUp(self):
        self.n1 = Nivel.objects.get(numero=1)
        self.aluno = Aluno.objects.create_user(
            email='aluno@teste.com', password='senha123', first_name='Ana'
        )
        self.professor = Professor.objects.create_user(
            email='prof@teste.com', password='senha123', first_name='Levi'
        )
        self.superusuario = Professor.objects.create_superuser(
            email='dona@teste.com', password='senha123', first_name='Cal'
        )

    def test_professor_nasce_no_grupo_sem_ser_superusuario(self):
        self.assertTrue(self.professor.is_staff)
        self.assertFalse(self.professor.is_superuser)
        self.assertTrue(self.professor.groups.filter(name='Professores').exists())

    def test_superusuario_continua_sendo_professor(self):
        self.assertIn(self.superusuario, Professor.objects.all())

    def test_professores_e_alunos_separados(self):
        self.assertCountEqual(
            Professor.objects.all(), [self.professor, self.superusuario]
        )
        self.assertIn(self.aluno, Aluno.objects.filter(is_staff=False))

    def test_saudacao_do_professor_na_home(self):
        self.client.login(username='prof@teste.com', password='senha123')
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'Olá, Professor(a) Levi')

        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, 'Olá, Ana')
        self.assertNotContains(resp, 'Professor(a)')

    def test_professor_acessa_gerenciamento(self):
        self.client.login(username='prof@teste.com', password='senha123')
        resp = self.client.get(reverse('admin:index'))
        self.assertEqual(resp.status_code, 200)

    def test_professor_gerencia_aulas_mas_nao_alunos(self):
        self.client.login(username='prof@teste.com', password='senha123')
        resp = self.client.get(reverse('admin:core_aula_add'))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse('admin:core_aluno_changelist'))
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get(reverse('admin:core_professor_add'))
        self.assertEqual(resp.status_code, 403)

    def test_superusuario_cadastra_professor(self):
        self.client.login(username='dona@teste.com', password='senha123')
        resp = self.client.post(reverse('admin:core_professor_add'), {
            'email': 'novo.prof@teste.com',
            'first_name': 'Carla',
            'last_name': 'Souza',
            'password1': 'SenhaForte#2026',
            'password2': 'SenhaForte#2026',
        })
        self.assertEqual(resp.status_code, 302)
        novo = Professor.objects.get(email='novo.prof@teste.com')
        self.assertTrue(novo.is_staff)
        self.assertFalse(novo.is_superuser)
        self.assertTrue(novo.groups.filter(name='Professores').exists())

    def test_aluno_nao_acessa_gerenciamento(self):
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('admin:index'))
        self.assertEqual(resp.status_code, 302)


class CalendarioTests(TestCase):
    def setUp(self):
        self.n1 = Nivel.objects.get(numero=1)
        self.aluno = Aluno.objects.create_user(
            email='aluno@teste.com', password='senha123', first_name='Ana'
        )
        self.aluno.niveis.add(self.n1)
        self.client.login(username='aluno@teste.com', password='senha123')

    def test_horarios_criados_pela_migracao(self):
        self.assertEqual(HorarioAula.objects.count(), 5)
        self.assertEqual(
            HorarioAula.objects.filter(rotulo='Nível 2 avançado').get().nivel.numero, 2
        )
        recesso = Recesso.objects.get()
        self.assertEqual(recesso.inicio, date(2026, 7, 1))
        self.assertEqual(recesso.fim, date(2026, 7, 31))

    def test_pagina_mostra_links_de_todos_os_niveis(self):
        resp = self.client.get(reverse('calendario'))
        self.assertContains(resp, 'https://meet.google.com/zjb-fenc-jeo')
        self.assertContains(resp, 'https://meet.google.com/qsi-ytck-dqy')
        self.assertContains(resp, 'https://meet.google.com/yhs-qngv-ixx')
        self.assertContains(resp, 'Nível 1 avançado')

    def test_calendario_exige_login(self):
        self.client.logout()
        resp = self.client.get(reverse('calendario'))
        self.assertEqual(resp.status_code, 302)

    def _dias_com_aula(self, mes):
        return sorted(
            dia['data'].day
            for semana in mes['semanas'] for dia in semana
            if dia['aulas'] and not dia['outro_mes']
        )

    def test_montar_mes_marca_proximas_aulas(self):
        horarios = list(HorarioAula.objects.filter(nivel=self.n1))
        hoje = date(2026, 6, 12)
        mes = montar_mes(2026, 6, horarios, [], [], [], hoje)
        self.assertEqual(mes['nome'], 'Junho de 2026')
        # Sábados 13, 20, 27 e segundas 15, 22, 29 — nada antes de hoje (dia 12).
        self.assertEqual(self._dias_com_aula(mes), [13, 15, 20, 22, 27, 29])

    def test_montar_mes_recesso_suspende_grade_semanal(self):
        horarios = list(HorarioAula.objects.filter(nivel=self.n1))
        recessos = list(Recesso.objects.all())
        mes = montar_mes(2026, 7, horarios, [], [], recessos, date(2026, 6, 12))
        self.assertEqual(self._dias_com_aula(mes), [])
        self.assertEqual(len(mes['recessos']), 1)

    def test_intensivo_de_julho_aparece_mesmo_no_recesso(self):
        horarios = list(HorarioAula.objects.filter(nivel=self.n1))
        extras = list(AulaExtra.objects.filter(nivel=self.n1))
        recessos = list(Recesso.objects.all())
        mes = montar_mes(2026, 7, horarios, extras, [], recessos, date(2026, 6, 12))
        self.assertEqual(self._dias_com_aula(mes), [1, 2, 3, 6, 7, 8, 9, 10])

    def test_intensivo_nivel_3_termina_dia_7(self):
        n3 = Nivel.objects.get(numero=3)
        extras = list(AulaExtra.objects.filter(nivel=n3))
        mes = montar_mes(2026, 7, [], extras, [], list(Recesso.objects.all()), date(2026, 6, 12))
        self.assertEqual(self._dias_com_aula(mes), [1, 2, 3, 6, 7])

    def test_intensivo_criado_pela_migracao(self):
        self.assertEqual(AulaExtra.objects.count(), 21)
        aula = AulaExtra.objects.filter(nivel=self.n1).first()
        self.assertEqual(aula.hora_inicio.strftime('%H:%M'), '09:20')
        self.assertEqual(aula.link_meet, 'https://meet.google.com/zjb-fenc-jeo')


class NovaAulaCalendarioTests(TestCase):
    def setUp(self):
        self.n2 = Nivel.objects.get(numero=2)
        self.aluno = Aluno.objects.create_user(
            email='aluno@teste.com', password='senha123', first_name='Ana'
        )
        self.professor = Professor.objects.create_user(
            email='prof@teste.com', password='senha123', first_name='Levi'
        )

    def _dados(self, **extra):
        dados = {
            'nivel': self.n2.pk,
            'data': '2026-08-15',
            'hora_inicio': '14:00',
            'hora_fim': '15:40',
            'link_meet': '',
        }
        dados.update(extra)
        return dados

    def test_professor_cadastra_aula(self):
        self.client.login(username='prof@teste.com', password='senha123')
        resp = self.client.post(reverse('nova_aula_calendario'), self._dados())
        self.assertRedirects(resp, reverse('calendario'))
        aula = AulaExtra.objects.get(data=date(2026, 8, 15))
        self.assertEqual(aula.nivel, self.n2)
        self.assertEqual(aula.hora_inicio.strftime('%H:%M'), '14:00')

    def test_link_vazio_herda_link_do_nivel(self):
        self.client.login(username='prof@teste.com', password='senha123')
        self.client.post(reverse('nova_aula_calendario'), self._dados())
        aula = AulaExtra.objects.get(data=date(2026, 8, 15))
        self.assertEqual(aula.link_meet, 'https://meet.google.com/qsi-ytck-dqy')

    def test_link_informado_e_mantido(self):
        self.client.login(username='prof@teste.com', password='senha123')
        self.client.post(
            reverse('nova_aula_calendario'),
            self._dados(link_meet='https://meet.google.com/aaa-bbbb-ccc'),
        )
        aula = AulaExtra.objects.get(data=date(2026, 8, 15))
        self.assertEqual(aula.link_meet, 'https://meet.google.com/aaa-bbbb-ccc')

    def test_fim_antes_do_inicio_da_erro(self):
        self.client.login(username='prof@teste.com', password='senha123')
        resp = self.client.post(
            reverse('nova_aula_calendario'),
            self._dados(hora_inicio='15:00', hora_fim='14:00'),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'O horário de fim deve ser depois do horário de início.')
        self.assertFalse(AulaExtra.objects.filter(data=date(2026, 8, 15)).exists())

    def test_aluno_nao_cadastra_aula(self):
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.post(reverse('nova_aula_calendario'), self._dados())
        self.assertRedirects(resp, reverse('calendario'))
        self.assertFalse(AulaExtra.objects.filter(data=date(2026, 8, 15)).exists())

    def test_botao_so_aparece_para_professor(self):
        self.client.login(username='prof@teste.com', password='senha123')
        resp = self.client.get(reverse('calendario'))
        self.assertContains(resp, 'Nova aula no calendário')

        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.get(reverse('calendario'))
        self.assertNotContains(resp, 'Nova aula no calendário')



class CancelarAulaTests(TestCase):
    def setUp(self):
        self.n1 = Nivel.objects.get(numero=1)
        self.aluno = Aluno.objects.create_user(
            email='aluno@teste.com', password='senha123', first_name='Ana'
        )
        self.aluno.niveis.add(self.n1)
        self.professor = Professor.objects.create_user(
            email='prof@teste.com', password='senha123', first_name='Levi'
        )
        # Sábado 08:00–09:40 do nível 1.
        self.horario_sabado = HorarioAula.objects.get(nivel=self.n1, dia_semana=5)

    def test_professor_cancela_ocorrencia(self):
        self.client.login(username='prof@teste.com', password='senha123')
        resp = self.client.post(reverse('cancelar_aula_calendario'), {
            'horario': self.horario_sabado.pk,
            'data': '2026-06-20',  # um sábado
            'motivo': '',
        })
        self.assertRedirects(resp, reverse('calendario'))
        cancelamento = AulaCancelada.objects.get(
            horario=self.horario_sabado, data=date(2026, 6, 20)
        )
        self.assertEqual(cancelamento.motivo, '')

    def test_cancelamento_com_motivo(self):
        self.client.login(username='prof@teste.com', password='senha123')
        self.client.post(reverse('cancelar_aula_calendario'), {
            'horario': self.horario_sabado.pk,
            'data': '2026-06-20',
            'motivo': 'Feriado de Corpus Christi',
        })
        cancelamento = AulaCancelada.objects.get(data=date(2026, 6, 20))
        self.assertEqual(cancelamento.motivo, 'Feriado de Corpus Christi')

    def test_motivo_disponivel_no_calendario(self):
        cancelamento = AulaCancelada.objects.create(
            horario=self.horario_sabado, data=date(2026, 6, 20), motivo='Feriado'
        )
        horarios = list(HorarioAula.objects.filter(nivel=self.n1))
        mes = montar_mes(2026, 6, horarios, [], [cancelamento], [], date(2026, 6, 12))
        cancelados = [
            c for semana in mes['semanas'] for dia in semana for c in dia['canceladas']
        ]
        self.assertEqual(len(cancelados), 1)
        self.assertEqual(cancelados[0].motivo, 'Feriado')
        self.assertEqual(cancelados[0].horario, self.horario_sabado)

    def test_data_em_dia_errado_da_erro(self):
        self.client.login(username='prof@teste.com', password='senha123')
        resp = self.client.post(reverse('cancelar_aula_calendario'), {
            'horario': self.horario_sabado.pk,
            'data': '2026-06-19',  # uma sexta
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'A data não corresponde ao dia dessa aula')
        self.assertFalse(AulaCancelada.objects.exists())

    def test_aluno_nao_cancela(self):
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.post(reverse('cancelar_aula_calendario'), {
            'horario': self.horario_sabado.pk,
            'data': '2026-06-20',
        })
        self.assertRedirects(resp, reverse('calendario'))
        self.assertFalse(AulaCancelada.objects.exists())

    def test_ocorrencia_cancelada_sai_das_aulas_e_aparece_riscada(self):
        cancelamento = AulaCancelada.objects.create(
            horario=self.horario_sabado, data=date(2026, 6, 20)
        )
        horarios = list(HorarioAula.objects.filter(nivel=self.n1))
        mes = montar_mes(2026, 6, horarios, [], [cancelamento], [], date(2026, 6, 12))
        dias_com_aula = sorted(
            dia['data'].day
            for semana in mes['semanas'] for dia in semana
            if dia['aulas'] and not dia['outro_mes']
        )
        # Sábado 20 sai da lista de aulas...
        self.assertEqual(dias_com_aula, [13, 15, 22, 27, 29])
        # ...mas aparece como cancelada naquele dia.
        dias_cancelados = [
            dia['data'].day
            for semana in mes['semanas'] for dia in semana
            if dia['canceladas']
        ]
        self.assertEqual(dias_cancelados, [20])

    def test_professor_desfaz_cancelamento(self):
        cancelamento = AulaCancelada.objects.create(
            horario=self.horario_sabado, data=date(2026, 6, 20)
        )
        self.client.login(username='prof@teste.com', password='senha123')
        resp = self.client.post(reverse('desfazer_cancelamento', args=[cancelamento.pk]))
        self.assertRedirects(resp, reverse('calendario'))
        self.assertFalse(AulaCancelada.objects.exists())

    def test_aluno_nao_desfaz_cancelamento(self):
        cancelamento = AulaCancelada.objects.create(
            horario=self.horario_sabado, data=date(2026, 6, 20)
        )
        self.client.login(username='aluno@teste.com', password='senha123')
        resp = self.client.post(reverse('desfazer_cancelamento', args=[cancelamento.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(AulaCancelada.objects.exists())


class SegurancaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.n1 = Nivel.objects.get(numero=1)
        Aluno.objects.create_user(
            email='aluno@teste.com', password='SenhaCerta#2026', first_name='Ana'
        )

    def test_upload_nao_pdf_e_rejeitado(self):
        material = Material(titulo='Falso', nivel=self.n1)
        material.arquivo = SimpleUploadedFile(
            'malicioso.html', b'<script>alert(1)</script>', content_type='text/html'
        )
        with self.assertRaises(ValidationError):
            material.full_clean()

    def test_upload_pdf_e_aceito(self):
        material = Material(titulo='Lista', nivel=self.n1)
        material.arquivo = SimpleUploadedFile(
            'lista.pdf', b'%PDF-1.4 conteudo', content_type='application/pdf'
        )
        try:
            material.full_clean()
        except ValidationError as e:
            self.assertNotIn('arquivo', e.message_dict)

    def test_login_bloqueia_apos_excesso_de_tentativas(self):
        url = reverse('login')
        for _ in range(MAX_TENTATIVAS):
            self.client.post(url, {'username': 'aluno@teste.com', 'password': 'errada'})
        resp = self.client.post(
            url, {'username': 'aluno@teste.com', 'password': 'SenhaCerta#2026'}
        )
        self.assertContains(resp, 'Muitas tentativas')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_correto_zera_contador(self):
        url = reverse('login')
        for _ in range(MAX_TENTATIVAS - 1):
            self.client.post(url, {'username': 'aluno@teste.com', 'password': 'errada'})
        resp = self.client.post(
            url, {'username': 'aluno@teste.com', 'password': 'SenhaCerta#2026'}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_paginas_protegidas_exigem_login(self):
        cache.clear()
        for nome in ['home', 'calendario', 'materiais', 'comunidade']:
            resp = self.client.get(reverse(nome))
            self.assertEqual(resp.status_code, 302, nome)
            self.assertIn('/entrar/', resp.url, nome)
