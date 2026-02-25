from django.contrib.auth.decorators import login_required
from django.forms import modelform_factory
from django.shortcuts import redirect
from django.utils.decorators import method_decorator

from statement.models import AppConfig, Notification
from statement.services.core.account import AccountService
from statement.services.core.bank import BankService
from statement.services.core.card import CardService
from statement.services.core.category import CategoryService
from statement.services.core.fixed_expenses import FixedExpensesService
from statement.services.core.flag import FlagService
from statement.services.core.notification import NotificationService
from statement.services.core.subcategory import SubcategoryService
from statement.services.portfolio.fixed_income.index import IndexService
from statement.services.portfolio.fixed_income.security import FixedIncomeSecurityService
from statement.services.portfolio.variable_income.sector import SectorService
from statement.services.portfolio.variable_income.ticker import TickerService
from statement.views.base_view import BaseView


class SettingsView(BaseView):
    """
    View responsável pela gestão das configurações
    """

    redirect_url = 'setup_settings'

    @method_decorator(login_required)
    def settings(self, request):
        """
        Retorna todas as instâncias do modelo.
        """
        # Protege acesso às configurações para usuários não staff
        if not request.user.is_staff:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied()
        # Recupera a flag de configuração do App de forma segura para evitar falhas
        # caso as migrations ainda não tenham sido aplicadas
        try:
            enable_transaction_classifier = AppConfig.get_solo().enable_transaction_classifier
        except Exception:
            enable_transaction_classifier = False

        specific_content = {
            'accounts': AccountService.get_all(request.user),
            'banks': BankService.get_all(),
            'flags': FlagService.get_all(),
            'cards': CardService.get_all(request.user),
            'categories': CategoryService.get_all(),
            'subcategories': SubcategoryService.get_all(),
            'fixed_expenses': FixedExpensesService.get_all(request.user),
            # Renda Fixa
            'indexes': IndexService.get_all(request.user),
            'fixed_income_securities': FixedIncomeSecurityService.get_all(request.user),
            # Renda Variável
            'sectors': SectorService.get_all(request.user),
            'tickers': TickerService.get_all(request.user),
            'app_config_enable_transaction_classifier': enable_transaction_classifier,
            'notification_titles': [],
            'recent_notifications': [],
        }
        # Prepara os títulos de notificação: garante que exista um NotificationTitle
        # para cada título único presente em Notification e monta a lista com o
        # estado (habilitado) do admin (request.user)
        try:
            from statement.services.core.notification_title import NotificationTitleService

            titles = Notification.objects.values_list('title', flat=True).distinct()
            titles = [t for t in titles if t]
            NotificationTitleService.ensure_titles(titles)
            # monta lista de dicts com estado para o usuário admin
            all_titles = NotificationTitleService.get_all_titles()
            admin_enabled = NotificationTitleService.get_enabled_titles_for_user(request.user)
            specific_content['notification_titles'] = [
                {'id': nt.id, 'title': nt.title, 'enabled': (nt.title in admin_enabled)} for nt in all_titles
            ]
        except Exception:
            specific_content['notification_titles'] = []
        # últimas notificações (primeiras 5)
        try:
            specific_content['recent_notifications'] = NotificationService.get_by_filter(order='-created_at')[:5]
        except Exception:
            specific_content['recent_notifications'] = []
        return self._render(request, None, 'general/setup_settings.html', specific_content)

    @method_decorator(login_required)
    def edit_notification_titles(self, request):
        """Atualiza os títulos de notificação habilitados a partir do formulário de settings."""
        # Protege acesso às configurações para usuários não staff
        if not request.user.is_staff:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied()
        if request.method != 'POST':
            return redirect('setup_settings')
        enabled_ids = request.POST.getlist('enabled_ids')
        try:
            from statement.services.core.notification_title import NotificationTitleService

            NotificationTitleService.set_user_enabled_titles(request.user, enabled_ids)
        except Exception:
            pass
        return redirect('setup_settings')

    @method_decorator(login_required)
    def edit_app_config(self, request):
        """Edita o AppConfig global (`enable_transaction_classifier`) pela interface de configurações."""
        # Protege acesso às configurações para usuários não staff
        if not request.user.is_staff:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied()
        try:
            cfg = AppConfig.get_solo()
        except Exception:
            # Se a tabela ainda não existir, cria uma instância padrão em memória
            cfg = AppConfig()

        AppConfigForm = modelform_factory(AppConfig, fields=('enable_transaction_classifier',))
        if request.method == 'POST':
            form = AppConfigForm(request.POST, instance=cfg)
            if form.is_valid():
                form.save()
                return redirect('setup_settings')
        else:
            form = AppConfigForm(instance=cfg)

        # Reutiliza o template base de formulário global
        return self._render(request, form, 'base/form.html', {})
