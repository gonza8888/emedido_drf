from rest_framework import serializers
from .models import Zone
from back_emedido.apps.zone_details.serializer import ZoneDetailsSerializer


class ZoneSerializer(serializers.ModelSerializer):
    zonedetails = ZoneDetailsSerializer(many=True,read_only=True)
    class Meta:
        model = Zone
        fields = ('code','id','name','zonedetails')

class ZoneSerializerApp(serializers.ModelSerializer):
    class Meta:
        model = Zone
        exclude = ('zone',)
