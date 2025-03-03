from datetime import datetime
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from myapp.config_helper import load_config
from myapp.forms import VMCreationForm
from myapp.models import Deployment, Node, HardwareProfile, OperatingSystem, Status
from myapp.serializers import NodeSerializer
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from time import sleep
import json
import os as _os
import socket
import subprocess
import yaml

@api_view(['POST'])
def register_node(request):
    serializer = NodeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# deployment status refresh
def get_deployment_status(request, deployment_id):
    deployment = Deployment.objects.get(id=deployment_id)
    return JsonResponse({'status': deployment.status})

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


# deployment destruction - this is triggeed either by the usr clicking destory from 
# the deployment list page, or by the scheduled task in the event that the destroy 
# did not complete for some reason.  i may change this so the scheduled task is the 
# only trigger since this seems illogical

import logging
from SOLIDserverRest import SOLIDserverRest

# Get the logger for the deployment tasks
logger = logging.getLogger('deployment')

# function to remove node from vcenter
def destroy_vm(node, deployment):
    datacenter_name = deployment.datacenter
    config = load_config()
    datacenter = config['datacenters'].get(datacenter_name)
    vcenter = datacenter['vcenter']
    username = datacenter['credentials']['username']
    password = datacenter['credentials']['password']

    # Log the vCenter credentials being used
    logger.info(f"Using vCenter {vcenter} to destroy VM {node.name}")

    # Set environment variables for govc
    _os.environ["GOVC_URL"] = f"https://{vcenter}"
    _os.environ["GOVC_USERNAME"] = username
    _os.environ["GOVC_PASSWORD"] = password
    
    vm_short_name = node.name.split('.')[0]
    domain = deployment.domain or 'corp.pvt'
    vm_fqdn = f"{vm_short_name}.{domain}"

    # Check if VM is found in Vcenter
    govc_command = ["govc", "vm.info", f"{vm_short_name}"]
    result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode == 0:
        logger.info(f"Found {vm_short_name} in Vcenter")
        vm_name = vm_short_name
    else:
        govc_command = ["govc", "vm.info", f"{vm_fqdn}"]
        result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode == 0:
            logger.info(f"Found {vm_fqdn} in Vcenter")  
            vm_name = vm_fqdn
        else:
            logger.info(f"Failed to find {vm_short_name} or {vm_fqdn} in Vcenter, skipping VM delete operation")
            return True
    
    # Try destroying by short name, then FQDN if needed
    logger.info(f"Attempting to destroy VM: {vm_name}")
    destroy_vm_command = ["govc", "vm.destroy", vm_name]
    result = subprocess.run(destroy_vm_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode == 0:
        logger.info(f"VM {vm_name} destroyed successfully.")
        node.status = Status.objects.get(name='destroyed')
        node.save(update_fields=['status'])
        return True
    else:
        logger.error(f"Error destroying VM {vm_name}: {result.stderr}")
    return False

# function to remove node from DNS
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
    
    logger.info(f"Attempting to fetch DNS entry for {dns_name}.{dns_zone}")
    response = sds_conn.query("ip_address_list", parameters)

    if response.status_code == 200:
        ip_list = json.loads(response.content)
        if ip_list:
            ip_id = ip_list[0].get('ip_id')
            delete_response = sds_conn.query("ip_address_delete", {"ip_id": ip_id})
            if delete_response.status_code == 200:
                logger.info(f"DNS entry {dns_name}.{dns_zone} deleted.")
                return True
            else:
                logger.error(f"Error deleting DNS entry: {delete_response.content.decode()}")
    else:
        logger.error(f"Error fetching DNS entry: {response.content.decode()}")
    return False

# Main Destroy Deployment logic
def destroy_deployment(request, deployment_id):
    deployment = get_object_or_404(Deployment, id=deployment_id)
    
    # Check if the deployment is protected
    if deployment.protected:
        logger.warning(f"Deployment {deployment.deployment_name} is protected and cannot be deleted.")
        messages.error(request, f"Deployment {deployment.deployment_name} is protected and cannot be deleted.")
        return redirect('deployment_list')
    
    try:
        if deployment.status == 'queued':
            if request.method == 'POST':
                deployment.delete()
                logger.info(f"Deployment {deployment.deployment_name} deleted (queued).")
                messages.success(request, f"Deployment {deployment.deployment_name} has been successfully destroyed.")
                return redirect('deployment_list')
            else:
                logger.warning(f"Confirmation required to destroy queued deployment: {deployment.deployment_name}")
                messages.warning(request, "Confirmation required to destroy queued deployments.")
                return render(request, 'confirm_destroy.html', {'deployment': deployment})

        if deployment.status in ['needsapproval', 'failed']:
            deployment.delete()
            logger.info(f"Deployment {deployment.deployment_name} deleted (needsapproval/failed).")
            messages.success(request, f"Deployment {deployment.deployment_name} has been successfully queued for destruction.")
            return redirect('deployment_list')

        if deployment.status == 'deployed':
            if request.method == 'POST':
                deployment.status = 'queued-for-destroy'
                deployment.save()
                logger.info(f"Deployment {deployment.deployment_name} is now in 'queued-for-destroy' status.")
                # Queue the destroy operation as a background task
                #destroy_deployment_task(deployment_id)
                return redirect('deployment_list')

            else:
                logger.warning(f"Confirmation required to destroy running deployment: {deployment.deployment_name}")
                messages.warning(request, "Confirmation required to destroy running deployments.")
                return render(request, 'confirm_destroy.html', {'deployment': deployment})
        
        messages.error(request, "Invalid deployment status for destruction.")
        return redirect('deployment_list')

    except Exception as e:
        logger.error(f"Error queueing deployment destruction: {str(e)}")
        messages.error(request, f"An error occurred while queueing deployment destruction {deployment.deployment_name}: {str(e)}")
        return redirect('deployment_list')
                
def destroy_deployment_logic(deployment_id):
    deployment = get_object_or_404(Deployment, id=deployment_id)
    
    nodes_in_deployment = Node.objects.filter(deployment=deployment)
    vm_destroyed, dns_removed = True, True  # Initialize variables for logging

    for node in nodes_in_deployment:

        # Step 1: Destroy VMs in the deployment
        vm_destroyed = destroy_vm(node, deployment)
        if vm_destroyed:
            logger.info(f"Node {node.name} destroyed from vCenter.")
        else:
            logger.error(f"Failed to destroy node {node.name} from vCenter.")

        # Step 2: Remove DNS entries
        dns_removed = remove_dns_entry(node, deployment)
        if dns_removed:
            logger.info(f"Node {node.name} removed from DNS.")
        else:
            logger.error(f"Failed to remove node {node.name} from DNS.")

    # Update deployment status
    if vm_destroyed and dns_removed:
        deployment.status = 'destroyed'
        deployment.save()
        logger.info(f"Deployment {deployment.deployment_name} marked as 'destroyed'.")
        messages.success(request, f"Deployment {deployment.deployment_name} has been successfully destroyed.")
        return True
    else:
        deployment.status = 'error'
        deployment.save()
        logger.error(f"Failed to completely destroy deployment {deployment.deployment_name}.")
        messages.error(request, f"Failed to completely destroy deployment {deployment.deployment_name}.")
        return False


def view_log(request, node_id):
    node = get_object_or_404(Node, id=node_id)
    vm_short_name = node.name.split('.')[0]
    
    # Construct the path to the log file based on the node's name or other identifier
    log_file_path = _os.path.join(settings.MEDIA_ROOT, f"{vm_short_name}.log")
    
    print(f"Looking for log file at: {log_file_path}")
    
    try:
        with open(log_file_path, 'r') as log_file:
            log_content = log_file.read()
    except FileNotFoundError:
        return HttpResponse("Log file not found", status=404)

    return render(request, 'view_log.html', {'node': node, 'vm_short_name': vm_short_name})

import logging
logger = logging.getLogger(__name__)

def tail_log(request, node_name):
    vm_short_name = node_name.split('.')[0]
    log_file_path = _os.path.join(settings.MEDIA_ROOT, f"{vm_short_name}.log")
    
    logger.info(f"Looking for log file at: {log_file_path}")
    
    if not _os.path.exists(log_file_path):
        logger.error(f"Log file {log_file_path} not found")
        return JsonResponse({"status": "error", "message": "Log file {vm_short_name}.log not found"}, status=404)

    try:
        with open(log_file_path, 'r') as log_file:
            # Get the last N lines of the file
            log_file.seek(0, _os.SEEK_END)
            file_size = log_file.tell()
            log_file.seek(max(file_size - 1024 * 10, 0))  # Read the last 10 KB of the log file

            lines = log_file.readlines()
            logger.info(f"Successfully read log file: {log_file_path}")
            return JsonResponse({"status": "success", "log": ''.join(lines)}, status=200)
    except Exception as e:
        logger.error(f"Error reading log file {log_file_path}: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

    

def node_list(request):
    #nodes = Node.objects.all().order_by('name')
    query = request.GET.get('q')
    if query:
        nodes = Node.objects.filter(name__icontains=query).order_by('name') 
    else:
        nodes = Node.objects.all().order_by('name')
    
    paginator = Paginator(nodes, 20)  # Show 10 nodes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number) 
    return render(request, 'nodes.html', {'page_obj': page_obj})

# for listing node status
def node_detail(request, node_id):
    node = get_object_or_404(Node, id=node_id)
    return render(request, 'node_detail.html', {'node': node})

# lists all deployments
def deployment_list(request):
    deployments = Deployment.objects.all().order_by('-created_at')
    return render(request, 'deployment_list.html', {'deployments': deployments})

# for listing deployment status
def deployment_detail(request, deployment_id):
    deployment = get_object_or_404(Deployment, id=deployment_id)
    return render(request, 'deployment_detail.html', {'deployment': deployment})

def create_vm(request):
    # Load the configuration and prepare the datacenter choices
    config = load_config()
    
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
            deployment_date = timezone.now()
            #deployment_date = datetime.now().strftime('%Y-%m-%dT%H:%M') 
            #deployment_name = f"{deployment_date}-{owner}-{hostname}-{deployment_count}"
            deployment_name = f"{datacenter}{server_type}{hostname}-{owner}-{deployment_date}" 

            # Determine the correct label for the hostname
            hostname_label = "Hostname" if deployment_count == 1 else "Hostnames"
        
            vm_details = []
            # Append each field to the list, checking for conditionals where needed
            vm_details.append(f"<strong>Builtby</strong>: {builtby}<br>")
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
                os=os_raw,
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
            
        # Create a new Node instance using the already defined variables, looping through the nodes
            
            # Attempt to get the os and status from the database, or create it if it doesn't exist
            os_instance, created = OperatingSystem.objects.get_or_create(
                name=os_value,
            )
            
            status_instance, status_created = Status.objects.get_or_create(
                name='prebuild',
                    defaults={
                        'description': 'Node is in prebuild status',  
                    }
            )
            hwprofile_instance, hwprofile_created = HardwareProfile.objects.get_or_create(
                name='Vmware Virtual Platform',
                    defaults={
                        'description': 'Vmware Virtual Platform',  
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

                
            # Flash message
            from django.contrib import messages
            nodes_url = reverse('node_list')
            deployments_url = reverse('deployment_list')
            messages.success(request, mark_safe(f'VM creation request submitted:<br>{vm_details_str} <br><a href="{nodes_url}">View Nodes</a><br><a href="{deployments_url}">View Deployments</a>'))
            return redirect('create_vm')
            #return redirect('deployment_list')
        

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
        'deployments': deployments
    })


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