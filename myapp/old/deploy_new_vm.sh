#!/bin/bash
#
# This is a temporary script for triggering all the pythin scripts
# 9-16-24 Mike Kuriger

#DEBUG_ECHO="/bin/echo"
#DEBUG_DNS="/bin/echo"

# these should come from the app
VM=$1              #vm name     (st1lntmike01)
OS=$2              #os          (SSVM-OEL8)
CPU=$3             #cpu         (2)
MEM=$(($4*1024))   #mem         (2)
DISK=$5            #disk        (100)
DC=$6              #datacenter  (st1)
VLAN=$7            #vlan        (VLAN540)
CLUSTER=$8         #cluster     (B-2-1)

TYPE=$9            # (Testing)
BUILTBY=${10}      # mk7193
TICKET=${11}       # TSM-00000
APPNAME=${12}      # "Some App Name"
OWNER=${13}        # "Michael Kuriger (mk7193)"
DOMAIN="corp.pvt"

# options
PATCH="--patch 1"
NFS="--automount 1"
#ADDDISK="--disk_size 100 --disk_mountpoint /opt"
ADDDISK="--adddisk 100,/opt"
CENTRIFY="--centrify_zone grp-unix --centrify_role group-unix-dev"


bold='\e[1m'
_bold='\e[0m'


# function for getting datastore from cluster
get_ds() {
    local arg=$8
    CLUSTER=$(echo ${1,,} | sed 's/-//g')
    govc datastore.cluster.info|grep Name|grep $CLUSTER |awk '{print $2}'
}

if [[ $DC = "st1" ]]; then
  DNS=10.6.1.111,10.4.1.111
  DOMAINS='corp.pvt dexmedia.com superpages.com supermedia.com prod.st1.yellowpages.com np.st1.yellowpages.com st1.yellowpages.com'
  if [[ "$VLAN" = "VLAN540" ]]; then
    NETWORK=10.5.32-VLAN540-DvS
    NETMASK=255.255.252.0
  elif [[ "$VLAN" = "VLAN673" ]]; then
    NETWORK=10.5.106-VLAN673-DvS
    NETMASK=255.255.254.0
  elif [[ "$VLAN" = "VLAN421" ]]; then
    NETWORK=10.5.4-VLAN421-DvS
    NETMASK=255.255.252.0
  else
    echo "$VLAN is not a valid VLAN"
    exit 1
  fi
  export GOVC_URL=https://st1vccomp01a.corp.pvt	
else
  DNS=10.4.1.111,10.6.1.111
  DOMAINS='corp.pvt dexmedia.com superpages.com supermedia.com prod.ev1.yellowpages.com np.ev1.yellowpages.com ev1.yellowpages.com'
  if [[ "$VLAN" = "VLAN540" ]]; then
    NETWORK=10.2.32-VLAN540-DvS
    NETMASK=255.255.252.0
  elif [[ "$VLAN" = "VLAN673" ]]; then
    NETWORK=10.4.106-VLAN673-DvS
    NETMASK=255.255.254.0
  elif [[ "$VLAN" = "VLAN421" ]]; then
    NETWORK=10.2.4-VLAN421-DvS
    NETMASK=255.255.252.0
  else
    echo "$VLAN is not a valid VLAN"
    exit 1
  fi
  export GOVC_URL=https://ev3vccomp01a.corp.pvt	
fi

GATEWAY="${NETWORK%%-*}.1"
export GOVC_USERNAME=mk7193
export GOVC_PASSWORD=Mrkamk2021#

# deploy VM by cloning template
bold='\e[1m'
_bold='\e[0m'
echo -n "Getting Datastore Cluster - "
DATASTORECLUSTER=$(get_ds ${CLUSTER}) # datastore cluster
echo "$DATASTORECLUSTER"
echo -e "${bold}Deploying $VM to $CLUSTER${_bold}"
echo -e "${bold}Details:${_bold}"
echo OS - $OS
echo CPU - $CPU
echo MEM - $MEM
echo Disk - $DISK
echo Datacenter - $DC
echo Domain - $DOMAIN
echo VLAN - $VLAN
echo CLUSTER - $CLUSTER
echo DNS - $DNS
echo Domains - $DOMAINS
echo Network - $NETWORK
echo Netmask - $NETMASK
echo Type - $TYPE
echo Built by - $BUILTBY #mk7193
echo Ticket - $TICKET
echo App Name - $APPNAME
echo Owner - $OWNER #Michael Kuriger (mk7193)
echo

echo -e "${bold}Checking to see if a VM already exists with the name $VM${_bold}"
vmstat=$(govc vm.info $VM)
if [[ "$vmstat" =~ $VM ]]; then
  echo -e "${bold}A VM with the name $VM already exists, bailing out!${_bold}"
  govc vm.info $VM
  exit 1
fi
echo "$VM does not exist"
echo -e "${bold}Cloning template${_bold}"
 ${DEBUG_ECHO} govc vm.clone -on=false -vm $OS -c $CPU -m $MEM -net $NETWORK -pool /st1dccomp01/host/${CLUSTER}/Resources -datastore-cluster ${DATASTORECLUSTER} -folder '/st1dccomp01/vm/vRA - Thryv Cloud/TESTING' $VM

# Resize boot disk to match requested size if over 100 (since 100 is default)
if [[ "DISK" -gt "100" ]] && [[ "$OS" = "SSVM-OEL8" ]]; then
  echo -e "${bold}Resizing boot disk to $DISK GB${_bold}"
  ${DEBUG_ECHO} govc vm.disk.change -vm $VM -disk.name "disk-1000-0" -size $DISK
else 
  echo -e "${bold}Disk size is 100G (default), no resize needed${_bold}"
fi

# Get mac address of VM 
echo -e "${bold}Getting mac address${_bold} from vcenter, needed for adding to eIP"
MAC=$(govc vm.info -json $VM | jq -r '.virtualMachines[].config.hardware.device[] | select(.macAddress != null) | .macAddress')
echo "MAC - $MAC"

# add vm to DNS
addit() {
  echo -e "${bold}Adding ${VM}.${DOMAIN} to DNS${_bold}"
  #echo "Running python ./add_vm_to_dns.py --dc $DC --network $VLAN --hostname ${VM}.corp.pvt --mac $MAC"
  python ./add_vm_to_dns.py --dc $DC --network $VLAN --hostname ${VM}.corp.pvt --mac $MAC # 2> /dev/null
  echo "Sleeping 20 seconds for DNS to start working"
  sleep 20
}
adderror() {
  echo -e "${bold}Unable to add $VM to DNS, bailing out!${_bold}"
  exit 1
}
echo -e "${bold}Checking to see if ${VM}.${DOMAIN} is in DNS${_bold}"
host ${VM}.${DOMAIN} &> /dev/null || addit
host ${VM}.${DOMAIN} &> /dev/null || adderror
IP=$(host ${VM}.${DOMAIN} | grep 'has address' | awk '{print $4}')
echo $(host ${VM}.${DOMAIN})

# make sure VM is off 
echo -e "${bold}Powering off $VM in case it's on${_bold}"
POWER=$(govc vm.info $VM | grep 'Power state' |awk -F: '{print $2}' | sed 's/ //g')
if [[ "$POWER" = "poweredOn" ]]; then
    ${DEBUG_ECHO} govc vm.power -off -force $VM
fi

# Customize hotname and IP
echo -e "${bold}Customizing hostname, and IP${_bold}"

#echo 'govc vm.customize -vm '$VM' -type Linux -name '$VM' -domain '$DOMAIN' --mac '$MAC' -ip '$IP' -netmask '$NETMASK' -gateway '$GATEWAY' -dns-server '$DN'S -dns-suffix "'$DOMAINS'"'
${DEBUG_ECHO} govc vm.customize -vm $VM -type Linux -name $VM -domain $DOMAIN --mac $MAC -ip $IP -netmask $NETMASK -gateway $GATEWAY -dns-server $DNS -dns-suffix "$DOMAINS"

# Create cloud-init files
echo -e "${bold}Generating ISO files for cloud-init${_bold}"

CD=$(govc device.ls -vm $VM |grep cdrom | awk '{print $1}')

${DEBUG_ECHO} python generate_iso_command.py --vm ${VM}.${DOMAIN} --type $TYPE --builtby "$BUILTBY" --ticket $TICKET --appname "$APPNAME" --owner "$OWNER" $NFS $ADDDISK $CENTRIFY $PATCH 


# Create ISO image from cloud-init files
echo -e "${bold}Creating ISO image${_bold}"
${DEBUG_ECHO} genisoimage  -output cloud-init-images/${VM}.${DOMAIN}/seed.iso -volid cidata -joliet -rock cloud-init-images/${VM}.${DOMAIN}/user-data cloud-init-images/${VM}.${DOMAIN}/meta-data 

# copy the ISO image to the VM's datastore
echo -e "${bold}Copying the ISO to the VM's datastore${_bold}"
DS=$(govc vm.info -json $VM | jq -r '.virtualMachines[].config.hardware.device[].backing.fileName' |grep '\['|tail -1 | sed -e 's/\[//' -e 's/\]//' | awk '{print $1}')
${DEBUG_ECHO} govc datastore.upload -ds $DS ./cloud-init-images/$VM/seed.iso $VM/seed.iso

# mount the ISO to the VM and power it on
echo -e "${bold}Mount the ISO to the VM and BOOT up${_bold}"
CD=$(govc device.ls -vm $VM |grep cdrom | awk '{print $1}')
${DEBUG_ECHO} govc device.cdrom.insert -vm $VM -device $CD -ds $DS ${VM}/seed.iso
${DEBUG_ECHO} govc device.connect -vm $VM $CD 
${DEBUG_ECHO} govc vm.power -on $VM