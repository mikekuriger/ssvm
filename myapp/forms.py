import csv
from django import forms
from django.core.exceptions import ValidationError
import re
import yaml
from .config_helper import load_config

# 9-16-24 Mike Kuriger

# functions to read details from config file (moved to helper file so I can read it in views.py also
# def load_config():
#     with open('myapp/config.yaml', 'r') as file:
#         config = yaml.safe_load(file)
#     return config

def get_config_for_datacenter(datacenter):
        config = load_config()  # Load the config file once

        # Retrieve datacenter-specific data
        datacenter_data = config.get('datacenters', {}).get(datacenter, {})
        
        return {
            'clusters': datacenter_data.get('clusters', {}).items(),
            'vlans': datacenter_data.get('vlans', {}).items(),
            'domains': datacenter_data.get('domains', {}).items(),
        }

def load_dc():
    config = load_config()
    dc = config.get('datacenters', {})
    return [(dc, dc) for dc in dc.keys()]

def load_oss():
    config = load_config()
    os = config.get('oss', {})
    return [(key, value) for key, value in os.items()]

def load_servertypes():
    config = load_config()
    server_types = config.get('server_types', {})
    return [(key, value) for key, value in server_types.items()]

def load_centrify_zones():
    config = load_config()
    zones = config.get('centrify_zones', {})
    return [(zone, zone) for zone in zones.keys()]

# function to load users from CSV file
def load_users_from_csv(filepath='myapp/data/users2.csv'):
    users = []
    with open(filepath, mode='r') as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            username, full_name = row
            display_value = f"{full_name} ({username})"
            users.append((username, display_value))
    return users

# validator functions to prevent spaces and special characters
def validate_no_spaces_or_special_characters(value):
    if not re.match(r'^[A-Za-z0-9_-]+$', value):  
        raise ValidationError('Only letters, numbers, hyphens, and underscores are allowed.')
    if re.search(r'\s', value):
        raise ValidationError('Spaces are not allowed.')
        
class VMCreationForm(forms.Form):
    
    ticket = forms.CharField(
        label="Ticket #",
        min_length=6,
        max_length=11,
        required=True,
        initial='TSM-00000',
        widget=forms.TextInput(attrs={'id': 'ticket', 'class': 'form-control'})
    )

    appname = forms.CharField(
        label="App",
        required=True,
        widget=forms.TextInput(attrs={'id': 'appname', 'class': 'form-control', 'placeholder': 'My App'})
    )
    
    description = forms.CharField(
        label="Description",
        required=False,
        widget=forms.TextInput(attrs={'id': 'description', 'class': 'form-control', 'placeholder': 'Description'})
    )
    
    domain = forms.ChoiceField(
        label="Domain",
        choices=[],
        initial='corp.pvt',
        required=False,
        #widget=forms.Select(attrs={'id': 'domain', 'class': 'form-control', 'disabled': 'disabled'})
        widget=forms.Select(attrs={'id': 'domain', 'class': 'form-control'})
    )

    owner = forms.ChoiceField(
        label="Owner",
        #choices=load_users_from_csv(),
        choices=[('', '--- Select Owner ---')] + load_users_from_csv(),
        widget=forms.Select(attrs={'id': 'owner', 'class': 'form-control'}),
        required=True
    )

    datacenter = forms.ChoiceField(
        label="Datacenter",
        choices=load_dc(),
        required=True,
        widget=forms.Select(attrs={'id': 'datacenter', 'class': 'form-control'})
    )

    server_type = forms.ChoiceField(
        label="Type",
        choices=load_servertypes(),
        initial='lnt',
        required=True,
        widget=forms.Select(attrs={'id': 'server_type', 'class': 'form-control'})
    )

    deployment_count = forms.ChoiceField(
        label="Count",
        choices=[(str(i), str(i)) for i in range(1, 11)],
        initial='1',
        required=True,
        widget=forms.Select(attrs={'id': 'deployment_count', 'class': 'form-control'})
    )

    hostname = forms.CharField(
        label="Hostname",
        max_length=8,
        min_length=3,
        required=True,
        validators=[validate_no_spaces_or_special_characters],
        widget=forms.TextInput(attrs={'id': 'hostname', 'class': 'form-control', 'placeholder': 'example'})
    )

    cpu = forms.ChoiceField(
        label="CPUs",
        choices=[(str(i), str(i)) for i in [2, 4, 8, 12, 16, 20, 24, 32, 48, 64]],
        initial='2',
        required=True,
        widget=forms.Select(attrs={'id': 'cpu', 'class': 'form-control'})
    )

    ram = forms.ChoiceField(
        label="RAM (GB)",
        choices=[(str(i), str(i)) for i in [2, 4, 8, 12, 16, 20, 24, 32, 48, 64]],
        initial='2',
        required=True,
        widget=forms.Select(attrs={'id': 'ram', 'class': 'form-control'})
    )

    os = forms.ChoiceField(
        label="Linux Version",
        choices=load_oss(),
        initial='SSVM-OEL8',
        required=True,
        widget=forms.Select(attrs={'id': 'os', 'class': 'form-control'})
    )

    disk_size = forms.ChoiceField(
        label="Disk (GB)",
        choices=[(str(i), str(i)) for i in [80, 100, 150, 200, 250, 512, 1024]],
        initial='60',
        required=True,
        widget=forms.Select(attrs={'id': 'disk_size', 'class': 'form-control'})
    )

    cluster = forms.ChoiceField(
        label="Cluster",
        choices=[],
        required=True,
        widget=forms.Select(attrs={'id': 'cluster', 'class': 'form-control'})
    )

    network = forms.ChoiceField(
        label="Network",
        choices=[],
        required=True,
        widget=forms.Select(attrs={'id': 'network', 'class': 'form-control'})
    )

    nfs_home = forms.BooleanField(
        label="NFS Home",
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'nfs_home', 'class': 'form-check-input'})
    )

    add_disks = forms.BooleanField(
        label="2nd Disk",
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'add_disks', 'class': 'form-check-input'})
    )

    additional_disk_size = forms.IntegerField(
        label="2nd Disk (GB)",
        required=False,
        widget=forms.TextInput(attrs={'id': 'additional_disk_size', 'class': 'form-control'})
    )

    mount_path = forms.CharField(
        label="Mount point",
        required=False,
        widget=forms.TextInput(attrs={'id': 'mount_path', 'class': 'form-control'})
    )

    join_centrify = forms.BooleanField(
        label="Centrify",
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'join_centrify', 'class': 'form-check-input'})
    )

    centrify_zone = forms.ChoiceField(
        label="Centrify Zone",
        #choices=load_centrify_zones(),
        choices=[('', '--- Select Zone ---')] + load_centrify_zones(),
        required=False,
        widget=forms.Select(attrs={'id': 'centrify_zone', 'class': 'form-control'})
    )
    
    centrify_role = forms.CharField(
        label="Centrify Role",
        required=False,
        widget=forms.Select(attrs={'id': 'centrify_role', 'class': 'form-control'})
    )

    install_patches = forms.BooleanField(
        label="Install Patches",
        required=False,
        widget=forms.CheckboxInput(attrs={'id': 'install_patches', 'class': 'form-check-input'})
    )
    
    full_hostnames = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'full_hostnames'})
    )

    def clean_centrify_role(self):
        centrify_role = self.cleaned_data.get('centrify_role')
        # Simply return the value without validating it against the form's choices
        return centrify_role
    
    def __init__(self, *args, **kwargs):
        # Pop the datacenter value from kwargs
        datacenter = kwargs.pop('datacenter', None)
        super().__init__(*args, **kwargs)  # Call parent's __init__
        
        if datacenter:
            config_data = get_config_for_datacenter(datacenter)

            if config_data:
                self.fields['cluster'].choices = config_data['clusters']
                self.fields['network'].choices = config_data['vlans']
                self.fields['domain'].choices = config_data['domains']