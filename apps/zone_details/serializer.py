from rest_framework import serializers
from .models import ZoneDetails


class ZoneDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneDetails
        fields = '__all__'
