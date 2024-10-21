# myapp/tasks.py
from background_task import background
from myapp.models import Deployment
#from myapp.views import destroy_deployment
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
import subprocess
import os, sys

sys.path.append("/home/ssvm/ssvm")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')


#@background(schedule=300)  # delay 5 minutes before running (first time)
# this task looks for 'queued' deployments and triggers the build script
@background
def check_queued_deployments():
    queued_deployments = Deployment.objects.filter(status='queued')
    #source_path = settings.MEDIA_ROOT
    base_path = settings.BASE_DIR
    python_executable = f"{base_path}/ssvm_env/bin/python"
    #python_executable = "python"
    


    # Loop through each deployment and run the deploy script
    for deployment in queued_deployments:
        deployment_name = deployment.deployment_name
        print(deployment_name)
        deploy_command = [python_executable, f"{base_path}/myapp/deploy.py", deployment_name]
        print(deploy_command)

        try:
            # Run the deploy script and wait for it to finish
            subprocess.run(deploy_command, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            
        except subprocess.CalledProcessError as e:
            print(f"Error deploying {deployment_name}: {e.stderr.decode('utf-8')}")

            
# # Background task to check and destroy 'destroying' deployments
# @background
# def check_destroying_deployments():
#     destroying_deployments = Deployment.objects.filter(status='destroying')

#     # Loop through each deployment and run the destroy logic
#     for deployment in destroying_deployments:
#         deployment_name = deployment.deployment_name
#         print(f"Attempting to destroy: {deployment_name}")

#         # Call the destroy function from the views logic
#         success, error = destroy_deployment_logic(deployment)

#         if success:
#             print(f"Deployment {deployment_name} destroyed successfully.")
#         else:
#             print(f"Error destroying {deployment_name}: {error}")

            
@background
def send_failure_alert():
    failed_deployments = Deployment.objects.filter(status='failed')
    
    if failed_deployments.exists():
        deployment_names = ", ".join([d.deployment_name for d in failed_deployments])
        subject = f"Approval Needed: SSVM Deployment {deployment_names}"
        message = f"The following deployments are waiting for approval: {deployment_names}"
        recipient_list = [admin[1] for admin in settings.ADMINS]  # Send to all admins
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        

@background
def send_approval_alert():
    # Get deployments waiting for approval, where no alert has been sent
    waiting_deployments = Deployment.objects.filter(status='needsapproval', approval_alert_sent=False)

    if waiting_deployments.exists():
        deployment_names = ", ".join([d.deployment_name for d in waiting_deployments])
        # Reverse URL to get the deployment list page
        deployment_url = f"{settings.SITE_URL}{reverse('deployment_list')}"

        # Craft the message with a link
        message = f"The following deployments are waiting for approval: {deployment_names}\n\n"
        message += f"Please review them here: {deployment_url}"

        subject = f"Approval Needed: SSVM Deployment {deployment_names}"
        recipient_list = [admin[1] for admin in settings.ADMINS]  # Send to all admins

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )

        # Update the deployments to indicate that an alert has been sent
        waiting_deployments.update(approval_alert_sent=True)
