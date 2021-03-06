import click
import sys

from .utils import JhubNginxError
from . import utils
from ._impl import add_or_check_vhost, remove_vhost


def message(msg):
    click.echo(msg)


def parse_config(ctx, param, value):
    if ctx.obj is None:
        ctx.obj = {}

    if value is None:
        opts = utils.default_opts()
    else:
        opts = utils.opts_from_file(value)
        if opts is None:
            ctx.abort()

    ctx.obj['opts'] = utils.opts_update_from_env(opts)


@click.group()
@click.option('--config', '-c', help='Supply config file', callback=parse_config)
def cli(config):
    pass


@cli.command('add')
@click.argument('domain', type=str)
@click.option('--hub-ip', type=str, default='127.0.0.1', help="IP JupyterHub is running on")
@click.option('--hub-port', type=int, default=8000, help="Port JupyterHub is running on")
@click.option('--skip-dns-check', default=False, is_flag=True, help="Don't check DNS record")
@click.option('--email', type=str, help="Supply E-mail address for Let's Encrypt")
@click.option('--token', type=str, help="Supply `duckdns.org` token for updating DNS entry")
@click.option('--route53', default=False, is_flag=True,
              help="Use route53 DNS provider with credentials queried with boto3")
@click.option('--standalone', default=False, is_flag=True,
              help="Obtain SSL certs using standalone mode of certbot (no nginx running)")
@click.pass_obj
def add(ctx, domain, hub_ip, hub_port, skip_dns_check, email, token, route53, standalone):
    """ Create new or update existing proxy config
    """
    opts = ctx['opts']

    if email is not None:
        opts['letsencrypt']['email'] = email

    if token is not None:
        opts['dns']['token'] = token
    elif route53:
        opts['dns']['type'] = 'route53'

    try:
        add_or_check_vhost(domain,
                           hub_ip=hub_ip,
                           hub_port=hub_port,
                           skip_dns_check=skip_dns_check,
                           standalone=standalone,
                           opts=opts)
    except JhubNginxError as e:
        print(e)
        sys.exit(1)

    sys.exit(0)


@cli.command('remove')
@click.option('--keep-certificates', default=False, is_flag=True,
              help="Don't revoke certificates")
@click.argument('domain', type=str)
@click.pass_obj
def remove(ctx, domain, keep_certificates):
    """ Revoke SSL certificates and remove vhost entry from nginx.

    """
    opts = ctx['opts']

    try:
        remove_vhost(domain, opts, keep_certificates=keep_certificates)
    except JhubNginxError as e:
        print(e)
        sys.exit(1)

    sys.exit(0)


@cli.command('dns')
@click.option('--update/--no-update', default=True, help="Whether to attempt DNS update")
@click.option('--route53', default=False, is_flag=True,
              help="Use route53 DNS provider with credentials queried with boto3")
@click.option('--token', type=str, help="Supply `duckdns.org` token for updating DNS entry")
@click.argument('domain', type=str)
@click.pass_obj
def dns(ctx, domain, update, route53=None, token=None):
    """ Check if DNS record is up to date
    """
    from . import dns

    opts = ctx['opts']
    if token is not None:
        opts['dns']['token'] = token
    elif route53:
        opts['dns']['type'] = 'route53'

    try:
        result = dns.check_dns(domain,
                               opts=opts,
                               message=message,
                               no_update=not update)

        if not result:
            message("DNS record doesn't match public ip")

        sys.exit(0 if result else 1)
    except JhubNginxError as e:
        message(str(e))
        sys.exit(1)

    sys.exit(0)
