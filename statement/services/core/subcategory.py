from statement.models import Subcategory, SubcategoryChartConfig
from statement.services.base_service import BaseService


class SubcategoryService(BaseService):
    """Serviço para gerenciar operações relacionadas ao modelo Subcategory."""

    model = Subcategory
    chart_config_model = SubcategoryChartConfig
    chart_flag_names = (
        'show_in_monthly_cashflow_donut',
        'show_in_annual_statement',
        'show_in_monthly_expense_category_bar',
        'show_in_annual_expense_category_bar',
        'show_in_monthly_expense_line',
    )

    @staticmethod
    def get_by_category(category_id):
        """
        Obtém as subcategorias de uma categoria
        """
        return Subcategory.objects.select_related('category').filter(category=category_id)

    @classmethod
    def get_chart_config_values(cls, user, subcategory_id):
        config = cls.get_chart_config(user, subcategory_id)
        if not config:
            return cls.get_default_chart_config_values()

        return {flag_name: getattr(config, flag_name) for flag_name in cls.chart_flag_names}

    @classmethod
    def get_default_chart_config_values(cls):
        return {flag_name: True for flag_name in cls.chart_flag_names}

    @classmethod
    def get_chart_config(cls, user, subcategory_id):
        if not user or not getattr(user, 'is_authenticated', False):
            return None

        return cls.chart_config_model.objects.filter(user=user, subcategory_id=subcategory_id).first()

    @classmethod
    def ensure_chart_configs_for_user(cls, user):
        if not user or not getattr(user, 'is_authenticated', False):
            return

        existing_subcategory_ids = set(
            cls.chart_config_model.objects.filter(user=user).values_list('subcategory_id', flat=True)
        )
        configs = [
            cls.chart_config_model(user=user, subcategory=subcategory)
            for subcategory in cls.model.objects.exclude(id__in=existing_subcategory_ids)
        ]
        cls.chart_config_model.objects.bulk_create(configs, ignore_conflicts=True)


class SubcategoryChartConfigService(BaseService):
    model = SubcategoryChartConfig

    @classmethod
    def get_all(cls, user=None):
        SubcategoryService.ensure_chart_configs_for_user(user)
        return super().get_all(user).select_related('subcategory', 'subcategory__category').order_by(
            'subcategory__category__description',
            'subcategory__description',
        )
