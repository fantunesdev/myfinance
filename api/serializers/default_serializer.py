from rest_framework import serializers

class DefaultsSerializer(serializers.Serializer):
    version = serializers.CharField()
    year = serializers.IntegerField()