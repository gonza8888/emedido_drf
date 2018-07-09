from rest_framework import serializers
from .models import EndUser


class EndUserSerializer(serializers.ModelSerializer):
    # Fields coming from properties
    # If field name is same as source, do not put it in parameter, if done :error
    #count_patents = serializers.Field(source='count_patents')
    count_patents = serializers.ReadOnlyField()
    count_recharges = serializers.ReadOnlyField()
    count_faults = serializers.ReadOnlyField()
    class Meta:
        model = EndUser
        exclude = ('created', 'last_modified', 'locked', 'locked_reason','init_tries')
        
class EndUserSerializerShort(serializers.ModelSerializer):
    class Meta:
        model = EndUser
        fields = ('phone',)

class EndUserSerializerAll(serializers.ModelSerializer):
    class Meta:
        model = EndUser
        fields = '__all__'
