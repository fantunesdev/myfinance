from django.urls import path

from statement.views.dashboards import DashboardView

dashboard_view = DashboardView()

urlpatterns = [
    path('', dashboard_view.show_dashboard, name='show_dashboard'),
]
