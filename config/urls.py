from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from comunidade import views as comunidade_views
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', core_views.home, name='home'),
    path('calendario/', core_views.calendario, name='calendario'),
    path('calendario/nova-aula/', core_views.nova_aula_calendario, name='nova_aula_calendario'),
    path('calendario/cancelar-aula/', core_views.cancelar_aula_calendario, name='cancelar_aula_calendario'),
    path('calendario/cancelamento/<int:pk>/desfazer/', core_views.desfazer_cancelamento, name='desfazer_cancelamento'),
    path('aula/<int:pk>/', core_views.aula_detalhe, name='aula_detalhe'),
    path('aula/comentario/<int:pk>/editar/', core_views.editar_comentario_aula, name='editar_comentario_aula'),
    path('aula/comentario/<int:pk>/excluir/', core_views.excluir_comentario_aula, name='excluir_comentario_aula'),
    path('materiais/', core_views.materiais, name='materiais'),

    path('entrar/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('sair/', auth_views.LogoutView.as_view(), name='logout'),

    # Recuperação de senha. Os templates usam o prefixo "senha_" para não
    # colidir com os registration/password_reset_*.html do django.contrib.admin.
    path('senha/esqueci/', auth_views.PasswordResetView.as_view(
        template_name='registration/senha_esqueci.html',
        email_template_name='registration/senha_email.html',
        subject_template_name='registration/senha_assunto.txt',
    ), name='password_reset'),
    path('senha/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/senha_enviado.html',
    ), name='password_reset_done'),
    path('senha/redefinir/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/senha_redefinir.html',
    ), name='password_reset_confirm'),
    path('senha/concluida/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/senha_concluida.html',
    ), name='password_reset_complete'),

    path('comunidade/', comunidade_views.lista_posts, name='comunidade'),
    path('comunidade/novo/', comunidade_views.novo_post, name='novo_post'),
    path('comunidade/post/<int:pk>/', comunidade_views.post_detalhe, name='post_detalhe'),
    path('comunidade/comentario/<int:pk>/editar/', comunidade_views.editar_comentario, name='editar_comentario'),
    path('comunidade/comentario/<int:pk>/excluir/', comunidade_views.excluir_comentario, name='excluir_comentario'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
