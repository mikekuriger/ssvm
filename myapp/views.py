from datetime import datetime
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .config_helper import load_config
from .forms import VMCreationForm
from .models import Deployment
from .models import HardwareProfile
from .models import Node
from .models import OperatingSystem
from .models import Status
from .serializers import NodeSerializer
import json
import os as _os
import socket
import yaml


@api_view(['POST'])
def register_node(request):
    serializer = NodeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

# deployment destruction
def destroy_deployment(request, deployment_id):
    deployment = get_object_or_404(Deployment, id=deployment_id)
    
    # Check if the status requires confirmation
    if deployment.status in ['queued']:
    # if deployment.status in ['deployed', 'queued']:  # to delete a "deplpyed" deployment, i need to code up the delete process.  maybe someday
        # Only proceed with deletion if confirmation has been given (POST request)
        if request.method == 'POST':
            deployment.delete()
            #messages.success(request, "Deployment has been successfully destroyed.")
            return redirect('deployment_list')
        else:
            # Render the confirmation page for GET requests
            return render(request, 'confirm_destroy.html', {'deployment': deployment})
    
    # For other statuses, delete immediately
    if deployment.status in ['needsapproval', 'failed']:
        deployment.delete()
        #messages.success(request, "Deployment has been successfully destroyed.")
    
    return redirect('deployment_list')


# # list nodes
# def nodes(request):
#     nodes = Node.objects.all().order_by('name')
#     return render(request, 'nodes.html', {'nodes': nodes})

# pagination
from django.core.paginator import Paginator
from django.shortcuts import render

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
            deployment_date = datetime.now().strftime('%Y-%m-%dT%H:%M') 
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
                    physical_memory=ram,
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
            messages.success(request, mark_safe(f'VM creation request submitted:<br>{vm_details_str} <br><a href="{nodes_url}">Back to Nodes</a>'))
            return redirect('create_vm')
        

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




import socket
from django.http import JsonResponse

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
