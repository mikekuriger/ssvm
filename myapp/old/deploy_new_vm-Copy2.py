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
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

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
print(f"{bold}Creating ISO image for cloud-init{_bold}", flush=True)
subprocess.run([
    "genisoimage", "-output", iso_file, "-volid", "cidata",
    "-joliet", "-rock", user_data_file, meta_data_file
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

if "poweredOn" in power_status.stdout:
    print(f"{VM} is powered up and booting. Cloud-init will now perform post-deployment operations.  Please be patient, this can take a while", flush=True)
else:
    print(f"{VM} build has completed, but the VM won't power up.  Please ask for assistance from the UNIX or CLoud team", flush=True)
