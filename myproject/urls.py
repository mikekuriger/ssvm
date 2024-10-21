from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from myapp import views
from myapp.views import get_deployment_status

   
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.node_list, name='node_list'),
    path('nodes/', views.node_list, name='node_list'),
    path('nodes/<int:node_id>/', views.node_detail, name='node_detail'),
    path('create_vm/', views.create_vm, name='create_vm'),
    path('check_dns/', views.check_dns, name='check_dns'),
    path('deployments/', views.deployment_list, name='deployment_list'),
    path('deployments/<int:deployment_id>/', views.deployment_detail, name='deployment_detail'),
    path('api/register_node/', views.register_node, name='register_node'),
    path('approve_deployment/<int:deployment_id>/', views.approve_deployment, name='approve_deployment'),
    path('destroy_deployment/<int:deployment_id>/', views.destroy_deployment, name='destroy_deployment'),
    path('cancel_deployment/<int:deployment_id>/', views.cancel_deployment, name='cancel_deployment'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('deployment-status/<int:deployment_id>/', get_deployment_status, name='get_deployment_status'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
