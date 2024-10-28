import argparse
import subprocess
import os
import django
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from django.conf import settings
from datetime import datetime
from myapp.models import Deployment
from myapp.config_helper import load_config


sys.path.append("/home/ssvm/ssvm")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

config = load_config()
logger = logging.getLogger('deployment')

# this file reads the deployment output, and creates
# individual deployment files for each VM in the deployment.
# Currently, it puts each VM in a different cluster, round robin
# skipping the Oracle clusters
# I will add a checkbox to the form so the user can decide
# if the VMs go into one cluster or if they are divided up

# once the deployment files are generated, the VMs are deployed

# Configuration constants
# SOURCE_DIR = settings.BASE_DIR / "media"
TMP_DIR = settings.BASE_DIR / "media"
SPOOL_EXT = ".queued"
BUILDING_EXT = ".building"
DEPLOYED_EXT = ".deployed"
#DEPLOYED_EXT = ""
FAILED_EXT = ".failed"
LOG_EXT = ".log"
DEPLOY_SCRIPT = settings.BASE_DIR / "myapp" / "deploy_new_vm.py"
MAX_PARALLEL_JOBS = 5


def create_spool_files(deployment_name):
    try:
        content = Deployment.objects.get(deployment_name=deployment_name)
        hostname_list = content.full_hostnames.split(",") if content.full_hostnames else []

        if not hostname_list:
            print(f"No hostnames found for deployment {deployment_name}.")
            return

        st1_clusters = list(config.get('datacenters', {}).get('st1', {}).get('clusters', {}).keys())
        ev3_clusters = list(config.get('datacenters', {}).get('ev3', {}).get('clusters', {}).keys())

        for i, hostname in enumerate(hostname_list):
            hostname = hostname.strip()  
            if hostname.startswith("st1"):
                clusters = st1_clusters
            elif hostname.startswith("ev3"):
                clusters = ev3_clusters
            else:
                print(f"Unrecognized hostname prefix for {hostname}. Skipping.")
                continue  # Skip if the prefix doesn't match any known cluster list

            cluster = clusters[i % len(clusters)]    
            create_spool_file(content, hostname, cluster)

    except Deployment.DoesNotExist:
        print(f"Deployment {deployment_name} does not exist.")
    except Exception as e:
        print(f"An error occurred while creating spool files: {e}")

def extract_hostnames(content):
    hostnames_line = next((line for line in content if line.startswith("Hostnames:")), None)
    if hostnames_line:
        _, hostnames = hostnames_line.split(": ", 1)
        return [hostname.strip() for hostname in hostnames.split(",")]
    hostname_line = next((line for line in content if line.startswith("Hostname:")), None)
    if hostname_line:
        _, hostname = hostname_line.split(": ", 1)
        return [hostname.strip()]
    print("No hostnames found in the specified file.")
    return []



def create_spool_file(content, hostname, cluster):
    spool_content = [
        f"Deployment_id: {content.deployment_name}",
        f"Deployment_date: {content.deployment_date}",
        f"Hostname: {hostname}",                  # calculated
        f"Builtby: {content.builtby}",
        f"Domain: {content.domain}",
        f"Ticket: {content.ticket}",
        f"App_Name: {content.appname}",
        f"Owner: {content.owner}",
        f"Datacenter: {content.datacenter}",
        f"Type: {content.server_type}",
        f"Deployment_count: {content.deployment_count}",
        f"CPU: {content.cpu}",
        f"RAM: {content.ram}",
        f"OS: {content.os}",
        f"VERSION: {content.os_value}",
        f"Disk: {content.disk_size}",
        f"Cluster: {cluster}",                    # calculated
        f"Network: {content.network}",
        f"NFS: {'True' if content.nfs_home else 'False'}",
        f"Add_disk: {f'{content.additional_disk_size},{content.mount_path}' if content.add_disks else 'False'}",
        f"Centrify: {'True' if content.join_centrify else 'False'}",
        f"Centrify_zone: {content.centrify_zone if content.join_centrify else ''}",
        f"Centrify_role: {content.centrify_role if content.join_centrify else ''}",
        f"Patches: {'True' if content.install_patches else 'False'}"
    ]

    # Join all lines with newlines and add a final newline
    spool_text = "\n".join(spool_content) + "\n"
    
    # Define the path and write the spool file
    new_file_path = TMP_DIR / f"{hostname}{SPOOL_EXT}"
    with new_file_path.open('w') as new_file:
        new_file.write(spool_text)

    print(f"Created spool file: {new_file_path}")


    
def deploy_vm(file_name, deployment_name):
    try:
        # Retrieve the deployment object from the database
        deployment = Deployment.objects.get(deployment_name=deployment_name)
        
        # Update status to 'building'
        deployment.status = 'building'
        deployment.save()
    
    except Deployment.DoesNotExist:
        print(f"Deployment with name {deployment_name} does not exist in database.")
        return f"Deployment {deployment_name} not found."
    
    except Exception as e:
        # In case of an error, update the status to 'failed'
        if 'deployment' in locals():
            deployment.status = 'failed'
            deployment.save()
        print(f"An error occurred: {e}")
        return f"Failed to start deployment for {deployment_name}"

    print(f"Deploying {file_name}")
    
    base_name = file_name.stem
    spool_path = TMP_DIR / file_name
    building_path = TMP_DIR / f"{base_name}{BUILDING_EXT}"
    deployed_path = TMP_DIR / f"{base_name}{DEPLOYED_EXT}"
    failed_path = TMP_DIR / f"{base_name}{FAILED_EXT}"
    log_path = TMP_DIR / f"{base_name}{LOG_EXT}"
    
    spool_path.rename(building_path)
    
    with log_path.open("w") as log_file:
        try:
            subprocess.run(
                ["python", DEPLOY_SCRIPT, str(building_path)], 
                stdout=log_file, stderr=log_file, check=True
            )
            # Update status to 'deployed'
            deployment.status = 'deployed' 
            deployment.save()
            building_path.rename(deployed_path)
            return f"Deployment completed successfully for {file_name}"
        except subprocess.CalledProcessError:
            # Update status to 'failed'
            deployment.status = 'failed' 
            deployment.save()
            building_path.rename(failed_path)
            return f"Deployment failed for {file_name}"
        
        
def main():
    parser = argparse.ArgumentParser(description='Deploy script with file input')
    parser.add_argument('file', help='Name of the file to read for deployment, or NONE to run existing spool files')
    args = parser.parse_args()
    deployment_name = args.file
    
    
    # for now, read the deployment info from the text file, but we do have 
    # access to the same info from the database so I'll add that soon.
    # for now, just process the text file and update the status in the DB
    
    # this part is for creating spool files from the deployment file (text file)
    # I'll change it to pull this data from the database and get rid of the deployment text file
    # Spool files are the same as deployment file if we're building one Vm
    # We create multiple spool files for multiple VMs
    
    # Ensure deployment_name exists before processing
    if deployment_name != 'None':
        create_spool_files(deployment_name)
    
    spool_files = [f for f in TMP_DIR.glob(f"*{SPOOL_EXT}")]
    if not spool_files:
        print("No spool files to process.")
        return

    # deploy VMs from spool files, in parallel, {MAX_PARALLEL_JOBS} (5) at a time
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_JOBS) as executor:
        futures = {executor.submit(deploy_vm, file, deployment_name): file for file in spool_files}
        
        for future in as_completed(futures):
            file_name = futures[future]
            try:
                result = future.result()
                print(result)
            except Exception as e:
                print(f"An error occurred with {file_name}: {e}")

if __name__ == "__main__":
    main()
