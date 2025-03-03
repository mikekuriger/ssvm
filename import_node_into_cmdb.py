#!/usr/bin/env python

import sys
sys.path.append('/home/mk7193/python/myenv/lib/python3.6/site-packages')
from collections import defaultdict
from datetime import datetime
import argparse
import os
import pprint
import re
import subprocess
import xml.etree.ElementTree as ET
import time
import shutil


# Set up Django environment
sys.path.append('/home/mk7193/python/myproject') 
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

import django
django.setup()

from myapp.models import Node, OperatingSystem, Status, HardwareProfile


def get_dmidecode_output():
    try:
        # Using Popen instead of subprocess.run for Python 2.6 compatibility
        result = subprocess.Popen(['dmidecode'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _ = result.communicate()
        return stdout.decode('utf-8') if isinstance(stdout, bytes) else stdout
    except subprocess.CalledProcessError as e:
        print("Error running dmidecode: {}".format(e))
        return None

def parse_dmidecode(output):
    dmidata = defaultdict(list)
    dmi_section = None
    dmi_section_data = {}
    dmi_section_array = None

    for line in output.splitlines():
        if line.startswith("Handle"):
            if dmi_section and dmi_section_data:
                # Store current section data into dmidata
                tmp = dict(dmi_section_data)  # copy current section data
                dmidata[dmi_section].append(tmp)
                dmi_section_data = {}  # reset for the next section

            dmi_section = None
            dmi_section_array = None
        elif line.startswith("DMI type"):
            continue
        elif dmi_section is None and line.strip():
            # Set section name
            dmi_section = line.strip()
        elif dmi_section and re.match(r"^\s*([^:]+):\s*(\S.*)", line):
            key, value = re.match(r"^\s*([^:]+):\s*(\S.*)", line).groups()
            dmi_section_data[key] = value
            dmi_section_array = None
        elif dmi_section and re.match(r"^\s*([^:]+):$", line):
            dmi_section_array = line.strip().rstrip(":")
        elif dmi_section and dmi_section_array and line.strip():
            dmi_section_data.setdefault(dmi_section_array, []).append(line.strip())
    
    if dmi_section and dmi_section_data:
        dmidata[dmi_section].append(dmi_section_data)

    return dmidata

def get_host_info():
    dmidecode_output = get_dmidecode_output()
    if not dmidecode_output:
        print("Failed to retrieve dmidecode output")
        return

    dmidata = parse_dmidecode(dmidecode_output)
    host_info = 'Unknown'
    host_model = 'Unknown'
    host_serial = 'Unknown'
    
    if "System Information" in dmidata:
        for entry in dmidata["System Information"]:
            host_info = entry.get('Manufacturer', 'Unknown')
            host_model = entry.get('Product Name', 'Unknown')
            host_serial = entry.get('Serial Number', 'Unknown')
            break  # Stop after the first match

    return host_info, host_model, host_serial

def get_cpu_info():
    dmidecode_output = get_dmidecode_output()
    if not dmidecode_output:
        print("Failed to retrieve dmidecode output")
        return
    
    cpu_count = 0
    dmidata = parse_dmidecode(dmidecode_output)
    if "Processor Information" in dmidata and dmidata["Processor Information"]:
        cpu_info=dmidata["Processor Information"][0].get('Manufacturer')
        cpu_model=dmidata["Processor Information"][0].get('Family')
        cpu_version=dmidata["Processor Information"][0].get('Version')
        cpu_speed=dmidata["Processor Information"][0].get('Current Speed')

        if cpu_version and cpu_version != "Not Specified" and (not cpu_model or cpu_model == "Unknown"):
            cpu_model = cpu_version
            cpu_version = ""

        for entry in dmidata["Processor Information"]:
            cpu_status=entry.get('Status')
            if "Populated" in cpu_status:
                cpu_count += 1
    
        # cpu core count
        cpu_core_count = 0
        cpu_socket_count = 0
        cores = {}
        sockets = set()

        # Check if we're on a Linux system
        if os.name == 'posix' and os.path.isfile('/proc/cpuinfo'):

            with open('/proc/cpuinfo', 'r') as cpuinfo:
                physical_id = None
                core_id = None

                for line in cpuinfo:
                    if line.startswith('processor'):
                        physical_id = None
                        core_id = None
                    elif line.startswith('physical id'):
                        physical_id = line.split(':')[1].strip()
                        sockets.add(physical_id)
                    elif line.startswith('core id'):
                        core_id = line.split(':')[1].strip()

                    if physical_id is not None and core_id is not None:
                        # Each unique physical_id and core_id pair represents a core
                        cores["{0}:{1}".format(physical_id, core_id)] = 1

            # Determine core count based on unique (physical_id, core_id) pairs
            cpu_core_count = len(cores)
            cpu_socket_count = len(sockets)
            
        return cpu_info, cpu_model, cpu_version, cpu_speed, cpu_count, cpu_core_count, cpu_socket_count



def get_physical_memory():
    physical_memory = 0
    memory_sizes = []  # Initialize an empty list to match the original return pattern

    try:
        with open('/proc/meminfo', 'r') as meminfo:
            for line in meminfo:
                if line.startswith('MemTotal'):
                    # MemTotal is in kilobytes, so we convert to megabytes
                    physical_memory_kb = int(line.split()[1])
                    physical_memory_mb = physical_memory_kb // 1024  # Convert to MB
                    return physical_memory_mb, memory_sizes  # Return both values
    except IOError:
        print("Failed to read /proc/meminfo")
        return None, None








def get_first_nic_hwaddr():
    try:
        result = subprocess.Popen(['ip', 'link', 'show'], stdout=subprocess.PIPE)
        output, _ = result.communicate()
        for line in output.splitlines():
            line = line.strip()
            if re.search(r'link/ether', line):
                return line.split()[1]
    except OSError as e:
        print("Error running ip link show: {}".format(e))
    return None

def get_uniqueid():

    dmidecode_output = get_dmidecode_output()
    if not dmidecode_output:
        print("Failed to retrieve dmidecode output")
        return None

    dmidata = parse_dmidecode(dmidecode_output)

    if dmidata and 'System Information' in dmidata and dmidata['System Information']:
        # Access the first item in the list if 'System Information' is a list
        uniqueid = dmidata['System Information'][0].get('UUID')

    if not uniqueid:
        uniqueid = get_first_nic_hwaddr()
        if not uniqueid:
            raise RuntimeError("Unable to find a uniqueid")

    return uniqueid

def get_swap_space():
    swap_total = 0
    swap_free = 0
    swap_used = 0

    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('SwapTotal'):
                    swap_total = int(line.split()[1])  # Value in kB
                elif line.startswith('SwapFree'):
                    swap_free = int(line.split()[1])  # Value in kB
        swap_used = swap_total - swap_free
    except IOError as e:
        print("Error reading /proc/meminfo: {}".format(e))
        return None

    # Convert values from kB to MB
    swap_total_mb = swap_total / 1024
    swap_free_mb = swap_free / 1024
    swap_used_mb = swap_used / 1024

    return swap_total_mb

def get_kernel_version():
    try:
        kernel_version = subprocess.Popen(['uname', '-r'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = kernel_version.communicate()

        if kernel_version.returncode != 0:
            print("Error retrieving kernel version: {}".format(error))
            return None

        return output.strip().decode('utf-8')
        
    except Exception as e:
        print("An error occurred: {}".format(e))
        return None
    
def get_timezone():
    try:
        # Get the current time's timezone offset in seconds from UTC
        offset = -time.timezone if time.localtime().tm_isdst == 0 else -time.altzone
        # Convert offset to hours and minutes
        offset_hours = offset // 3600
        offset_minutes = (offset % 3600) // 60
        # Format the timezone string
        timezone_str = "UTC{:+03d}:{:02d}".format(offset_hours, offset_minutes)
        return timezone_str

    except Exception as e:
        print("An error occurred while retrieving the timezone: {}".format(e))
        return None

def get_disk_usage():
    try:
        # Get disk usage statistics for the root filesystem
        total, used, free = shutil.disk_usage("/")
        
        # Convert used space to megabytes
        used_space = used // (1024 * 1024 )
        avail_space = free // (1024 * 1024 )
        
        return used_space, avail_space
    
    except Exception as e:
        print("An error occurred while retrieving filesystem usage: {}".format(e))
        return None
    

def get_centrify_zone():
    try:
        result = subprocess.Popen(['adinfo'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, _ = result.communicate()
        
        # Decode if necessary (for Python 3)
        if isinstance(output, bytes):
            output = output.decode('utf-8')
        
        # Split output by lines and find the line that starts with "Zone:"
        for line in output.splitlines():
            if line.startswith("Zone:"):
                # Extract only the last part after the last '/'
                zone = line.split('/')[-1].strip()
                return zone
        print("Zone not found in adinfo output.")
        return None
    except Exception as e:
        print("Error running adinfo: {}".format(e))
        return None





    

def import_node(hw_name, hw_model, owner, serial, processor_manufacturer, processor_model, processor_speed, processor_socket_count, processor_core_count, processor_count, physical_memory, physical_memory_sizes, swap, uniqueid, kernel_version, timezone, used_space, avail_space, centrify_zone):
    
    import platform
    os_name, os_version, _ = platform.linux_distribution()
    os_value=os_name + ' ' + os_version
    
    # Attempt to get or create the OS, Status, and Hardware Profile instances
    os_instance, _ = OperatingSystem.objects.get_or_create(name=os_value)
    status_instance, _ = Status.objects.get_or_create(
        name='setup',
        defaults={'description': 'Node is not in production'}
    )
    hwprofile_instance, _ = HardwareProfile.objects.get_or_create(
        #name='Vmware Virtual Platform',
        #defaults={'description': 'Vmware Virtual Platform'}
        name=hw_name,
        defaults={'description': hw_model}
    )

    #updated_at = datetime.now().date() Not needed, this field updates automatically in model
    
    import socket
    hostname = socket.gethostname()
    

    
    # Attempt to update or create the Node instance
    node, created = Node.objects.update_or_create(
        name=hostname,
        defaults={
            'contact': owner,
            'serial_number': serial,
            'processor_manufacturer': processor_manufacturer,
            'processor_model': processor_model,
            'processor_speed': processor_speed,
            'processor_socket_count': processor_socket_count,
            'processor_core_count': processor_core_count,
            'processor_count': processor_count,
            'physical_memory': physical_memory,
            'physical_memory_sizes': physical_memory_sizes,
            'swap': swap,
            'uniqueid': uniqueid,
            'kernel_version': kernel_version,
            'timezone': timezone,
            'used_space': used_space,
            'avail_space': avail_space,
            'centrify_zone': centrify_zone,
            'operating_system': os_instance,
            'status': status_instance,
            "centrify_zone": centrify_zone,
            'hardware_profile': hwprofile_instance
        }
    )
    
    #Only set 'created_at' if the node was just created
    if created:
        node.created_at = datetime.now().date()
        node.save(update_fields=['created_at'])

    action = "created" if created else "updated"
    print(f"Successfully {action} node: {node.name}")
 

    

if __name__ == "__main__":

    # get details from functions:
    host_info, host_model, host_serial = get_host_info()
    if host_info:
        hw_manufacturer=host_info
        hw_model=host_model
        hw_name=hw_manufacturer + hw_model
        serial=host_serial

    cpu_info, cpu_model, cpu_version, cpu_speed, cpu_count, cpu_core_count, cpu_socket_count = get_cpu_info() 
    if cpu_info:
        processor_manufacturer=cpu_info
        processor_model=cpu_model
        #print("CPU Version: {0}".format(cpu_version))   
        processor_speed=cpu_speed
        processor_socket_count=cpu_socket_count
        processor_count=cpu_count
        processor_core_count=cpu_core_count
        
    memory, memory_sizes = get_physical_memory()
    if memory:
        physical_memory=memory
        physical_memory_sizes=memory_sizes
        
    swap_space = get_swap_space()
    if swap_space:
        swap=swap_space

    unique_id = get_uniqueid()
    if unique_id:
        uniqueid=unique_id
        
    kernel_version = get_kernel_version()
    if kernel_version:
        kernel_version=kernel_version
    
    timezone = get_timezone()
    if timezone:
        timezone=timezone
    
    used_space, avail_space = get_disk_usage()
    if used_space:
        used_space=used_space
        avail_space=avail_space
        print(f"used: {used_space} MB")
        print(f"avail: {avail_space} MB")

    centrify_zone = get_centrify_zone()
    if centrify_zone:
        centrify_zone=centrify_zone

    # Call the function with parsed arguments
    import_node(
        hw_name=hw_name,
        hw_model=hw_model,
        owner='mk7193',
        serial=serial,
        processor_manufacturer=processor_manufacturer,
        processor_model=processor_model,
        processor_speed=processor_speed,
        processor_socket_count=processor_socket_count,
        processor_core_count=processor_core_count,
        processor_count=processor_count,
        physical_memory=physical_memory,
        physical_memory_sizes=physical_memory_sizes,
        swap=swap,
        uniqueid=uniqueid,
        kernel_version=kernel_version,
        timezone=timezone,
        used_space=used_space,
        avail_space=avail_space,
        centrify_zone=centrify_zone
    )


