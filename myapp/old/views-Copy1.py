from django.shortcuts import render, redirect
from .forms import VMCreationForm
from django.utils.safestring import mark_safe
# 9-16-24 Mike Kuriger

def create_vm(request):
    if request.method == 'POST':
        datacenter = request.POST.get('datacenter', None)
        form = VMCreationForm(request.POST, datacenter=datacenter)  # Pass datacenter to the form
        if form.is_valid():
            # Process the form data
            data = form.cleaned_data
            
            ticket = data['ticket']
            appname = data['appname']
            owner = data['owner']
            owner_value = request.POST.get('owner_value')
            datacenter = data['datacenter']
            server_type_value = request.POST.get('server_type_value')
            deployment_count = int(data['deployment_count'])
            cpu = data['cpu']
            ram = data['ram']
            os = data['os']
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
            full_hostnames = data['full_hostnames']
            
            # Create a string with all form fields and their values
            #vm_details = "<br>".join([f"<strong>{key.capitalize()}</strong>: {value}" for key, value in data.items()])

            # Determine the correct label for the hostname
            hostname_label = "Hostname" if deployment_count == 1 else "Hostnames"
            vm_details = f"""
            <strong>{hostname_label}</strong>: {full_hostnames}<br>
            <strong>Ticket</strong>: {ticket}<br>
            <strong>Application Name</strong>: {appname}<br>
            <strong>Owner</strong>: {owner_value}<br>
            <strong>Datacenter</strong>: {datacenter}<br>
            <strong>Server Type</strong>: {server_type_value}<br>
            <strong>Deployment Count</strong>: {deployment_count}<br>
            <strong>CPU</strong>: {cpu}<br>
            <strong>RAM</strong>: {ram}<br>
            <strong>OS</strong>: {os_value}<br>
            <strong>Disk Size</strong>: {disk_size}<br>
            <strong>Cluster</strong>: {cluster}<br>
            <strong>Network</strong>: {network}<br>
            <strong>NFS Home</strong>: {nfs_home}<br>
            <strong>Additional Disks</strong>: {add_disks}<br>
            <strong>Additional Disk Size</strong>: {additional_disk_size}<br>
            <strong>Mount Path</strong>: {mount_path}<br>
            <strong>Join Centrify</strong>: {join_centrify}<br>
            <strong>Centrify Zone</strong>: {centrify_zone}<br>
            <strong>Centrify Role</strong>: {centrify_role}<br>
            <strong>Install Patches</strong>: {install_patches}<br>
            """
            # Flash message in Django
            from django.contrib import messages
            #messages.success(request, f'VM creation request submitted with the following details:\n\n{vm_details}')
            messages.success(request, mark_safe(f'VM creation request submitted with the following details:<br><br>{vm_details}'))

            
            print(form.cleaned_data)
            # Redirect or render success page
            form = VMCreationForm()    # Create a new, empty form
            return redirect('create_vm')
        
        if not form.is_valid():
            print(form.errors)  # Print form errors to see if there is an issue with validation

    else:
        form = VMCreationForm()    # Create a new, empty form

    return render(request, 'create_vm.html', {'form': form})

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
