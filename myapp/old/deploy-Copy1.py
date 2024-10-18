import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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

# this file reads the deployment output, and creates
# individual deployment files for each VM in the deployment.
# Currently, it puts each VM in a different cluster, round robin
# skipping the Oracle clusters
# I will add a checkbox to the form so the user can decide
# if the VMs go into one cluster or if they are divided up

# once the deployment files are generated, the VMs are deployed

# Configuration constants
SOURCE_DIR = Path("/home/mk7193/python/myproject/media/")
SOURCE_DIR = Path("/home/mk7193/python/myproject/media/")
TMP_DIR = Path("/home/mk7193/python/myproject/tmp")
SPOOL_EXT = ".spool"
BUILDING_EXT = ".building"
DEPLOYED_EXT = ".deployed"
FAILED_EXT = ".failed"
LOG_EXT = ".log"
DEPLOY_SCRIPT = "./deploy_new_vm.py"
MAX_PARALLEL_JOBS = 5
#CLUSTERS_CONFIG_FILE = "clusters.yaml"

# def load_clusters():
#     with open(CLUSTERS_CONFIG_FILE, 'r') as file:
#         clusters_data = yaml.safe_load(file)
#     return clusters_data["clusters"]

def create_spool_files(deployment_name):
    source_path = SOURCE_DIR / deployment_name
    if not source_path.exists():
        print(f"Source file {source_path} not found.")
        return

    with source_path.open('r') as file:
        content = file.readlines()

    hostname_list = extract_hostnames(content)
    
    st1_clusters = ["B-2-3", "B-2-4", "B-2-6", "B-2-7", "B-2-8", "B-2-9"]
    ev3_clusters = ["A-1-1", "A-1-2", "A-1-3", "A-1-5", "A-1-6", "A-1-7", "A-1-8"]

    for i, hostname in enumerate(hostname_list):
        if hostname.startswith("st1"):
            clusters = st1_clusters
        elif hostname.startswith("ev3"):
            clusters = ev3_clusters
        else:
            print(f"Unrecognized hostname prefix for {hostname}. Skipping.")
            continue  # Skip if the prefix doesn't match any known cluster list
        
        cluster = clusters[i % len(clusters)]    
        create_spool_file(content, hostname, cluster)

    # Rename the source file to indicate it has been processed
    deployed_source_path = source_path.with_suffix(DEPLOYED_EXT) 
    source_path.rename(deployed_source_path)
    print(f"Source file renamed to {deployed_source_path}")


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

def deploy_vm(file_name):
    # Update status in database
    try:
        # Retrieve the deployment object from the database
        deployment = Deployment.objects.get(deployment_name=deployment_name)

    except Deployment.DoesNotExist:
        print(f"Deployment with name {deployment_name} does not exist in database.")

    except Exception as e:
        # In case of an error, update the status to 'failed'
        deployment.status = 'failed'
        deployment.save()
        print(f"An error occurred: {e}")
    
    deployment.status = 'building'
    deployment.save()

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
            # Update status to deployed
            deployment.status = 'deployed' 
            deployment.save()
            building_path.rename(deployed_path)
            return f"Deployment completed successfully for {file_name}"
        except subprocess.CalledProcessError:
            # Update status to failed
            deployment.status = 'failed' 
            deployment.save()
            building_path.rename(failed_path)
            return f"Deployment failed for {file_name}"

        
        
def main():
    parser = argparse.ArgumentParser(description='Deploy script with file input')
    parser.add_argument('file', help='Name of the file to read for deployment, or NONE to run existing spool files')
    args = parser.parse_args()
    deployment_name = args.file
    deployment = None  # Initialize deployment to None
    
    # for now, read the deployment info from the text file, but we do have 
    # access to the same info from the database so I'll add that soon.
    # for now, just process the text file and update the status in the DB
    
    # this part is for creating spool files from the deployment file (text file)
    # I'll change it to pull this data from the database and get rid of the deployment text file
    # Spool files are the same as deployment file if we're building one Vm
    # We create multiple spool files for multiple VMs
    
    # create spool files
    if deployment_name != 'None':
        create_spool_files(deployment_name)
    
    spool_files = [f for f in TMP_DIR.glob(f"*{SPOOL_EXT}")]
    if not spool_files:
        print("No spool files to process.")
        return

    # deploy VMs from spool files, in parallel, {MAX_PARALLEL_JOBS} (5) at a time
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_JOBS) as executor:
        futures = {executor.submit(deploy_vm, file): file for file in spool_files}
        
        for future in as_completed(futures):
            file_name = futures[future]
            try:
                result = future.result()
                print(result)
            except Exception as e:
                print(f"An error occurred with {file_name}: {e}")

if __name__ == "__main__":
    main()
