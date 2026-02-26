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
from myfinance.settings import ENVIRONMENT
from statement.models import AppConfig
from statement.services.core.device import DeviceService
from statement.services.core.fixed_expenses import FixedExpensesService
from statement.services.core.notification import NotificationService
from statement.services.core.notification_title import NotificationTitleService

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
    transaction_classifier = None
    transaction_classifier_enabled = False

    # Determina se o classificador está ativado (seguro: não falha se a tabela AppConfig estiver ausente)
    try:
        appcfg_enabled = False
        try:
            appcfg_enabled = AppConfig.get_solo().enable_transaction_classifier
        except Exception:
            appcfg_enabled = False

        transaction_classifier_enabled = appcfg_enabled and (ENVIRONMENT != 'development')

        if transaction_classifier_enabled:
            microservice_client = TransactionClassifierClient(request.user)
            status = microservice_client.status()
            transaction_classifier = status['data']
    except Exception:
        transaction_classifier = None

    profile = ProfileService(request.user)
    fixed_expenses = FixedExpensesService.get_all(request.user)
    # dispositivos do usuário
    devices = DeviceService.get_all(request.user)
    templatetags = {
        'transaction_classifier': transaction_classifier,
        'transaction_classifier_enabled': transaction_classifier_enabled,
        'profile': profile,
        'fixed_expenses': fixed_expenses,
        'devices': devices,
        'recent_notifications': [],
        'notification_titles': [],
    }
    try:
        templatetags['recent_notifications'] = list(
            NotificationService.get_by_filter(order='-created_at', user=request.user)[:5]
        )
    except Exception:
        templatetags['recent_notifications'] = []
    # Ensure notification titles exist and prepare user preferences list
    try:
        titles = NotificationService.get_by_filter(order='-created_at', user=request.user)
        # collect distinct titles from notifications
        distinct_titles = list({n.title for n in titles if getattr(n, 'title', None)})
        NotificationTitleService.ensure_titles(distinct_titles)
        all_titles = NotificationTitleService.get_all_titles()
        enabled = NotificationTitleService.get_enabled_titles_for_user(request.user)
        templatetags['notification_titles'] = [
            {'id': nt.id, 'title': nt.title, 'enabled': (nt.title in enabled)} for nt in all_titles
        ]
    except Exception:
        templatetags['notification_titles'] = []
    return render(request, 'user/get_profile.html', templatetags)


@login_required
def edit_user_notification_titles(request):
    """Endpoint para atualizar preferências de títulos de notificação do usuário."""
    if request.method != 'POST':
        return redirect('get_profile')
    enabled_ids = request.POST.getlist('enabled_ids')
    try:
        NotificationTitleService.set_user_enabled_titles(request.user, enabled_ids)
    except Exception:
        pass
    return redirect('get_profile')


@login_required
def get_user_notification_titles(request):
    """Exibe a lista completa de títulos de notificação e o estado do usuário."""
    try:
        # Garante que existam títulos derivados das notificações já salvas
        titles_qs = NotificationService.get_by_filter(order='-created_at', user=request.user)
        distinct_titles = list({n.title for n in titles_qs if getattr(n, 'title', None)})
    except Exception:
        distinct_titles = []

    try:
        NotificationTitleService.ensure_titles(distinct_titles)
        all_titles = NotificationTitleService.get_all_titles()
        enabled = NotificationTitleService.get_enabled_titles_for_user(request.user)
        notification_titles = [{'id': nt.id, 'title': nt.title, 'enabled': (nt.title in enabled)} for nt in all_titles]
    except Exception:
        notification_titles = []

    return render(request, 'user/list.html', {'notification_titles': notification_titles})


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
            profile_form.save()
            return redirect('get_profile')
        else:
            print(profile_form.errors)
    else:
        profile_form = user_forms.ProfileForm(instance=request.user)
    return render(request, 'user/profile_form.html', {'profile_form': profile_form})
