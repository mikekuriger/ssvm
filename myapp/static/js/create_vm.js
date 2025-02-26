// ssvm javascripts
// 9-16-24 Mike Kuriger

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


// Ticket must be number
document.addEventListener('DOMContentLoaded', function() {
   const ticketField = document.getElementById('ticket');

   ticketField.addEventListener('input', function() {
        this.value = this.value.replace(/[^0-9]/g, '').replace(/^(\d)/, 'TSM-$1');
   });
});

// Initally, populate "hostname" field from "appname"
document.addEventListener('DOMContentLoaded', function() {
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

    // Automatically populate the hostname based on application value
    appnameField.addEventListener('input', updateHostname);

    // Adjust max length when VM count changes
    vmCountField.addEventListener('input', function() {
        const vmCount = parseInt(vmCountField.value, 10) || 1; // Default to 1 if empty or invalid
        if (vmCount > 1) {
            maxHostnameLength = 7;
        } else {
            maxHostnameLength = 9;
        }
        updateHostname();
    });

    // Convert hostname input to lowercase, no spaces
    hostnameField.addEventListener('input', function() {
        hostnameField.dataset.userModified = true;
        this.value = this.value.replace(/[^a-zA-Z0-9_-]/g, '').toLowerCase();
    });
});



// document.addEventListener('DOMContentLoaded', function() {
//     const hostnameField = document.getElementById('hostname');
//     const appnameField = document.getElementById('appname');

//     // Automatically populate the hostname based on application value, Enforce 8-character limit
//     appnameField.addEventListener('input', function() {
//         if (!hostnameField.dataset.userModified) {
//             hostnameField.value = appnameField.value.replace(/[^a-zA-Z0-9_-]/g, '').toLowerCase().substring(0, 8);
//         };
//     });

//     // Convert hostname input to lowercase, no spaces
//     hostnameField.addEventListener('input', function() {
//         hostnameField.dataset.userModified = true;
//        // this.value = this.value.toLowerCase();
//         this.value = this.value.replace(/[^a-zA-Z0-9_-]/g, '').toLowerCase();
//     });
// });

// Dynamically update Full Hostnames and enforce hostname length
document.addEventListener('DOMContentLoaded', function() {
    const submitButton = document.getElementById('submit_button');
    const datacenterField = document.querySelector('#datacenter');
    const serverTypeField = document.querySelector('#server_type');
    const hostnameField = document.querySelector('#hostname');
    const appnameField = document.querySelector('#appname');
    const domainField = document.querySelector('#domain');
    const deploymentCountField = document.querySelector('#deployment_count');
    const fullHostnameField = document.querySelector('#full_hostname');
    const dnsResult = document.querySelector('#dns_result');

    let dnsConflict = false;

    // Function to check form validity
    function checkFormValidity() {
        const datacenter = datacenterField.value.trim();
        const serverType = serverTypeField.value.trim();
        const hostname = hostnameField.value.trim();
        const appname = appnameField.value.trim();
        const deploymentCount = deploymentCountField.value.trim();
        // const dnsConflict = !dnsResult.classList.contains('d-none'); 

        // Enable button only if all fields are filled and no DNS conflict
        if (datacenter && serverType && hostname && deploymentCount && !dnsConflict) {
            submitButton.disabled = false;
        } else {
            submitButton.disabled = true;
        }
    }

    // Function to check DNS and manage conflict display
    function checkDNS(hostnames) {
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
            dnsConflict = false;

            for (const [hostname, exists] of Object.entries(data)) {
                if (exists) {
                    dnsConflict = true;
                    dnsResult.classList.remove('d-none');
                    dnsResult.textContent = `Host already exists in DNS: ${hostname}`;
                    break;
                }
            }

            if (!dnsConflict) {  // Only hide the message if the user typed
                dnsResult.classList.add('d-none');
            }

            // Re-check form validity after DNS check
            checkFormValidity();  
        })
        .catch(error => console.error('Error:', error));
    }

    // Function to resize the Full Hostname box
    function resizeTextArea() {
        const hostnames = fullHostnameField.value.split('\n'); // Split by newline to get number of lines
        const numberOfLines = hostnames.length;
        // Set the textarea 'rows' attribute to the number of lines, but with a minimum of 3 rows
        fullHostnameField.rows = Math.max(numberOfLines, 3);  
    }

    // Function to put hostnames into textarea box
    function updateFullHostnames(hostnames) {
        // Add hostnames to textarea
        fullHostnameField.value = hostnames.join('\n');
        // Resize the textarea to fit the hostnames
        resizeTextArea();  
    }

    // Function to generate Full Hostname(s) and trigger DNS check
    function updateHostnamesAndCheckDNS() {
        const datacenter = datacenterField.value;
        const serverType = serverTypeField.value;
        const userHostname = hostnameField.value;
        const domain = domainField.value;
        const deploymentCount = parseInt(deploymentCountField.value) || 1;

        let fullHostnames = [];
        for (let i = 1; i <= deploymentCount; i++) {
            const suffix = (deploymentCount > 1) ? `${i.toString().padStart(2, '0')}` : '';
           // fullHostnames.push(`${datacenter}${serverType}${userHostname}${suffix}.${domain}`);
            fullHostnames.push(`${datacenter}${serverType}${userHostname}${suffix}`);
        }      
        console.log(fullHostnames);

        // Display generated hostnames in the Full Hostname box
        updateFullHostnames(fullHostnames);

        // Perform DNS check after updating hostnames
        checkDNS(fullHostnames);  

        // Store full hostnames in the hidden input field
        document.getElementById('full_hostnames').value = fullHostnames.join(', ');
        return fullHostnames;
    }

    // Hide the DNS conflict message whenever the user interacts with the form fields
    function resetDNSWarning() {
        dnsResult.classList.add('d-none'); 
        checkFormValidity();  
    }

    // Attach event listeners to all relevant fields to hide the DNS conflict message
    datacenterField.addEventListener('change', resetDNSWarning);
    serverTypeField.addEventListener('change', resetDNSWarning);
    domainField.addEventListener('change', resetDNSWarning);
    hostnameField.addEventListener('input', resetDNSWarning);
    deploymentCountField.addEventListener('input', resetDNSWarning);

    // Event listeners to track input changes
    datacenterField.addEventListener('change', updateHostnamesAndCheckDNS);
    serverTypeField.addEventListener('change', updateHostnamesAndCheckDNS);
    domainField.addEventListener('change', updateHostnamesAndCheckDNS);
    hostnameField.addEventListener('input', updateHostnamesAndCheckDNS);
    appnameField.addEventListener('input', updateHostnamesAndCheckDNS);
    deploymentCountField.addEventListener('input', updateHostnamesAndCheckDNS);

    // Re-check form validity on every input change
    datacenterField.addEventListener('input', checkFormValidity);
    serverTypeField.addEventListener('input', checkFormValidity);
    domainField.addEventListener('input', checkFormValidity);
    hostnameField.addEventListener('input', checkFormValidity);
    deploymentCountField.addEventListener('input', checkFormValidity);
});



// event listener to update some fields' default value, in case the user leaves them alone
document.addEventListener('DOMContentLoaded', function() {
    const fields = [
        { fieldId: 'server_type', valueId: 'server_type_value' },
        { fieldId: 'owner', valueId: 'owner_value' },
        { fieldId: 'os', valueId: 'os_value' },
    ];

    // Function to update the hidden value for a field
    function updateFieldValue(fieldId, valueId) {
        const field = document.getElementById(fieldId);
        const valueField = document.getElementById(valueId);
        const selectedValue = field.options ? field.options[field.selectedIndex].text : field.value;
        valueField.value = selectedValue;
    }

    // Trigger the value update for all fields on page load
    fields.forEach(function(field) {
        updateFieldValue(field.fieldId, field.valueId);
    });

    // Add event listeners for changes on all fields
    fields.forEach(function(field) {
        document.getElementById(field.fieldId).addEventListener('change', function() {
            updateFieldValue(field.fieldId, field.valueId);
        });
    });
});



// populate the cluster and network options (and domain!)
document.addEventListener('DOMContentLoaded', function() {
    const datacenterField = document.getElementById('datacenter');
    const clusterField = document.getElementById('cluster');
    const networkField = document.getElementById('network');
    const domainField = document.getElementById('domain');

    console.log("Datacenters data:", datacenters);  // Ensure this logs the correct structure
    
    // Function to update the cluster options based on the selected datacenter
    function updateClusterOptions(datacenter) {
        clusterField.innerHTML = ''; // Clear current options

        // Add new options based on the selected datacenter's CLUSTERs
        if (datacenters[datacenter] && datacenters[datacenter].clusters) {
            Object.entries(datacenters[datacenter].clusters).forEach(([cluster, description]) => {
                const option = document.createElement('option');
                option.value = cluster;
                if (description) {
                    option.textContent = cluster + " (" + description + ")";
                } else {
                    option.textContent = cluster;
                }
                clusterField.appendChild(option);
            });
        }
    }
    
    // Function to update the network options based on the selected datacenter
    function updateNetworkOptions(datacenter) {
        networkField.innerHTML = ''; // Clear current options
    
        // Add new options based on the selected datacenter's VLANs
        if (datacenters[datacenter] && datacenters[datacenter].vlans) {
            Object.entries(datacenters[datacenter].vlans).forEach(([vlan, vlanData]) => {
                const option = document.createElement('option');
                option.value = vlan;
    
                // Ensure we extract the VLAN name correctly
                if (typeof vlanData === 'object' && vlanData.name) {
                    option.textContent = vlan + " (" + vlanData.name + ")";
                } else {
                    option.textContent = vlan;  // Fallback if 'name' is missing
                }
    
                networkField.appendChild(option);
            });
        }
    }

    // function updateNetworkOptions(datacenter) {
    //     networkField.innerHTML = ''; // Clear current options

    //     // Add new options based on the selected datacenter's VLANs
    //     if (datacenters[datacenter] && datacenters[datacenter].vlans) {
    //         Object.entries(datacenters[datacenter].vlans).forEach(([vlan, description]) => {
    //             const option = document.createElement('option');
    //             option.value = vlan;
    //             option.textContent = vlan + " (" + description + ")";
    //             networkField.appendChild(option);
    //         });
    //     }
    // }
    
    // Function to update the domain options based on the selected datacenter
    function updateDomainOptions(datacenter) {
        domainField.innerHTML = ''; // Clear current options

        // Add new options based on the selected datacenter's Domains
        if (datacenters[datacenter] && datacenters[datacenter].domains) {
            Object.entries(datacenters[datacenter].domains).forEach(([domain, bla]) => {
                const option = document.createElement('option');
                option.value = domain;
                option.textContent = domain;
                domainField.appendChild(option);
            });
        }
    }
    
    // Listen for changes to the datacenter field
    datacenterField.addEventListener('change', function() {
        const selectedDatacenter = datacenterField.value;
        updateClusterOptions(selectedDatacenter);
        updateNetworkOptions(selectedDatacenter);
        updateDomainOptions(selectedDatacenter);
    });
    
    // Trigger the update when the page loads to set the initial options
    // if (datacenterField.value) {
    //     updateClusterOptions(datacenterField.value);
    //     updateNetworkOptions(datacenterField.value);
    //     updateDomainOptions(datacenterField.value);
    // }

    // Trigger the update when the page loads to set the initial options
    updateClusterOptions(datacenterField.value);
    updateNetworkOptions(datacenterField.value);
    updateDomainOptions(datacenterField.value);
});


// calculate centrify-role based on server-type, and centrify-zone slecected
document.addEventListener('DOMContentLoaded', function() {
    const zoneField = document.getElementById('centrify_zone');
    const roleField = document.getElementById('centrify_role');
    const environmentField = document.getElementById('server_type');

    function updateRoles() {
        const centrify_zone = zoneField.value;
        const Type = environmentField.value;

        let roles = [];

        // Mike Kuriger logic for role assignment
        if (centrify_zone.indexOf('app-') !== -1) {
            if (Type === 'Production' || Type === 'lnp') {
                roles = [centrify_zone + '-prod'];
            } else {
                roles = [centrify_zone + '-dev'];
            }
        }
        else if (centrify_zone === 'grp-dba') {
            roles = (Type === 'Production' || Type === 'lnp') ? 
                ["app-db-prod", "app-mariadb-prod", "app-mongodb-prod", "app-mysql-prod", "app-postgresdb-prod"] :
                ["app-db-dev", "app-mariadb-dev", "app-mongodb-dev", "app-mysql-dev", "app-postgresdb-dev"];
        }
        else if (centrify_zone === 'grp-search') {
            roles = (Type === 'Production' || Type === 'lnp') ? 
                ["grp-search-prod"] :
                ["grp-search-dev"];
        }
        else if (centrify_zone === 'grp-sre') {
            roles = (Type === 'Production' || Type === 'lnp') ? 
                ["app-adportal", "app-cdn", "app-git-prod", "app-jenkins", "app-jmeter", "app-junkins", "app-reverseproxy-prod", "app-rundeck", "app-stash", "app-svn-prod", "grp-sre-prod"] :
                ["app-adportal", "app-cdn", "app-jenkins", "app-jmeter", "app-junkins", "app-rundeck", "app-stash"];
        }
        else if (centrify_zone === 'grp-vra') {
            roles = (Type === 'Production' || Type === 'lnp') ? 
                ["grp-vra-prod"] :
                ["grp-vra-dev"];
        }
        else {
            let appname = centrify_zone.split('-');
            roles = (Type === 'Production' || Type === 'lnp') ? 
                ["app-" + appname[1] + "-prod"] :
                ["app-" + appname[1] + "-dev"];
        }

        // Clear previous options in roleField
        roleField.innerHTML = '';

        // Populate the role dropdown with new options
        roles.forEach(role => {
            let option = document.createElement('option');
            option.value = role;
            option.text = role;
            //roleField.add(option);
            roleField.appendChild(option);
        });
    }

    // Event listeners to update roles dynamically
    zoneField.addEventListener('change', updateRoles);
    environmentField.addEventListener('change', updateRoles);

    zoneField.addEventListener('change', function() {
        const selectedZone = zoneField.value;
        updateRoles(selectedZone);
    });

});

// JavaScript to show/hide extra disk fields
document.addEventListener('DOMContentLoaded', function() {
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
});

// JavaScript to show/hide centrify fields
document.addEventListener('DOMContentLoaded', function() {
    const joincentrifyCheckbox = document.getElementById('join_centrify');
    const centrifyzoneFields = document.getElementById('centrify_zone_field');
    const centrifyroleField = document.getElementById('centrify_role_field');

    joincentrifyCheckbox.addEventListener('change', function() {

        //console.log("Checkbox state:", joincentrifyCheckbox.checked);

        if (joincentrifyCheckbox.checked) {
            // Remove 'hidden' class to show fields
            centrifyzoneFields.classList.remove('hidden');
            centrifyroleField.classList.remove('hidden');
        } else {
            // Add 'hidden' class to hide fields
            centrifyzoneFields.classList.add('hidden');
            centrifyroleField.classList.add('hidden');
        }
    });
});

// enable clone
function toggleFields() {
    const cloneCheckbox = document.getElementById("clone");
    const osFieldContainer = document.getElementById("os-field"); // Linux Version container div
    const osField = document.getElementById("os"); // Linux Version field (select or input)
    const cloneFromFieldContainer = document.getElementById("clone-from-field"); // Clone From container div
    const cloneFromField = document.getElementById("clone_from"); // Clone From field (input)

    if (cloneCheckbox.checked) {
        osFieldContainer.classList.add("hidden");            // Hide Linux Version container
        cloneFromFieldContainer.classList.remove("hidden");  // Show Clone From container
        // osField.removeAttribute("required");                 // Make Linux Version optional
        // cloneFromField.setAttribute("required", "required"); // Make Clone From required
    } else {
        osFieldContainer.classList.remove("hidden");         // Show Linux Version container
        cloneFromFieldContainer.classList.add("hidden");     // Hide Clone From container
        // cloneFromField.removeAttribute("required");          // Make Clone From optional
        // osField.setAttribute("required", "required");        // Make Linux Version required
    }
}

// Run toggleFields on page load
document.addEventListener("DOMContentLoaded", toggleFields);
