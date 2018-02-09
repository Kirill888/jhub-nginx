import os
import subprocess
from pathlib import Path
from jinja2 import Template
from pydash import get as _get

from . import utils
from .utils import JhubNginxError
from ._templates import NGINX_VHOST
from .dns import check_dns


def warn(msg):
    print('WARNING:'+msg)


def debug(msg):
    print(msg)


def render_vhost(domain, opts, **kwargs):
    return Template(NGINX_VHOST).render(domain=domain, **kwargs, **opts)


def domain_config_path(domain, opts):
    return Path(_get(opts, 'nginx.sites'))/domain


def add_or_check_vhost(domain,
                       hub_ip='127.0.0.1',
                       hub_port='8000',
                       skip_dns_check=False,
                       standalone=False,
                       opts=None):

    opts = utils.default_opts(opts)
    vhost_cfg_file = domain_config_path(domain, opts)
    public_ip = None if skip_dns_check else utils.public_ip()
    email = _get(opts, 'letsencrypt.email', None)

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

        if standalone:
            cmd = ('certbot certonly'
                   ' --standalone'
                   ' --text --agree-tos --no-eff-email'
                   ' --email {email}'
                   ' --domains {domain}').format(
                       email=_get(opts, 'letsencrypt.email'),
                       domain=domain).split()

        else:
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

    def attempt_cleanup():
        debug('Cleaning up {}'.format(vhost_cfg_file))

        try:
            os.remove(str(vhost_cfg_file))
            nginx_reload()
        except JhubNginxError as e:
            debug('Ooops failure within a failure: {}'.format(str(e)))
        except OSError as e:
            debug('Ooops failure within a failure: {}'.format(str(e)))

    def have_ssl_files():
        ssl_root = Path(_get(opts, 'nginx.ssl_root'))/domain
        privkey = ssl_root/"privkey.pem"
        fullchain = ssl_root/"fullchain.pem"
        return privkey.exists() and fullchain.exists()

    def obtain_ssl():
        if email is None:
            raise JhubNginxError("Can't request SSL without an E-mail address")

        if standalone:
            return run_certbot()

        debug(' writing temp vhost config')
        gen_config(nossl=True)
        try:
            nginx_reload()
            run_certbot()
        except JhubNginxError as e:
            attempt_cleanup()
            raise e

    def add_ssl_vhost():
        updated = gen_config()
        if updated:
            debug('Updated vhost config {}'.format(vhost_cfg_file))

            if standalone:
                return

            try:
                nginx_reload()
            except JhubNginxError as e:
                attempt_cleanup()
                raise e
        else:
            debug('No changes were required {}'.format(vhost_cfg_file))

    if vhost_cfg_file.exists():

        if not skip_dns_check:
            try:
                check_dns(domain, public_ip, opts, message=debug)
            except JhubNginxError as e:
                warn('Virtual host config already exists but DNS check/update failed:\n {}'.format(str(e)))

        add_ssl_vhost()  # Make sure content is up to date
    else:
        if not skip_dns_check:
            check_dns(domain, public_ip, opts, message=debug)

        if have_ssl_files():
            debug('Found SSL files, no need to run certbot')
        else:
            debug('Obtaining SSL for {}'.format(domain))
            obtain_ssl()

        add_ssl_vhost()

    return True
