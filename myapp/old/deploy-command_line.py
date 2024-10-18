import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from django.conf import settings

# This program deploys the jobs that the user has requested 
# and is run by the task scheduler
# it reads the deployment info from the database
# and writes deployment files for each VM on the filesystem
# the deploy_new_vm script reads those files and performs the deploys
# and logs the process.

# Currently, it puts each VM in a different cluster, round robin
# skipping the Oracle clusters
# I may a checkbox to the form so the user can decide
# if the VMs go into one cluster or if they are divided up

# for updating status in database
import os
import django
import sys
from datetime import datetime

# Adjust this to the path of your Django project
sys.path.append("/home/mk7193/python/myproject")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from myapp.models import Deployment

from myapp.config_helper import load_config 
config = load_config()


# Configuration constants
TMP_DIR = settings.BASE_DIR / "tmp"
SPOOL_EXT = ".spool"
BUILDING_EXT = ".building"
DEPLOYED_EXT = ".deployed"
FAILED_EXT = ".failed"
LOG_EXT = ".log"
DEPLOY_SCRIPT = settings.BASE_DIR / "myapp" / "deploy_new_vm.py"
MAX_PARALLEL_JOBS = 5


def create_spool_files(deployment_name):
    
    #deployment_date = content.deployment_date.strftime('%Y-%m-%dT%H:%M')

    # Create the lines for the spool file based on the database fields
    spool_content = [
        f"Deployment_name: {content.deployment_name}",
        f"Deployment_date: {content.deployment_date}",
        f"Hostname: {hostname}",
        f"Ticket: {content.ticket}",
        f"App_Name: {content.appname}",
        f"Owner: {content.owner}",
        f"Datacenter: {content.datacenter}",
        f"Type: {content.server_type}",
        f"Deployment_count: {content.deployment_count}",
        f"CPU: {content.cpu}",
        f"RAM: {content.ram}",
        f"OS: {content.os}",  # Adjust as needed
        f"Disk: {content.disk_size}",
        f"Cluster: {content.cluster}",
        f"Network: {content.network}",
        f"NFS: {'True' if content.nfs_home else 'False'}",
        f"Add_disk: {f'{content.additional_disk_size},{content.mount_path}' if content.add_disks else 'False'}",
        f"Centrify: {'True' if content.join_centrify else 'False'}",
        f"Centrify_zone: {'Centrify_zone' if content.join_centrify else ''}",
        f"Centrify_role: {'Centrify_role' if content.join_centrify else ''}",
        f"Patches: {'True' if content.install_patches else 'False'}"
    ]

    # Join all lines with newlines and add a final newline
    spool_text = "\n".join(spool_content) + "\n"
    
    # Define the path and write the spool file
    new_file_path = TMP_DIR / f"{hostname}{SPOOL_EXT}"
    with new_file_path.open('w') as new_file:
        new_file.write(spool_text)

    print(f"Created spool file: {new_file_path}")

def create_spool_file(content, hostname, cluster):
    new_content = []
    for line in content:
        if line.startswith("Hostnames:") or line.startswith("Hostname:"):
            new_content.append(f"Hostname: {hostname}\n")
        elif line.startswith("Deployment_name:"):
            base_name = line.split(": ", 1)[1].strip().rsplit("-", 1)[0]
            new_content.append(f"Deployment_name: {base_name}-{hostname.split()[-1]}\n")
        elif line.startswith("Deployment_count:"):
            new_content.append("Deployment_count: 1\n")
        elif line.startswith("Cluster:"):
            new_content.append(f"Cluster: {cluster}\n")
        else:
            new_content.append(line)

    new_file_path = TMP_DIR / f"{hostname}{SPOOL_EXT}"
    with new_file_path.open('w') as new_file:
        new_file.writelines(new_content)
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
    parser.add_argument('deployment', help='Name of the deployment to read from the DB')
    args = parser.parse_args()
    deployment_name = args.deployment
    
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
