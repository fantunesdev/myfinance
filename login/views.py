from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import usuario_form, login_form
from .entidades.usuario import Usuario
from .services import usuario_service

# Create your views here.


def cadastrar_usuario(request):
    if request.method == 'POST':
        form_usuario = usuario_form.UsuarioForm(data=request.POST)
        print('teste')
        if form_usuario.is_valid():
            usuario_novo = Usuario(nome=form_usuario.cleaned_data['nome'],
                                   email=form_usuario.cleaned_data['email'],
                                   username=form_usuario.cleaned_data['username'],
                                   password=form_usuario.cleaned_data['password1'])
            print('passou')
            usuario_service.cadastrar_usuario(usuario_novo)
            return redirect('logar_usuario')
        else:
            print('não passou')
    else:
        form_usuario = usuario_form.UsuarioForm()
    return render(request, 'login/cadastro.html', {'form_usuario': form_usuario})


def logar_usuario(request):
    if request.method == "POST":
        form_login = login_form.LoginForm(data=request.POST)
        if form_login.is_valid():
            username = form_login.cleaned_data["username"]
            password = form_login.cleaned_data["password"]
            usuario = authenticate(request, username=username, password=password)
            if usuario is not None:
                login(request, usuario)
                return redirect('logado')
            else:
                form_login = login_form.LoginForm()
    else:
        form_login = login_form.LoginForm()
    return render(request, 'login/login.html', {'form_login': form_login})


def deslogar_usuario(request):
    logout(request)
    return redirect('logar_usuario')


@login_required
def logado(request):
    return render(request, 'login/teste.html')
