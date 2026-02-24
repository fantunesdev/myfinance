from django.urls import path
from django.contrib.auth.decorators import user_passes_test

from statement.views.core.notification import NotificationView

notification_view = NotificationView()

# Decorator that allows only staff users
staff_required = user_passes_test(lambda u: u.is_staff)

urlpatterns = [
    path('cadastrar/', staff_required(notification_view.create), name='create_notification'),
    path('editar/<int:id>/', staff_required(notification_view.update), name='update_notification'),
    path('remover/<int:id>/', staff_required(notification_view.delete), name='delete_notification'),
    # allow non-staff users to view their own notifications; the view will filter by user
    path('todas/', notification_view.get_all, name='get_all_notification'),
    path('detalhe/<int:id>/', staff_required(notification_view.detail), name='detail_notification'),
]
