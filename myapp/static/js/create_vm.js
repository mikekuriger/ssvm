// ssvm javascripts
// 9-16-24 Mike Kuriger

// updated 2-28-25

// Function to get the CSRF token from the cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Get the CSRF token from the cookie
const csrfToken = getCookie('csrftoken');

// Function to enforce ticket field format
function enforceTicketFormat() {
    const ticketField = document.getElementById('ticket');
    if (ticketField) {
        ticketField.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '').replace(/^(\d)/, 'TSM-$1');
        });
    }
}

// Function to initialize hostname based on appname
function initializeHostname() {
    const hostnameField = document.getElementById('hostname');
    const appnameField = document.getElementById('appname');
    const vmCountField = document.querySelector('#deployment_count');
    let maxHostnameLength = 9;

    function updateHostname() {
        if (!hostnameField.dataset.userModified) {
            hostnameField.value = appnameField.value
                .replace(/[^a-zA-Z0-9_-]/g, '')
                .toLowerCase()
                .substring(0, maxHostnameLength);
        }
    }

    if (appnameField) {
        appnameField.addEventListener('input', updateHostname);
    }

    if (vmCountField) {
        vmCountField.addEventListener('input', function() {
            const vmCount = parseInt(vmCountField.value, 10) || 1; // Default to 1 if empty or invalid
            maxHostnameLength = vmCount > 1 ? 7 : 9;
            updateHostname();
        });
    }

    if (hostnameField) {
        hostnameField.addEventListener('input', function() {
            hostnameField.dataset.userModified = true;
            this.value = this.value.replace(/[^a-zA-Z0-9_-]/g, '').toLowerCase();
        });
    }
}

// Function to check form validity
function checkFormValidity() {
    const datacenterField = document.querySelector('#datacenter');
    const serverTypeField = document.querySelector('#server_type');
    const hostnameField = document.querySelector('#hostname');
    const appnameField = document.querySelector('#appname');
    const deploymentCountField = document.querySelector('#deployment_count');
    const submitButton = document.getElementById('submit_button');
    const dnsResult = document.querySelector('#dns_result');

    const datacenter = datacenterField.value.trim();
    const serverType = serverTypeField.value.trim();
    const hostname = hostnameField.value.trim();
    const deploymentCount = deploymentCountField.value.trim();
    const dnsConflict = !dnsResult.classList.contains('d-none');

    if (datacenter && serverType && hostname && deploymentCount && !dnsConflict) {
        submitButton.disabled = false;
    } else {
        submitButton.disabled = true;
    }
}

// Function to check DNS and manage conflict display
function checkDNS(hostnames) {
    const dnsResult = document.querySelector('#dns_result');
    fetch('/check_dns/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ hostnames: hostnames })
    })
    .then(response => response.json())
    .then(data => {
        let dnsConflict = false;

        for (const [hostname, exists] of Object.entries(data)) {
            if (exists) {
                dnsConflict = true;
                dnsResult.classList.remove('d-none');
                dnsResult.textContent = `Host already exists in DNS: ${hostname}`;
                break;
            }
        }

        if (!dnsConflict) {
            dnsResult.classList.add('d-none');
        }

        checkFormValidity();
    })
    .catch(error => console.error('Error:', error));
}

// Function to resize the Full Hostname box
function resizeTextArea() {
    const fullHostnameField = document.querySelector('#full_hostname');
    const hostnames = fullHostnameField.value.split('\n');
    const numberOfLines = hostnames.length;
    fullHostnameField.rows = Math.max(numberOfLines, 3);
}

// Function to update Full Hostnames
function updateFullHostnames(hostnames) {
    const fullHostnameField = document.querySelector('#full_hostname');
    fullHostnameField.value = hostnames.join('\n');
    resizeTextArea();
}

// Function to generate Full Hostname(s) and trigger DNS check
function updateHostnamesAndCheckDNS() {
    const datacenterField = document.querySelector('#datacenter');
    const serverTypeField = document.querySelector('#server_type');
    const hostnameField = document.querySelector('#hostname');
    const domainField = document.querySelector('#domain');
    const deploymentCountField = document.querySelector('#deployment_count');

    const datacenter = datacenterField.value;
    const serverType = serverTypeField.value;
    const userHostname = hostnameField.value;
    const domain = domainField.value;
    const deploymentCount = parseInt(deploymentCountField.value) || 1;

    let fullHostnames = [];
    for (let i = 1; i <= deploymentCount; i++) {
        const suffix = (deploymentCount > 1) ? `${i.toString().padStart(2, '0')}` : '';
        fullHostnames.push(`${datacenter}${serverType}${userHostname}${suffix}`);
    }

    updateFullHostnames(fullHostnames);
    checkDNS(fullHostnames);
    document.getElementById('full_hostnames').value = fullHostnames.join(', ');

    return fullHostnames;
}

// Function to hide DNS conflict message
function resetDNSWarning() {
    const dnsResult = document.querySelector('#dns_result');
    dnsResult.classList.add('d-none');
    checkFormValidity();
}

// Attach event listeners to form fields
function attachEventListeners() {
    const datacenterField = document.querySelector('#datacenter');
    const serverTypeField = document.querySelector('#server_type');
    const domainField = document.querySelector('#domain');
    const hostnameField = document.querySelector('#hostname');
    const appnameField = document.querySelector('#appname');
    const deploymentCountField = document.querySelector('#deployment_count');

    datacenterField.addEventListener('change', resetDNSWarning);
    serverTypeField.addEventListener('change', resetDNSWarning);
    domainField.addEventListener('change', resetDNSWarning);
    hostnameField.addEventListener('input', resetDNSWarning);
    deploymentCountField.addEventListener('input', resetDNSWarning);

    datacenterField.addEventListener('change', updateHostnamesAndCheckDNS);
    serverTypeField.addEventListener('change', updateHostnamesAndCheckDNS);
    domainField.addEventListener('change', updateHostnamesAndCheckDNS);
    hostnameField.addEventListener('input', updateHostnamesAndCheckDNS);
    appnameField.addEventListener('input', updateHostnamesAndCheckDNS);
    deploymentCountField.addEventListener('input', updateHostnamesAndCheckDNS);

    datacenterField.addEventListener('input', checkFormValidity);
    serverTypeField.addEventListener('input', checkFormValidity);
    domainField.addEventListener('input', checkFormValidity);
    hostnameField.addEventListener('input', checkFormValidity);
    deploymentCountField.addEventListener('input', checkFormValidity);
}

// Function to update hidden field values
function updateFieldValue(fieldId, valueId) {
    const field = document.getElementById(fieldId);
    const valueField = document.getElementById(valueId);
    const selectedValue = field.options ? field.options[field.selectedIndex].text : field.value;
    valueField.value = selectedValue;
}

// Function to update hidden field values on page load and change
function updateHiddenFieldValues() {
    const fields = [
        { fieldId: 'server_type', valueId: 'server_type_value' },
        { fieldId: 'owner', valueId: 'owner_value' },
        { fieldId: 'os', valueId: 'os_value' },
    ];

    fields.forEach(function(field) {
        updateFieldValue(field.fieldId, field.valueId);
    });

    fields.forEach(function(field) {
        document.getElementById(field.fieldId).addEventListener('change', function() {
            updateFieldValue(field.fieldId, field.valueId);
        });
    });
}

// Function to update cluster, network, and domain options based on the selected datacenter
function updateOptions() {
    const datacenterField = document.getElementById('datacenter');
    const clusterField = document.getElementById('cluster');
    const networkField = document.getElementById('network');
    const domainField = document.getElementById('domain');

    function updateClusterOptions(datacenter) {
        clusterField.innerHTML = '';
        if (datacenters[datacenter] && datacenters[datacenter].clusters) {
            Object.entries(datacenters[datacenter].clusters).forEach(([cluster, description]) => {
                const option = document.createElement('option');
                option.value = cluster;
                option.textContent = description ? `${cluster} (${description})` : cluster;
                clusterField.appendChild(option);
            });
        }
    }

    function updateNetworkOptions(datacenter) {
        networkField.innerHTML = '';
        if (datacenters[datacenter] && datacenters[datacenter].vlans) {
            Object.entries(datacenters[datacenter].vlans).forEach(([vlan, vlanData]) => {
                const option = document.createElement('option');
                option.value = vlan;
                option.textContent = typeof vlanData === 'object' && vlanData.name ? `${vlan} (${vlanData.name})` : vlan;
                networkField.appendChild(option);
            });
        }
    }

    function updateDomainOptions(datacenter) {
        domainField.innerHTML = '';
        if (datacenters[datacenter] && datacenters[datacenter].domains) {
            Object.entries(datacenters[datacenter].domains).forEach(([domain, _]) => {
                const option = document.createElement('option');
                option.value = domain;
                option.textContent = domain;
                domainField.appendChild(option);
            });
        }
    }

    datacenterField.addEventListener('change', function() {
        const selectedDatacenter = datacenterField.value;
        updateClusterOptions(selectedDatacenter);
        updateNetworkOptions(selectedDatacenter);
        updateDomainOptions(selectedDatacenter);
    });

    updateClusterOptions(datacenterField.value);
    updateNetworkOptions(datacenterField.value);
    updateDomainOptions(datacenterField.value);
}

// Function to update Centrify roles based on zone and environment
function updateCentrifyRoles() {
    const zoneField = document.getElementById('centrify_zone');
    const roleField = document.getElementById('centrify_role');
    const environmentField = document.getElementById('server_type');

    function updateRoles() {
        const centrify_zone = zoneField.value;
        const Type = environmentField.value;

        let roles = [];
        if (centrify_zone.indexOf('app-') !== -1) {
            roles = Type === 'Production' || Type === 'lnp' ? [centrify_zone + '-prod'] : [centrify_zone + '-dev'];
        } else if (centrify_zone === 'grp-dba') {
            roles = Type === 'Production' || Type === 'lnp' ? 
                ["app-db-prod", "app-mariadb-prod", "app-mongodb-prod", "app-mysql-prod", "app-postgresdb-prod"] :
                ["app-db-dev", "app-mariadb-dev", "app-mongodb-dev", "app-mysql-dev", "app-postgresdb-dev"];
        } else if (centrify_zone === 'grp-search') {
            roles = Type === 'Production' || Type === 'lnp' ? ["grp-search-prod"] : ["grp-search-dev"];
        } else if (centrify_zone === 'grp-sre') {
            roles = Type === 'Production' || Type === 'lnp' ? 
                ["app-adportal", "app-cdn", "app-git-prod", "app-jenkins", "app-jmeter", "app-junkins", "app-reverseproxy-prod", "app-rundeck", "app-stash", "app-svn-prod", "grp-sre-prod"] :
                ["app-adportal", "app-cdn", "app-jenkins", "app-jmeter", "app-junkins", "app-rundeck", "app-stash"];
        } else if (centrify_zone === 'grp-vra') {
            roles = Type === 'Production' || Type === 'lnp' ? ["grp-vra-prod"] : ["grp-vra-dev"];
        } else {
            let appname = centrify_zone.split('-');
            roles = Type === 'Production' || Type === 'lnp' ? ["app-" + appname[1] + "-prod"] : ["app-" + appname[1] + "-dev"];
        }

        roleField.innerHTML = '';
        roles.forEach(role => {
            let option = document.createElement('option');
            option.value = role;
            option.text = role;
            roleField.appendChild(option);
        });
    }

    zoneField.addEventListener('change', updateRoles);
    environmentField.addEventListener('change', updateRoles);
}

// Function to toggle additional disk fields visibility
function toggleAdditionalDiskFields() {
    const addDisksCheckbox = document.getElementById('add_disks');
    const additionalDiskFields = document.getElementById('additional_disk_field');
    const mountPathFields = document.getElementById('mount_path_field');

    addDisksCheckbox.addEventListener('change', function() {
        if (addDisksCheckbox.checked) {
            additionalDiskFields.classList.remove('hidden');
            mountPathFields.classList.remove('hidden');
        } else {
            additionalDiskFields.classList.add('hidden');
            mountPathFields.classList.add('hidden');
        }
    });
}

// Function to toggle Centrify fields visibility
function toggleCentrifyFields() {
    const joincentrifyCheckbox = document.getElementById('join_centrify');
    const centrifyzoneFields = document.getElementById('centrify_zone_field');
    const centrifyroleField = document.getElementById('centrify_role_field');

    joincentrifyCheckbox.addEventListener('change', function() {
        if (joincentrifyCheckbox.checked) {
            centrifyzoneFields.classList.remove('hidden');
            centrifyroleField.classList.remove('hidden');
        } else {
            centrifyzoneFields.classList.add('hidden');
            centrifyroleField.classList.add('hidden');
        }
    });
}

// Function to toggle fields based on clone checkbox
function toggleFields() {
    const cloneCheckbox = document.getElementById("clone");
    const osFieldContainer = document.getElementById("os-field");
    const cloneFromFieldContainer = document.getElementById("clone-from-field");

    if (cloneCheckbox.checked) {
        osFieldContainer.classList.add("hidden");
        cloneFromFieldContainer.classList.remove("hidden");
    } else {
        osFieldContainer.classList.remove("hidden");
        cloneFromFieldContainer.classList.add("hidden");
    }
}

// Initialize event listeners on DOM content loaded
document.addEventListener('DOMContentLoaded', function() {
    enforceTicketFormat();
    initializeHostname();
    attachEventListeners();
    updateHiddenFieldValues();
    updateOptions();
    updateCentrifyRoles();
    toggleAdditionalDiskFields();
    toggleCentrifyFields();
    toggleFields();
});