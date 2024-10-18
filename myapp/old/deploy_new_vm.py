from generate_ovf import generate_ovf_xml  # Import the function

# Call the function with required arguments
generate_ovf_xml(
    vm='st1lntmike02',
    date='2024-10-02',
    env='test',
    builtby='John Smith',
    ticket='TSM-123456',
    appname='appserver',
    owner='Jane Doe',
    mac='00:50:56:84:fc:ff',
    network='VLAN421'
)

