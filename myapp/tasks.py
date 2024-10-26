# myapp/tasks.py
from background_task import background
from myapp.models import Deployment
from myapp.views import destroy_deployment_logic
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
import subprocess
import os, sys
import logging

logger = logging.getLogger('frequent_tasks')

sys.path.append("/home/ssvm/ssvm")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')


#@background(schedule=300)  # delay 5 minutes before running (first time)
# this task looks for 'queued' deployments and triggers the build script
# @background
# def check_queued_deployments():
#     queued_deployments = Deployment.objects.filter(status='queued')
#     #source_path = settings.MEDIA_ROOT
#     base_path = settings.BASE_DIR
#     python_executable = f"{base_path}/ssvm_env/bin/python"
#     #python_executable = "python"
    
#     # Loop through each deployment and run the deploy script
#     for deployment in queued_deployments:
#         deployment_name = deployment.deployment_name
#         print(deployment_name)
#         deploy_command = [python_executable, f"{base_path}/myapp/deploy.py", deployment_name]
#         print(deploy_command)

#         try:
#             # Run the deploy script and wait for it to finish
#             subprocess.run(deploy_command, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            
#         except subprocess.CalledProcessError as e:
#             print(f"Error deploying {deployment_name}: {e.stderr.decode('utf-8')}")



# this task looks for 'queued' deployments and triggers the build script
@background
def check_queued_deployments():
    queued_deployments = Deployment.objects.filter(status='queued')
    
    for deployment in queued_deployments:
        deployment_name = deployment.deployment_name
        print(f"Dispatching deploy task for {deployment_name}")
        
        # Schedule deploy_task for each deployment individually
        deploy_task(deployment_name)
        
        # Optionally update deployment status to "processing"
        # deployment.status = 'building'
        # deployment.save(update_fields=['status'])

        

# this is called from the check_queued_deployments function, to allow multiple deployments to run
@background
def deploy_task(deployment_name):
    base_path = settings.BASE_DIR
    python_executable = os.path.join(base_path, "ssvm_env", "bin", "python")
    deploy_command = [python_executable, os.path.join(base_path, "myapp", "deploy.py"), deployment_name]
    
    try:
        # Run the deploy script as a separate process
        result = subprocess.run(deploy_command, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        print(f"Deployment {deployment_name} completed successfully: {result.stdout.decode('utf-8')}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error deploying {deployment_name}: {e.stderr.decode('utf-8')}")
        
            
# Background task to check and destroy deployments stuck in "queued for destruction"
@background
def check_destroy_deployments():
    destroying_deployments = Deployment.objects.filter(status='queued_for_destroy')

    print(f"Found {destroying_deployments.count()} deployments queued for destruction.")
    logger.info(f"Found {destroying_deployments.count()} deployments queued for destruction.")
        
    # Loop through each deployment and run the destroy logic
    for deployment in destroying_deployments:
        deployment_name = deployment.deployment_name
        deployment_id = deployment.id
        print(f"Attempting to destroy deployment: {deployment_name} with ID: {deployment_id}")
        logger.info(f"Attempting to destroy Deployment: {deployment_name} with ID: {deployment_id}")

        # Call the destroy function from the views logic
        success, error = destroy_deployment_logic(deployment_id)

        if success:
            print(f"Deployment {deployment_name} destroyed successfully.")
            logger.info(f"Deployment {deployment_name} destroyed successfully.")
        else:
            print(f"Error destroying {deployment_name}: {error}")
            logger.error(f"Error destroying {deployment_name}: {error}")

            
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
