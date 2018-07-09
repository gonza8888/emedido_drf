from rest_framework import serializers
from .models import Parking
from back_emedido.apps.block.serializer import BlockSerializer

class ParkingSerializer(serializers.ModelSerializer):
    block=BlockSerializer()
    remaining_time = serializers.ReadOnlyField()
    date_end = serializers.ReadOnlyField()
    class Meta:
        model = Parking
        fields = '__all__'

class ParkingSerializer2(serializers.ModelSerializer):
    remaining_time = serializers.ReadOnlyField()
    date_end = serializers.ReadOnlyField()
    class Meta:
        model = Parking
        fields = ('patent','remaining_time','date_start','date_end','duration')

class ParkingSerializerShort(serializers.ModelSerializer):
    class Meta:
        model = Parking
        fields = ('patent','date_start','duration')
