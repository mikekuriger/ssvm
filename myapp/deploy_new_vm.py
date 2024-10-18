import subprocess
import os
import sys
import json
import socket
import yaml
import time
import argparse
import random
import django
import re
from datetime import datetime

# This script is called from deploy.py, to do the deployment
# deploy.py is called by the scheduler

# Ensure the script is aware of the Django settings module
sys.path.append('/home/mk7193/python/myproject') 
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.shortcuts import render, redirect, get_object_or_404
from django.utils.safestring import mark_safe
from django.conf import settings
from myapp.models import Deployment, Node, OperatingSystem, HardwareProfile, Status



# Set up argument parsing
parser = argparse.ArgumentParser(description='Deploy script with file input')
parser.add_argument('file', help='Name of the file to read for deployment')

# Parse the arguments
args = parser.parse_args()

# Use the provided file name
file_path = args.file

print(f"Deploying using file: {file_path}", flush=True)


# Dictionary to store the parsed values
data = {}

# Open and read the file line by line
with open(file_path, 'r') as f:
    for line in f:
        # Split each line into a key and value pair
        if ':' in line:
            key, value = line.split(':', 1)
            # Strip any whitespace and store in the dictionary
            data[key.strip()] = value.strip()


deployment_name = data.get("Deployment_id")
deployment_date = data.get("Deployment_date")
deployment_count = int(data.get("Deployment_count", 0))
# required for build
DOMAIN = data.get("Domain")
VM = data.get("Hostname")
OS = data.get("OS")
VERSION = data.get("VERSION")
CPU = int(data.get("CPU", 0))
MEM = int(data.get("RAM", 0)) * 1024  # it's in MB
DISK = int(data.get("Disk", 0))
DC = data.get("Datacenter")
VLAN = data.get("Network")
CLUSTER = data.get("Cluster")
TYPE = data.get("Type")
BUILTBY = data.get("Builtby")
TICKET = data.get("Ticket")
APPNAME = data.get("App_Name")
OWNER = data.get("Owner")
# options
ADDDISK = data.get("Add_disk")
centrify_zone = data.get("Centrify_zone") or "None"
centrify_role = data.get("Centrify_role")
CENTRIFY = data.get("Centrify")
PATCH = data.get("Patches")
NFS = data.get("NFS")


def get_datastorecluster(cluster_name):
    # Normalize the cluster name to lowercase and remove hyphens
    normalized_cluster = cluster_name.replace('-', '').lower()
    govc_command = ["govc", "datastore.cluster.info"]

    try:
        result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        #print(f"result - {result}")
        
        for line in result.stdout.splitlines():
            #print(f"Line - {line}")
            if "Name" in line and normalized_cluster in line:
                # Split line to get the second field (assuming it’s space-separated)
                datastorecluster_name = line.split()[1]
                #print(f"Using datastorecluster - {datastorecluster_name}")
                return datastorecluster_name
            
        #in case there is no datasource cluster, use the datastore directly
        rawdatastore_name = f"rawev3ds_{normalized_cluster}_01"
        #print(f"No Datastore Cluster found, using datastore {rawdatastore_name} directly")
        return rawdatastore_name
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr}", flush=True)
        return None

# set status to "building for the VM"
# The VM should already be there so update status if it is.
# If the VM is not there, add it with all the details

statusb_instance, statusb_created = Status.objects.get_or_create(
    name='building',
        defaults={
            'description': 'Node is building',  
        }
)

statuss_instance, statuss_created = Status.objects.get_or_create(
    name='setup',
        defaults={
            'description': 'Node is in setup',  
        }
)

statusf_instance, statusf_created = Status.objects.get_or_create(
    name='failed',
        defaults={
            'description': 'Build has failed',  
        }
)

statusi_instance, statusi_created = Status.objects.get_or_create(
    name='inservice',
        defaults={
            'description': 'Node is in production',  
        }
)

hwprofile_instance, hwprofile_created = HardwareProfile.objects.get_or_create(
    name='Vmware Virtual Platform',
        defaults={
            'description': 'Vmware Virtual Platform',  
        }
)

os_instance, created = OperatingSystem.objects.get_or_create(
                name=VERSION,
            )
            

node, created = Node.objects.update_or_create(
    name=f"{VM}.{DOMAIN}",  # The criteria for finding the VM
    defaults={
        'status': statusb_instance,
        'contact': OWNER,
        'centrify_zone': centrify_zone,
        'created_at': deployment_date,
        'processor_count': CPU,
        'disk_size': DISK,
        'physical_memory': MEM,
        'operating_system': os_instance,
        'hardware_profile': hwprofile_instance
        # Add other fields for initial creation as needed
        #operating_system=os_instance,  # we don't have this value here yet
        #physical_memory_kb = MEM * 1024,
        #serial_number - get at end
        #uniqueid - get at end
    }
)

# If updating an existing VM, only update the status field
if not created:
    node.status = statusb_instance
    node.save(update_fields=['status'])
    




from myapp.config_helper import load_config 
config = load_config()

# Define DNS and Domain information based on DC value
if DC == "st1":
    DNS = "10.6.1.111,10.4.1.111"
    DOMAINS = "corp.pvt dexmedia.com superpages.com supermedia.com prod.st1.yellowpages.com np.st1.yellowpages.com st1.yellowpages.com"
    
    # Network and Netmask selection based on VLAN
    if VLAN == "VLAN540":
        NETWORK = "10.5.32-VLAN540-DvS"
        NETMASK = "255.255.252.0"
    elif VLAN == "VLAN673":
        NETWORK = "10.5.106-VLAN673-DvS"
        NETMASK = "255.255.254.0"
    elif VLAN == "VLAN421":
        NETWORK = "10.5.4-VLAN421-DvS"
        NETMASK = "255.255.252.0"
    else:
        print(f"{VLAN} is not a valid VLAN", flush=True)
        
        node.status = statusf_instance
        node.save(update_fields=['status'])
        sys.exit(1)
    
    # Set the GOVC_URL environment variables for ST1 Vcenter
    pool = f"/st1dccomp01/host/{CLUSTER}/Resources"
    folder = "/st1dccomp01/vm/vRA - Thryv Cloud/TESTING"
    datacenter = config['datacenters'][DC]
    vcenter = datacenter['vcenter']
    username = datacenter['credentials']['username']
    password = datacenter['credentials']['password']
    os.environ["GOVC_URL"] = ("https://" + vcenter)
    os.environ["GOVC_USERNAME"] = username
    os.environ["GOVC_PASSWORD"] = password

else:
    DNS = "10.4.1.111,10.6.1.111"
    DOMAINS = "corp.pvt dexmedia.com superpages.com supermedia.com prod.ev1.yellowpages.com np.ev1.yellowpages.com ev1.yellowpages.com"
    
    # Network and Netmask selection based on VLAN
    if VLAN == "VLAN540":
        NETWORK = "10.2.32-VLAN540-DvS"
        NETMASK = "255.255.252.0"
    elif VLAN == "VLAN673":
        NETWORK = "10.4.106-VLAN673-DvS"
        NETMASK = "255.255.254.0"
    elif VLAN == "VLAN421":
        NETWORK = "10.2.4-VLAN421-DvS"
        NETMASK = "255.255.252.0"
    else:
        print(f"{VLAN} is not a valid VLAN", flush=True)
        
        node.status = statusf_instance
        node.save(update_fields=['status'])
        sys.exit(1)

    # Set the GOVC_URL environment variables
    pool = f"/ev3dccomp01/host/{CLUSTER}/Resources"
    folder = "/ev3dccomp01/vm/vRA - Thryv Cloud/TESTING"
    datacenter = config['datacenters'][DC]
    vcenter = datacenter['vcenter']
    username = datacenter['credentials']['username']
    password = datacenter['credentials']['password']
    os.environ["GOVC_URL"] = ("https://" + vcenter)
    os.environ["GOVC_USERNAME"] = username
    os.environ["GOVC_PASSWORD"] = password
    
GATEWAY = NETWORK.split('-')[0] + ".1"

# ANSI escape codes for bold text
bold = '\033[1m'
_bold = '\033[0m'
# Print deployment information
#print("Getting Datastore Cluster - ", end="", flush=True)

DATASTORECLUSTER = get_datastorecluster(CLUSTER)
if DATASTORECLUSTER.startswith("raw"):
    DATASTORE = DATASTORECLUSTER[3:]
    print(f"No Datastore Cluster found, using datastore {DATASTORE} directly", flush=True)    
else:    
    print(f"Using datastorecluster - {DATASTORECLUSTER}", flush=True)
print(f"{bold}Deploying {VM} to {CLUSTER}{_bold}", flush=True)



#Deployment details
print(f"{bold}Details:{_bold}", flush=True)
print(f"OS - {OS}", flush=True)
print(f"VERSION - {VERSION}", flush=True)
print(f"CPU - {CPU}", flush=True)
print(f"MEM - {MEM} MB", flush=True)
print(f"Disk - {DISK} GB", flush=True)
print(f"Datacenter - {DC}", flush=True)
print(f"Domain - {DOMAIN}", flush=True)
print(f"VLAN - {VLAN}", flush=True)
print(f"CLUSTER - {CLUSTER}", flush=True)
print(f"DNS - {DNS}", flush=True)
print(f"Domains - {DOMAINS}", flush=True)
print(f"Network - {NETWORK}", flush=True)
print(f"Netmask - {NETMASK}", flush=True)
print(f"Type - {TYPE}", flush=True)
print(f"Built by - {BUILTBY}", flush=True)
print(f"Ticket - {TICKET}", flush=True)
print(f"App Name - {APPNAME}", flush=True)
print(f"Owner - {OWNER}", flush=True)
print(f"Automount - {NFS}", flush=True)
print(f"Patches - {PATCH}", flush=True)
print(f"Centrify Join - {CENTRIFY}", flush=True)
print(f"centrify_zone - {centrify_zone}", flush=True)
print(f"centrify_role - {centrify_role}", flush=True)
print(f"Add_disk - {ADDDISK}", flush=True)
print()

# CLONE TEMPLATE
# Check if a VM with the same name already exists 
# remove yellowpages from name if it exists
if "yellowpages" in DOMAIN:
    govc_command = ["govc", "vm.info", f"{VM}.{DOMAIN}"]
    result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode == 0:
        govc_command = ["govc", "vm.change", "-name", VM, "-vm", f"{VM}.{DOMAIN}"]
        result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode == 0:
            print(f"Renamed {VM}.{DOMAIN} to {VM}")
        else:
            print(f"Failed to rename {VM}")
            print("Error:", set_result.stderr)    
            
             
print(f"{bold}Begin clone for deployment: {deployment_name}{_bold}", flush=True)
print()
try:
    govc_command = ["govc", "vm.info", VM]
    result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    vmstat = result.stdout

    # Check if the output contains the VM name and deployment_name
    print(f"{bold}Checking to see if a VM already exists with the name {VM}{_bold}", flush=True)
    if VM in vmstat:
        govc_command2 = ["govc", "vm.info", "-json", VM]
        result2 = subprocess.run(govc_command2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        vmstat2 = result2.stdout
        
        if deployment_name in vmstat2:
            print(f"{bold}{VM} exists with the same deploment_id, using current VM.  I'll use this for triggering a rebuild eventually.  Right now, all build operations will run, just skipping the clone operation{_bold}", flush=True)
            vm_rebuild='True'
        else:
            print(f"{bold}A VM with the name {VM} already exists, bailing out!{_bold}", flush=True)
            print(vmstat, flush=True)
            print(f"{bold}A VM with the name {VM} already exists, bailing out!{_bold}", flush=True)
            node.status = statusf_instance
            node.save(update_fields=['status'])
            sys.exit(1)
    else:
        print(f"{VM} does not exist", flush=True)

        # VM does not exist, proceed with clone
        print(f"{bold}Cloning template{_bold}", flush=True)
        if DATASTORECLUSTER.startswith("raw"):
            DATASTORE = DATASTORECLUSTER[3:]
            clone_command = [
                "govc", "vm.clone", "-on=false", "-vm", OS, "-c", str(CPU), "-m", str(MEM),
                "-net", NETWORK, "-pool", pool,
                "-ds", DATASTORE,
                "-folder", folder, VM
            ]
        else:
            clone_command = [
                "govc", "vm.clone", "-on=false", "-vm", OS, "-c", str(CPU), "-m", str(MEM),
                "-net", NETWORK, "-pool", pool,
                "-datastore-cluster", DATASTORECLUSTER,
                "-folder", folder, VM
            ]
        
        try:
            # Run the command with both stdout and stderr being captured in real-time LOGGING 
            with subprocess.Popen(clone_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
                last_logged_percentage = -10  # Start with a negative to ensure 0% logs initially if needed
                
                for line in process.stdout:
                    line = line.strip()  
                    # Use a regular expression to find the percentage
                    match = re.search(r"...(\d+)%\)", line)
                    if match:
                        current_percentage = int(match.group(1))

                        # Log progress only for every 10% increment
                        if current_percentage >= last_logged_percentage + 10:
                            last_logged_percentage = current_percentage
                            print(f"Progress: {line}")
                
                process.wait()  # Wait for the clone to complete

                # Check the return code and raise an error if the command failed
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, clone_command)

            # subprocess.run(clone_command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            print(f"{bold}Cloning completed for {VM}{_bold}", flush=True)
            
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while cloning the VM: {e.stderr}", flush=True)
            
            node.status = statusf_instance
            node.save(update_fields=['status'])
            sys.exit(1)
            
except subprocess.CalledProcessError as e:
    print(f"An error occurred while checking the VM (govc): {e.stderr}", flush=True)
    
    node.status = statusf_instance
    node.save(update_fields=['status'])
    sys.exit(1)

    
# print("Exiting early for testing")
# exit()

    
# Resize boot disk if needed
if DISK > 100 and OS != "SSVM-OEL7":
    boot_disk_size=(str(DISK) + "G")
    print(f"{bold}Resizing boot disk to {boot_disk_size}{_bold}", flush=True)
    subprocess.run(["govc", "vm.disk.change", "-vm", VM, "-disk.name", "disk-1000-0", "-size", str(boot_disk_size)], check=True)
else:
    print(f"{bold}Disk size is 100G (default), no resize needed{_bold}", flush=True)


# govc vm.info -json st1lndmike04 | jq '.virtualMachines[].config.hardware.device[] | select(.deviceInfo.label | test("Hard disk"))'


# if requested, add 2nd disk 
if ADDDISK == 'True':
    disk_size, label = ADDDISK.split(',')
    disk_name = (VM + "/" + VM + "_z")
    disk_size = (disk_size + "G")
    print(f"{bold}Adding 2nd disk - {disk_size}{_bold}", flush=True)

    datastore_result = subprocess.run(
        ["govc", "vm.info", "-json", VM], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True
    )
    datastore_json = json.loads(datastore_result.stdout)

    # Extract the datastore information
    datastore = None
    for device in datastore_json["virtualMachines"][0]["config"]["hardware"]["device"]:
        if "backing" in device and "fileName" in device["backing"] and device["backing"]["fileName"]:
            datastore = device["backing"]["fileName"]
            # Trim to get the datastore name
            datastore = datastore.split('[')[-1].split(']')[0]
            break

    if datastore:
        command = ["govc", "vm.disk.create", "-vm", VM, "-thick", "-eager", "-size", disk_size, "-name", disk_name, "-ds", datastore] 
        try:
            subprocess.run(command, check=True)
            print(f"Added a {disk_size} disk to {VM}", flush=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to add disk to {VM}: {e}", flush=True)
    else:
        print("No valid datastore found for the VM.", flush=True)
else:
    ADDDISK="False"


# Get MAC address of VM
print(f"{bold}Getting MAC address from vCenter, needed for adding to eIP{_bold}", flush=True)
mac_result = subprocess.run(
    ["govc", "vm.info", "-json", VM], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True
)

vm_info = json.loads(mac_result.stdout)

# Extract the MAC address
mac_address = None
for device in vm_info['virtualMachines'][0]['config']['hardware']['device']:
    if 'macAddress' in device:
        mac_address = device['macAddress']
        break

# Check if MAC address was found
if mac_address:
    print("MAC -", mac_address, flush=True)
else:
    print("No MAC address found for VM:", VM, flush=True)
    
    node.status = statusf_instance
    node.save(update_fields=['status'])
    sys.exit(1)


# Add VM to DNS and attempt resolution
def add_to_dns():
    sleep_delay=int(random.uniform(5, 30))
    time.sleep(sleep_delay)
    print(f"{bold}Sleeping for {sleep_delay} seconds{_bold}", flush=True)
    print(f"{bold}Adding {VM}.{DOMAIN} to DNS{_bold}", flush=True)

    from SOLIDserverRest import SOLIDserverRest
    import logging, math, ipaddress, pprint


    # Generate dc_to_dc from config
    def generate_dc_to_dc(config):
        return {dc_key: dc_data['name'] for dc_key, dc_data in config['datacenters'].items()}

    def get_space(name):
        parameters = {
            "WHERE": "site_name='{}'".format(name),
            "limit": "1"
        }

        rest_answer = SDS_CON.query("ip_site_list", parameters)

        if rest_answer.status_code != 200:
            logging.error("cannot find space %s", name)
            return None

        rjson = json.loads(rest_answer.content)

        return {
            'type': 'space',
            'name': name,
            'id': rjson[0]['site_id']
        }

    def get_subnet_v4(name, dc=None):
        parameters = {
            "WHERE": "subnet_name='{}' and is_terminal='1'".format(name),
            "TAGS": "network.gateway"
        }

        if dc is not None:
            parameters['WHERE'] = parameters['WHERE'] + " and parent_subnet_name='{}'".format(dc)

        rest_answer = SDS_CON.query("ip_subnet_list", parameters)

        if rest_answer.status_code != 200:
            logging.error("cannot find subnet %s", name)
            return None

        rjson = json.loads(rest_answer.content)

        return {
            'type': 'terminal_subnet',
            'dc': rjson[0]['parent_subnet_name'],
            'name': name,
            'addr': rjson[0]['start_hostaddr'],
            'cidr': 32-int(math.log(int(rjson[0]['subnet_size']), 2)),
            'gw': rjson[0]['tag_network_gateway'],
            'used_addresses': rjson[0]['subnet_ip_used_size'],
            'free_addresses': rjson[0]['subnet_ip_free_size'],
            'space': rjson[0]['site_id'],
            'id': rjson[0]['subnet_id']
        }

    def get_next_free_address(subnet_id, number=1, start_address=None):
        parameters = {
            "subnet_id": str(subnet_id),
            "max_find": str(number),
        }

        if start_address is not None:
            parameters['begin_addr'] = str(ipaddress.IPv4Address(start_address))

        rest_answer = SDS_CON.query("ip_address_find_free", parameters)

        if rest_answer.status_code != 200:
            logging.error("cannot find subnet %s", name)
            return None

        rjson = json.loads(rest_answer.content)

        result = {
            'type': 'free_ip_address',
            'available': len(rjson),
            'address': []
        }

        for address in rjson:
            result['address'].append(address['hostaddr'])

        return result

    def add_ip_address(ip, name, space_id, mac_addr):
        parameters = {
            "site_id": str(space_id),
            "hostaddr": str(ipaddress.IPv4Address(ip)),
            "name": str(name),
            "mac_addr": str(mac_addr)
        }

        rest_answer = SDS_CON.query("ip_address_create", parameters)

        if rest_answer.status_code != 201:
            logging.error("cannot add IP node %s", name)
            return None

        rjson = json.loads(rest_answer.content)

        return {
           'type': 'add_ipv4_address',
           'name': str(name),
           'id': rjson[0]['ret_oid'],
        }

    # main program

    # Extract details from the config
    datacenter = config['datacenters'][DC]
    master = datacenter['eipmaster']
    username = datacenter['eip_credentials']['username']
    password = datacenter['eip_credentials']['password']
    vlans = datacenter['vlans']

    SDS_CON = SOLIDserverRest(master)
    SDS_CON.set_ssl_verify(False)
    SDS_CON.use_basicauth_sds(user=username, password=password)

    # get space (site id)
    space = get_space("thryv-eip-ipam")

    # Dynamic VLAN to subnet mapping
    network_to_subnet = vlans
    dc_to_dc = generate_dc_to_dc(config)

    dc = dc_to_dc.get(DC, "Unknown DC")
    vlan = network_to_subnet.get(VLAN, "Unknown Network")

    subnet = get_subnet_v4(vlan)
    #print(subnet)

    # get next free address (pick 5 free IPs, skip the first 20)
    ipstart = ipaddress.IPv4Address(subnet['addr']) + 50
    free_address = get_next_free_address(subnet['id'], 5, ipstart)
    #pprint.pprint(free_address)

    # add ip to IPAM
    hostname = f"{VM}.{DOMAIN}"
    mac_addr = mac_address
    node = add_ip_address(free_address['address'][2],hostname,space['id'],mac_addr)
    #print(node)
    print(free_address['address'][2])

    del(SDS_CON)

def resolve_dns():
    max_retries = 30
    retry_delay = 30
    
    for attempt in range(max_retries):
        try:
            ip_address = socket.gethostbyname(f"{VM}.{DOMAIN}")
            print(f"{VM}.{DOMAIN} resolves to {ip_address}", flush=True)
            return ip_address
        except socket.gaierror:
            if attempt == 0:
                # Only attempt to add to DNS on the first failure
                add_to_dns()
            time.sleep(retry_delay)
    
    # If all attempts fail, exit with error
    print(f"{bold}Failed to resolve {VM}.{DOMAIN} after {max_retries} attempts!{_bold}", flush=True)
    
    node.status = statusf_instance
    node.save(update_fields=['status'])
    sys.exit(1)

# Run the DNS check and get the IP
IP = resolve_dns()



# Power off VM if necessary
print(f"{bold}Powering off {VM} in case it's on{_bold}", flush=True)
power_status = subprocess.run(["govc", "vm.info", VM], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)
if "poweredOn" in power_status.stdout:
    subprocess.run(["govc", "vm.power", "-off", "-force", VM], check=True)

    
    
# Customize hostname and IP
# (cpu, memory, disk are set during clone)
print(f"{bold}Customizing hostname, and IP (these settings are stored in vcenter and applied at first boot){_bold}", flush=True)
customize_command = [
    "govc", "vm.customize", "-vm", VM, "-type", "Linux", "-name", VM, "-domain", DOMAIN,
    "-mac", mac_address, "-ip", IP, "-netmask", NETMASK, "-gateway", GATEWAY, "-dns-server", DNS,
    "-dns-suffix", DOMAINS
]

result = subprocess.run(customize_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

if result.returncode != 0:
    if "Guest Customization is already pending" in result.stderr:
        print("Customization is already pending for this VM.", flush=True)
    else:
        print("An error occurred while executing the command:", flush=True)
        print("Command:", result.args, flush=True)
        print("Return Code:", result.returncode, flush=True)
        print("Standard Output:", result.stdout, flush=True)
        print("Standard Error:", result.stderr, flush=True)
else:
    # Success case
    print(result.stdout, flush=True)



# tag the VM with our deployment_id so that we can determine if it's ours 
# this will be used when someone tries to re-deploy, delete, etc

# for py3.7
# fields_set_command = ["govc", "fields.set", "deployment", deployment_name, folder]
# set_result = subprocess.run(fields_set_command, capture_output=True, text=True)

# custom fields in VCenter
fields_set_command = ["govc", "fields.set", "deployment", deployment_name, f"{folder}/{VM}"]
set_result = subprocess.run(fields_set_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

if set_result.returncode == 0:
    print("Custom field 'deployment' set successfully.")
else:
    print("Failed to set custom field 'deployment'.")
    print("Error:", set_result.stderr)

fields_set_command = ["govc", "fields.set", "Created_by", "Michael Kuriger (mk7193)", f"{folder}/{VM}"]
#fields_set_command = ["govc", "fields.set", "Created_by", "Michael Kuriger", f"{folder}/{VM}"]
set_result = subprocess.run(fields_set_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                      
if set_result.returncode == 0:
    print("Custom field 'createdby' set successfully.")
else:
    print("Failed to set custom field 'createdby'.")
    print("Error:", set_result.stderr)

# grab cmdb_uuid_value to put into the database at end of build
govc_command = ["govc", "vm.info", "-json", VM]
uuid_result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
if uuid_result.returncode == 0:
    vm_info = json.loads(uuid_result.stdout)
    custom_values = vm_info.get("virtualMachines", [])[0].get("customValue", [])
    cmdb_uuid_value = None
    for field in custom_values:
        if field.get("key") == 1001: #this is the cmdb_uuid
            cmdb_uuid_value = field.get("value")
            break
                      
    if cmdb_uuid_value:
        print("cmdb_uuid value:", cmdb_uuid_value)
    else:
        print("cmdb_uuid value not found.")
                      
    vm_values = vm_info.get("virtualMachines", [{}])[0] 
    config = vm_values.get("config", {})

    uuid_value = config.get("uuid")
    #name = config.get("name")
                      
    if uuid_value:
        print("uuid value:", uuid_value)
    else:
        print("uuid value not found.")
else:
    print("Failed to retrieve VM info.")
    print("Error:", uuid_result.stderr)                    
    
# Generate ISO files for cloud-init
from jinja2 import Environment, FileSystemLoader

print(f"{bold}Generating ISO files for cloud-init{_bold}", flush=True)

if ADDDISK:
    mountdisks = f"/vra_automation/installs/mount_extra_disks.sh"
    dumpdisks = f"echo '{ADDDISK}' >> /etc/vra.disk"
else:
    mountdisks = ""
    dumpdisks = ""
        
if centrify_zone:
    adjoin = f"/usr/sbin/adjoin --server DFW2W2SDC05.corp.pvt -z {centrify_zone} -R {centrify_role} " \
             "-c OU=Computers,OU=Centrify,DC=corp,DC=pvt -f corp.pvt -u svc_centrify -p '#xupMcMlURubO2|'"

    centrify_sshd = f"sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication yes/' " \
                    "/etc/centrifydc/ssh/sshd_config; systemctl mask sshd; systemctl enable " \
                    "centrify-sshd; mv /usr/bin/sudo /usr/bin/sudo.pre.cfy; ln -s /usr/bin/dzdo /usr/bin/sudo"
else:
    adjoin = ""
    centrify_sshd = ""

yumupdate = f"/usr/bin/yum update -y"
automount_homedir = f"/vra_automation/installs/automount_homedir.sh"

# future maybe
fyptools_install = f"/vra_automation/installs/fyptools_install.sh"
cohesity_install = f"/vra_automation/installs/cohesity_install.sh"

# get date
now = datetime.now()
date = now.strftime("%Y-%m-%dT%H:%M:%S")

# Set up Jinja2 environment and load the template file
env = Environment(loader=FileSystemLoader(searchpath=os.path.join(settings.BASE_DIR, 'myapp', 'templates')))
usertemplate = env.get_template("user_data_template.j2")
metatemplate = env.get_template("meta_data_template.j2")
  
# Values to populate in the template from arguments
template_data = {
    'vm': f"{VM}.{DOMAIN}",
    'date': date,
    'type': TYPE,
    'builtby': BUILTBY,
    'ticket': TICKET,
    'appname': APPNAME,
    'owner': OWNER,
    'patch': PATCH,
    'yumupdate': yumupdate,
    'dumpdisks': dumpdisks,
#    'disk_size': args.disk_size,
    'adddisk': ADDDISK,
    'mountdisks': mountdisks,
    'automount_homedir': automount_homedir,
    'automount': NFS,
    'adjoin': adjoin,
    'centrify_sshd': centrify_sshd,
    'centrify_zone': centrify_zone
}
   
# Render the user-data and meta-data
user_data = usertemplate.render(template_data)
meta_data = metatemplate.render(template_data)

# Directory to save the file  
output_dir = os.path.join(settings.BASE_DIR, 'myapp', 'cloud-init-images', f"{VM}.{DOMAIN}")

# Create the full paths for the ISO file and other necessary files
iso_file = os.path.join(output_dir, "seed.iso")
user_data_file = os.path.join(output_dir, "user-data")
meta_data_file = os.path.join(output_dir, "meta-data")

# Create the directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Write user-data
output_file = f'{output_dir}/user-data'
with open(output_file, 'w') as f:
    f.write(user_data)

# Write meta-data
output_file = f'{output_dir}/meta-data'
with open(output_file, 'w') as f:
    f.write(meta_data)

    
# Create the ISO image (bash command)
# Determine the OS
import platform
os_type = platform.system()
iso_command = [
    "-o", iso_file, "-volid", "cidata", "-joliet", "-rock", user_data_file, meta_data_file
]
print(os_type)

print(f"{bold}Creating ISO image for cloud-init{_bold}", flush=True)

if os_type == "Linux":
    subprocess.run(
        ["genisoimage"] + iso_command,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True
    )
elif os_type == "Darwin":  # macOS is identified as "Darwin"
    subprocess.run(
        ["mkisofs"] + iso_command,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True
    )
else:
    raise EnvironmentError("Unsupported operating system for this script")



# Copy the ISO image to the VM's datastore
print(f"{bold}Copying the ISO to the VM's datastore{_bold}", flush=True)
datastore_result = subprocess.run(
    ["govc", "vm.info", "-json", VM], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True
)

datastore_json = json.loads(datastore_result.stdout)

# Extract the datastore information
datastore = None
for device in datastore_json["virtualMachines"][0]["config"]["hardware"]["device"]:
    if "backing" in device and "fileName" in device["backing"] and device["backing"]["fileName"]:
        datastore = device["backing"]["fileName"]
        # Trim to get the datastore name
        datastore = datastore.split('[')[-1].split(']')[0]
        break

# Check if the datastore was found
if datastore:
    # Run the command to upload the ISO to the VM's datastore
    subprocess.run(
        ["govc", "datastore.upload", "-ds", datastore, iso_file, f"{VM}/seed.iso"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True
    )
else:
    print("No valid datastore found for the VM.", flush=True)



# Mount the ISO to the VM and power it on
print(f"{bold}Attach the ISO to the VM{_bold}", flush=True)
cd_device = subprocess.run(["govc", "device.ls", "-vm", VM], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True).stdout.splitlines()
cdrom_device = [line.split()[0] for line in cd_device if "cdrom" in line][0]
subprocess.run(["govc", "device.cdrom.insert", "-vm", VM, "-device", cdrom_device, "-ds", datastore, f"{VM}/seed.iso"], check=True)
#print(f"ISO has been inserted into the CDROM", flush=True)
time.sleep(int(random.uniform(1, 3)))
subprocess.run(["govc", "device.connect", "-vm", VM, cdrom_device], check=True)
#print(f"ISO has been inserted and attached to {VM}", flush=True)

print(f"{bold}Power on the VM, then check status{_bold}", flush=True)
time.sleep(int(random.uniform(1, 3)))
subprocess.run(["govc", "vm.power", "-on", VM], check=True)

# Wait a bit, then check to see if VM will stay powered up, if not not sure what to do...
time.sleep(15)
power_status = subprocess.run(["govc", "vm.info", VM], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)

# update details in cmdb
now = datetime.now()
node = Node.objects.get(name=f"{VM}.{DOMAIN}")
node.status = statuss_instance
node.updated_at = now
node.uniqueid = cmdb_uuid_value
node.serial_number = uuid_value

if "yellowpages" in DOMAIN:
    govc_command = ["govc", "vm.change", "-name", f"{VM}.{DOMAIN}", "-vm", VM]
    result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode == 0:
        print(f"{VM} has been renamed to {VM}.{DOMAIN}")
    else:
        print(f"Failed to rename {VM}")
        print("Error:", set_result.stderr)

                            
if "poweredOn" in power_status.stdout:
    print(f"{VM} is powered up and booting. Cloud-init will now perform post-deployment operations.  Please be patient, this can take a while", flush=True)

    # Update the specific fields
    node.status = statuss_instance

else:
    print(f"{VM} did not power on after the build.  Please check with the Unix team for assistance.", flush=True)
    node = Node.objects.get(name=f"{VM}.{DOMAIN}")

    # Update the specific fields
    node.status = statusf_instance

# Save the changes
node.save(update_fields=['status', 'updated_at', 'uniqueid', 'serial_number'])