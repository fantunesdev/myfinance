from django.urls import path

from statement.views.next_month_view import NextMonthViewView

next_month_view = NextMonthViewView()

urlpatterns = [path('editar/', next_month_view.update, name='update_next_month_view')]
