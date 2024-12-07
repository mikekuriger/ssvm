#!/usr/bin/env python3

import sys
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
import distro
import socket
import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning


def get_dmidecode_output():
    try:
        result = subprocess.run(['sudo', 'dmidecode'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)
        return result.stdout
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
                    physical_memory_mb = physical_memory_kb // 1024 // 1024  # Convert to GB
                    return physical_memory_mb, memory_sizes  
    except IOError:
        print("Failed to read /proc/meminfo")
        return None, None



def get_first_nic_hwaddr():
    try:
        result = subprocess.run(['ip', 'link', 'show'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)
        for line in result.stdout.splitlines():
            line = line.strip()
            if re.search(r'link/ether', line):
                return line.split()[1]  # Extract the MAC address
    except subprocess.CalledProcessError as e:
        print(f"Error running ip link show: {e.stderr}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    return None


    
def convert_dmi_to_vcenter(dmi_uuid):
    # Split the DMI UUID into its components
    parts = dmi_uuid.split('-')
    
    # Reverse the byte order of the first three groups
    part1 = ''.join(reversed([parts[0][i:i+2] for i in range(0, len(parts[0]), 2)]))
    part2 = ''.join(reversed([parts[1][i:i+2] for i in range(0, len(parts[1]), 2)]))
    part3 = ''.join(reversed([parts[2][i:i+2] for i in range(0, len(parts[2]), 2)]))
    
    # Keep the last two groups unchanged
    part4 = parts[3]
    part5 = parts[4]
    
    # Reassemble the vCenter UUID
    vcenter_uuid = f"{part1}-{part2}-{part3}-{part4}-{part5}"
    return vcenter_uuid

    
    
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

    return convert_dmi_to_vcenter(uniqueid)


    
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
    swap_total_mb = round(swap_total / 1024)
    swap_free_mb = round(swap_free / 1024)
    swap_used_mb = round(swap_used / 1024)

    return swap_total_mb



def get_kernel_version():
    try:
        kernel_version = subprocess.run(['uname', '-r'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

        if kernel_version.returncode != 0:
            print("Error retrieving kernel version: {}".format(error))
            return None
            
        return kernel_version.stdout.strip()
        
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
        result = subprocess.run(['adinfo'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        for line in result.stdout.splitlines():
            if line.startswith("Zone:"):
                # Extract only the last part after the last '/'
                zone = line.split('/')[-1].strip()
                return zone
        #print("Zone not found in adinfo output.")
        return None
    except Exception as e:
        print("Error running adinfo: {}".format(e))
        return None


if __name__ == "__main__":

    # get details from functions:
    hostname = socket.gethostname()
    
    now = datetime.now()
    created_at = now.strftime('%Y-%m-%dT%H:%M')
    
    host_info, host_model, host_serial = get_host_info()
    if host_info:
        hw_manufacturer=host_info
        hw_desc=host_model
        hw_name=host_info + ' ' + host_model
        serial_number=host_serial

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

    centrify_zone = get_centrify_zone()
    if centrify_zone:
        centrify_zone=centrify_zone

        
    os_name = distro.name(pretty=True)
    os_varient = distro.name()
    os_version = distro.version()
    os_vendor = distro.id()
    
        #hw_manufacturer=host_info
        #hw_desc=host_model
        #hw_name=host_info + ' ' + host_model

    # print(f"name - {hostname}")
    # print(f"serial_number - {serial_number}")
    # print(f"processor_manufacturer - {processor_manufacturer}")
    # print(f"processor_model - {processor_model}")
    # print(f"processor_speed - {processor_speed}")
    # print(f"processor_socket_count - {processor_socket_count}")
    # print(f"processor_core_count - {processor_core_count}")
    # print(f"processor_count - {processor_count}")
    # print(f"physical_memory - {physical_memory}")
    # print(f"physical_memory_sizes - {physical_memory_sizes}")
    # print(f"swap - {swap}")
    # print(f"uniqueid - {uniqueid}")
    # print(f"kernel_version - {kernel_version}")
    # print(f"timezone - {timezone}")
    # print(f"used_space - {used_space}")
    # print(f"avail_space - {avail_space}")
    # print(f"centrify_zone - {centrify_zone}")
    # print(f"created_at - {created_at}")
    # print(f"* operating_system - {os_name}, {os_varient}, {os_version}, {os_vendor}")
    # print(f"* hardware_profile - {hw_name}, {hw_manufacturer}, {hw_desc}")

    # sys.exit(0)

    SVR = 'st1lndssvm01.corp.pvt'
    url = f"https://{SVR}/api/register_node/"
    data = {
        "name": hostname,
        "serial_number": serial_number,
        "processor_manufacturer": processor_manufacturer,
        "processor_model": processor_model,
        "processor_speed": processor_speed,
        "processor_socket_count": processor_socket_count,
        "processor_core_count": processor_core_count,
        "processor_count": processor_count,
        "physical_memory": physical_memory,
        # "physical_memory_sizes": physical_memory_sizes,
        "physical_memory_sizes": ', '.join(physical_memory_sizes) if physical_memory_sizes else '',
        "swap": swap,
        "uniqueid": uniqueid,
        "kernel_version": kernel_version,
        "timezone": timezone,
        "used_space": used_space,
        "avail_space": avail_space,
        "centrify_zone": centrify_zone,
        "os_name": os_name,
        "os_varient": os_varient,
        "os_version": os_version,
        "os_vendor": os_vendor,
        "hw_name": hw_name,
        "hw_manufacturer": hw_manufacturer,
        "hw_desc": hw_desc,
    }

    #print(data)
    #sys.exit(0)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', InsecureRequestWarning)
        response = requests.post(url, json=data, verify=False)
        
    #print(response.json())

    if response.status_code == 200:
        print(f"Registration succeeded")
    else:
        print(f"Status Code: {response.status_code}")
        print(f"Response Content: {response.text}")

