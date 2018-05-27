# jhub-nginx-vhost

Library and a command line tool for generating virtual hosts configuration files for nginx to serve as a proxy for JupyterHub instance. Library takes care of obtaining free SSL certificates from letsencrypt.org and optionally DNS management (if using supported dns provider, anything supported by Apache libcloud also duckdns.org).

1. OPTIONAL: update DNS record
2. Obtain SSL certificate using `certbot` (using webroot method)
3. Generate vhost entry to forward traffic to JupyterHub

## Dependencies

1. Nginx (needs to be installed an running)
2. Certbot


## Installation

### Ubuntu

First prepare dependencies

Install certbot:

```
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:certbot/certbot
sudo apt-get update
sudo apt-get install -y certbot

```

Install nginx and upgrade pip

```
sudo apt-get install -y nginx python3-pip
sudo -H pip3 install --upgrade pip
```

Install this app

```
sudo -H pip3 install git+https://github.com/Kirill888/jhub-nginx-vhost.git#egg=jhub-nginx[dns]
```

Or if running on AWS and want to use IAM roles, install with `ec2` option, this will pull in `boto3` dependency.

```
sudo -H pip3 install git+https://github.com/Kirill888/jhub-nginx-vhost.git#egg=jhub-nginx[ec2]
```

## Configuration


```yaml

# nginx section, this shows defaults being used
nginx:
   check_cmd: 'nginx -t'
   reload_cmd: 'systemctl reload nginx'

   sites: /etc/nginx/conf.d
   ssl_root: /etc/letsencrypt/live

   ssl_options: |
     ssl_session_timeout 1d;
     ssl_session_tickets off;
     ssl_protocols TLSv1.2;
     ssl_ciphers EECDH+AESGCM:EECDH+AES;
     ssl_ecdh_curve secp384r1;
     ssl_prefer_server_ciphers on;
     ssl_stapling on;
     ssl_stapling_verify on;
     add_header Strict-Transport-Security "max-age=15768000; includeSubdomains; preload";
     add_header X-Frame-Options DENY;
     add_header X-Content-Type-Options nosniff;

# letsencrypt.webroot -- where to put temp files
# letsencrypt.email   -- email to use
letsencrypt:
   webroot: /var/www/letsencrypt
   email: env/EMAIL

# Example DNS using cloudflare
dns:
   type: cloudflare
   key: env/EMAIL
   secret: env/CLOUDFLARE_TOKEN
```
