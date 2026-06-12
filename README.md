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

## Publicar no PythonAnywhere (produção)

O site fica em `https://SEUUSUARIO.pythonanywhere.com` (plano gratuito).

1. **Criar a conta:** em https://www.pythonanywhere.com, crie uma conta
   "Beginner" (gratuita). O nome de usuário escolhido vira o endereço do site.
2. **Enviar o código:** na aba **Files**, faça upload do projeto zipado e
   descompacte num console Bash (`unzip plataforma.zip`), ou clone do GitHub.
3. **Instalar e preparar** (num console Bash, dentro da pasta do projeto):

   ```bash
   pip3.13 install --user -r requirements.txt
   python3.13 manage.py migrate
   python3.13 manage.py createsuperuser
   python3.13 manage.py collectstatic --noinput
   ```

4. **Criar o `.env` de produção** na pasta do projeto, copiando o
   `.env.exemplo` e preenchendo tudo — inclusive o bloco "Apenas em produção"
   (SECRET_KEY nova, `DEBUG=False`, `ALLOWED_HOSTS` e `SITE_URL` com seu
   endereço real).
5. **Criar o web app:** aba **Web** → *Add a new web app* → *Manual
   configuration* → Python 3.13. Em seguida:
   - **Source code / Working directory:** a pasta do projeto;
   - **WSGI configuration file:** apague o conteúdo e deixe apenas:

     ```python
     import sys
     sys.path.insert(0, '/home/SEUUSUARIO/plataforma')  # pasta do projeto

     import os
     os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

     from django.core.wsgi import get_wsgi_application
     application = get_wsgi_application()
     ```

   - **Static files:** mapeie `/static/` → `/home/SEUUSUARIO/plataforma/staticfiles`
     e `/media/` → `/home/SEUUSUARIO/plataforma/media`.
6. **Reload** (botão verde na aba Web) e pronto.

Observações do plano gratuito:

- O envio de email pelo Gmail (`smtp.gmail.com`) funciona normalmente — é um
  dos servidores liberados para contas gratuitas.
- A cada 3 meses o PythonAnywhere pede um clique em **"Run until..."** na aba
  Web para manter o site no ar (eles avisam por email).
- Para usar domínio próprio (ex.: `plataforma.cursosolucao.com.br`), é preciso
  o plano pago (US$ 5/mês), que também remove o limite de tráfego.

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
