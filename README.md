# Plataforma Curso Solução

Plataforma web do **Curso Solução** (olimpíadas de matemática) feita em Django.
Os alunos acessam aulas (material em PDF, gravação no YouTube e resolução) do(s)
seu(s) nível(is) e participam de um fórum por nível na aba **Comunidade**.

**Níveis:** Nível 1 (6º/7º ano) · Nível 2 (8º/9º ano) · Nível 3 (Ensino Médio)
— já cadastrados automaticamente no banco.

## Como rodar

Requisitos: Python 3.12+ instalado.

```bash
# 1. Instalar dependências
pip install django

# 2. Criar o banco de dados (SQLite)
python manage.py migrate

# 3. Iniciar o servidor
python manage.py runserver
```

A plataforma fica disponível em http://127.0.0.1:8000/.

## Como criar o superusuário (sua conta de administrador)

```bash
python manage.py createsuperuser
```

Informe seu email e uma senha. Depois acesse http://127.0.0.1:8000/admin/
para gerenciar tudo.

## Fluxo de uso (admin)

1. **Cadastrar alunos:** Admin → Alunos → Adicionar. Informe email, nome,
   senha e marque o(s) nível(is) do aluno. O aluno entra na plataforma com
   esse email e senha.
2. **Postar uma aula:** Admin → Aulas → Adicionar. Preencha título, data e
   nível; anexe o material em PDF antes da aula. Depois da aula, edite a
   mesma aula para anexar a resolução e colar o link da gravação no YouTube
   (não listado) — o vídeo aparece embedado na página da aula.
3. **Moderar a comunidade:** Admin → Posts / Comentários permite editar ou
   apagar qualquer publicação.

## Rodar os testes

```bash
python manage.py test
```

## Estrutura

- `core/` — alunos (login por email), níveis e aulas
- `comunidade/` — fórum (posts e comentários por nível)
- `config/` — configurações do projeto
- `media/` — PDFs enviados pelo admin (não versionado)
- `static/css/estilo.css` — visual (azul e verde, responsivo)
