import requests
import urllib3

# Disable SSL warning messages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up authentication details
url = 'https://st1dceipmaster.corp.pvt/rest'
username = 'mk7193'
password = 'Mrkamk2021#'

# Authenticate and obtain a session
session = requests.Session()
session.auth = (username, password)
    
# Set up the DNS record details
data = {
    'dns_name': 'zigzag.corp.pvt',
    'dns_type': 'A',
    'dns_value': '192.168.1.101',
    'dns_class_name': 'IN',
    'dns_zone': 'corp.pvt'
}
    
# Send the request to add the record
response = session.post(url, data=data, verify=False)
if response.status_code == 200:
    print(f"DNS record added: {data['dns_name']} -> {data['dns_value']}")
else:
    print(f"Failed to add DNS record: {response.status_code} - {response.text}")
