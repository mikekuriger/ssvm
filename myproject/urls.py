from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from myapp import views
from myapp.views import get_deployment_status

   
urlpatterns = [
    path('', views.node_list, name='node_list'),
    path('admin/', admin.site.urls),
    path('api/register_node/', views.register_node, name='register_node'),
    path('api/node_status/<int:node_id>/', views.get_node_status, name='get_node_status'),
    #path('api/deployment_status/<int:deployment_id>/', views.get_deployment_status, name='get_deployment_status'),
    path('approve_deployment/<uuid:deployment_id>/', views.approve_deployment, name='approve_deployment'),
    path('cancel_deployment/<uuid:deployment_id>/', views.cancel_deployment, name='cancel_deployment'),
    path('cancel_screamtest/<uuid:deployment_id>/', views.cancel_screamtest, name='cancel_screamtest'),
    path('check_dns/', views.check_dns, name='check_dns'),
    path('create_vm/', views.create_vm, name='create_vm'),
    path('deployments/', views.deployment_list, name='deployment_list'),
    path('deployments/<uuid:deployment_id>/', views.deployment_detail, name='deployment_detail'),
    path('deployment-status/<uuid:deployment_id>/', get_deployment_status, name='get_deployment_status'),
    path('destroy_deployment/<uuid:deployment_id>/', views.destroy_deployment, name='destroy_deployment'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/login/', LoginView.as_view(template_name='login.html'), name='accounts_login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('logs/<str:node_name>/', views.tail_log, name='tail_log'),
    path('nodes/', views.node_list, name='node_list'),
    #path('nodes/<int:node_id>/', views.node_detail, name='node_detail'),
    path('nodes/<str:model_type>/<int:node_id>/', views.node_detail, name='node_detail'),
    path('nodes/<int:node_id>/view-log/', views.view_log, name='view_log'),
    path('screamtest_deployment/<uuid:deployment_id>/', views.screamtest_deployment, name='screamtest_deployment'),
    #path('system-logs/<str:log_type>/', views.view_system_logs, name='view_system_logs'),
    path('deployment-log/', views.view_deployment_log, name='view_deployment_log'),
    path('tail_deployment_log/', views.tail_deployment_log, name='tail_deployment_log'),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
