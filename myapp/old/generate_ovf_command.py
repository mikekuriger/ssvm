import base64
from jinja2 import Environment, FileSystemLoader
import argparse
import os

# Set up argument parsing
parser = argparse.ArgumentParser(description='Generate OVF environment file.')
parser.add_argument('--vm', required=True, help='VM name')
parser.add_argument('--date', required=True, help='Build date')
parser.add_argument('--env', required=True, help='Environment')
parser.add_argument('--builtby', required=True, help='Built by')
parser.add_argument('--ticket', required=True, help='Jira ticket')
parser.add_argument('--appname', required=True, help='App name')
parser.add_argument('--owner', required=True, help='App owner')
parser.add_argument('--mac', required=True, help='MAC address')
parser.add_argument('--network', required=True, help='Network')

args = parser.parse_args()

# Set up Jinja2 environment and load the template file
env = Environment(loader=FileSystemLoader(searchpath="./templates"))
template = env.get_template("user_data_template.j2")

# Values to populate in the template from arguments
template_data = {
    'vm': args.vm,
    'date': args.date,
    'env': args.env,
    'builtby': args.builtby,
    'ticket': args.ticket,
    'appname': args.appname,
    'owner': args.owner
}

# Render the user-data template with data
user_data = template.render(template_data)

# Base64 encode the user-data output
encoded_user_data = base64.b64encode(user_data.encode('utf-8')).decode('utf-8')

# MAC and network values from arguments
mac_address = args.mac
network = args.network

# OVF XML Template
ovf_xml = f"""
<?xml version="1.0" encoding="UTF-8"?>
<Environment
     xmlns="http://schemas.dmtf.org/ovf/environment/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xmlns:oe="http://schemas.dmtf.org/ovf/environment/1"
     xmlns:ve="http://www.vmware.com/schema/ovfenv"
     oe:id=""
     ve:vCenterId="vm-1711886">
   <PlatformSection>
      <Kind>VMware ESXi</Kind>
      <Version>8.0.3</Version>
      <Vendor>VMware, Inc.</Vendor>
      <Locale>en_US</Locale>
   </PlatformSection>
   <PropertySection>
         <Property oe:key="user-data" oe:value="{encoded_user_data}"/>
   </PropertySection>
   <ve:EthernetAdapterSection>
      <ve:Adapter ve:mac="{mac_address}" ve:network="{network}" ve:unitNumber="7"/>
   </ve:EthernetAdapterSection>
</Environment>
"""

# Directory to save the file
output_dir = f'cloud-init-images/{args.vm}'

# Create the directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Write the OVF XML to a file
output_file = f'{output_dir}/ovf-env.xml'
with open(output_file, 'w') as f:
    f.write(ovf_xml)

print(f"OVF XML generated and saved to {output_file}")
