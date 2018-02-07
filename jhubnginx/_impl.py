from . import utils
from ._templates import NGINX_VHOST

import subprocess
from pathlib import Path
from jinja2 import Template
from pydash import get as _get


class JhubNginxError(Exception):
    def __init___(self, opts=None, *args):
        Exception.__init__(self, *args)


def warn(msg):
    print('WARNING:'+msg)


def debug(msg):
    print(msg)


def render_vhost(domain, opts, **kwargs):
    return Template(NGINX_VHOST).render(domain=domain, **kwargs, **opts)


def domain_config_path(domain, opts):
    return Path(_get(opts, 'nginx.sites'))/domain


def update_dns(domain, public_ip, opts):
    import requests

    token = _get(opts, 'duckdns.token', None)
    if token is None:
        return False

    if not domain.endswith('.duckdns.org'):
        return False

    domain = domain.split('.')[-3]

    try:
        with requests.get('https://www.duckdns.org/update',
                          dict(domains=domain,
                               token=token,
                               ip=public_ip)) as req:
            if req and req.text == "OK":
                return True

            if req.text == 'KO':
                raise JhubNginxError('Duck DNS refused to update -- {} token:{}'.format(domain, token))
            else:
                raise JhubNginxError('Failed to contact duck DNS')

    except IOError as e:
        raise JhubNginxError('Failed to update duck DNS')

    return False


def check_dns(domain, public_ip=None, opts=None):
    '''Check that domain resolves to public ip of this host.

       If it doesn't and it is a duckdns domain and duckdns token is configured then update DNS record.

       throws JhubNginxError if
       - DNS doesn't match public ip and can not be updated
       - Public ip can not be discovered
    '''
    opts = opts if opts else utils.default_opts()

    if public_ip is None:
        public_ip = utils.public_ip()
        if public_ip is None:
            raise JhubNginxError("Can't finds public IP of this host")

    domain_ip = utils.resolve_hostname(domain)

    if domain_ip == public_ip:
        debug('DNS record is already up to date')
        return True

    if domain_ip != public_ip:
        if update_dns(domain, public_ip, opts):
            debug('Updated DNS record successfully')
            return True

    if domain_ip is None:
        raise JhubNginxError('No DNS record for {}, and no way to update'.format(domain))
    else:
        raise JhubNginxError("DNS record doesn't match public IP: {} is {} should be {}".format(
            domain, domain_ip, public_ip))


def add_or_check_vhost(domain,
                       hub_ip='127.0.0.1',
                       hub_port='8000',
                       opts=None):

    opts = utils.default_opts(opts)
    vhost_cfg_file = domain_config_path(domain, opts)
    public_ip = utils.public_ip()

    def nginx_reload():
        debug('Reloading nginx config')
        try:
            subprocess.check_call(_get(opts, 'nginx.check_cmd'), shell=True)
            subprocess.check_call(_get(opts, 'nginx.reload_cmd'), shell=True)
        except FileNotFoundError as e:
            raise JhubNginxError('Failed to reload nginx config, bad command: {}'.format(str(e)))
        except subprocess.CalledProcessError as e:
            raise JhubNginxError('Failed to reload nginx config: {}'.format(str(e)))

    def run_certbot():
        debug('Running certbot for {}'.format(domain))

        cmd = ('certbot certonly'
               ' --webroot -w {webroot}'
               ' --text --agree-tos --no-eff-email'
               ' --email {email}'
               ' --domains {domain}').format(
                   email=_get(opts, 'letsencrypt.email'),
                   webroot=_get(opts, 'letsencrypt.webroot'),
                   domain=domain).split()

        try:
            out = subprocess.check_output(cmd).decode('utf-8')
            debug(out)
        except FileNotFoundError as e:
            raise JhubNginxError('certbot is not installed')
        except subprocess.CalledProcessError as e:
            raise JhubNginxError('certbot reported an error')

    def gen_config(**kwargs):
        txt = render_vhost(domain, opts,
                           hub_port=hub_port,
                           hub_ip=hub_ip,
                           **kwargs)

        return utils.write_if_different(str(vhost_cfg_file), txt)

    def obtain_ssl():
        debug('Obtaining SSL for {}, writing temp vhost config'.format(domain))
        gen_config(nossl=True)
        nginx_reload()
        run_certbot()

    def add_ssl_vhost():
        updated = gen_config()
        if updated:
            debug('Updated vhost config {}'.format(vhost_cfg_file))
            nginx_reload()
        else:
            debug('No changes were required {}'.format(vhost_cfg_file))

    if vhost_cfg_file.exists():
        try:
            check_dns(domain, public_ip, opts)
        except JhubNginxError as e:
            warn('Virtual host config already exists but DNS check/update failed:\n {}'.format(str(e)))

        add_ssl_vhost()  # Make sure content is up to date
        return True

    check_dns(domain, public_ip, opts)
    obtain_ssl()
    add_ssl_vhost()
