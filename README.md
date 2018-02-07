# jhub-nginx-vhost

Library and a command line tool for generating virtual hosts configuration files for nginx to serve as a proxy for JupyterHub instance. Library takes care of obtaining free SSL certificates from letsencrypt.org and optionally DNS management (if using free dns provider duckdns.org).

1. OPTIONAL: update DNS record if using duckdns.org
2. Obtain SSL certificate using `certbot` (using webroot method)
3. Generate vhost entry to forward traffic to JupyterHub

## Dependencies

1. Nginx (needs to installed an running)
2. Certbot
