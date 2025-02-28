# SSVM

This started off as some shell scripts to set up VMs in Vcenter, and has evolved into this thing.

## govc binary and yum install
```
curl -L -o - "https://github.com/vmware/govmomi/releases/latest/download/govc_$(uname -s)_$(uname -m).tar.gz" | tar -C /usr/local/bin -xvzf - govc

yum install -y python3-devel git npm conda genisoimage nginx certbot python3-certbot-nginx openssl
```
## nginx ssl:
```
mkdir -p /etc/nginx/ssl;
cd /etc/nginx/ssl;
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx-selfsigned.key -out nginx-selfsigned.crt
openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
```
## Replace the http section of your config
```
vi /etc/nginx/nginx.conf
```
```
http {
    include       mime.types;
    default_type  application/octet-stream;

    #log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
    #                  '$status $body_bytes_sent "$http_referer" '
    #                  '"$http_user_agent" "$http_x_forwarded_for"';

    #access_log  logs/access.log  main;

    sendfile        on;
    #tcp_nopush     on;

    #keepalive_timeout  0;
    keepalive_timeout  65;

    #gzip  on;

    server {
        listen 80;
        server_name ssvm.corp.pvt st1lntmk7193.corp.pvt st1lntmk7193;
    
        # Redirect all HTTP requests to HTTPS
        return 301 https://$host$request_uri;
    }
    
    server {
        listen 443 ssl;
        server_name ssvm.corp.pvt st1lntmk7193.corp.pvt st1lntmk7193;
    
        ssl_certificate /etc/nginx/ssl/nginx-selfsigned.crt;
        ssl_certificate_key /etc/nginx/ssl/nginx-selfsigned.key;
	ssl_dhparam /etc/nginx/ssl/dhparam.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
    
        location / {
            proxy_pass http://127.0.0.1:8000;  # Your Django app's internal address
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```
## database setup
curl -LsS https://r.mariadb.com/downloads/mariadb_repo_setup | bash
yum install MariaDB-server MariaDB-client MariaDB-devel
systemctl start mariadb
mysql_secure_installation

create root password for mysql
```
systemctl enable mariadb
systemctl start  mariadb
mysql_secure_installation
```
## import a copy of the database
```
mysql -u root -p ssvm < ssvm.dump
```
## create ssvm user
```
useradd ssvm
su - ssvm
mkdir ssvm
cd ssvm
```
## get the code from github
```
cd ~ssvm
git clone https://{username}@stash.int.yp.com/scm/mk/ssvm.git
```
## python stuff
```
python3 -m venv ssvm_env
source ssvm_env/bin/activate

cat <<EOF >> ~/.bash_profile
cd ssvm
source ssvm_env/bin/activate
EOF

pip install --upgrade pip
pip install mysqlclient
pip install django
pip install djangorestframework
pip install django-debug-toolbar
pip install django-background-tasks
pip install jupyterlab
pip install jupyterlab-git
pip install jupyterlab_github
pip install PyYAML
pip install SOLIDserverRest
#pip install channels
```

## database stuff
```
mysql -u root -p
CREATE DATABASE ssvm;
CREATE USER 'ssvm'@'%' IDENTIFIED BY 'pay4ssvm';
GRANT ALL PRIVILEGES ON ssvm.* TO 'ssvm'@'*';
FLUSH PRIVILEGES;
EXIT;
```
## to create database structure, or anytime you change the model, ie add a new field
```
python manage.py makemigrations
python manage.py migrate
```
## to create django admin user
```
cd ~ssvm/ssvm
python manage.py createsuperuser
```
## to start Django app
### standalone:
```
nohup python manage.py runserver 0.0.0.0:8000 > django_output.log 2>&1 & (maybe use systemd)
```
### localhost with nginx ssl
```
nohup python manage.py runserver 127.0.0.1:8000 > django_output.log 2>&1 &
```

The rest of this is just helpful to know


## to set up background task during installation
```
python manage.py migrate background_task
```
## to start the task scheduler (maybe use systemd)
```
python manage.py process_tasks
```
## to run jupytherlab 
```
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser
http://localhost:8888/lab/tree/Users/mk7193/python/myproject/myproject/settings.py
```
## systemd for tasks
vi /etc/systemd/system/django-background-tasks.service
```
[Unit]
Description=Django Background Task Processor
After=network.target

[Service]
User=ssvm
Group=ssvm
WorkingDirectory=/home/svm/ssvm
ExecStart=/bin/bash -c 'source /home/ssvm/ssvm/ssvm_env/bin/activate && python /home/ssvm/ssvm/manage.py process_tasks'
Restart=on-failure
Environment="PATH=/home/ssvm/ssvm/ssvm_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="DJANGO_SETTINGS_MODULE=myproject.settings"
StandardOutput=append:/home/ssvm/ssvm/django-background-tasks.log
StandardError=append:/home/ssvm/ssvm/django-background-tasks.log

[Install]
WantedBy=multi-user.target

TODO: 
remove static configs from deploy_new_vm.py and use the config file 
document all functions and files
remove govc dependency (maybe)
