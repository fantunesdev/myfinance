from django.urls import path
from statement.views.next_month_view import edit_next_month_view

urlpatterns = [path('editar/', edit_next_month_view, name='update_next_month_view')]
