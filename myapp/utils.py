import subprocess
import socket
import json
import logging
import time
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

    
# Remove VM from vcenter (called from destroy_deployment_logic)
def destroy_vm(node, deployment):
    config = load_config()
    datacenter = config['datacenters'].get(deployment.datacenter)
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
    
    # Test vCenter connectivity
    if subprocess.run(["govc", "about"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).returncode != 0:
        loggerdestroy.error(f"vCenter {vcenter} is not responding. Setting deployment back to 'deployed'.")
        deployment.status = 'deployed'
        deployment.save(update_fields=['status'])
        return 'Error'

    vm_name = node.name.split('.')[0] if "yellowpages" not in node.name else node.name
    vm_uuid = node.serial_number
   
    if vm_uuid:
        loggerdestroy.info(f"Attempting to destroy VM: {vm_name} by UUID {vm_uuid}")
        info_command = ["govc", "vm.info", "-vm.uuid", vm_uuid]
        info_json_command = ["govc", "vm.info", "-json", "-vm.uuid", vm_uuid]
        poweroff_vm_command = ["govc", "vm.power", "-off", "-force", "-vm.uuid", vm_uuid]
        eject_cd_command = ["govc", "device.cdrom.eject", "-vm.uuid", vm_uuid]
        destroy_vm_command = ["govc", "vm.destroy", "-vm.uuid", vm_uuid]

    else:
        loggerdestroy.info(f"Attempting to destroy VM: {vm_name}")
        info_command = ["govc", "vm.info", vm_name]
        info_json_command = ["govc", "vm.info", "-json", vm_name]
        poweroff_vm_command = ["govc", "vm.power", "-off", "-force", vm_name]
        eject_cd_command = ["govc", "device.cdrom.eject", "-vm", vm_name]
        destroy_vm_command = ["govc", "vm.destroy", vm_name]

    # Check power status
    loggerdestroy.info(f"Checking power status for VM {vm_name}.")
    for attempt in range(3):
        power_status = subprocess.run(info_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if power_status.returncode != 0:
            loggerdestroy.error(f"Error checking power status for VM {vm_name}: {power_status.stderr.strip()}")
            return 'Error'

        if "poweredOff" in power_status.stdout:
            loggerdestroy.info(f"VM {vm_name} is already powered off.")
            break

        if "poweredOn" in power_status.stdout:
            loggerdestroy.info(f"VM {vm_name} is powered on. Attempting to power it off (Attempt {attempt + 1}/3).")
            result = subprocess.run(poweroff_vm_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if result.returncode == 0:
                time.sleep(5)
            else:
                loggerdestroy.error(f"Failed to send power off command for VM {vm_name}: {result.stderr.strip()}")
        else:
            loggerdestroy.warning(f"Unexpected power status for VM {vm_name}: {power_status.stdout.strip()}")
            return 'Error'

        time.sleep(5)

    else:
        loggerdestroy.error(f"VM {vm_name} failed to power off after 10 attempts.")
        return 'Error'
            
    # Eject CDROM
    loggerdestroy.info(f"Ejecting CDROM for VM {vm_name}.")
    result = subprocess.run(eject_cd_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode != 0:
        loggerdestroy.warning(f"Failed to eject CDROM for VM {vm_uuid}: {result.stderr.strip()}")


    # Delete seed.iso
    datastore_result = subprocess.run(info_json_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    try:
        datastore_json = json.loads(datastore_result.stdout)
        datastore = None
        for device in datastore_json["virtualMachines"][0]["config"]["hardware"]["device"]:
            if "backing" in device and "fileName" in device["backing"]:
                backing_file = device["backing"]["fileName"]
                if "seed.iso" in backing_file:
                    datastore = device["backing"]["fileName"].split('[')[-1].split(']')[0]
                    folder = device["backing"]["fileName"].split("]")[-1].strip().split("/")[0]
                    break

        if datastore:
            delete_iso_command = ["govc", "datastore.rm", "-ds", datastore, f"{folder}/seed.iso"]
            subprocess.run(delete_iso_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        else:
            loggerdestroy.warning(f"No seed.iso found for VM {vm_name}. Skipping seed.iso deletion.")
    except (KeyError, IndexError, json.JSONDecodeError):
        loggerdestroy.error(f"Error parsing datastore details for VM {vm_name}. Skipping seed.iso deletion.")

    # Destroy VM
    loggerdestroy.info(f"Destroying VM {vm_name}.")
    result = subprocess.run(destroy_vm_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode == 0:
        loggerdestroy.info(f"VM {vm_name} successfully destroyed.")
        node.status = Status.objects.get(name='destroyed')
        node.save(update_fields=['status'])
        return True
    elif 'no such' in result.stderr.lower() or 'not found' in result.stderr.lower():
        loggerdestroy.info(f"VM {vm_name} not found in vCenter. Marking as destroyed.")
        node.status = Status.objects.get(name='destroyed')
        node.save(update_fields=['status'])
        return False
    else:
        loggerdestroy.error(f"Error destroying VM {vm_name}: {result.stderr.strip()}")
        deployment.status = 'error'
        deployment.save(update_fields=['status'])
        node.status = Status.objects.get(name='error')
        node.save(update_fields=['status'])
        return 'Error'
    

    
# Remove node from DNS
def remove_dns_entry(node, deployment):
    datacenter_name = deployment.datacenter
    config = load_config()
    datacenter = config['datacenters'].get(datacenter_name)
    vcenter = datacenter['vcenter']
    username = datacenter['credentials']['username']
    password = datacenter['credentials']['password']

    # Extract details from the config
    master   = config['global']['eip']['eipmaster']
    username = config['global']['eip']['username']
    password = config['global']['eip']['password']
    #print(f"dns username: {username}, password {password}")
    
    sds_conn = SOLIDserverRest(master)
    sds_conn.set_ssl_verify(False)
    sds_conn.use_basicauth_sds(user=username, password=password)
    
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
                # loggerdestroy.info(f"DNS entry {dns_name}.{dns_zone} deleted.")
                return True
            else:
                # loggerdestroy.error(f"Error deleting DNS entry {dns_name}.{dns_zone}: {delete_response.content.decode()}")
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
            loggerdestroy.info(f"Step 1: Destroy VMs in the deployment")
            vm_destroyed = destroy_vm(node, deployment)
            if vm_destroyed == True:
                loggerdestroy.info(f"{node.name} destroyed from vCenter.")
                
            elif vm_destroyed == False:  
                loggerdestroy.info(f"{node.name} not found in vCenter.")
                vm_destroyed = True # all is good
                
            elif vm_destroyed == 'Error':  
                loggerdestroy.error(f"Error deleting {node.name} ({node.serial_number}) in vCenter")
                return 'Error'
            # else:
            #     # loggerdestroy.info(f"Node {node.name} not in vCenter, no need to destroy.")
            #     loggerdestroy.error(f"Failed to find {node.name} ({node.serial_number}) in vCenter, skipping VM delete operation")
            #     return 'Error'
            
        
            # Step 2: Remove DNS entries
            loggerdestroy.info(f"Step 2: Remove DNS entries")
            dns_removed = remove_dns_entry(node, deployment)
            if dns_removed == True:
                loggerdestroy.info(f"{node.name} removed from DNS.")
                
            elif dns_removed == False:
                loggerdestroy.info(f"{node.name} not found in DNS.")
                dns_removed = True # for next check, all is good!
                
            else:
                loggerdestroy.error(f"Error deleting DNS entry for {node.name}.")
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