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

# Ensure the script is aware of the Django settings module
sys.path.append('/home/mk7193/python/myproject') 
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

# Set up Django
django.setup()

from django.conf import settings
#from myapp.config_helper import load_config

# Set up argument parsing
parser = argparse.ArgumentParser(description='Deploy script with file input')
parser.add_argument('file', help='Name of the file to read for deployment')

# Parse the arguments
args = parser.parse_args()

# Use the provided file name
file_path = args.file

# Path to your file
#file_path = ('/home/mk7193/python/myproject/media/' + file)

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

# not used yet
deployment_name = data.get("Deployment_name")
deployment_date = data.get("Deployment_date")
deployment_count = int(data.get("Deployment_count", 0))
# required for build
DOMAIN = "corp.pvt"
VM = data.get("Hostname")
OS = data.get("OS")
CPU = int(data.get("CPU", 0))
MEM = int(data.get("RAM", 0)) * 1024  # it's in MB
DISK = int(data.get("Disk", 0))
DC = data.get("Datacenter")
VLAN = data.get("Network")
CLUSTER = data.get("Cluster")
TYPE = data.get("Type")
BUILTBY = "mk7193"
TICKET = data.get("Ticket")
APPNAME = data.get("App_Name")
OWNER = data.get("Owner")
# options
ADDDISK = data.get("Add_disk")
centrify_zone = data.get("Centrify_zone")
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
        for line in result.stdout.splitlines():
            if "Name" in line and normalized_cluster in line:
                # Split line to get the second field (assuming it’s space-separated)
                datastore_name = line.split()[1]
                return datastore_name
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr}", flush=True)
        return None


def load_config():
    file_path = os.path.join(settings.BASE_DIR, 'myapp', 'config.yaml')
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config
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
        sys.exit(1)
    
    # Set the GOVC_URL environment variables for ST1 Vcenter
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
        sys.exit(1)

    # Set the GOVC_URL environment variables
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
#print(DATASTORECLUSTER, flush=True)
print(f"{bold}Deploying {VM} to {CLUSTER}{_bold}", flush=True)

#Deployment details
print(f"{bold}Details:{_bold}", flush=True)
print(f"OS - {OS}", flush=True)
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

# # Check if a VM with the same name already exists
# print(f"{bold}Checking to see if a VM already exists with the name {VM}{_bold}", flush=True)
# try:
#     # Capture the output of the govc vm.info command
#     govc_command = ["govc", "vm.info", VM]
#     result = subprocess.run(govc_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
#     vmstat = result.stdout

#     # Check if the output contains the VM name
#     if VM in vmstat:
#         print(f"{bold}A VM with the name {VM} already exists, bailing out!{_bold}", flush=True)
#         print(vmstat, flush=True)
#         sys.exit(1)
#         print(f"{bold}{VM} already exists, skipping clone operation - disabled in production{_bold}", flush=True)
#     else:
#         print(f"{VM} does not exist", flush=True)
#         # Clone the template if the VM does not exist
#         print(f"{bold}Cloning template{_bold}", flush=True)
#         clone_command = [
#             "govc", "vm.clone", "-on=false", "-vm", OS, "-c", str(CPU), "-m", str(MEM),
#             "-net", NETWORK, "-pool", f"/st1dccomp01/host/{CLUSTER}/Resources",
#             "-datastore-cluster", DATASTORECLUSTER,
#             "-folder", "/st1dccomp01/vm/vRA - Thryv Cloud/TESTING", VM
#         ]
#         try:
#             subprocess.run(clone_command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
#             print(f"{bold}Cloning completed for {VM}{_bold}", flush=True)
#         except subprocess.CalledProcessError as e:
#             print(f"An error occurred while cloning the VM: {e.stderr}", flush=True)
#             sys.exit(1)
            
# except subprocess.CalledProcessError as e:
#     print(f"An error occurred while checking the VM: {e.stderr}", flush=True)
#     sys.exit(1)

    
# Resize boot disk if needed
if DISK > 100 and OS == "SSVM-OEL8":
    boot_disk_size=(str(DISK) + "G")
    print(f"{bold}Resizing boot disk to {boot_disk_size}{_bold}", flush=True)
    subprocess.run(["govc", "vm.disk.change", "-vm", VM, "-disk.name", "disk-1000-0", "-size", str(boot_disk_size)], check=True)
else:
    print(f"{bold}Disk size is 100G (default), no resize needed{_bold}", flush=True)


# govc vm.info -json st1lndmike04 | jq '.virtualMachines[].config.hardware.device[] | select(.deviceInfo.label | test("Hard disk"))'


# if requested, add 2nd disk 
if ADDDISK:
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

# Parse the JSON output
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


# Add VM to DNS and attempt resolution
def add_to_dns():
    sleep_delay=int(random.uniform(5, 30))
    time.sleep(sleep_delay)
    print(f"{bold}Sleeping for {sleep_delay} seconds{_bold}", flush=True)
    print(f"{bold}Adding {VM}.{DOMAIN} to DNS{_bold}", flush=True)
    dns_command_path = os.path.join(settings.BASE_DIR, 'myapp', 'add_vm_to_dns.py')
    dns_command = [
        "python", dns_command_path, "--dc", DC, "--network", VLAN,
        "--hostname", f"{VM}.{DOMAIN}", "--mac", mac_address
    ]
    subprocess.run(dns_command, check=True)

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
    sys.exit(1)

# Run the DNS check and get the IP
IP = resolve_dns()



# Power off VM if necessary
print(f"{bold}Powering off {VM} in case it's on{_bold}", flush=True)
power_status = subprocess.run(["govc", "vm.info", VM], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)
if "poweredOn" in power_status.stdout:
    subprocess.run(["govc", "vm.power", "-off", "-force", VM], check=True)

    
    
# Customize hostname and IP
print(f"{bold}Customizing hostname, and IP{_bold}", flush=True)
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


    
# Generate ISO files for cloud-init
print(f"{bold}Generating ISO files for cloud-init{_bold}", flush=True)

# Build the command, including optional arguments if they are set
generate_iso_command_path = os.path.join(settings.BASE_DIR, 'myapp', 'generate_iso_command.py')
command = [
    "python", generate_iso_command_path, "--vm", f"{VM}.{DOMAIN}", "--type", TYPE,
    "--builtby", BUILTBY, "--ticket", TICKET, "--appname", APPNAME, "--owner", OWNER,
    "--automount", NFS, "--patch", PATCH
]
if ADDDISK:
    command.extend(["--adddisk", ADDDISK])

if CENTRIFY == "True":
    command.extend(["--centrify_zone", centrify_zone, "--centrify_role", centrify_role])

try:
    # Run the command
    subprocess.run(command, check=True)
except subprocess.CalledProcessError as e:
    print(f"An error occurred: {e}", flush=True)

    
# Create the ISO image
print(f"{bold}Creating ISO image for cloud-init{_bold}", flush=True)
subprocess.run([
    "genisoimage", "-output", f"cloud-init-images/{VM}.{DOMAIN}/seed.iso", "-volid", "cidata",
    "-joliet", "-rock", f"cloud-init-images/{VM}.{DOMAIN}/user-data",
    f"cloud-init-images/{VM}.{DOMAIN}/meta-data"
], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True)



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
        ["govc", "datastore.upload", "-ds", datastore, f"./cloud-init-images/{VM}.{DOMAIN}/seed.iso", f"{VM}/seed.iso"],
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

if "poweredOn" in power_status.stdout:
    print(f"{VM} is powered up and booting. Cloud-init will now perform post-deployment operations.  Please be patient, this can take a while", flush=True)
else:
    print(f"{VM} build has completed, but the VM won't power up.  Please ask for assistance from the UNIX or CLoud team", flush=True)
