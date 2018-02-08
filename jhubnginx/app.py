import click
import sys

from .utils import JhubNginxError
from . import utils
from ._impl import add_or_check_vhost


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

    ctx.obj['opts'] = opts


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
@click.pass_obj
def add(ctx, domain, hub_ip, hub_port, skip_dns_check, email, token):
    opts = ctx['opts']

    if email is not None:
        opts['letsencrypt']['email'] = email

    if token is not None:
        opts['duckdns']['token'] = token

    try:
        add_or_check_vhost(domain,
                           hub_ip=hub_ip,
                           hub_port=hub_port,
                           skip_dns_check=skip_dns_check,
                           opts=opts)
    except JhubNginxError as e:
        print(e)
        sys.exit(1)

    sys.exit(0)


@cli.command('dns')
@click.option('--update/--no-update', default=True, help="Whether to attempt DNS update")
@click.option('--token', type=str, help="Supply `duckdns.org` token for updating DNS entry")
@click.argument('domain', type=str)
@click.pass_obj
def dns(ctx, domain, update, token=None):
    from . import dns

    opts = ctx['opts']
    if token is not None:
        opts['duckdns']['token'] = token

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
