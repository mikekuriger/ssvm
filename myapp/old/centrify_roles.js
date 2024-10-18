// Mike Kuriger Sept 20, 2023
// apps should all be configured with a -dev and -prod role

if (centrify_zone.indexOf('app-') !== -1) {
    if(Type == 'Production') {
        var role = [centrify_zone + "-prod"]
    }
    else {
        var role = [centrify_zone +  "-dev"]
    }
}

// groups are not all set up the same so we have this mess here...

else if (centrify_zone == 'grp-dba') {
    if(Type == 'Production') {
        var role = ["app-db-prod", "app-mariadb-prod", "app-mongodb-prod", "app-mysql-prod", "app-postgresdb-prod"]
    }
    else {
        var role = ["app-db-dev", "app-mariadb-dev", "app-mongodb-dev", "app-mysql-dev", "app-postgresdb-dev"]
    }
}
else if (centrify_zone == 'grp-dba-aix') {
    if(Type == 'Production') {
        var role = ["app-dba-aix-prod"]
    }
    else {
        var role = ["app-dba-aix-dev", "app-vision-db=aix-dev"]
    }
}
else if (centrify_zone == 'grp-hadoop-nodes') {
    if(Type == 'Production') {
        var role = ["app-hadoop-prod"]
    }
    else {
        var role = ["app-hadoop-dev", "app-hadoop-qa"]
    }
}
else if (centrify_zone == 'grp-kgen') {
    if(Type == 'Production') {
        var role = ["app-kgen-prod"]
    }
    else {
        var role = ["app-kgen-ftx", "app-kgen-sk1", "app-kgen-sk2", "app-kgen-sk3"]
    }
}
else if (centrify_zone == 'grp-search') {
    if(Type == 'Production') {
        var role = ["grp-search-prod"]
    }
    else {
        var role = ["grp-search-dev"]
    }
}
else if (centrify_zone == 'grp-sre') {
    if(Type == 'Production') {
        var role = ["app-adportal", "app-cdn", "app-git-prod", "app-jenkins", "app-jmeter", "app-junkins", "app-reverseproxy-prod", "app-rundeck", "app-stash", "app-svn-prod", "grp-sre-prod"]
    }
    else {
        var role = ["app-adportal", "app-cdn", "app-jenkins", "app-jmeter", "app-junkins", "app-rundeck", "app-stash"]
    }
}
else if (centrify_zone == 'grp-vra') {
    if(Type == 'Production') {
        var role = ["grp-vra-prod"]
    }
    else {
        var role = ["grp-vra-dev"]
    }
}

// the rest assume all grp-<appname> remaining have roles named app-<appname>-prod and app-<appname>-dev

else {
    var appname = centrify_zone.split('-')
    if(Type == 'Production') {
        var role = ["app-" + appname[1] + "-prod"]
    }
    else {
        var role = ["app-" + appname[1] + "-dev"]
    }
}
return role