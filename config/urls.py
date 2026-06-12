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
    path('aula/<int:pk>/', core_views.aula_detalhe, name='aula_detalhe'),
    path('materiais/', core_views.materiais, name='materiais'),

    path('entrar/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('sair/', auth_views.LogoutView.as_view(), name='logout'),

    path('comunidade/', comunidade_views.lista_posts, name='comunidade'),
    path('comunidade/novo/', comunidade_views.novo_post, name='novo_post'),
    path('comunidade/post/<int:pk>/', comunidade_views.post_detalhe, name='post_detalhe'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
