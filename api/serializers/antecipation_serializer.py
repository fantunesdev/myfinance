from rest_framework import serializers

from balanco.models import Antecipation


class AntecipationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Antecipation
        fields = '__all__'
