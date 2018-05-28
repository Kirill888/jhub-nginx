# jhub-nginx-vhost

Library and a command line tool for generating virtual hosts configuration files for nginx to serve as a proxy for JupyterHub instance. Library takes care of obtaining free SSL certificates from letsencrypt.org and optionally DNS management (if using supported dns provider, anything supported by Apache libcloud also duckdns.org).

1. OPTIONAL: update DNS record
2. Obtain SSL certificate using `certbot` (using webroot method)
3. Generate vhost entry to forward traffic to JupyterHub

## Dependencies

1. Nginx (needs to be installed and running)
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
sudo apt-get install -y nginx git python3-pip
sudo -H pip3 install --upgrade pip
```

Install this app

```
sudo -H pip3 install git+https://github.com/Kirill888/jhub-nginx.git#egg=jhub-nginx[dns]
```

Or if running on AWS and want to use IAM roles, install with `ec2` option, this will pull in `boto3` dependency.

```
sudo -H pip3 install git+https://github.com/Kirill888/jhub-nginx.git#egg=jhub-nginx[ec2]
```

Check that everything worked:

```
jhub-vhost --help
```

If you manage DNS records externally then you can skip configuration and just run:

```
sudo jhub-vhost add --email user@example.com jupyter.example.com
```

This will:

1. Create temporary configuration for Nginx compatible with `certbot`
2. Obtain SSL certificate from Let's Encrypt using `certbot`
3. Create final configuration for Nginx that will proxy outside traffic to default jupyterhub configuration `http://127.0.0.1:8000`

## Configuration

Configuration is done via YAML file. At the absolute minimum you need to supply
an email address to give to Let's Encrypt. If you want `jhub-vhost` to manage
DNS records for you, DNS credentials will also need to be supplied. If
running in AWS and using Route53, then the recommended way is to set up IAM role
with proper permissions, `jhub-vhost` will then automatically use credentials
from `boto3` library.

Rather than storing sensitive information in the configuration file you can
instead reference it via environment variables, any value of the form
`env/VARNAME` will be replaced with the value of `VARNAME` environment variable.

Example minimal configuration when using [Cloudflare](https://www.cloudflare.com) 
DNS servers (free for personal use)

Create file `cfg.yml`

```yaml
letsencrypt:
   email: env/EMAIL
dns:
   type: cloudflare
   key: env/EMAIL
   secret: env/CLOUDFLARE_TOKEN
```

Setup environment and run `jhub-vhost`

```bash
export EMAIL=user@example.com
export CLOUDFLARE_TOKEN=96809e84055d7ed8575173103308639df1724d

jhub-vhost -c cfg.yml add jupyter.example.com
```

To just update DNS following command can be used

```bash
jhub-vhost -c cfg.yml dns --update jupyter.example.com
```

When you are done, you can revoke SSL certificate and remove Nginx configuration
with the following command:

```bash
jhub-vhost remove jupyter.example.com
```

### Default Configuration

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

# location used by certbot to write temporary files to, to prove domain name ownership
letsencrypt:
   webroot: /var/www/letsencrypt
```
