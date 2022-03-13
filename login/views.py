from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect
from .forms import usuario_form, login_form, perfil_form, senha_form
from .entidades.usuario import Usuario
from .services import usuario_service


# Create your views here.


def cadastrar_usuario(request):
    if request.method == 'POST':
        form_usuario = usuario_form.UsuarioForm(request.POST, request.FILES)
        if form_usuario.is_valid():
            usuario_novo = Usuario(nome=form_usuario.cleaned_data['nome'],
                                   email=form_usuario.cleaned_data['email'],
                                   username=form_usuario.cleaned_data['username'],
                                   password=form_usuario.cleaned_data['password1'],
                                   foto=form_usuario.cleaned_data['foto'])
            usuario_service.cadastrar_usuario(usuario_novo)
            return redirect('logar_usuario')
    else:
        form_usuario = usuario_form.UsuarioForm()
    return render(request, 'login/cadastro.html', {'form_usuario': form_usuario})


@login_required
def alterar_senha(request):
    if request.method == 'POST':
        form_senha = senha_form.PasswordChangeCustomForm(request.user, request.POST)
        if form_senha.is_valid():
            user = form_senha.save()
            update_session_auth_hash(request, user)
            return redirect('perfil')
    else:
        form_senha = PasswordChangeForm(request.user)
    return render(request, 'login/alterar_senha.html', {'form_senha': form_senha})


@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form_perfil = perfil_form.PerfilForm(request.POST, request.FILES, instance=request.user)
        if form_perfil.is_valid():
            form_perfil.foto = form_perfil.cleaned_data['foto']
            form_perfil.save()
            return redirect('perfil')
    else:
        form_perfil = perfil_form.PerfilForm(instance=request.user)
    return render(request, 'login/form_perfil.html', {'form_perfil': form_perfil})


def logar_usuario(request):
    if request.method == 'POST':
        form_login = login_form.LoginForm(data=request.POST)
        if form_login.is_valid():
            username = form_login.cleaned_data["username"]
            password = form_login.cleaned_data["password"]
            usuario = authenticate(request, username=username, password=password)
            if usuario is not None:
                login(request, usuario)
                return redirect('perfil')
            else:
                form_login = login_form.LoginForm()
    else:
        form_login = login_form.LoginForm()
    return render(request, 'login/login.html', {'form_login': form_login})


def deslogar_usuario(request):
    logout(request)
    return redirect('logar_usuario')


@login_required
def perfil(request):
    return render(request, 'login/perfil.html')
