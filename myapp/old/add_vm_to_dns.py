from SOLIDserverRest import SOLIDserverRest
import json, logging, math, ipaddress, pprint, argparse, yaml, sys

# Initialize parser
parser = argparse.ArgumentParser(description="Process args")

# Add arguments
parser.add_argument("--dc", required=True, help="st1, ev3")
parser.add_argument("--network", required=True, help="VLAN540")
parser.add_argument("--hostname", required=True, help="example.corp.pvt")
parser.add_argument("--mac", required=True, help="mac address")

# Parse arguments
args = parser.parse_args()

# Load the config
def load_config(filepath):
    with open(filepath, 'r') as file:
        return yaml.safe_load(file)

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
config = load_config('config.yaml')
args_dc = args.dc

if args_dc not in config['datacenters']:
    print(f"Unknown datacenter: {args_dc}")
    sys.exit(1)

# Extract details from the config
datacenter = config['datacenters'][args_dc]
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

dc = dc_to_dc.get(args.dc, "Unknown DC")
vlan = network_to_subnet.get(args.network, "Unknown Network")

subnet = get_subnet_v4(vlan)
#print(subnet)

# get next free address (pick 5 free IPs, skip the first 20)
ipstart = ipaddress.IPv4Address(subnet['addr']) + 50
free_address = get_next_free_address(subnet['id'], 5, ipstart)
#pprint.pprint(free_address)

# add ip to IPAM
hostname = args.hostname
mac_addr = args.mac
node = add_ip_address(free_address['address'][2],hostname,space['id'],mac_addr)
#print(node)
print(free_address['address'][2])

del(SDS_CON)

