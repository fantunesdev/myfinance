from django.urls import path

from statement.views.core.subcategory_chart_config import SubcategoryChartConfigView

subcategory_chart_config_view = SubcategoryChartConfigView()

urlpatterns = [
    path('', subcategory_chart_config_view.get_all, name='get_all_subcategory_chart_config'),
    path('editar/<int:id>/', subcategory_chart_config_view.update, name='update_subcategory_chart_config'),
]
