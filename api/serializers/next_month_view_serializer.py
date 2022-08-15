from rest_framework import serializers

from statement.models import NextMonthView


class NextMonthViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = NextMonthView
        fields = '__all__'
