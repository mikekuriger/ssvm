# SSVM
## govc binary for interacting with vcenter
```
curl -L -o - "https://github.com/vmware/govmomi/releases/latest/download/govc_$(uname -s)_$(uname -m).tar.gz" | tar -C /usr/local/bin -xvzf - govc

yum install -y python3-devel git mariadb-server mariadb-devel npm conda genisoimage
 nginx certbot python3-certbot-nginx openssl
```
## nginx ssl:
```
mkdir -p /etc/nginx/ssl;
cd /etc/nginx/ssl;
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx-selfsigned.key -out nginx-selfsigned.crt
openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
```
## Add the following configuration to configure nginx
```
vi /etc/nginx/nginx.conf

#user  nobody;
worker_processes  1;

#error_log  logs/error.log;
#error_log  logs/error.log  notice;
#error_log  logs/error.log  info;

#pid        logs/nginx.pid;


events {
    worker_connections  1024;
}


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
## python stuff
```
pip install mysqlclient
pip install django
pip install django-debug-toolbar
pip install django-background-tasks
pip install jupyterlab
pip install jupyterlab_github
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

## to make changes to the database, ie add a new field
```
python manage.py makemigrations
python manage.py migrate
```

## to set up background task during installation
```
python manage.py migrate background_task
```

## to create django admin user
```
python manage.py createsuperuser
```

## to start the task scheduler (maybe use systemd)
```
python manage.py process_tasks
```

## to start app
### standalone:
```
nohup python manage.py runserver 0.0.0.0:8000 > django_output.log 2>&1 & (maybe use systemd)
```

### localhost with nginx ssl
```
nohup python manage.py runserver 127.0.0.1:8000 > django_output.log 2>&1 &
```

## to run jupytherlab 
```
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser
http://localhost:8888/lab/tree/Users/mk7193/python/myproject/myproject/settings.py
```
