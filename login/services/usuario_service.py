from ..models import Usuario


def cadastrar_usuario(usuario):
    usuario = Usuario.objects.create_user(nome=usuario.nome,
                                          email=usuario.email,
                                          username=usuario.username,
                                          password=usuario.password)
    usuario.save()

