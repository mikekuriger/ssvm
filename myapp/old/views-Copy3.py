from django.shortcuts import render, redirect
from .forms import VMCreationForm
from django.utils.safestring import mark_safe
from django.conf import settings
from datetime import datetime 
import os as _os
from .config_helper import load_config
import yaml

# 9-16-24 Mike Kuriger

from django.shortcuts import render, redirect
from .forms import VMCreationForm
from django.utils.safestring import mark_safe
from django.conf import settings
from datetime import datetime 
import os as _os
from .config_helper import load_config
import json

def create_vm(request):
    # Load the configuration and prepare the datacenter choices
    config = load_config()
    datacenters = {
        dc: {
            'clusters': list(dc_data['clusters']),
            'vlans': dc_data['vlans']
        } for dc, dc_data in config.get('datacenters', {}).items()
    }
    
    #print("Datacenters data:", datacenters)  # Debug print statement
    # Read deployment file names from the /media directory
    media_path = settings.MEDIA_ROOT
    #deployments = _os.listdir(media_path) if _os.path.exists(media_path) else []
    deployments = []
    if _os.path.exists(media_path):
        for file in _os.listdir(media_path):
            full_path = _os.path.join(media_path, file)
            if '-' in file:
                # Split at the last 'T' and keep the first part
               #processed_file = file.rsplit('T', 1)[0]
                processed_file = file
                # Append a tuple of (processed filename, modification time)
                deployments.append((processed_file, _os.path.getmtime(full_path)))
            else:
                deployments.append((file, _os.path.getmtime(full_path)))
    
    # Sort deployments by modification time, newest first
    deployments.sort(key=lambda x: x[1], reverse=True)
    
    # Extract only the filenames, now sorted by date
    deployments = [file[0] for file in deployments]

    
    if request.method == 'POST':
        datacenter = request.POST.get('datacenter', None)
        form = VMCreationForm(request.POST, datacenter=datacenter)
        
        if form.is_valid():
            # Process the form data
            data = form.cleaned_data
            
            full_hostnames = data['full_hostnames']
            #hostname = full_hostnames.split(',')[0].strip()
            hostname = data['hostname']
    
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
            
            #deployment_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S') 
            deployment_date = datetime.now().strftime('%y-%m-%dT%H:%M') 
            deployment_name = f"{deployment_date}-{owner}-{hostname}-{deployment_count}"  

            # Determine the correct label for the hostname
            hostname_label = "Hostname" if deployment_count == 1 else "Hostnames"

            vm_details = []
            # Append each field to the list, checking for conditionals where needed
            vm_details.append(f"<strong>{hostname_label}</strong>: {full_hostnames}<br>")
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
            
            # build details need to be less fancy
            build_details = []
            # Append each field to the list, checking for conditionals where needed
            build_details.append(f"Deployment_name: {deployment_name}\n")
            build_details.append(f"Deployment_date: {deployment_date}\n")
            build_details.append(f"{hostname_label}: {full_hostnames}\n")
            build_details.append(f"Ticket: {ticket}\n")
            build_details.append(f"App_Name: {appname}\n")
            build_details.append(f"Owner: {owner}\n")
            build_details.append(f"Datacenter: {datacenter}\n")
            build_details.append(f"Type: {server_type_value}\n")
            build_details.append(f"Deployment_count: {deployment_count}\n")
            build_details.append(f"CPU: {cpu}\n")
            build_details.append(f"RAM: {ram}\n")
            build_details.append(f"OS: {os_raw}\n")
            build_details.append(f"Disk: {disk_size}\n")
            build_details.append(f"Cluster: {cluster}\n")
            build_details.append(f"Network: {network}\n")
            build_details.append(f"NFS: {nfs_home}\n")
            build_details.append(f"Add_disk: {add_disks}\n")

            if add_disks:
                build_details.append(f"Add_disk_size: {additional_disk_size}\n")
                build_details.append(f"Add_disk_path: {mount_path}\n")

            build_details.append(f"Centrify: {join_centrify}\n")

            if join_centrify:
                build_details.append(f"Centrify_zone: {centrify_zone}\n")
                build_details.append(f"Centrify_role: {centrify_role}\n")

            build_details.append(f"Patches: {install_patches}\n")
            build_details = ''.join(build_details)

            # Save details to file
            file_path = _os.path.join(settings.MEDIA_ROOT, deployment_name)
            with open(file_path, 'w') as file:
                file.write(vm_details_str)
                
            # filename is (appname fixed)-(count)-(owner)-(date)
            file_path = _os.path.join(settings.MEDIA_ROOT, deployment_name)
            # Write the form data to a text file
            with open(file_path, 'w') as file:
                #for detail in build_details:
                #    file.write(detail + "\n")
                file.write(build_details)

            # Flash message
            from django.contrib import messages
            messages.success(request, mark_safe(f'VM creation request submitted:<br>{vm_details_str}'))
            return redirect('create_vm')

        if not form.is_valid():
            # Debug: print any form errors to console
            print(form.errors)

    else:
        form = VMCreationForm()  # GET request, render an empty form

    # Return form and datacenter data for JavaScript use
    return render(request, 'create_vm.html', {
        'form': form,
        'datacenters': datacenters,
        'deployments': deployments
    })




import socket
from django.http import JsonResponse
import json

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
