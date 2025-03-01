from api.services.websocket_services import send_websocket_update
from statement.models import NextMonthView


def create_next_month_view(next_month_view):
    new_next_month_view = NextMonthView.objects.create(
        day=next_month_view.day,
        active=next_month_view.active,
        user=next_month_view.user,
    )

    # Enviando a atualização para o frontend pelo WebSocket
    next_month_view = get_next_month_view_by_user(next_month_view.user)
    send_websocket_update('next_month_view', next_month_view)
    return new_next_month_view


def get_next_month_view_by_user(user):
    return NextMonthView.objects.get(user=user)


def update_next_month_view(old_next_month_view, new_next_month_view):
    old_next_month_view.day = new_next_month_view.day
    old_next_month_view.active = new_next_month_view.active
    old_next_month_view.user = new_next_month_view.user
    old_next_month_view.save(force_update=True)

    # Enviando a atualização da lista de categorias para o frontend pelo WebSocket
    next_month_view = get_next_month_view_by_user(old_next_month_view.user)
    send_websocket_update('next_month_view', next_month_view)
