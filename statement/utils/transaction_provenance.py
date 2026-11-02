from django.core.exceptions import ValidationError

from statement.utils.transaction_input import parse_notification


def validate_notification_source(instance, user):
    instance.event_type = instance.event_type or "unknown"
    notification = instance.source_notification
    if not notification:
        return
    owner = notification.user_id
    if owner is None and notification.card_id:
        owner = notification.card.user_id
    if not user or owner != user.pk:
        raise ValidationError("A notificação de origem não pertence ao usuário.")
    instance.source_type = "notification"
    instance.source_app = notification.app
    instance.original_description = notification.message
    if not instance.merchant_description:
        instance.merchant_description = parse_notification(notification)["merchant_description"]
