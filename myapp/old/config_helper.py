# config_helper.py

# not used anymore, moved to forms.py

import yaml

# Load config from YAML file (for centrify and other stuff)
def load_config():
    with open('myapp/config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    return config

def get_config_for_datacenter(datacenter):
    config = load_config()  # Load the config file once

    # Retrieve datacenter-specific data
    datacenter_data = config.get('datacenters', {}).get(datacenter, {})
    
    # Retrieve Centrify zones
    centrify_zones = config.get('centrify_zones')

    return {
        'clusters': datacenter_data.get('clusters', {}).items(),
        'vlans': datacenter_data.get('vlans', {}).items(),
        'centrify_zones': centrify_zones
    }

