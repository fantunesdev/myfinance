from django.urls import path

from statement.views.next_month_view_view import *

urlpatterns = [
    path('editar/', update_next_month_view, name='update_next_month_view')
]
