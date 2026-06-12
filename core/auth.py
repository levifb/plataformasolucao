"""Login com proteção contra força-bruta.

Conta tentativas falhas por IP no cache. Passado o limite, o IP entra num
período de espera antes de poder tentar de novo. Um login bem-sucedido zera
a contagem. Os limites são folgados de propósito: protegem contra varredura
automatizada sem atrapalhar o aluno que errou a senha algumas vezes.
"""

from django.contrib.auth.views import LoginView
from django.core.cache import cache

MAX_TENTATIVAS = 10          # falhas toleradas por IP...
JANELA_SEGUNDOS = 15 * 60    # ...dentro desta janela; também é o tempo de espera.


def _chave(request):
    # REMOTE_ADDR no PythonAnywhere já vem do proxy; sem confiar em headers
    # falsificáveis pelo cliente (X-Forwarded-For).
    ip = request.META.get('REMOTE_ADDR', 'desconhecido')
    return f'login-falhas:{ip}'


class LoginComLimite(LoginView):
    def post(self, request, *args, **kwargs):
        if cache.get(_chave(request), 0) >= MAX_TENTATIVAS:
            return self.render_to_response(
                self.get_context_data(form=self.get_form(), bloqueado=True)
            )
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        cache.delete(_chave(request=self.request))
        return super().form_valid(form)

    def form_invalid(self, form):
        chave = _chave(self.request)
        try:
            cache.incr(chave)
        except ValueError:
            cache.set(chave, 1, JANELA_SEGUNDOS)
        return super().form_invalid(form)
