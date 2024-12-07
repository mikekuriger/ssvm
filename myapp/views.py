from datetime import datetime
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from myapp.config_helper import load_config
from myapp.forms import VMCreationForm, load_users_from_csv
from myapp.models import Deployment, Node, HardwareProfile, OperatingSystem, Status, VRA_Deployment, VRA_Node
from myapp.utils import destroy_vm, remove_dns_entry, screamtest_vm

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.response import Response
from myapp.serializers import NodeSerializer

from time import sleep
import glob
import json
import logging
import os as _os
import socket
import subprocess
import yaml


# function based apt, uses api_view
@api_view(['POST'])
def register_node(request):
    serializer = NodeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class based api, uses APIView
class NodeRegistrationAPIView(APIView):
    def post(self, request):
        data = request.data

        # Step 1: Extract and process OS-related data
        os_name = data.pop('os_name', None)
        os_varient = data.pop('os_varient', None)
        os_version = data.pop('os_version', None)
        os_vendor = data.pop('os_vendor', None)
        
        if not os_name:
            return Response({'error': 'Operating system is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        os_instance, _ = OperatingSystem.objects.get_or_create(
            name=os_name,
            defaults={
                'varient': os_varient,
                'version': os_version,
                'vendor': os_vendor
            }
        )

        # Step 2: Handle Hardware Profile
        hw_name = data.pop('hw_name', None)
        hw_manufacturer = data.pop('hw_manufacturer', None)
        hw_desc = data.pop('hw_desc', None)
        if not hw_name:
            return Response({'error': 'Hardware profile is required.'}, status=status.HTTP_400_BAD_REQUEST)

        hwprofile_instance, _ = HardwareProfile.objects.get_or_create(
            name=hw_name,
            defaults={
                'description': hw_desc,
                'manufacturer': hw_manufacturer
            }
        )

        # Step 3: Add the related object references to the Node data
        data['operating_system'] = os_instance.id
        data['hardware_profile'] = hwprofile_instance.id
        
        # Step 4: Check for existing Node and update or create
        uniqueid = data.get('uniqueid')  # Use unique identifier to find the Node

        try:
            # Try to update the existing node
            node = Node.objects.get(uniqueid=uniqueid)
            serializer = NodeSerializer(instance=node, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Node.DoesNotExist:
            # Create a new node if not found
            status_instance, _ = Status.objects.get_or_create(
                name='setup',
                defaults={'description': 'Node is not in production'}
            )
            data['status'] = status_instance.id
            serializer = NodeSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# deployment status refresh
def get_deployment_status(request, deployment_id):
    try:
        deployment = Deployment.objects.get(id=deployment_id)
        data = {
            'status': deployment.status,
            'protected': deployment.protected,
            'is_staff': request.user.is_staff
        }
        return JsonResponse(data)
    except Deployment.DoesNotExist:
        return JsonResponse({'error': 'Deployment not found'}, status=404)


# Node status refresh
def get_node_status(request, node_id):
    try:
        node = Node.objects.get(id=node_id)
        data = {
            'status': node.status.name,
            'ping_status': node.ping_status
        }
        return JsonResponse(data)
    except Node.DoesNotExist:
        return JsonResponse({'error': 'Node not found'}, status=404)


# deployment approvals
def approve_deployment(request, deployment_id):
    deployment = get_object_or_404(Deployment, id=deployment_id)
    
    # Toggle the status or set it to approved
    if deployment.status == 'needsapproval' or 'failed':
        deployment.status = 'queued'
    else:
        deployment.status = 'needsapproval'
    
    deployment.save()
    return redirect('deployment_list') 


# deployment cancel (set to failed)
def cancel_deployment(request, deployment_id):
    deployment = get_object_or_404(Deployment, id=deployment_id)
    
    if deployment.status == 'building':
        deployment.status = 'failed' 
    else:
        deployment.status = 'building'  
    deployment.save()
    return redirect('deployment_list') 


# Get the logger for the deployment tasks
loggerdestroy = logging.getLogger('destroy')
logger = logging.getLogger('deployment')


# Main Destroy Deployment logic
@login_required
def destroy_deployment(request, deployment_id):
    deployment = get_object_or_404(Deployment, id=deployment_id)
    
    # Check if the deployment is protected
    if deployment.protected:
        loggerdestroy.warning(f"Deployment {deployment.deployment_name} is protected and cannot be deleted.")
        messages.error(request, f"Deployment {deployment.deployment_name} is protected and cannot be deleted.")
        return redirect('deployment_list')
    
    try:
        # these statuses do not have VMs already built so we will delete the deployment right away and not try to delete VMs (get confirmation)
        if deployment.status == 'queued':
            if request.method == 'POST':
                deployment.delete()
                loggerdestroy.info(f"Deployment {deployment.deployment_name} deleted (queued).")
                messages.success(request, f"Deployment {deployment.deployment_name} has been successfully destroyed.")
                return redirect('deployment_list')
            else:
                loggerdestroy.warning(f"Confirmation required to destroy queued deployment: {deployment.deployment_name}")
                messages.warning(request, "Confirmation required to destroy queued deployments.")
                return render(request, 'confirm_destroy.html', {'deployment': deployment})

        # these statuses do not have VMs already built so we will delete the deployment right away and not try to delete VMs
        elif deployment.status in ['needsapproval', 'destroyed']:
            deployment.delete()
            loggerdestroy.info(f"Deployment {deployment.deployment_name} deleted (needsapproval/failed/destroyed).")
            messages.success(request, f"Deployment {deployment.deployment_name} has been successfully destroyed.")
            return redirect('deployment_list')

        # these statuses may or may not have VMs already built so we will try to delete the VMs and DNS (get confirmation)
        elif deployment.status in ['screamtest', 'failed', 'deployed']:
            if request.method == 'POST':
                deployment.status = 'queued_for_destroy'
                deployment.save()
                loggerdestroy.info(f"Deployment {deployment.deployment_name} is now in 'queued_for_destroy' status.")
                messages.success(request, f"Deployment {deployment.deployment_name} has been successfully queued for destroy.")
                return redirect('deployment_list')

            else:
                loggerdestroy.warning(f"Confirmation required to destroy deployment: {deployment.deployment_name}")
                messages.warning(request, "Confirmation required to destroy deployment.")
                return render(request, 'confirm_destroy.html', {'deployment': deployment})
        
        messages.error(request, "Invalid deployment status for destruction.")
        return redirect('deployment_list')

    except Exception as e:
        loggerdestroy.error(f"Error queueing deployment destruction: {str(e)}")
        messages.error(request, f"An error occurred while queueing deployment destruction {deployment.deployment_name}: {str(e)}")
        return redirect('deployment_list')


        
        
# screamtest deployment function (calls screamtest vm function)
@login_required
def screamtest_deployment(request, deployment_id):
    if request.method == 'POST':
        deployment = get_object_or_404(Deployment, id=deployment_id)
        decom_ticket = request.POST.get('jira_ticket')  # Retrieve the Jira ticket from the form data
        decom_date = datetime.now().strftime("%m-%d-%y")
        
        if deployment.status == 'deployed':
            
        # Implement the screamtest logic here, ie shutting down VMs and renaming them
            try:
                deployment.status = 'screamtest'
                deployment.decom_ticket = decom_ticket
                deployment.save()
                loggerdestroy.info(f"Deployment {deployment.deployment_name} is now in 'screamtest' status.")

                nodes_in_deployment = Node.objects.filter(deployment=deployment)
                vm_screamtest = True

                for node in nodes_in_deployment:
                    # Screamtest VMs in the deployment
                    vm_screamtest = screamtest_vm(node, deployment, decom_ticket, decom_date)
                    if vm_screamtest == True:
                        loggerdestroy.info(f"VM {node.name} has been screamtested successfully.")
                        # update node.name ?  maybe not...
                        # update node.status
                        node.status = Status.objects.get(name='screamtest')
                        node.save()
                
                    elif vm_screamtest == False:  
                        loggerdestroy.info(f"Failed to screamtest VM {node.name} - operation failed.")

                
                # update deployment.decom_date and deployment.status
                deployment.status = 'screamtest'
                deployment.decom_date = decom_date
                deployment.save(update_fields=['status'])
                
            
                messages.success(request, f"Deployment {deployment_id} has been screamtested successfully.")
                loggerdestroy.info(request, f"Deployment {deployment_id} has been screamtested successfully.")

            except Exception as e:
                messages.error(request, f"Failed to screamtest deployment {deployment_id}. Error: {e}")

            return redirect('deployment_list')
        
        else:
            messages.error(request, f"Failed to screamtest deployment {deployment_id}. Not in 'deployed' status")
            return redirect('deployment_list')

    # If not a POST request, deny access or return an error
    return HttpResponse("Invalid request method.", status=405)



# Cancel screamtest
@login_required   
def cancel_screamtest(request, deployment_id):
    # Retrieve the deployment object
    deployment = get_object_or_404(Deployment, id=deployment_id)
    
    # Check if the deployment is in a screamtest status before canceling
    if deployment.status == 'screamtest':
        
        # bring VMs back online and rename them back to their original name
        nodes_in_deployment = Node.objects.filter(deployment=deployment)
        all_restored = True  # Track if all VMs are restored successfully
        
        for node in nodes_in_deployment:
            if deployment.domain == 'corp.pvt':
                original_name = node.name.split('.')[0]
            else:
                original_name = node.name
            vm_uuid = node.serial_number  # UUID for more reliable identification

            # Step 1: Rename the VM back to its original name
            rename_command = ["govc", "vm.change", "-vm.uuid", vm_uuid, "-name", original_name]
            rename_result = subprocess.run(rename_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

            if rename_result.returncode == 0:
                logger.info(f"VM {original_name} renamed in Vcenter")
            else:
                logger.error(f"Failed to rename VM {vm_uuid}. Error: {rename_result.stderr}")
                all_restored = False
                
            # Step 2: Power on the VM
            power_on_command = ["govc", "vm.power", "-on", "-vm.uuid", vm_uuid]
            power_on_result = subprocess.run(power_on_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            
            if power_on_result.returncode == 0:
                logger.info(f"VM {original_name} powered on successfully.")
            
            elif 'current state (Powered on)' in power_on_result.stderr:
                logger.info(f"VM {original_name} already powered on.")
                
            else:
                logger.error(f"Failed to power on VM {original_name}. Error: {power_on_result.stderr}")
                all_restored = False
                continue  # Move to next VM in case of error

            # Step 3: Update the VM status to "inservice"
            node.status = Status.objects.get(name='inservice')
            node.save(update_fields=['status'])
            

        # Update deployment status based on restoration success
        if all_restored:
            deployment.status = 'deployed'
            deployment.save()
            logger.info(f"Screamtest for Deployment {deployment_id} has been canceled.")
            messages.success(request, f"Screamtest for Deployment {deployment.deployment_name} has been successfully canceled.")
        else:
            deployment.status = 'error'
            deployment.save()
            messages.error(request, f"Failed to fully cancel screamtest for Deployment {deployment.deployment_name}. Check logs for details.")
    
    else:
        messages.error(request, f"Deployment {deployment.deployment_name} is not in screamtesting status.")
    
    return redirect('deployment_list')



# functions to view system logs
# @login_required
# def view_system_logs(request, log_type):
#     log_files = {
#         'destroy': [ _os.path.join(settings.BASE_DIR, 'logs', 'destroy.log')],
#         'deployment': [ _os.path.join(settings.BASE_DIR, 'logs', 'deployment.log')],
#         'task': [ _os.path.join(settings.BASE_DIR, 'logs', 'django-background-tasks.log') ],
#         'application': [
#             _os.path.join(settings.BASE_DIR, 'logs', 'django.log'),
#             _os.path.join(settings.BASE_DIR, 'django_output.log')
#         ],
#     }

#      # Get the requested log file path
#     log_file_paths = log_files.get(log_type)
    
#     if log_file_paths:
#         filtered_lines = []
#     # Iterate through each log file in the list
#         for log_file_path in log_file_paths:
#             if _os.path.exists(log_file_path):
#                 with open(log_file_path, 'r') as log_file:
#                     log_lines = log_file.readlines()

#                     # Apply filters based on the log type
#                     if log_type == 'deployment':
#                         # Filter out specific deployment log entries
#                         filtered_lines.extend([
#                             line for line in log_lines
#                             if "Successfully read log file" not in line
#                             and "Looking for log file at" not in line
#                         ])
#                     elif log_type == 'destroy':
#                         # Filter out specific deployment log entries
#                         filtered_lines.extend([
#                             line for line in log_lines
#                             if "Successfully read log file" not in line
#                             and "Looking for log file at" not in line
#                         ])
#                     elif log_type == 'task':
#                         # Filter out 'Found 0 deployments' from the background task log
#                         filtered_lines.extend([
#                             line for line in log_lines
#                             if "Found 0 deployments" not in line
#                         ])
#                     elif log_type == 'application':
#                         # Filter out 'Looking for log file' from both application log files
#                         filtered_lines.extend([
#                             line for line in log_lines
#                             if "INFO" not in line
#                         ])
#                     else:
#                         # No filtering for other log types
#                         filtered_lines.extend(log_lines)
#             else:
#                 return HttpResponse(f"Log file '{log_file_path}' not found.", status=404)

#         # Return the filtered log content as plain text
#         response_content = ''.join(filtered_lines)
#         return HttpResponse(response_content, content_type='text/plain')

#     return HttpResponse(f"Log type '{log_type}' not found.", status=404)



@login_required
def view_deployment_log(request):
    log_file_path = _os.path.join(settings.BASE_DIR, 'logs', 'deployment.log')

    if not _os.path.exists(log_file_path):
        return HttpResponse("Deployment log file not found.", status=404)

    try:
        with open(log_file_path, 'r') as log_file:
            log_content = log_file.read()
    except Exception as e:
        return HttpResponse(f"Error reading log file: {str(e)}", status=500)

    return render(request, 'view_deployment_log.html', {'log_content': log_content})



@login_required
def tail_deployment_log(request):
    log_file_path = _os.path.join(settings.BASE_DIR, 'logs', 'deployment.log')

    # Check if the log file exists
    if not _os.path.exists(log_file_path):
        return JsonResponse({"status": "error", "message": "Log file 'deployment.log' not found"}, status=404)

    try:
        with open(log_file_path, 'r') as log_file:
            # Move to the end of the file
            log_file.seek(0, _os.SEEK_END)
            file_size = log_file.tell()
            # Read the last 10 KB of the file
            log_file.seek(max(file_size - 1024 * 10, 0))
            lines = log_file.readlines()

            # Filter out specific entries if needed
            filtered_lines = [
                line for line in lines
                if "Successfully read log file" not in line and "Looking for log file at" not in line
            ]

            # Return the filtered log content as a JSON response
            return JsonResponse({"status": "success", "log": ''.join(filtered_lines)}, status=200)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    
    
@login_required
def view_log(request, node_id):
    node = get_object_or_404(Node, id=node_id)
    vm_short_name = node.name.split('.')[0]
    log_file_path = _os.path.join(settings.MEDIA_ROOT, f"{vm_short_name}.log")
    
    print(f"Looking for log file at: {log_file_path}")
    
    try:
        with open(log_file_path, 'r') as log_file:
            log_content = log_file.read()
    except FileNotFoundError:
        return HttpResponse("Log file not found", status=404)

    return render(request, 'view_log.html', {'model_type': 'nodes', 'node': node, 'vm_short_name': vm_short_name})




@login_required
def tail_log(request, node_name):
    vm_short_name = node_name.split('.')[0]
    log_file_path = _os.path.join(settings.MEDIA_ROOT, f"{vm_short_name}.log")
    
    # loggerdestroy.info(f"Looking for log file at: {log_file_path}")
    
    if not _os.path.exists(log_file_path):
        # loggerdestroy.error(f"Log file {log_file_path} not found")
        return JsonResponse({"status": "error", "message": "Log file {vm_short_name}.log not found"}, status=404)

    try:
        with open(log_file_path, 'r') as log_file:
            # Get the last N lines of the file
            log_file.seek(0, _os.SEEK_END)
            file_size = log_file.tell()
            log_file.seek(max(file_size - 1024 * 10, 0))  # Read the last 10 KB of the log file

            lines = log_file.readlines()
            # loggerdestroy.info(f"Successfully read log file: {log_file_path}")
            return JsonResponse({"status": "success", "log": ''.join(lines)}, status=200)
    except Exception as e:
        # loggerdestroy.error(f"Error reading log file {log_file_path}: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    

@login_required
def create_vm(request):
    # Load the configuration and prepare the datacenter choices
    config = load_config()
    owner_choices = load_users_from_csv()  # Load choices from CSV
    
    # find who built it
    if request.user.is_authenticated:
        builtby = request.user.username
    else:
        builtby = "Guest"
        
    datacenters = {
        dc: {
           # 'clusters': list(dc_data['clusters']),
            'clusters': dc_data['clusters'],
            'vlans': dc_data['vlans'],
            'domains': dc_data['domains']
        } for dc, dc_data in config.get('datacenters', {}).items()
    }
    

    # Read deployment file names from the /media directory
    media_path = settings.MEDIA_ROOT

    
    if request.method == 'POST':
        datacenter = request.POST.get('datacenter', None)
        form = VMCreationForm(request.POST, datacenter=datacenter)
        
        if form.is_valid():
            # Process the form data
            data = form.cleaned_data

            full_hostnames = data['full_hostnames']
            hostname = data['hostname']
            domain = data['domain']
            ticket = data['ticket']
            appname = data['appname']
            owner = data['owner']
            owner_value = request.POST.get('owner_value')
            datacenter = data['datacenter']
            server_type = data['server_type']
            server_type_value = request.POST.get('server_type_value')
            deployment_count = int(data['deployment_count'])
            cpu = data['cpu']
            ram = data['ram']
            os_raw = data['os']
            clone_from = data['clone_from']
            os_value = request.POST.get('os_value')
            disk_size = data['disk_size']
            cluster = data['cluster']
            network = data['network']
            nfs_home = data['nfs_home']
            add_disks = data['add_disks']
            additional_disk_size = data['additional_disk_size']
            mount_path = data['mount_path']
            join_centrify = data['join_centrify']
            centrify_zone = data['centrify_zone']
            centrify_role = data['centrify_role']
            install_patches = data['install_patches']
            date = timezone.now()
            deployment_date = date.strftime('%Y-%m-%dT%H:%M')
            #deployment_date = datetime.now().strftime('%Y-%m-%dT%H:%M') 
            #deployment_name = f"{deployment_date}-{owner}-{hostname}-{deployment_count}"
            deployment_name = f"{datacenter}{server_type}{hostname}-{owner}-{deployment_date}" 

            # Determine the correct label for the hostname
            hostname_label = "Hostname" if deployment_count == 1 else "Hostnames"
        
            vm_details = []
            # Append each field to the list, checking for conditionals where needed
            vm_details.append(f"<strong>Builtby</strong>: {builtby}<br>")
            if clone_from:
                vm_details.append(f"<strong>Clone From</strong>: {clone_from}<br>")
            
            vm_details.append(f"<strong>{hostname_label}</strong>: {full_hostnames}<br>")
            vm_details.append(f"<strong>Domain</strong>: {domain}<br>")
            vm_details.append(f"<strong>Ticket</strong>: {ticket}<br>")
            vm_details.append(f"<strong>Application Name</strong>: {appname}<br>")
            vm_details.append(f"<strong>Owner</strong>: {owner_value}<br>")
            vm_details.append(f"<strong>Datacenter</strong>: {datacenter}<br>")
            vm_details.append(f"<strong>Server Type</strong>: {server_type_value}<br>")
            vm_details.append(f"<strong>Deployment Count</strong>: {deployment_count}<br>")
            vm_details.append(f"<strong>CPU</strong>: {cpu}<br>")
            vm_details.append(f"<strong>RAM</strong>: {ram}<br>")

            if not clone_from:
                vm_details.append(f"<strong>OS</strong>: {os_value}<br>")
        
            vm_details.append(f"<strong>Disk Size</strong>: {disk_size}<br>")
            vm_details.append(f"<strong>Cluster</strong>: {cluster}<br>")
            vm_details.append(f"<strong>Network</strong>: {network}<br>")
            vm_details.append(f"<strong>NFS Home</strong>: {nfs_home}<br>")
            vm_details.append(f"<strong>Additional Disks</strong>: {add_disks}<br>")

            if add_disks:
                vm_details.append(f"<strong>Additional Disk Size</strong>: {additional_disk_size}<br>")
                vm_details.append(f"<strong>Mount Path</strong>: {mount_path}<br>")

            vm_details.append(f"<strong>Join Centrify</strong>: {join_centrify}<br>")

            if join_centrify:
                vm_details.append(f"<strong>Centrify Zone</strong>: {centrify_zone}<br>")
                vm_details.append(f"<strong>Centrify Role</strong>: {centrify_role}<br>")

            vm_details.append(f"<strong>Install Patches</strong>: {install_patches}<br>")
            #vm_details.append(f"<strong>Deployment Name</strong>: {deployment_name}<br>")
            vm_details.append(f"<strong>Deployment Date</strong>: {deployment_date}<br>")
            vm_details_str = ''.join(vm_details)
            
            
            # Create a new Deployment instance using the already defined variables
            deployment = Deployment(
                deployment_date=deployment_date,
                deployment_name=deployment_name,
                builtby=builtby,
                hostname=hostname,
                domain=domain,
                full_hostnames=full_hostnames,
                ticket=ticket,
                appname=appname,
                owner=owner,
                owner_value=owner_value,
                datacenter=datacenter,
                server_type=server_type,
                server_type_value=server_type_value,
                deployment_count=deployment_count,
                cpu=cpu,
                ram=ram,
                os = clone_from if clone_from else os_raw,
                os_value=os_value,
                disk_size=disk_size,
                add_disks=add_disks,
                additional_disk_size=additional_disk_size,
                mount_path=mount_path,
                cluster=cluster,
                network=network,
                nfs_home=nfs_home,
                join_centrify=join_centrify,
                centrify_zone=centrify_zone,
                centrify_role=centrify_role,
                install_patches=install_patches
            )

            # Save the deployment to the database
            deployment.save()
            logger.info(f"Deployment {deployment_name} created.")
            
        # Create a new Node instance using the already defined variables, looping through the nodes
            
            # Attempt to get the os and status from the database, or create it if it doesn't exist
            os_instance, created = OperatingSystem.objects.get_or_create(
                name=os_value,
            )
            
            status_instance, status_created = Status.objects.get_or_create(
                name='prebuild',
                    defaults={
                        'description': 'VM is in prebuild status',  
                    }
            )
            hwprofile_instance, hwprofile_created = HardwareProfile.objects.get_or_create(
                name='Vmware Virtual Platform',
                    defaults={
                        'description': 'Vmware Virtual Platform',  
                        'manufacturer:': 'Vmware, Inc.',  
                    }
            )
            
            # Add the requested nodes to the database and set status to prebuild
            #full_hostnames_list = full_hostnames.split(",")
            full_hostnames_list = [hostname.strip() for hostname in full_hostnames.split(",")]
            ram=int(ram)
            rammb = int(ram*1024)
            nodes = [
                Node(
                    name=f"{hostname}.{domain}",
                    contact=owner,
                    centrify_zone=centrify_zone,
                    created_at=deployment_date,
                    operating_system=os_instance,
                    status=status_instance,
                    processor_count=cpu,
                    disk_size=disk_size,
                    physical_memory=rammb,
                    hardware_profile=hwprofile_instance,
                    deployment=deployment
                    # add these to the model to deploy without spool files
                    # or read these from the deployment...
                    # name=hostname,
                    # ticket=ticket,
                    # appname=appname,
                    # datacenter=datacenter,
                    # server_type_value=server_type_value,
                    # deployment_count=deployment_count,
                    # cpu=cpu,
                    # ram=ram,
                    # os=os_raw,
                    # disk_size=disk_size,
                    # add_disks=add_disks,
                    # additional_disk_size=additional_disk_size,
                    # mount_path=mount_path,
                    # cluster=cluster,
                    # network=network,
                    # nfs_home=nfs_home,
                    # join_centrify=join_centrify,
                    # centrify_zone=centrify_zone,
                    # centrify_role=centrify_role,
                    # install_patches=install_patches
                )
                for hostname in full_hostnames_list
            ]
            Node.objects.bulk_create(nodes)
            logger.info(f"Nodes for Deployment {deployment_name} created.")

                
            # Flash message
            from django.contrib import messages
            nodes_url = reverse('node_list')
            #deployments_url = reverse('deployment_list')
            messages.success(request, mark_safe(f'Deployment request submitted:<br></br><br>{vm_details_str} <br><a href="{nodes_url}">View Nodes</a>'))
            
            #return redirect('create_vm')
            return redirect('deployment_list')
        

        if not form.is_valid():
            # Debug: print any form errors to console
            print(form.errors)

    else:
        form = VMCreationForm()  # GET request, render an empty form

    # Return form and datacenter data for JavaScript use
    #deployments = Deployment.objects.all()
    deployments = Deployment.objects.all().order_by('-created_at')
    
    return render(request, 'create_vm.html', {
        'form': form,
        'datacenters': datacenters,
        'deployments': deployments,
        'owner_choices': owner_choices  # Pass to the template context
    })


# used by create_vm.js via urls.py
def check_dns(request):
    if request.method == 'POST':
        try:
            # Parse the incoming JSON data
            data = json.loads(request.body)
            hostnames = data.get('hostnames', [])
            results = {}

            # Perform DNS lookup for each hostname
            for hostname in hostnames:
                try:
                    socket.gethostbyname(hostname)
                    results[hostname] = True  # Hostname exists in DNS
                except socket.error:
                    results[hostname] = False  # Hostname does not exist

            # Return the results as a JSON response
            return JsonResponse(results)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    

# List all nodes
def node_list(request):
    model_type = request.GET.get('model', 'node')  # Get the model type from the URL parameter
    query = request.GET.get('q', '')
    page_size = int(request.GET.get('page_size', 20))
    
    if model_type == 'vra':
        # query = request.GET.get('q')
        vranodes = VRA_Node.objects.filter(name__icontains=query).order_by('name') if query else VRA_Node.objects.all().order_by('name')
        paginator = Paginator(vranodes, page_size)
    else:
        # query = request.GET.get('q')
        nodes = Node.objects.filter(name__icontains=query).order_by('name') if query else Node.objects.all().order_by('name')
        paginator = Paginator(nodes, page_size)
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pass the model type to the template
    return render(request, 'nodes.html', {
        'page_obj': page_obj,
        'model_type': model_type,
        'query': query,
    })


# for listing node status
#def node_detail(request, node_id):
def node_detail(request, node_id, model_type):
    if model_type == 'vra':
        node = get_object_or_404(VRA_Node, id=node_id)
        deployment = get_object_or_404(VRA_Deployment, id=node.deployment_id)
    else:
        node = get_object_or_404(Node, id=node_id)
        deployment = get_object_or_404(Deployment, id=node.deployment_id)
        
    #node = get_object_or_404(Node, id=node_id)
    return render(request, 'node_detail.html', {
        'node': node,
        'deployment': deployment
    })


# lists all deployments
def deployment_list(request):
    deployments = Deployment.objects.all().order_by('-created_at')
    show_vra_deployments = request.GET.get('show_vra', 'false') == 'true'
    vra_deployments = VRA_Deployment.objects.all().order_by('-created_at') if show_vra_deployments else None
    
    return render(request, 'deployment_list.html', {
        'deployments': deployments,
        'vra_deployments': vra_deployments,
        'show_vra_deployments': show_vra_deployments
    })


# for listing deployment status
def deployment_detail(request, deployment_id):
    # Try to retrieve the deployment from `Deployment`
    try:
        deployment = Deployment.objects.get(id=deployment_id)
    except Deployment.DoesNotExist:
        # If not found, try `VRA_Deployment`
        deployment = get_object_or_404(VRA_Deployment, id=deployment_id)
        
    #deployment = get_object_or_404(Deployment, id=deployment_id)
    return render(request, 'deployment_detail.html', {'deployment': deployment})


