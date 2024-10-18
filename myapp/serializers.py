from rest_framework import serializers
from .models import HardwareProfile
from .models import Node
from .models import OperatingSystem

class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = '__all__' 
        
class OperatingSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatingSystem
        fields = '__all__'

class HardwareProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareProfile
        fields = '__all__'
