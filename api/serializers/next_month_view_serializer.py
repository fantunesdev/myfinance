from rest_framework import serializers


class NextMonthViewSerializer(serializers.Serializer):
    """Serializador simples que expõe `day` e `active` (do `Profile`)."""

    day = serializers.IntegerField(allow_null=True)
    active = serializers.BooleanField()

    def to_representation(self, instance):
        if instance is None:
            return {'day': None, 'active': False}

        return {
            'day': getattr(instance, 'day', None),
            'active': getattr(instance, 'active', False),
        }
