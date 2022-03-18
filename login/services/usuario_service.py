from django.utils import timezone

from ..models import Usuario


def cadastrar_usuario(usuario):
    usuario = Usuario.objects.create_user(nome=usuario.nome,
                                          email=usuario.email,
                                          username=usuario.username,
                                          password=usuario.password,
                                          date_joined=timezone.localtime(),
                                          foto=usuario.foto)

