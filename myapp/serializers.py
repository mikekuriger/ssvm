from rest_framework import serializers
from .models import HardwareProfile
from .models import Node
from .models import OperatingSystem
from .models import Status

# class NodeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Node
#         fields = '__all__' 
        
# class OperatingSystemSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OperatingSystem
#         fields = '__all__'

# class HardwareProfileSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = HardwareProfile
#         fields = '__all__'


class NodeSerializer(serializers.ModelSerializer):
    operating_system = serializers.SlugRelatedField(
        queryset=OperatingSystem.objects.all(),
        slug_field='id'
    )
    hardware_profile = serializers.SlugRelatedField(
        queryset=HardwareProfile.objects.all(),
        slug_field='id'
    )

    def validate(self, attrs):
        serial_number = attrs.get('serial_number')
        name = attrs.get('name')

        # Check if the node already exists
        node = Node.objects.filter(serial_number=serial_number).first()
        if node and self.instance is None:
            # Pass existing node instance to update logic
            self.instance = node

        return attrs

    def create(self, validated_data):
        status_instance, _ = Status.objects.get_or_create(
            name='setup',
            defaults={'description': 'Node is not in production'}
        )
        validated_data['status'] = status_instance
        return super().create(validated_data)

    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

    class Meta:
        model = Node
        fields = [
            'name', 'serial_number', 'processor_manufacturer', 'processor_model', 
            'processor_speed', 'processor_socket_count', 'processor_core_count', 
            'processor_count', 'physical_memory', 'physical_memory_sizes', 'swap', 
            'uniqueid', 'kernel_version', 'timezone', 'used_space', 'avail_space', 
            'centrify_zone', 'created_at', 'operating_system', 'hardware_profile',
            'disk_size', 'ping_status', 'disk_usage_percent', 'contact'
        ]
