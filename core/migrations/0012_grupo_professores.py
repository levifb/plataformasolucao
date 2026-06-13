from django.db import migrations

GRUPO = 'Professores'

# Modelos que o professor gerencia no admin; alunos, professores e níveis
# ficam de fora — são exclusivos de superusuários.
MODELOS = [
    'aula', 'material', 'comentarioaula',
    'horarioaula', 'aulaextra', 'aulacancelada', 'recesso',
]
ACOES = ['add', 'change', 'delete', 'view']

SUPERUSUARIOS = ['levi.fb.123@gmail.com', 'calexmo@gmail.com']


def criar_grupo(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Aluno = apps.get_model('core', 'Aluno')

    grupo, _ = Group.objects.get_or_create(name=GRUPO)

    # get_or_create porque, num banco recém-criado, o post_migrate que gera
    # as permissões padrão só roda depois de todas as migrações.
    for modelo in MODELOS:
        ct, _ = ContentType.objects.get_or_create(app_label='core', model=modelo)
        for acao in ACOES:
            perm, _ = Permission.objects.get_or_create(
                codename=f'{acao}_{modelo}',
                content_type=ct,
                defaults={'name': f'Can {acao} {modelo}'},
            )
            grupo.permissions.add(perm)

    professores = Aluno.objects.filter(is_staff=True)
    for professor in professores:
        professor.groups.add(grupo)
    professores.exclude(email__in=SUPERUSUARIOS).update(is_superuser=False)


def remover_grupo(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name=GRUPO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_alter_aula_material_alter_material_arquivo'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(criar_grupo, remover_grupo),
    ]
