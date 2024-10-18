# ssvm

#linux
# govc binary for interacting with vcenter
curl -L -o - "https://github.com/vmware/govmomi/releases/latest/download/govc_$(uname -s)_$(uname -m).tar.gz" | tar -C /usr/local/bin -xvzf - govc
yum install -y python37 python3-devel git git-credential-manager mariadb-server mariadb-devel npm conda genisoimage
 nginx certbot python3-certbot-nginx

# nginx ssl:

dnf install nginx
dnf install openssl
mkdir -p /etc/nginx/ssl
cd /etc/nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx-selfsigned.key -out nginx-selfsigned.crt

#Generating a RSA private key
#.....................+++++
#...................................+++++
#writing new private key to 'nginx-selfsigned.key'
#-----
#You are about to be asked to enter information that will be incorporated
#into your certificate request.
#What you are about to enter is what is called a Distinguished Name or a DN.
#There are quite a few fields but you can leave some blank
#For some fields there will be a default value,
#If you enter '.', the field will be left blank.
#-----
#Country Name (2 letter code) [XX]:us
#State or Province Name (full name) []:tx
#Locality Name (eg, city) [Default City]:dfw
#Organization Name (eg, company) [Default Company Ltd]:thryv
#Organizational Unit Name (eg, section) []:techops
#Common Name (eg, your name or your server's hostname) []:st1lntmk7193.corp.pvt
#Email Address []:mk7193@thryv.com

openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
#(takes a long time)

vi /etc/nginx/nginx.conf
#Add the following configuration to configure nginx
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

## mac
#brew install cdrtools # for genisoimage
#brew install govmomi/tap/govc
#brew install mysql
#xcode-select --install
#brew install openssl
#brew install pkg-config
#export LDFLAGS="-L/usr/local/opt/openssl/lib"
#export CPPFLAGS="-I/usr/local/opt/openssl/include"
#* env LDFLAGS="-L/usr/local/opt/openssl/lib" CPPFLAGS="-I/usr/local/opt/openssl/include" pip install mysqlclient

# python stuff
pip install mysqlclient
pip install django
pip install django-debug-toolbar
pip install django-background-tasks
pip install jupyterlab
pip install jupyterlab_github


mysql -u root -p
CREATE DATABASE ssvm;
CREATE USER 'ssvm'@'%' IDENTIFIED BY 'pay4ssvm';
GRANT ALL PRIVILEGES ON ssvm.* TO 'ssvm'@'*';
FLUSH PRIVILEGES;
EXIT;

# to make changes to the database, ie add a new field
python manage.py makemigrations
python manage.py migrate

# to set up background task during installation
python manage.py migrate background_task

# to create django admin user
python manage.py createsuperuser

# to start the task scheduler (maybe use systemd)
python manage.py process_tasks

# to start app
nohup python manage.py runserver 0.0.0.0:8000 > django_output.log 2>&1 & (maybe use systemd)
http://localhost:8000/

# to import scheduled tasks (for build, and alerting), edit the settings.py and uncomment #SCHEDULER_AUTOSTART = True
# the app "should" restart once you make the change, and the tasks will be imported.  
# comment the setting again, or the tasks will keep importing every time you make a change that restarts the app

# to run jupytherlab 
jupyter lab --ip=0.0.0.0 --port=8888 --no-browser
http://localhost:8888/lab/tree/Users/mk7193/python/myproject/myproject/settings.py
