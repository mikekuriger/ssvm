import subprocess
import socket
import json
import logging
from myapp.config_helper import load_config
from SOLIDserverRest import SOLIDserverRest
from django.contrib import messages
from django.shortcuts import get_object_or_404
from myapp.models import Deployment, Node, HardwareProfile, OperatingSystem, Status
import os as _os
import subprocess
from django.contrib.auth import get_user_model


logger = logging.getLogger('deployment')
loggerdestroy = logging.getLogger('destroy')


# get emails of admins, plan to use for sending emails 
def get_admin_emails():
    User = get_user_model()
    admins = User.objects.filter(is_active=True).filter(is_staff=True) | User.objects.filter(is_superuser=True)
    return [admin.email for admin in admins if admin.email]


# Remove VM from vcenter
def destroy_vm(node, deployment):
    datacenter_name = deployment.datacenter
    config = load_config()
    datacenter = config['datacenters'].get(datacenter_name)
    vcenter = datacenter['vcenter']
    username = datacenter['credentials']['username']
    password = datacenter['credentials']['password']
    loggerdestroy = logging.getLogger('destroy')

    # Log the vCenter credentials being used
    loggerdestroy.info(f"Using vCenter {vcenter} to destroy VM {node.name} with UUID {node.serial_number}")

    # Set environment variables for govc
    _os.environ["GOVC_URL"] = f"https://{vcenter}"
    _os.environ["GOVC_USERNAME"] = username
    _os.environ["GOVC_PASSWORD"] = password
    
    loggerdestroy.info(f"Testing vCenter {vcenter}")
    
    govc_command = ["govc", "about"]
    result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode != 0 or "503 Service Unavailable" in result.stderr:
        loggerdestroy.error(f"vCenter {vcenter} is not responding (503 error), setting deployment back to 'deployed'.")
        deployment.status = 'deployed'  
        deployment.save(update_fields=['status'])
        return False
    
    else:
        loggerdestroy.info(f"vCenter {vcenter} is responding successfully.")

        vm_uuid = node.serial_number
        vm_short_name = node.name.split('.')[0]
        vm_fqdn = node.name
        
        if "yellowpages" in vm_fqdn:
            vm_name = vm_fqdn
        else:
            vm_name = vm_short_name

        if vm_uuid is not None:
            destroy_vm_command = ["govc", "vm.destroy", "-vm.uuid", vm_uuid]
            loggerdestroy.info(f"Attempting to destroy VM: {vm_name} by UUID {vm_uuid}")
        else:
            destroy_vm_command = ["govc", "vm.destroy", vm_name]
            loggerdestroy.info(f"Attempting to destroy VM: {vm_name}")

        result = subprocess.run(destroy_vm_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        if result.returncode == 0:
            # If the command succeeded, the VM was destroyed
            loggerdestroy.info(f"VM {vm_name} successfully destroyed from vCenter.")
            node.status = Status.objects.get(name='destroyed')
            node.save(update_fields=['status'])
            return True  

        elif 'no such' in result.stderr.lower() or 'not found' in result.stderr.lower():
            loggerdestroy.info(f"VM {vm_name} not found in vCenter.")
            node.status = Status.objects.get(name='destroyed')
            node.save(update_fields=['status'])
            return False # this is OK, it was likely already deleted

        else:
            # If there was any other error, log it and exit with an error
            loggerdestroy.error(f"Error executing govc vm.destroy command for VM {vm_name}: {result.stderr}")
            deployment.status = 'error'
            deployment.save(update_fields=['status'])
            node.status = Status.objects.get(name='error')
            node.save(update_fields=['status'])
            return 'Error'  # Exit if there was any unexpected error
    

    
# Remove node from DNS
def remove_dns_entry(node, deployment):
    datacenter_name = deployment.datacenter
    config = load_config()
    datacenter = config['datacenters'].get(datacenter_name)
    vcenter = datacenter['vcenter']
    username = datacenter['credentials']['username']
    password = datacenter['credentials']['password']
    
    sds_conn = SOLIDserverRest(datacenter['eipmaster'])
    sds_conn.set_ssl_verify(False)
    sds_conn.use_basicauth_sds(user=datacenter['eip_credentials']['username'], password=datacenter['eip_credentials']['password'])

    dns_name = node.name.split('.')[0]
    dns_zone = deployment.domain or 'corp.pvt'
    parameters = {"WHERE": f"name='{dns_name}.{dns_zone}'"}
    loggerdestroy = logging.getLogger('destroy')
    
    loggerdestroy.info(f"Attempting to fetch DNS entry for {dns_name}.{dns_zone}")
    response = sds_conn.query("ip_address_list", parameters)

    if response.status_code == 200:
        ip_list = json.loads(response.content)
        if ip_list:
            ip_id = ip_list[0].get('ip_id')
            delete_response = sds_conn.query("ip_address_delete", {"ip_id": ip_id})
            if delete_response.status_code == 200:
                loggerdestroy.info(f"DNS entry {dns_name}.{dns_zone} deleted.")
                return True
            else:
                loggerdestroy.error(f"Error deleting DNS entry {dns_name}.{dns_zone}: {delete_response.content.decode()}")
                return 'Error'
    else:
        #loggerdestroy.info(f"{dns_name}.{dns_zone} was not found in DNS: {response.content.decode()}")
        return False



# screamtest VM
def screamtest_vm(node, deployment, decom_ticket, decom_date):
    datacenter_name = deployment.datacenter
    config = load_config()
    datacenter = config['datacenters'].get(datacenter_name)
    vcenter = datacenter['vcenter']
    username = datacenter['credentials']['username']
    password = datacenter['credentials']['password']
    logger = logging.getLogger('deployment')

    # Log the vCenter credentials being used
    logger.info(f"Using vCenter {vcenter} to poweroff and rename {node.name}")

    # Set environment variables for govc
    _os.environ["GOVC_URL"] = f"https://{vcenter}"
    _os.environ["GOVC_USERNAME"] = username
    _os.environ["GOVC_PASSWORD"] = password
    
    # make sure vcenter is responding
    logger.info(f"Testing vCenter {vcenter}")
    govc_command = ["govc", "about"]
    result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode != 0 or "503 Service Unavailable" in result.stderr:
        logger.error(f"vCenter {vcenter} is not responding (503 error), setting deployment back to 'deployed'.")
        deployment.status = 'deployed'  
        deployment.save(update_fields=['status'])
        return False
    
    else:
        logger.info(f"vCenter {vcenter} is responding successfully.")
        
        # Proceed with VM naming
        vm_short_name = node.name.split('.')[0]
        vm_fqdn = node.name
        vm_uuid = node.serial_number  # Get UUID from serial_number
        
        if "yellowpages" in vm_fqdn:
            vm_name = vm_fqdn
        else:
            vm_name = vm_short_name
            
        # Construct new VM name for screamtest
        newname = f"{vm_name}-Screamtest_{decom_ticket}_{decom_date}"
        
        # Check if VM exists in vCenter
        if vm_uuid is not None and vm_uuid != '':
            govc_command = ["govc", "vm.info", "-vm.uuid", vm_uuid]
            power_off_command = ["govc", "vm.power", "-off", "-force", "-vm.uuid", vm_uuid]
            power_status_command = ["govc", "vm.info", "-vm.uuid", vm_uuid]
            rename_command = ["govc", "vm.change", "-vm.uuid", vm_uuid, "-name", newname]
            logger.info(f"using UUID {vm_uuid}")
        else:
            govc_command = ["govc", "vm.info", vm_name]
            power_off_command = ["govc", "vm.power", "-off", "-force", vm_name]
            power_status_command = ["govc", "vm.info", vm_name]
            rename_command = ["govc", "vm.change", "-vm", vm_name, "-name", newname]
            logger.info(f"using NAME {vm_name}")
            
        result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        if result.returncode == 0:
            # Power off the VM
            subprocess.run(power_off_command, check=True)
            
            # Confirm powered off status
            power_status = subprocess.run(power_status_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)

            if "poweredOff" in power_status.stdout:
                logger.info(f"{vm_name} has been powered off")

                # Rename VM to {vm_name}-Screamtest_{ticket}_{date}
                rename_result = subprocess.run(rename_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
 
                if rename_result.returncode == 0:
                    logger.info(f"Renamed {vm_name} to {newname}")
                    return True

                else:
                    logger.error(f"Failed to rename {vm_name}. Error: {rename_result.stderr}")
                    return False

            else:
                logger.error(f"Failed to power off {vm_name}. Error: {power_status.stderr}")
                return False
            
        else:
            logger.error(f"VM {vm_name} not found in vCenter")
            return False
        

        
# destroy deployment     
def destroy_deployment_logic(deployment_id):
    deployment = get_object_or_404(Deployment, id=deployment_id)
    if deployment.status == 'queued_for_destroy':
        deployment.status = 'destroying'
        deployment.save()
        loggerdestroy.info(f"Deployment {deployment.deployment_name} is now in 'destroying' status.")
        print(f"Deployment {deployment.deployment_name} is now in 'destroying' status.")
        
        nodes_in_deployment = Node.objects.filter(deployment=deployment)
        vm_destroyed, dns_removed = True, True  # Initialize variables for logging

        for node in nodes_in_deployment:

            # Step 1: Destroy VMs in the deployment
            vm_destroyed = destroy_vm(node, deployment)
            if vm_destroyed == True:
                loggerdestroy.info(f"VM {node.name} destroyed from vCenter.")
                
            elif vm_destroyed == False:  
                loggerdestroy.info(f"VM {node.name} not in Vcenter, skipping VM delete operation")
                vm_destroyed = True # all is good
                
            elif vm_destroyed == 'Error':  
                loggerdestroy.error(f"Error deleting {node.name} ({node.serial_number}) in vCenter")
                return 'Error'
            else:
                # loggerdestroy.info(f"Node {node.name} not in vCenter, no need to destroy.")
                loggerdestroy.error(f"Failed to find {node.name} ({node.serial_number}) in vCenter, skipping VM delete operation")
                return 'Error'
            
        
            # Step 2: Remove DNS entries
            dns_removed = remove_dns_entry(node, deployment)
            if dns_removed == True:
                loggerdestroy.info(f"VM {node.name} removed from DNS.")
                
            elif dns_removed == False:
                loggerdestroy.info(f"VM {node.name} not found in DNS.")
                dns_removed = True # for next check, all is good!
            else:
                loggerdestroy.error(f"Failed to remove node {node.name} from DNS.")
                return 'Error'

        
        # Update deployment status
        if vm_destroyed and dns_removed:
            deployment.status = 'destroyed'
            deployment.save()
            loggerdestroy.info(f"Deployment {deployment.deployment_name} marked as 'destroyed'.")
            messages.success(f"Deployment {deployment.deployment_name} has been successfully destroyed.")
            return True
        else:
            deployment.status = 'error'
            deployment.save()
            loggerdestroy.error(f"Failed to completely destroy deployment {deployment.deployment_name}. Check the logs to see what issues occured")
            messages.error(f"Failed to completely destroy deployment {deployment.deployment_name}. Check the logs to see what issues occured")
            return False
    else:
        loggerdestroy.info(f"Deployment {deployment.deployment_name} is not in 'queued_for_destroy' status.")