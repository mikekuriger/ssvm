from jinja2 import Environment, FileSystemLoader
import argparse
import os
from datetime import datetime
# 10-1-24 Mike Kuriger 

# Set up argument parsing
parser = argparse.ArgumentParser(description='Generate OVF environment file.')
parser.add_argument('--vm', required=True, help='VM name')
parser.add_argument('--type', required=True, help='Type (Production)')
parser.add_argument('--builtby', required=True, help='Built by')
parser.add_argument('--ticket', required=True, help='Jira ticket')
parser.add_argument('--appname', required=True, help='App name')
parser.add_argument('--owner', required=True, help='App owner')
# optional
parser.add_argument('--automount', required=False, help='Automount home dir (true/false)')
parser.add_argument('--adddisk', required=False, help='Add Disk (size,mountpoint)')
#parser.add_argument('--disk_size', required=False, help='disk size')
#parser.add_argument('--disk_mountpoint', required=False, help='disk mountpoint')
#parser.add_argument('--centrify', required=False, help='Join Centrify (true/false)')
parser.add_argument('--centrify_zone', required=False, help='Centrify Zone')
parser.add_argument('--centrify_role', required=False, help='Centrify Role')
parser.add_argument('--patch', required=False, help='Yum Update (true/false)')

args = parser.parse_args()

# Checks
# if args.disk_size:
#     if not args.disk_mountpoint:
#         parser.error("--disk_mountpoint is required when --disk_size is set")
if args.adddisk:
    mountdisks = f"/vra_automation/installs/mount_extra_disks.sh"
    #dumpdisks = f"echo '{args.disk_size},{args.disk_mountpoint}' >> /etc/vra.disk"
    dumpdisks = f"echo '{args.adddisk}' >> /etc/vra.disk"
else:
    mountdisks = ""
    dumpdisks = ""
        
if args.centrify_zone:
    if not args.centrify_role:
        parser.error("--centrify_role is required when --centrify_zone is set")
    else:
        adjoin = f"/usr/sbin/adjoin --server DFW2W2SDC05.corp.pvt -z {args.centrify_zone} -R {args.centrify_role} " \
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
env = Environment(loader=FileSystemLoader(searchpath="./templates"))
usertemplate = env.get_template("user_data_template.j2")
metatemplate = env.get_template("meta_data_template.j2")

# Values to populate in the template from arguments
template_data = {
    'vm': args.vm,
    'date': date,
    'type': args.type,
    'builtby': args.builtby,
    'ticket': args.ticket,
    'appname': args.appname,
    'owner': args.owner,
    'patch': args.patch,
    'yumupdate': yumupdate,
    'dumpdisks': dumpdisks,
#    'disk_size': args.disk_size,
    'adddisk': args.adddisk,
    'mountdisks': mountdisks,
    'automount_homedir': automount_homedir,
    'automount': args.automount,
    'adjoin': adjoin,
    'centrify_sshd': centrify_sshd,
    'centrify_zone': args.centrify_zone
}

# Render the user-data and meta-data
user_data = usertemplate.render(template_data)
meta_data = metatemplate.render(template_data)

# Directory to save the file
output_dir = f'cloud-init-images/{args.vm}'

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

