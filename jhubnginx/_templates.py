DEFAULT_CFG = '''
nginx:
   check_cmd: 'nginx -t'
   reload_cmd: 'systemctl reload nginx'

   sites: /etc/nginx/sites-enabled
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

letsencrypt:
   webroot: /var/www/letsencrypt

duckdns: {}
'''

NGINX_VHOST = '''
server {
    server_name {{domain}};
    listen 80;
{% if not nossl %}
    # Tell all requests to port 80 to be 302 redirected to HTTPS
    location / {
       return 302 https://$server_name$request_uri;
    }
{% endif %}
    location ^~ /.well-known/acme-challenge/ {
       default_type "text/plain";
       root {{letsencrypt['webroot']}};
    }
}

{% if not nossl %}
server {
    server_name {{domain}};
    listen 443 ssl http2;

    ssl_certificate /etc/letsencrypt/live/{{domain}}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{{domain}}/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/{{domain}}/fullchain.pem;

    {{nginx['ssl_options']}}

    # Managing literal requests to the JupyterHub front end
    location / {
        proxy_pass http://{{hub_ip}}:{{hub_port}};
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    # Managing WebHook/Socket requests between hub user servers and external proxy
    location ~* /(api/kernels/[^/]+/(channels|iopub|shell|stdin)|terminals/websocket)/? {
        proxy_pass http://{{hub_ip}}:{{hub_port}};
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
{% endif %}
'''
