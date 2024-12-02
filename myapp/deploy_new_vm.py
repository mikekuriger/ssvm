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

import warnings
from cryptography.utils import CryptographyDeprecationWarning
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

# This script is called from deploy.py, to do the deployment
# deploy.py is called by the scheduler

# Django Setup
sys.path.append('/home/ssvm/ssvm')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
import django
django.setup()

from django.shortcuts import render, redirect, get_object_or_404
from django.utils.safestring import mark_safe
from django.utils.timezone import make_aware
from django.conf import settings
from myapp.models import Deployment, Node, OperatingSystem, HardwareProfile, Status


# Logger Setup
import logging
logger = logging.getLogger('deployment')

# Global Variables
# ANSI escape codes for bold text
bold = '\033[1m'
_bold = '\033[0m'

# Function to read and parse deployment details
def parse_input_file(file_path):
    """Parse deployment file into a dictionary."""
    with open(file_path, 'r') as f:
        return {key.strip(): value.strip() for line in f if ':' in line for key, value in [line.split(':', 1)]}

def setup_status_instances():
    statuses = {
        'building': 'Node is building',
        'setup': 'Node is in setup',
        'failed': 'Build has failed',
        'inservice': 'Node is in production',
    }
    status_objects = {}
    for name, description in statuses.items():
        obj, _ = Status.objects.get_or_create(name=name, defaults={'description': description})
        status_objects[name] = obj
    return status_objects
    

parser = argparse.ArgumentParser(description='Deploy script with file input')
parser.add_argument('file', help='Name of the file to read for deployment')
args = parser.parse_args()
data = parse_input_file(args.file)

# Set up statuses
status_instances = setup_status_instances()

# Set deployment detail variables
deployment_name = data.get('Deployment_id')
naive_deployment_date_str = data.get('Deployment_date') 
naive_deployment_date = datetime.strptime(naive_deployment_date_str, "%Y-%m-%dT%H:%M")
deployment_date = make_aware(naive_deployment_date)
deployment_count = int(data.get("Deployment_count", 0))

DOMAIN = data.get('Domain') or 'corp.pvt'
VM = data.get('Hostname')
OS = data.get('OS')
VERSION = data.get('VERSION')
CPU = int(data.get('CPU', 0))
MEM = int(data.get('RAM', 0)) * 1024  # it's in MB
DISK = int(data.get('Disk', 0))
DC = data.get('Datacenter')
VLAN = data.get('Network')
CLUSTER = data.get('Cluster')
TYPE = data.get('Type')
BUILTBY = data.get('Builtby')
TICKET = data.get('Ticket')
APPNAME = data.get('App_Name')
OWNER = data.get('Owner')
ADDDISK = data.get('Add_disk') or 'False'
centrify_zone = data.get('Centrify_zone') or 'None'
centrify_role = data.get('Centrify_role')
CENTRIFY = data.get('Centrify')
PATCH = data.get('Patches')
NFS = data.get('NFS')

# Read config, datacenter and credential details
from myapp.config_helper import load_config
config = load_config()
datacenter_config = config['datacenters']

pool = f"/{DC}dccomp01/host/{CLUSTER}/Resources"
folder = f"/{DC}dccomp01/vm/vRA - Thryv Cloud/SSVM"

# for govc 
datacenter = config['datacenters'][DC]
vcenter = datacenter['vcenter']
username = datacenter['credentials']['username']
password = datacenter['credentials']['password']
os.environ["GOVC_URL"] = ("https://" + vcenter)
os.environ["GOVC_USERNAME"] = username
os.environ["GOVC_PASSWORD"] = password


CLONE=True
if "SSVM-" in OS:
    CLONE=False



def run_command(command, capture_output=True, check=True, text=True):
    """Run a shell command and handle errors."""
    try:
        return subprocess.run(command, capture_output=capture_output, check=check, text=text)
    except subprocess.CalledProcessError as e:
        class FailedResult:
            returncode = e.returncode
            stdout = e.stdout
            stderr = e.stderr
            args = e.cmd
        return FailedResult()
       


def get_dc_variables():
    """Set up datacenter-specific configuration."""
    if DC not in datacenter_config:
        handle_failure(f"Datacenter {DC} not found in configuration.")

    # Get the datacenter configuration
    dc_config = datacenter_config[DC]
    vlan_map = dc_config.get('vlans', {})

    # Check if the VLAN exists in the datacenter's VLAN map
    if VLAN not in vlan_map:
        handle_failure(f"Invalid VLAN {VLAN} for datacenter {DC}.")

    # Extract VLAN details from config.yaml
    vlan_details = vlan_map[VLAN]
    network = vlan_details.get('network')
    netmask = vlan_details.get('netmask')
    vlan_name = vlan_details.get('name')

    # Extract datacenter-level details
    dc_name = dc_config.get('name')
    dns = dc_config.get('dns')
    domains = dc_config.get('dnsdomains')

    # Check for None values and warn
    variables = {
        "network": network,
        "netmask": netmask,
        "vlan_name": vlan_name,
        "dc_name": dc_name,
        "dns": dns,
        "domains": domains,
    }
    print(f"date = {deployment_date}")
    for var_name, value in variables.items():
        if value is None:
            handle_failure(f"Warning: {var_name} was not found, check config.yaml for errors")
        else:
            if var_name == 'domains':
                print(f"{var_name} = corp.pvt dexmedia.com")
            else:
                print(f"{var_name} = {value}")
        
    # if all is good, set gateway
    gateway = network.split('-')[0] + ".1"
    return network, netmask, gateway, vlan_name, dc_name, dns, domains



def update_node():
    hw_profile, _ = HardwareProfile.objects.get_or_create(
        name='Vmware Virtual Platform',
        defaults={'description': 'Vmware Virtual Platform'}
    )
    os_obj, _ = OperatingSystem.objects.get_or_create(name=VERSION)

    node, created = Node.objects.update_or_create(
        name=f"{VM}.{DOMAIN}",
        defaults={
            'status': status_instances['building'],
            'contact': OWNER,
            'centrify_zone': centrify_zone,
            'created_at': deployment_date,
            'processor_count': CPU,
            'disk_size': int(DISK),
            'physical_memory': MEM,
            'operating_system': os_obj,
            'hardware_profile': hw_profile,
        }
    )
    return node, created


def get_datastorecluster():
    print(CLUSTER, DC)
    # Normalize the cluster name to lowercase and remove hyphens
    normalized_cluster = CLUSTER.replace('-', '').lower()
    govc_command = ["govc", "datastore.cluster.info"]

    try:
        result = run_command(govc_command)
        for line in result.stdout.splitlines():
            if "Name" in line and normalized_cluster in line:
                # Split line to get the second field (assuming it’s space-separated)
                datastorecluster_name = line.split()[1]
                return datastorecluster_name
            
        #in case there is no datasource cluster, use the datastore directly
        if DC == 'ev3':
            rawdatastore_name = f"rawev3ds_{normalized_cluster}_01"
            return rawdatastore_name
        else:
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e.stderr}", flush=True)
        logger.info(f"An error occurred: {e.stderr}")
        return None

def print_deployment(DNS, Domains, Netmask):
    print(f"{bold}Details:{_bold}", flush=True)
    print(f"OS - {OS}", flush=True)
    logger.info(f"OS - {OS}")
    print(f"VERSION - {VERSION}", flush=True)
    logger.info(f"VERSION - {VERSION}")
    print(f"CPU - {CPU}", flush=True)
    logger.info(f"CPU - {CPU}")
    print(f"MEM - {MEM} MB", flush=True)
    logger.info(f"MEM - {MEM} MB")
    print(f"Disk - {DISK} GB", flush=True)
    logger.info(f"Disk - {DISK} GB")
    print(f"Datacenter - {DC}", flush=True)
    logger.info(f"Datacenter - {DC}")
    print(f"Domain - {DOMAIN}", flush=True)
    logger.info(f"Domain - {DOMAIN}")
    print(f"VLAN - {VLAN}", flush=True)
    logger.info(f"VLAN - {VLAN}")
    print(f"CLUSTER - {CLUSTER}", flush=True)
    logger.info(f"CLUSTER - {CLUSTER}")
    print(f"DNS - {DNS}", flush=True)
    logger.info(f"DNS - {DNS}")
    print(f"Domains - {Domains}", flush=True)
    logger.info(f"Domains - {Domains}")
    print(f"Network - {VLAN}", flush=True)
    logger.info(f"Network - {VLAN}")
    print(f"Netmask - {Netmask}", flush=True)
    logger.info(f"Netmask - {Netmask}")
    print(f"Type - {TYPE}", flush=True)
    logger.info(f"Type - {TYPE}")
    print(f"Built by - {BUILTBY}", flush=True)
    logger.info(f"Built by - {BUILTBY}")
    print(f"Ticket - {TICKET}", flush=True)
    logger.info(f"Ticket - {TICKET}")
    print(f"App Name - {APPNAME}", flush=True)
    logger.info(f"App Name - {APPNAME}")
    print(f"Owner - {OWNER}", flush=True)
    logger.info(f"Owner - {OWNER}")
    print(f"Automount - {NFS}", flush=True)
    logger.info(f"Automount - {NFS}")
    print(f"Patches - {PATCH}", flush=True)
    logger.info(f"Patches - {PATCH}")
    print(f"Centrify Join - {CENTRIFY}", flush=True)
    logger.info(f"Centrify Join - {CENTRIFY}")
    print(f"centrify_zone - {centrify_zone}", flush=True)
    logger.info(f"centrify_zone - {centrify_zone}")
    print(f"centrify_role - {centrify_role}", flush=True)
    logger.info(f"centrify_role - {centrify_role}")
    print(f"Add_disk - {ADDDISK}", flush=True)
    logger.info(f"Add_disk - {ADDDISK}")

    
def does_vm_exist():
    """Check if a VM with the same name already exists, and check if the source VM (template) exists before cloning."""
    try:
        # Check for the template (source VM)
        print("Checking template - ", end="", flush=True)
        logger.info("Checking template")

        govc_os_command = ["govc", "vm.info", OS]
        result_os = run_command(govc_os_command)
        vmstat_os = result_os.stdout
        
        if OS in vmstat_os:
            print(f"Template {OS} found", flush=True)
            logger.info(f"Template {OS} found")
        else:
            handle_failure(f"Template {OS} does not exist")
        
        # Check for the target VM
        print("Checking VM - ", end="", flush=True)
        logger.info("Checking VM")

        govc_command = ["govc", "vm.info", VM]
        result = run_command(govc_command)
        vmstat = result.stdout

        if VM in vmstat:
            # Check for deployment_name in the VM details
            govc_command2 = ["govc", "vm.info", "-json", VM]
            result2 = run_command(govc_command2)
            vmstat2 = result2.stdout
            
            if deployment_name in vmstat2:
                print(f"{VM} exists with the same deployment_id. Skipping clone.", flush=True)
                logger.info(f"{VM} exists with the same deployment_id. Skipping clone.")
                return True
            else:
                # handle_failure(f"A VM with the name {VM} already exists, please delete it and re-deploy")
                print(f"{VM} exists, but without the same deployment_id. Skipping clone.", flush=True)
                logger.info(f"{VM} exists, but without the same deployment_id. Skipping clone.")
                return True
        else:
            print(f"{VM} does not exist", flush=True)
            logger.info(f"{VM} does not exist")
            return False
    except Exception as e:
        handle_failure(f"Error while checking VM existence: {str(e)}")



def clone_vm(datastorecluster, network):
    """Clone a VM from a template."""
    pool = f"/{DC}dccomp01/host/{CLUSTER}/Resources"
    folder = f"/{DC}dccomp01/vm/vRA - Thryv Cloud/SSVM"
    
    print(f"{bold}Cloning template{_bold}", flush=True)
    logger.info(f"Cloning template")
    
    if datastorecluster.startswith("raw"):
        datastore = datastorecluster[3:]
        clone_command = [
            "govc", "vm.clone", "-on=false", "-vm", OS, "-c", str(CPU), 
            "-m", str(MEM), "-net", network, "-pool", pool, 
            "-ds", datastore, "-folder", folder, VM
            
        ]
    else:
        clone_command = [
            "govc", "vm.clone", "-on=false", "-vm", OS, "-c", str(CPU),
            "-m", str(MEM), "-net", network, "-pool", pool,
            "-datastore-cluster", datastorecluster, "-folder", folder, VM
        ]

    retries = 3  # Number of retries
    delay = 30  # Delay between retries in seconds
    
    attempt = 0
    while attempt < retries:
    
        try:
            attempt += 1
            print(f"Attempt {attempt} of {retries} to clone VM...", flush=True)
            logger.info(f"Attempt {attempt} of {retries} to clone VM...")
    
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
                            logger.info(f"Progress: {line}")
    
                process.wait()  # Wait for the clone to complete
    
                # Check the return code and raise an error if the command failed
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, clone_command)
    
            # If the clone is successful, print a success message and break the loop
            print(f"Cloning completed for {VM}", flush=True)
            logger.info(f"Cloning completed for {VM}")
            break  # Exit the retry loop since the operation was successful
    
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while cloning the VM on attempt {attempt}: {e.stderr}", flush=True)
            logger.error(f"An error occurred while cloning the VM on attempt {attempt}: {e.stderr}")
    
            if attempt < retries:
                print(f"Retrying in {delay} seconds...", flush=True)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)  # Wait for 30 seconds before retrying
            else:
                handle_failure("Maximum retries reached. Exiting.")
        


def resize_boot_disk():
    # Resize boot disk if needed
    if DISK > 100:
        boot_disk_size=(str(DISK) + "G")
        print(f"Resizing boot disk to {bold}{boot_disk_size}{_bold}", flush=True)
        logger.info(f"Resizing boot disk to {boot_disk_size}")
        subprocess.run(["govc", "vm.disk.change", "-vm", VM, "-disk.name", "disk-1000-0", "-size", str(boot_disk_size)], check=True)
    else:
        print(f"Disk resize not needed", flush=True)
        logger.info(f"Disk resize not needed")
    

def add_disk():
    # if requested, add 2nd disk
    # global ADDDISK
    if ADDDISK != 'False':
        disk_size, label = ADDDISK.split(',')
        disk_name = (VM + "/" + VM + "_z")
        disk_size = (disk_size + "G")
        print(f"Adding 2nd disk - {bold}{disk_size}{_bold}", flush=True)
        logger.info(f"Adding 2nd disk - {disk_size}")
    
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
                logger.info(f"Added a {disk_size} disk to {VM}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to add disk to {VM}: {e}", flush=True)
                logger.error(f"Failed to add disk to {VM}: {e}")
        else:
            print("No valid datastore found for the VM.", flush=True)
            logger.error("No valid datastore found for the VM.")
    # else:
    #     ADDDISK='False'



def get_mac_address():
    print(f"{bold}Getting MAC address from vCenter{_bold}", flush=True)
    logger.info(f"Getting MAC address from vCenter")
    govc_command = ["govc", "vm.info", "-json", VM]
    mac_result = run_command(govc_command)
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
        logger.info(f"MAC - {mac_address}")
        return mac_address
    else:
        handle_failure("No MAC address found")



def add_to_dns(mac_address, vlan_name, dc_name):
    
    from SOLIDserverRest import SOLIDserverRest
    import logging, math, ipaddress, pprint

    sleep_delay = int(random.uniform(5, 30)) if deployment_count > 1 else 0

    print(f"Sleeping for {bold}{sleep_delay} seconds{_bold}", flush=True)
    logger.info(f"Sleeping for {sleep_delay} seconds")
    time.sleep(sleep_delay)
    print(f"{bold}Adding {VM}.{DOMAIN} to DNS{_bold}", flush=True)
    logger.info(f"Adding {VM}.{DOMAIN} to DNS")

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

    def add_ip_address(ip, name, space_id, mac_address):
        parameters = {
            "site_id": str(space_id),
            "hostaddr": str(ipaddress.IPv4Address(ip)),
            "name": str(name),
            "mac_addr": str(mac_address)
        }

        print(parameters)
        
        rest_answer = SDS_CON.query("ip_address_create", parameters)

        if rest_answer.status_code != 201:
            logging.error("cannot add %s to DNS", name)
            return None

        rjson = json.loads(rest_answer.content)

        return {
           'type': 'add_ipv4_address',
           'name': str(name),
           'id': rjson[0]['ret_oid'],
        }

    # Extract details from the config
    master   = config['global']['eip']['eipmaster']
    username = config['global']['eip']['username']
    password = config['global']['eip']['password']
    #print(f"dns username: {username}, password {password}")

    SDS_CON = SOLIDserverRest(master)
    SDS_CON.set_ssl_verify(False)
    SDS_CON.use_basicauth_sds(user=username, password=password)

    # get space (site id)
    space = get_space("thryv-eip-ipam")
    subnet = get_subnet_v4(vlan_name, dc_name)

    # get next free address (pick 5 free IPs, skip the first 20)
    ipstart = ipaddress.IPv4Address(subnet['addr']) + 50
    free_address = get_next_free_address(subnet['id'], 5, ipstart)

    # add ip to IPAM
    hostname = f"{VM}.{DOMAIN}"
    #mac_addr = mac_address
    node = add_ip_address(free_address['address'][2],hostname,space['id'],mac_address)
    del(SDS_CON)


def handle_dns(mac_address, vlan_name, dc_name):

    max_retries = 60
    retry_delay = 2
    
    print(f"{bold}Attempting to resolve{_bold} {VM}.{DOMAIN}", flush=True)
    
    for attempt in range(max_retries):
        
        try:
            ip_address = socket.gethostbyname(f"{VM}.{DOMAIN}")
            print(f"{VM}.{DOMAIN} resolves to {ip_address}", flush=True)
            logger.info(f"{VM}.{DOMAIN} resolves to {ip_address}")
            return ip_address
        except socket.gaierror:
            if attempt == 0:
                # Only attempt to add to DNS on the first failure
                add_to_dns(mac_address, vlan_name, dc_name)
                print("DNS added, waiting for name to be resolvable")
            print('.', flush=True, end="")
            time.sleep(retry_delay)
    
    # If all attempts fail, exit with error
    handle_failure(f"Failed to resolve {VM}.{DOMAIN} after {max_retries} attempts!")


def power_off():
    print(f"{bold}Powering off {VM} in case it's on{_bold}", flush=True)
    logger.info(f"Powering off {VM} in case it's on")
    power_status = run_command(["govc", "vm.info", VM])
    if "poweredOn" in power_status.stdout:
        run_command(["govc", "vm.power", "-off", "-force", VM])


def customize(mac_address, IP, netmask, gateway, dns, domains):                    
    # Customize the VM
    print(f"{bold}Customizing VM details{_bold}\n- IP ({IP})\n- Netmask ({netmask})\n- Gateway ({gateway})\n- DNS ({dns})\n- Domains ({domains})", flush=True)
  
    result = run_command([
        "govc", "vm.customize", "-vm", VM, "-type", "Linux", "-name", 
        VM, "-domain", DOMAIN, "-mac", mac_address, "-ip", IP, 
        "-netmask", netmask, "-gateway", gateway, "-dns-server", dns, "-dns-suffix", domains
    ])

    if result.returncode != 0:
        if "Guest Customization is already pending" in result.stderr:
            print("Customization is already pending for this VM.", flush=True)
            logger.info("Customization is already pending for this VM.")
        else:
            print("An error occurred while executing the command:", flush=True)
            logger.error("An error occurred while executing the command:")
            print("Command:", result.args, flush=True)
            logger.error("Command:", result.args)
            print("Return Code:", result.returncode, flush=True)
            logger.error("Return Code:", result.returncode)
            print("Standard Output:", result.stdout, flush=True)
            logger.error("Standard Output:", result.stdout)
            print("Standard Error:", result.stderr, flush=True)
            logger.error("Standard Error:", result.stderr)
    else:
        print(f"Customization successful.", flush=True)
        logger.info("Customization successful.")

    # Set custom fields in Vcenter
    print(f"{bold}Set custom fields in Vcenter{_bold}", flush=True)
    fields_set_command = ["govc", "fields.set", "deployment", deployment_name, f"{folder}/{VM}"]
    set_result = run_command(fields_set_command)
    
    if set_result.returncode == 0:
        print(f"Custom field 'deployment' successfully set to {deployment_name}", flush=True)
        logger.info(f"Custom field 'deployment' successfully set to {deployment_name}")
    else:
        print(f"Failed to set custom field 'deployment'.", flush=True)
        logger.error(f"Failed to set custom field 'deployment'.")
        print("Error:", set_result.stderr)
        logger.error("Error:", set_result.stderr)

    fields_set_command = ["govc", "fields.set", "Created_by", f"SSVM ({data.get('Builtby')})", f"{folder}/{VM}"]
    set_result = run_command(fields_set_command)
                          
    if set_result.returncode == 0:
        print(f"Custom field 'Created_by' successfully set to {data.get('Builtby')}")
        logger.info(f"Custom field 'Created_by' successfully set to {data.get('Builtby')}")
    else:
        print("Failed to set custom field 'Created_by'.")
        logger.error("Failed to set custom field 'Createdby'.")
        print("Error:", set_result.stderr)
        logger.error("Error:", set_result.stderr)
    
    # Fetch cmdb_uuid and UUID
    print(f"{bold}Fetching cmdb_uuid and UUID from Vcenter{_bold}")
    logger.info("Fetching cmdb_uuid and UUID from Vcenter")
    govc_command = ["govc", "vm.info", "-json", VM]
    uuid_result = run_command(govc_command)

    if uuid_result.returncode == 0:
        vm_info = json.loads(uuid_result.stdout)
        custom_values = vm_info.get("virtualMachines", [])[0].get("customValue", [])
        cmdb_uuid_value = None
        for field in custom_values:
            if field.get("key") == 1001:  # this is the cmdb_uuid
                cmdb_uuid_value = field.get("value")
                break

        if cmdb_uuid_value:
            print(f"cmdb_uuid value: {cmdb_uuid_value}", flush=True)
            logger.info(f"cmdb_uuid value: {cmdb_uuid_value}")
        else:
            print("cmdb_uuid value not found.")
            logger.error("cmdb_uuid value not found.")
                          
        vm_values = vm_info.get("virtualMachines", [{}])[0] 
        config = vm_values.get("config", {})
    
        uuid_value = config.get("uuid")
                          
        if uuid_value:
            print(f"uuid value: {uuid_value}")
            logger.info(f"uuid value: {uuid_value}")
        else:
            print("uuid value not found.")
            logger.error("uuid value not found.")

        return cmdb_uuid_value, uuid_value
        
    else:
        print("Failed to retrieve VM info.")
        logger.error("Failed to retrieve VM info.")
        print("Error:", uuid_result.stderr)                    
        logger.error("Error:", uuid_result.stderr)
        return None, None
                



def cloud_init():
    if not CLONE:
        from jinja2 import Environment, FileSystemLoader
        
        print(f"Generating ISO files for cloud-init", flush=True)
        logger.info(f"Generating ISO files for cloud-init")

        if data.get("Add_disk"):
            mountdisks = f"/vra_automation/installs/mount_extra_disks.sh"
            dumpdisks = f"echo '{data.get('Add_disk')}' >> /etc/vra.disk"

        else:
            mountdisks = ""
            dumpdisks = ""
                
        if data.get("Centrify_zone") and data.get("Centrify_role") != 'None':
            adjoin = (
                f"/usr/sbin/adjoin --server DFW2W2SDC05.corp.pvt "
                f"-z {data.get('Centrify_zone')} -R {data.get('Centrify_role')} "
                "-c OU=Computers,OU=Centrify,DC=corp,DC=pvt "
                "-f corp.pvt -u svc_centrify -p '#xupMcMlURubO2|'"
            )

        
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
        #now = datetime.now()
        
        naive_now = datetime.now()
        now = make_aware(naive_now)
        date = now.strftime("%Y-%m-%dT%H:%M:%S")
        
        # Set up Jinja2 environment and load the template file
        env = Environment(loader=FileSystemLoader(searchpath=os.path.join(settings.BASE_DIR, 'myapp', 'templates')))
        usertemplate = env.get_template("user_data_template.j2")
        metatemplate = env.get_template("meta_data_template.j2")
          
        # Values to populate in the template from arguments
        template_data = {
            'vm': f"{VM}.{DOMAIN}",
            'date': date,
            'type': data.get("Type"),
            'builtby': data.get("Builtby"),
            'ticket': data.get("Ticket"),
            'appname': data.get("App_Name"),
            'owner': data.get("Owner"),
            'patch': data.get("Patches"),
            'yumupdate': yumupdate,
            'dumpdisks': dumpdisks,
            'adddisk': data.get("Add_disk"),
            'mountdisks': mountdisks,
            'automount_homedir': automount_homedir,
            'automount': data.get("NFS"),
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
        iso_command = [
            "-o", iso_file, "-volid", "cidata", "-joliet", "-rock", user_data_file, meta_data_file
        ]
        
        print(f"Creating ISO image for cloud-init", flush=True)
        logger.info(f"Creating ISO image for cloud-init")
               
        run_command(["genisoimage"] + iso_command)


        # Copy the ISO image to the VM's datastore
        datastore_result = run_command(["govc", "vm.info", "-json", VM])
        
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
            print(f"Copying the ISO to the VM's datastore - {datastore}", flush=True)
            logger.info(f"Copying the ISO to the VM's datastore - {datastore}")
            
        # Upload the ISO to the VM's datastore
            run_command(["govc", "datastore.upload", "-ds", datastore, iso_file, f"{VM}/seed.iso"])
            
        else:
            print("No valid datastore found for the VM.", flush=True)
            logger.error("No valid datastore found for the VM.")


        # Mount the ISO to the VM and power it on
        print(f"{bold}Attach the ISO to the VM{_bold}", flush=True)
        logger.info(f"Attach the ISO to the VM")
        cd_device = subprocess.run(["govc", "device.ls", "-vm", VM], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True).stdout.splitlines()
        cdrom_device = [line.split()[0] for line in cd_device if "cdrom" in line][0]
        
        # added eject in case template or image being cloned has a cd incerted
        result = run_command(["govc", "device.cdrom.eject", "-vm", VM])
        if result.returncode == 0:
            print(f"CDROM ejected from {VM}", flush=True)
        else:
            print(f"Failed to eject CDROM from {VM}", flush=True)
            logger.error(f"Failed to eject CDROM from {VM}")
            print("Error:", set_result.stderr)
            logger.error("Error:", set_result.stderr)
        
        insert_command = ["govc", "device.cdrom.insert", "-vm", VM, "-device", cdrom_device, "-ds", datastore, f"{VM}/seed.iso"]
        # print(" ".join(insert_command))
        result = run_command(insert_command)
        if result.returncode == 0:
            print(f"CDROM inserted into {VM}", flush=True)
        else:
            print(f"Failed to insert CDROM into {VM}", flush=True)
            logger.error(f"Failed to insert CDROM into {VM}")
            print("Error:", set_result.stderr)
            logger.error("Error:", set_result.stderr)
        
        #print(f"ISO has been inserted into the CDROM", flush=True)
        #logger.info(f"ISO has been inserted into the CDROM")
        time.sleep(int(random.uniform(1, 3)))
        result = run_command(["govc", "device.connect", "-vm", VM, cdrom_device])
        if result.returncode != 0:
            print(f"Failed to connect CDROM to {VM}", flush=True)
            logger.error(f"Failed to connect CDROM to {VM}")
            print("Error:", set_result.stderr)
            logger.error("Error:", set_result.stderr)
        
        #print(f"ISO has been inserted and attached to {VM}", flush=True)
        #logger.info(f"ISO has been inserted and attached to {VM}")

    # this is a CLONE
    else:
        print(f"{bold}Cloning a live VM, Skipping cloud-init{_bold}", flush=True)
        logger.info(f"Cloning a live VM, Skipping cloud-init")
        result = run_command(["govc", "device.cdrom.eject", "-vm", VM])
        if result.returncode == 0:
            print(f"CDROM ejected from {VM}", flush=True)
        else:
            print(f"Failed to eject CDROM from {VM}", flush=True)
            logger.error(f"Failed to eject CDROM from {VM}")
            print("Error:", set_result.stderr)
            logger.error("Error:", set_result.stderr)



def power_on():
    print(f"{bold}Power on the VM, then check status{_bold}", flush=True)
    logger.info(f"Power on the VM, then check status")
    time.sleep(int(random.uniform(1, 3)))
    run_command(["govc", "vm.power", "-on", VM])
    
    # Wait a bit, then check to see if VM will stay powered up, if not not sure what to do...
    time.sleep(15)
    
    # try to unregister a clone's VM from centrify, or else it will be in conflict with the donor VM
    max_retries = 3
    retry_delay = 30 
    
    if CLONE:
        print(f"Attempting to unregister {VM} from Centrify.", flush=True)
        logger.info(f"Attempting to unregister {VM} from Centrify.")
        govc_command = ["govc", "guest.run", "-vm", VM, "-l", "root:'12ui34op!@#$'", "-k", "adleave", "-f"]
        
        for attempt in range(1, max_retries + 1):
            result = run_command(govc_command)
    
            if result.returncode == 0:
                print(f"{VM} has been removed from centrify", flush=True)
                logger.info(f"{VM} has been removed from centrify")
                break 
            else:
                print(f"Attempt {attempt} failed to remove {VM} from centrify", flush=True)
                logger.error(f"Attempt {attempt} failed to remove {VM} from centrify")
                print("Error:", result.stderr)
                logger.error(f"Error: {result.stderr}")
    
    
                # Wait before the next retry if this isn't the last attempt
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    handle_failure(f"Failed to remove {VM} from centrify after {max_retries} attempts")


def rename_yellowpages():
    if "yellowpages" in DOMAIN:
        govc_command = ["govc", "vm.change", "-name", f"{VM}.{DOMAIN}", "-vm", VM]
        result = run_command(govc_command)
        if result.returncode == 0:
            print(f"{VM} has been renamed to {VM}.{DOMAIN}")
            logger.info(f"{VM} has been renamed to {VM}.{DOMAIN}")
        else:
            print(f"Failed to rename {VM}", flush=True)
            logger.error(f"Failed to rename {VM}")
            print("Error:", set_result.stderr)
            logger.error("Error:", set_result.stderr)
            
            # finalize_node_status(f"{VM}.{DOMAIN}", "failed", uuid, serial_number, status_instances)
            
            print(f"Node status = failed.", flush=True)
            logger.info(f"Node status = failed.")
            return 'failed'
            

def check_power_status():
    vm=VM
    if "yellowpages" in DOMAIN:
        vm=f"{VM}.{DOMAIN}"
    power_status = run_command(["govc", "vm.info", vm])                       
    if "poweredOn" in power_status.stdout:
        print(f"{vm} is powered up and booting.", flush=True)
        logger.info(f"{vm} is powered up and booting.")
        # print(f"Cloud-init will now perform post-deployment operations.  Please be patient, this can take a while.", flush=True)
        # logger.info(f"Cloud-init will now perform post-deployment operations.  Please be patient, this can take a while.")
        # print(f"Build is complete.", flush=True)
        # logger.info(f"Build is complete.")
    
        # Update the cmdb
        # finalize_node_status(f"{VM}.{DOMAIN}", "inservice", uuid, serial_number, status_instances)
        print(f"Node status = inservice.", flush=True)
        logger.info(f"Node status = inservice.")
        return 'inservice'

    else:
        print(f"{vm} did not power on after the build.  Please check with the Unix team for assistance.", flush=True)
        logger.warning(f"{vm} did not power on after the build.  Please check with the Unix team for assistance.")
        
        print(f"Node status = failed.", flush=True)
        logger.info(f"Node status = failed.")
        return 'failed'



def finalize_node_status(status, uuid, serial_number):
    """Update node's final status and details."""
    name=f"{VM}.{DOMAIN}"
    try:
        node = Node.objects.get(name=name)
    except Node.DoesNotExist:
        print(f"Node {name} does not exist in the database. Logging failure.", flush=True)
        logger.error(f"Node {name} does not exist in the database. Logging failure.")
        sys.exit(1)
    naive_now = datetime.now()
    now = make_aware(naive_now)
    node.ping_status=True
    if status == "failed":
        node.ping_status=False
    node.status = status_instances[status]
    node.updated_at = now
    node.uniqueid = uuid
    node.serial_number = serial_number
    node.save(update_fields=['status', 'updated_at', 'uniqueid', 'serial_number', 'ping_status'])

    print(f"Build is complete.", flush=True)
    logger.info(f"Build is complete.")
    print(f"Cloud-init will now perform post-deployment operations.  Please be patient, this can take a while.", flush=True)
    logger.info(f"Cloud-init will now perform post-deployment operations.  Please be patient, this can take a while.")


def handle_failure(message):
    """Update node's status to failed"""
    name=f"{VM}.{DOMAIN}"
    try:
        node = Node.objects.get(name=name)
    except Node.DoesNotExist:
        print(f"Node {name} does not exist in the database. Logging failure.", flush=True)
        logger.error(f"Node {name} does not exist in the database. Logging failure.")
        sys.exit(1)
    logger.error(message)
    print(message, flush=True)
    node.status = status_instances['failed']
    node.save(update_fields=['status'])
    sys.exit(1)


    
def main():
    print(f"{bold}** Main **{_bold}")

    print(f"{bold}** get_dc_variables{_bold}")
    # Set up datacenter variables
    network, netmask, gateway, vlan_name, dc_name, dns, domains = get_dc_variables()

    # Update Node details in CMDB
    print(f"{bold}** update_node in CMDB{_bold}")
    node, created = update_node()

    # Print deployment details in logs
    print(f"{bold}** print_deployment - {_bold}", end="")
    print_deployment(dns, domains, netmask)
    
    # Look up the datastore cluster in Vcenter
    print(f"{bold}** get_datastorecluster - {_bold}", end="")
    datastorecluster = get_datastorecluster()

    # Check if VM exists in Vcenter
    print(f"{bold}** does_vm_exist{_bold}")
    status = does_vm_exist()
    
    # Create VM by Cloning template
    if status == False:  # vm does not exist in vcenter, so create it
        print(f"{bold}** clone_vm - {_bold}", end="")
        clone_vm(datastorecluster, network)

    # Resize boot disk
    if DISK > 100:
        print(f"{bold}** resize_boot_disk - {_bold}")
        resize_boot_disk()

    # Add disk
    if ADDDISK != 'False':
        print(f"{bold}** add_disk - {_bold}")
        add_disk()
    
    # get MAC from Vcenter
    print(f"{bold}** get_macaddress - {_bold}", end="")
    mac_address = get_mac_address()
    
    # Add to DNS
    print(f"{bold}** handle_dns{_bold}")
    IP = handle_dns(mac_address, vlan_name, dc_name)

    # Power off VM if necessary
    print(f"{bold}** power_off - {_bold}", end="")
    power_off()

    # Customize hostname and IP
    # (cpu, memory, disk are set during clone)
    print(f"{bold}** customize - {_bold}", end="")
    uniqueid, serial_number = customize(mac_address, IP, netmask, gateway, dns, domains)

    # Generate ISO, and mount to VM
    print(f"{bold}** cloud_init{_bold}")
    cloud_init()

    # Power On
    print(f"{bold}** power_on - {_bold}", end="")
    power_on()

    # add domain to yellowpages VMs in vcenter
    if "yellowpages" in DOMAIN:
        print(f"{bold}** rename_yellowpages{_bold}")
        status = rename_yellowpages()
        if status == 'Failed':
            finalize_node_status('failed', uniqueid, serial_number)
    
    # Check power state
    print(f"{bold}** check_power_status - {_bold}", end="")
    status2 = check_power_status()
    if status2 == 'Failed':
        finalize_node_status('failed', uniqueid, serial_number)
            
    # Finalize Node
    print(f"{bold}** finalize_node_status", _bold)
    if status != 'Failed' and status2 != 'Failed':
        finalize_node_status('inservice', uniqueid, serial_number)


if __name__ == "__main__":
    main()
