from django.db import models
import uuid

# to make changes to the database, ie add a new field or change something
# python manage.py makemigrations
# python manage.py migrate


class Item(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    

    
class Deployment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)  # Now primary key
    builtby = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True) 
    deployment_date = models.CharField(max_length=255)
    deployment_name = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, default='corp.pvt')
    #full_hostnames = models.CharField(max_length=255)
    full_hostnames = models.TextField()
    ticket = models.CharField(max_length=50)
    decom_ticket = models.CharField(max_length=50, null=True, blank=True)
    decom_date = models.CharField(max_length=255, null=True, blank=True)
    appname = models.CharField(max_length=255)
    owner = models.CharField(max_length=255)             # used for deployment name - uid
    owner_value = models.CharField(max_length=255)       # used for display - first last (uid)
    datacenter = models.CharField(max_length=50)
    server_type = models.CharField(max_length=50)        # lnt
    server_type_value = models.CharField(max_length=50)  # Testing
    deployment_count = models.IntegerField()
    cpu = models.IntegerField()
    ram = models.IntegerField()
    os = models.CharField(max_length=50)                 # template name
    os_value = models.CharField(max_length=50)           # long name
    disk_size = models.IntegerField()
    add_disks = models.BooleanField()
    additional_disk_size = models.IntegerField(null=True, blank=True)
    mount_path = models.CharField(max_length=50, null=True, blank=True)
    cluster = models.CharField(max_length=50)
    network = models.CharField(max_length=50)
    nfs_home = models.BooleanField()
    join_centrify = models.BooleanField()
    centrify_zone = models.CharField(max_length=50, null=True, blank=True)
    centrify_role = models.CharField(max_length=50,null=True, blank=True)
    install_patches = models.BooleanField()
    status = models.CharField(max_length=20, default='needsapproval')  # for tracking status
    created_at = models.DateTimeField(auto_now_add=True)
    approval_alert_sent = models.BooleanField(default=False)
    protected = models.BooleanField(default=False)
    pid = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.deployment_name} - {self.status} - {self.full_hostnames}"
    
    
# added to build a basic node page, similar to OPSDB
class OperatingSystem(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    vendor = models.CharField(max_length=255, null=True, blank=True)
    variant = models.CharField(max_length=255, null=True, blank=True)
    version_number = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    architecture = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name}"

    
class Status(models.Model):
    name                    = models.CharField(max_length=255, null=True, blank=True)
    description             = models.TextField(null=True, blank=True)
    created_at              = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at              = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name}"


class HardwareProfile(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    manufacturer = models.CharField(max_length=255, null=True, blank=True)
    rack_size = models.IntegerField(null=True, blank=True)
    memory = models.CharField(max_length=255, null=True, blank=True)
    disk = models.CharField(max_length=255, null=True, blank=True)
    nics = models.IntegerField(null=True, blank=True)
    processor_model = models.CharField(max_length=255, null=True, blank=True)
    processor_speed = models.CharField(max_length=255, null=True, blank=True)
    processor_count = models.IntegerField(null=True, blank=True)
    cards = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    outlet_count = models.IntegerField(null=True, blank=True)
    estimated_cost = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    visualization_color = models.CharField(max_length=255, null=True, blank=True)
    outlet_type = models.CharField(max_length=255, null=True, blank=True)
    power_supply_count = models.IntegerField(null=True, blank=True)
    model = models.CharField(max_length=255, null=True, blank=True)
    processor_manufacturer = models.CharField(max_length=255, null=True, blank=True)
    processor_socket_count = models.IntegerField(null=True, blank=True)
    power_supply_slot_count = models.IntegerField(null=True, blank=True)
    power_consumption = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name}"

    
class Node(models.Model):
    name = models.CharField(max_length=255, unique=True, null=True, blank=True)
    serial_number = models.CharField(max_length=255, unique=True, null=True, blank=True)
    centrify_zone = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True) #deployment_date = date.strftime('%Y-%m-%dT%H:%M')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    hardware_profile = models.ForeignKey(HardwareProfile, on_delete=models.SET_NULL, null=True, blank=True)
    operating_system = models.ForeignKey(OperatingSystem, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True)
    processor_manufacturer = models.CharField(max_length=255, null=True, blank=True)
    processor_model = models.CharField(max_length=255, null=True, blank=True)
    processor_speed = models.CharField(max_length=255, null=True, blank=True)
    processor_socket_count = models.IntegerField(null=True, blank=True)
    processor_count = models.IntegerField(null=True, blank=True)
    physical_memory = models.CharField(max_length=255, null=True, blank=True)
    physical_memory_sizes = models.CharField(max_length=255, null=True, blank=True)
    os_memory = models.CharField(max_length=255, null=True, blank=True)
    swap = models.CharField(max_length=255, null=True, blank=True)
    power_supply_count = models.IntegerField(null=True, blank=True)
    console_type = models.CharField(max_length=255, null=True, blank=True)
    uniqueid = models.CharField(max_length=255, null=True, blank=True)
    kernel_version = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    processor_core_count = models.IntegerField(null=True, blank=True)
    os_processor_count = models.IntegerField(null=True, blank=True)
    asset_tag = models.CharField(max_length=255, null=True, blank=True)
    timezone = models.CharField(max_length=255, null=True, blank=True)
    expiration = models.DateField(null=True, blank=True)
    contact = models.TextField(null=True, blank=True)
    virtualarch = models.CharField(max_length=255, null=True, blank=True)
    disk_size = models.IntegerField(null=True, blank=True)
    vmimg_size = models.IntegerField(null=True, blank=True)
    vmspace_used = models.IntegerField(null=True, blank=True)
    used_space = models.IntegerField(null=True, blank=True)
    avail_space = models.IntegerField(null=True, blank=True)
    os_virtual_processor_count = models.IntegerField(null=True, blank=True)
    deployment = models.ForeignKey(Deployment, on_delete=models.CASCADE, related_name="nodes", null=True, blank=True)    # Link to the Deployment model
    dns_status = models.BooleanField(default=False)
    ping_status = models.BooleanField(default=False)
    last_checked = models.DateTimeField(null=True, blank=True)
    # config_mgmt_tag = models.CharField(max_length=255, null=True, blank=True)
    # cage = models.CharField(max_length=255, null=True, blank=True)
    # rack_row = models.CharField(max_length=255, null=True, blank=True)
    # rack_num = models.CharField(max_length=255, null=True, blank=True)
    # rack_unit = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.status}"

class VRA_Deployment(models.Model):
    #id = models.AutoField(primary_key=True)
    id = models.UUIDField(primary_key=True, editable=True) 
    #id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    builtby = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True) 
    deployment_date = models.CharField(max_length=255)
    deployment_name = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, default='corp.pvt')
    #full_hostnames = models.CharField(max_length=255)
    full_hostnames = models.TextField()
    ticket = models.CharField(max_length=50)
    decom_ticket = models.CharField(max_length=50, null=True, blank=True)
    decom_date = models.CharField(max_length=255, null=True, blank=True)
    appname = models.CharField(max_length=255)
    owner = models.CharField(max_length=255)             
    owner_value = models.CharField(max_length=255)
    datacenter = models.CharField(max_length=50)
    server_type = models.CharField(max_length=50)
    server_type_value = models.CharField(max_length=50)
    deployment_count = models.IntegerField()
    cpu = models.IntegerField()
    ram = models.IntegerField()
    os = models.CharField(max_length=50)                
    os_value = models.CharField(max_length=50)           
    disk_size = models.IntegerField()
    add_disks = models.BooleanField()
    additional_disk_size = models.IntegerField(null=True, blank=True)
    mount_path = models.CharField(max_length=50, null=True, blank=True)
    cluster = models.CharField(max_length=50)
    network = models.CharField(max_length=50)
    nfs_home = models.BooleanField()
    join_centrify = models.BooleanField()
    centrify_zone = models.CharField(max_length=50, null=True, blank=True)
    centrify_role = models.CharField(max_length=50,null=True, blank=True)
    install_patches = models.BooleanField()
    status = models.CharField(max_length=20, default='needsapproval')
    created_at = models.DateTimeField(auto_now_add=True)
    approval_alert_sent = models.BooleanField(default=False)
    protected = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.deployment_name} - {self.status}"
    
    class Meta:
        managed = True

class VRA_Node(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    serial_number = models.CharField(max_length=255, null=True, blank=True)
    centrify_zone = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    hardware_profile = models.ForeignKey(HardwareProfile, on_delete=models.SET_NULL, null=True, blank=True)
    operating_system = models.ForeignKey(OperatingSystem, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.ForeignKey(Status, on_delete=models.SET_NULL, null=True, blank=True)
    processor_manufacturer = models.CharField(max_length=255, null=True, blank=True)
    processor_model = models.CharField(max_length=255, null=True, blank=True)
    processor_speed = models.CharField(max_length=255, null=True, blank=True)
    processor_socket_count = models.IntegerField(null=True, blank=True)
    processor_count = models.IntegerField(null=True, blank=True)
    physical_memory = models.CharField(max_length=255, null=True, blank=True)
    physical_memory_sizes = models.CharField(max_length=255, null=True, blank=True)
    os_memory = models.CharField(max_length=255, null=True, blank=True)
    swap = models.CharField(max_length=255, null=True, blank=True)
    power_supply_count = models.IntegerField(null=True, blank=True)
    console_type = models.CharField(max_length=255, null=True, blank=True)
    uniqueid = models.CharField(max_length=255, null=True, blank=True)
    kernel_version = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    processor_core_count = models.IntegerField(null=True, blank=True)
    os_processor_count = models.IntegerField(null=True, blank=True)
    asset_tag = models.CharField(max_length=255, null=True, blank=True)
    timezone = models.CharField(max_length=255, null=True, blank=True)
    expiration = models.DateField(null=True, blank=True)
    contact = models.TextField(null=True, blank=True)
    virtualarch = models.CharField(max_length=255, null=True, blank=True)
    disk_size = models.IntegerField(null=True, blank=True)
    vmimg_size = models.IntegerField(null=True, blank=True)
    vmspace_used = models.IntegerField(null=True, blank=True)
    used_space = models.IntegerField(null=True, blank=True)
    avail_space = models.IntegerField(null=True, blank=True)
    os_virtual_processor_count = models.IntegerField(null=True, blank=True)
    # Link to the Deployment model
    deployment = models.ForeignKey(VRA_Deployment, on_delete=models.CASCADE, related_name="vranodes", null=True, blank=True)
    dns_status = models.BooleanField(default=False)
    ping_status = models.BooleanField(default=False)
    last_checked = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.status}"
