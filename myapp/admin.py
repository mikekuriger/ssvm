from django.contrib import admin
from .models import VRA_Deployment
from .models import VRA_Node
from .models import Deployment
from .models import VRA_Deployment
from .models import Node
from .models import VRA_Node
from .models import OperatingSystem
from .models import HardwareProfile
from .models import Status


admin.site.register(Deployment)
admin.site.register(VRA_Deployment)
admin.site.register(Node)
admin.site.register(VRA_Node)
admin.site.register(OperatingSystem)
admin.site.register(HardwareProfile)
admin.site.register(Status)

