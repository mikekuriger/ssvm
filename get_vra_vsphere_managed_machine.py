import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Suppress only the InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

import sys, os, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings') 
django.setup()
sys.path.append("/home/ssvm/ssvm")


import csv
import time
import json
import concurrent.futures

from myapp.models import VRA_Deployment, VRA_Node, HardwareProfile, OperatingSystem, Status


def create_vm(deployment_data):
    deployment_name = deployment_data['deployment_name']
    hostname = deployment_data['hostname']
    domain = deployment_data['domain']
    full_hostname = f"{hostname}.{domain}"
    deployment_date = deployment_data['deployment_date']
    
    # Check if the deployment already exists
    deployment = VRA_Deployment.objects.filter(deployment_name=deployment_name).first()

    if deployment:
        # Deployment exists; update `full_hostnames` with the new hostname if it's not already included
        if full_hostname not in deployment.full_hostnames.split(','):
            deployment.full_hostnames += f", {full_hostname}" if deployment.full_hostnames else full_hostname
            deployment.save()
            print(f"VRA_Deployment {deployment_name} exists, updated full_hostnames.")
    else:
        
        deployment = VRA_Deployment(
            id=deployment_data['uuid'],
            deployment_name=deployment_name,
            deployment_date=deployment_date,
            builtby=deployment_data['builtby'],
            hostname=hostname,
            domain=domain,
            full_hostnames=full_hostname,  # Initialize with the first hostname
            ticket=deployment_data['ticket'],
            appname=deployment_data['appname'],
            owner=deployment_data['owner'],
            owner_value=deployment_data['owner_value'],
            datacenter=deployment_data['datacenter'],
            server_type=deployment_data['server_type'],
            server_type_value=deployment_data['server_type_value'],
            deployment_count=deployment_data['deployment_count'],
            cpu=deployment_data['cpu'],
            ram=deployment_data['ram'],
            os=deployment_data['os'],
            os_value=deployment_data['os_value'],
            disk_size=deployment_data['disk_size'],
            add_disks=deployment_data['add_disks'],
            additional_disk_size=deployment_data['additional_disk_size'],
            mount_path=deployment_data['mount_path'],
            cluster=deployment_data['cluster'],
            network=deployment_data['network'],
            nfs_home=deployment_data['nfs_home'],
            join_centrify=deployment_data['join_centrify'],
            centrify_zone=deployment_data['centrify_zone'],
            centrify_role=deployment_data['centrify_role'],
            install_patches=deployment_data['install_patches'],
            protected=True,
            status='deployed'
        )

        deployment.save()
        print(f"VRA_Deployment {deployment_name} created.")


    # Proceed with creating a VRA_Node regardless of whether the deployment was new or existing
    os_instance, _ = OperatingSystem.objects.get_or_create(name=deployment_data['os_value'])
    status_instance, _ = Status.objects.get_or_create(name='setup', defaults={'description': 'VM is in setup status'})
    hwprofile_instance, _ = HardwareProfile.objects.get_or_create(name='Vmware Virtual Platform', defaults={'description': 'Vmware Virtual Platform'})
    
    # Convert RAM to MB
    rammb = int(deployment_data['ram'] * 1024)

    # Create and save the node
    node = VRA_Node(
        name=full_hostname,
        contact=deployment_data['owner'],
        created_at=deployment_date,
        operating_system=os_instance,
        status=status_instance,
        disk_size=deployment_data['disk_size'],
        hardware_profile=hwprofile_instance,
        deployment=deployment,
        #ticket=deployment_data['ticket'],
        #appname=deployment_data['appname'],
        #datacenter=deployment_data['datacenter'],
        #server_type_value=deployment_data['server_type_value'],
        #deployment_count=deployment_data['deployment_count'],
        processor_count=deployment_data['cpu'],
        physical_memory=deployment_data['ram'],
        #cluster=deployment_data['cluster'],
        centrify_zone=deployment_data['centrify_zone'],
        #centrify_role=deployment_data['centrify_role']
        
    )

    node.save()
    print(f"VRA_Node {hostname} for VRA_Deployment {deployment_name} created.")

                

def vRAOnPrem_Login(vrafqdn, username, password):
    url = f"https://{vrafqdn}/iaas/api/about"
    headers = {
        'accept': "application/json",
        'content-type': "application/json"
    }
    apioutput = requests.get(url, headers=headers, verify=False)
    if apioutput.status_code == 200:
        latest_api_version = apioutput.json()['latestApiVersion']
        apiversion = latest_api_version


    refreshtokenurl = f"https://{vrafqdn}/csp/gateway/am/api/login?access_token"
    iaasUrl = f"https://{vrafqdn}/iaas/api/login?apiVersion={apiversion}"
    headers = {
        'accept': "application/json",
        'content-type': "application/json"
    }
    payload = f'{{"username":"{username}","password":"{password}"}}'
    apioutput = requests.post(refreshtokenurl, data=payload, verify=False, headers=headers)
    refreshtoken = apioutput.json()['refresh_token']
    iaasPayload = f'{{"refreshToken": "{refreshtoken}"}}'
    iaasApiOutput = requests.post(iaasUrl, data=iaasPayload, headers=headers, verify=False)
    if iaasApiOutput.status_code == 200:
        jsondata = iaasApiOutput.json()['token']
        bearerToken = "Bearer " + jsondata
        bearertoken = bearerToken
        return bearertoken
    else:
        print(iaasApiOutput.status_code)


        
def get_Managed_vSphere_VMs(url, token):
    start = time.time()
    global mainurl
    mainurl = url
    url1 = f'https://{url}/deployment/api/deployments?size=100'
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'authorization': token
    }
    totaldeploymentID = []
    csvheading = ['deployment_name', 'builtby', 'owner', 'appname', 'description',
             'created_at', 'deployment_date',
             'hostname', 'ticket',   'datacenter',
             'server_type', 'server_type_value', 'deployment_count', 'cpu',
             'ram', 'os', 'os_value', 'disk_size', 'cluster', 'centrify_zone',
             'centrify_role', 'VMState']
    
 
    csvdata = []
    csvdict = {}
    api_output = requests.get(url1, headers=headers, verify=False)
    if api_output.status_code == 200:
        totalPage = api_output.json()['totalPages']
        total_page = list(range(0, totalPage + 1))

        def get_all_deployment_id(pagenumber):
            url = f'https://{mainurl}/deployment/api/deployments?size=100&page={pagenumber}'
            headers = {
                'accept': "application/json",
                'content-type': "application/json",
                'authorization': token
            }
            api_result = requests.get(url, headers=headers, verify=False)
            if api_result.status_code == 200:
                for i in api_result.json()['content']:
                    totaldeploymentID.append(i['id'])


        def managevSpherevms(deploymentid):
            url2 = f"https://{mainurl}/deployment/api/deployments/{deploymentid}" \
                   f"/resources?resourceTypes=Cloud.vSphere.Machine"
            url3 = f"https://{mainurl}/deployment/api/deployments/{deploymentid}"
            headers = {
                'accept': "application/json",
                'content-type': "application/json",
                'authorization': token
            }
            api_output2 = requests.get(url2, headers=headers, verify=False).json()['content']
            api_output3 = requests.get(url3, headers=headers, verify=False).json()
            
            builtby = api_output3.get('createdBy', 'Unknown')
            description = api_output3.get('description', 'No Description')
            deployment_name = api_output3.get('name', 'No Name')
            domain = 'corp.pvt'
            ticket = api_output3['inputs']['jira']
            appname = api_output3['inputs']['app']
            owner = api_output3.get('ownedBy', 'No Owner')
            datacenter = api_output3['inputs']['text_76ce407a']
            server_type = api_output3['inputs']['text_f1df5dee']
            server_type_value = api_output3['inputs']['servertype']
            disk_size = api_output3['inputs']['storage']
            centrify_zone = api_output3['inputs']['centrify_zone']
            centrify_role = api_output3['inputs']['centrify_role']
            created_at = api_output3['createdAt']
            deployment_date = created_at.split('.')[0]
            
            for s in api_output2:
                if 'datastoreName' not in s['properties'].keys():
                    s['properties']['datastoreName'] = ''
                
                hostname = s['properties']['resourceName']
                uuid = s['id']
                deployment_count = s['properties']['count']
                cpu = s['properties']['cpuCount']
                ram = s['properties']['totalMemoryMB']
                os = s['properties']['cloneFromImage']
                os_value = s['properties']['softwareName']
                cluster = s['properties']['zone']
                
                print(uuid)
                
                # Bundle all data into a dictionary
                try:
                    # Check if 'networks' is a list or dictionary and handle accordingly
                    network_name = (
                        s['properties']['networks'][0]['name']  # Assuming you want the first network's name if it's a list
                        if isinstance(s['properties']['networks'], list) and s['properties']['networks']
                        else s['properties'].get('networks', {}).get('name', 'default_network')
                    )
                    
                    deployment_data = {
                        'deployment_name': deployment_name,
                        'uuid': uuid,
                        'deployment_date': deployment_date,
                        'builtby': builtby,
                        'hostname': hostname,
                        'domain': domain,
                        'full_hostnames': [hostname + '.' + domain],  # assuming full hostname is needed
                        'ticket': ticket,
                        'appname': appname,
                        'owner': owner,
                        'owner_value': owner,  # assuming owner and owner_value are the same
                        'datacenter': datacenter,
                        'server_type': server_type,
                        'server_type_value': server_type_value,
                        'deployment_count': deployment_count,
                        'cpu': cpu,
                        'ram': ram,
                        'os': os,
                        'os_value': os_value,
                        'disk_size': disk_size,
                        'add_disks': False,  # set based on requirements
                        'additional_disk_size': None,  # set based on requirements
                        'mount_path': None,  # set based on requirements
                        'cluster': cluster,
                        'network': network_name,  # Use the determined network_name
                        'nfs_home': False,  # set based on requirements
                        'join_centrify': False,  # set based on requirements
                        'centrify_zone': centrify_zone,
                        'centrify_role': centrify_role,
                        'install_patches': False  # set based on requirements
                        
                    }

                    create_vm(deployment_data)
                except KeyError as e:
                    print(f"KeyError: {e}")
                except Exception as e:
                    print(f"Error: {e}")

                
        with concurrent.futures.ThreadPoolExecutor() as Executor:
            data = Executor.map(get_all_deployment_id, total_page)
            
        with concurrent.futures.ThreadPoolExecutor() as Executor:
            results = Executor.map(managevSpherevms, totaldeploymentID)
            
        end = time.time()
        timetaken = end - start
        print(f'Managed VM Function Total Time Taken  :  {timetaken} Seconds')
    else:
        print(api_output.status_code)



sys.path.append("/home/ssvm/ssvm")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

authtoken = vRAOnPrem_Login(vrafqdn='st1vra.corp.pvt', username='mk7193', password='Mrkamk2021#')
get_Managed_vSphere_VMs(url='st1vra.corp.pvt', token=authtoken)

