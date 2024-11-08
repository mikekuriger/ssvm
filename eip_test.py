from SOLIDserverRest import SOLIDserverRest
import json, logging, math, ipaddress, pprint, uuid

SDS_CON = SOLIDserverRest('st1dceipmaster.corp.pvt')
SDS_CON.set_ssl_verify(False)
SDS_CON.use_basicauth_sds(user='mk7193', password='Mrkamk2021#')

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

#
#
# get space (site id)
space = get_space("thryv-eip-ipam")

#get_subnet_v4
# ST1
subnets1 = get_subnet_v4("ST1 - Weblogic")             # 10.5.32-VLAN540-DvS 'addr': '10.5.32.0', 'cidr': 22
subnets2 = get_subnet_v4("vlan 421- linux_421", dc="DFW Data Center")        # 10.5.4-VLAN421-DvS 'addr': '10.5.4.0', 'cidr': 22
# EV3
#subnet = get_subnet_v4("vlan673_vmware_management")  # 10.4.106-VLAN673-DvS 'addr': '10.5.106.0', 'cidr': 23
subnete1= get_subnet_v4("EV3 - Weblogic")             # 10.2.32-VLAN540-DvS 'addr': '10.2.32.0', 'cidr': 22
subnete2 = get_subnet_v4(name="vlan 421- linux_421", dc="Ashburn Datacenter")        # 10.2.4-VLAN421-DvS 'addr': '10.2.4.0', 'cidr': 22

subnet = subnets2
#print(f"subnet {subnet['addr']}")

# get next free address (pick 5 free IPs, skip the first 20)
ipstart = ipaddress.IPv4Address(subnet['addr']) + 10
free_address = get_next_free_address(subnet['id'], 5, ipstart)
#pprint.pprint(free_address)

# add ip to IPAM
hostname = "st1lntmk7193.corp.pvt"
mac_addr = "00:50:56:84:60:2e"
node = add_ip_address(free_address['address'][2],hostname,space['id'],mac_addr)
print(node)
print(free_address['address'][2])
del(SDS_CON)
