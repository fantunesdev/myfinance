from rest_framework import serializers

from statement.models import Subcategory
from statement.services.core.subcategory import SubcategoryService


class SubcategorySerializer(serializers.ModelSerializer):
    show_in_monthly_cashflow_donut = serializers.SerializerMethodField()
    show_in_annual_statement = serializers.SerializerMethodField()
    show_in_monthly_expense_category_bar = serializers.SerializerMethodField()
    show_in_annual_expense_category_bar = serializers.SerializerMethodField()
    show_in_monthly_expense_line = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        kwargs.pop('model', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Subcategory
        fields = (
            'id',
            'description',
            'category',
            'is_investment',
            'show_in_monthly_cashflow_donut',
            'show_in_annual_statement',
            'show_in_monthly_expense_category_bar',
            'show_in_annual_expense_category_bar',
            'show_in_monthly_expense_line',
        )

    def get_show_in_monthly_cashflow_donut(self, obj):
        return self._get_chart_config_value(obj, 'show_in_monthly_cashflow_donut')

    def get_show_in_annual_statement(self, obj):
        return self._get_chart_config_value(obj, 'show_in_annual_statement')

    def get_show_in_monthly_expense_category_bar(self, obj):
        return self._get_chart_config_value(obj, 'show_in_monthly_expense_category_bar')

    def get_show_in_annual_expense_category_bar(self, obj):
        return self._get_chart_config_value(obj, 'show_in_annual_expense_category_bar')

    def get_show_in_monthly_expense_line(self, obj):
        return self._get_chart_config_value(obj, 'show_in_monthly_expense_line')

    def _get_chart_config_value(self, obj, flag_name):
        values = self._get_chart_config_values(obj)
        return values[flag_name]

    def _get_chart_config_values(self, obj):
        config_cache = self.context.setdefault('subcategory_chart_config_cache', {})
        if obj.id not in config_cache:
            request = self.context.get('request')
            user = request.user if request else None
            config_cache[obj.id] = SubcategoryService.get_chart_config_values(user, obj.id)
        return config_cache[obj.id]
