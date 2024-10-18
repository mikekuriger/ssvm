# this is needed so I can avoid duplicating this code in forms.yp and views.py
import yaml
from django.conf import settings

CONFIG_FILE = settings.BASE_DIR / "myapp" / "config.yaml"

def load_config():
    with open(CONFIG_FILE, 'r') as file:
        config = yaml.safe_load(file)
    return config