from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render

from clients.transaction_classifier.transaction_classifier import TransactionClassifierClient
from login.entities.user import User
from login.forms import user_forms
from login.forms.password_form import PasswordChangeCustomForm
from login.models import Profile
from login.services import user_services
from login.services.profile import ProfileService

# Create your views here.


def create_user(request):
    """
    Método que cria um novo usuário.
    :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
    """
    if request.method == 'POST':
        user_form = user_forms.UserForm(request.POST, request.FILES)
        if user_form.is_valid():
            new_user = User(
                username=user_form.cleaned_data['username'],
                password=user_form.cleaned_data['password1'],
                name=user_form.cleaned_data['name'],
                email=user_form.cleaned_data['email'],
                is_superuser=False,
                is_staff=False,
                is_active=True,
                date_joined=None,
                photo=user_form.cleaned_data['photo'],
            )
            db_user = user_services.create_user(new_user)
            Profile.objects.create(user=db_user)
            return redirect('login_user')
        else:
            print(user_form.errors)
    else:
        user_form = user_forms.UserForm()
    return render(request, 'user/user_form.html', {'user_form': user_form})


def login_user(request):
    """
    Método que faz o login do usuário.
    :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
    """
    if request.method == 'POST':
        login_form = user_forms.LoginForm(data=request.POST)
        if login_form.is_valid():
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('get_current_month_transactions')
            else:
                messages.error(request, 'As credenciais estão incorretas')
    else:
        login_form = user_forms.LoginForm()
    return render(request, 'user/login.html', {'login_form': login_form})


@login_required
def change_password(request):
    """
    Método que altera a senha do usuário.
    :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
    """
    if request.method == 'POST':
        password_form = PasswordChangeCustomForm(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            return redirect('get_profile')
    else:
        password_form = PasswordChangeForm(request.user)
    return render(request, 'user/password_form.html', {'form_senha': password_form})


@login_required
def update_profile(request):
    """
    Método que atualiza o perfil do usuário.
    :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
    """
    if request.method == 'POST':
        profile_form = user_forms.ProfileForm(request.POST, request.FILES, instance=request.user)
        if profile_form.is_valid():
            profile_form.photo = profile_form.cleaned_data['photo']
            print(profile_form.photo)
            profile_form.save()
            return redirect('get_profile')
        else:
            print(profile_form.errors)
    else:
        profile_form = user_forms.ProfileForm(instance=request.user)
    return render(request, 'user/profile_form.html', {'profile_form': profile_form})


@login_required
def logout_user(request):
    """
    Método que faz o logout do usuário.
    :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
    """
    logout(request)
    return redirect('login_user')


@login_required
def get_profile(request):
    """
    Método que exibe as informações e configurações do usuário.

    :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
    """
    microservice_client = TransactionClassifierClient(request.user)
    status = microservice_client.status()
    transaction_classifier = status['data']
    profile = ProfileService(request.user)
    templatetags = {
        'transaction_classifier': transaction_classifier,
        'profile': profile,
    }
    return render(request, 'user/get_profile.html', templatetags)


@login_required
def update_configs(request):
    """
    Método que atualiza o perfil do usuário.
    :request (django.http.HttpRequest): - Informações sobre o cabeçalho, método e outros dados da requisição.
    """
    if request.method == 'POST':
        profile_form = user_forms.ProfileForm(request.POST, request.FILES, instance=request.user)
        if profile_form.is_valid():
            profile_form.photo = profile_form.cleaned_data['photo']
            print(profile_form.photo)
            profile_form.save()
            return redirect('get_profile')
        else:
            print(profile_form.errors)
    else:
        profile_form = user_forms.ProfileForm(instance=request.user)
    return render(request, 'user/profile_form.html', {'profile_form': profile_form})
