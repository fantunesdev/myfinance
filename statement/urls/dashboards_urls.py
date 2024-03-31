from django.urls import path

from statement.views.dashboards_views import *

urlpatterns = [
    path('', show_dashboard, name='show_dashboard'),
]
