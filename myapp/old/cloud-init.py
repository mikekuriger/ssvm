import base64
from jinja2 import Environment, FileSystemLoader

# Set up Jinja2 environment and load the template file
env = Environment(loader=FileSystemLoader(searchpath="./templates"))
template = env.get_template("user_data_template.j2")

# Values to populate in the template
template_data = {
    'vm': 'st1lntmike01',
    'date': '2024-10-01',
    'env': 'production',
    'builtby': 'Mike Kuriger',
    'ticket': 'TSM-184899',
    'appname': 'webserver',
    'owner': 'John Doe'
}

# Render the user-data template with data
user_data = template.render(template_data)

# Base64 encode the user-data output
encoded_user_data = base64.b64encode(user_data.encode('utf-8')).decode('utf-8')

# MAC and network values (these can be dynamically set as well)
mac_address = "00:50:56:84:fc:df"
network = "VLAN540"

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

# Write the OVF XML to a file
with open('cloud-init-images/{VM}/ovf-env.xml', 'w') as f:
    f.write(ovf_xml)

print("OVF XML generated and saved to cloud-init-images/{VM}/ovf-env.xml")
