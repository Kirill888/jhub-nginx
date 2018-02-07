import requests
from . import utils
from .utils import JhubNginxError
from pydash import get as _get


def update_dns(domain, public_ip, opts):

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


def check_dns(domain,
              public_ip=None,
              opts=None,
              message=lambda x: None,
              no_update=False):
    '''Check that domain resolves to public ip of this host.

       If it doesn't and it is a duckdns domain and duckdns token is configured then update DNS record.

       throws JhubNginxError if
       - DNS doesn't match public ip and can not be updated
       - Public ip can not be discovered

       opts['duckdns']['token'] <-- Put your duckdns token here
    '''
    opts = opts if opts else utils.default_opts()

    if public_ip is None:
        public_ip = utils.public_ip()
        if public_ip is None:
            raise JhubNginxError("Can't finds public IP of this host")

    domain_ip = utils.resolve_hostname(domain)

    if domain_ip == public_ip:
        message('DNS record is already up to date')
        return True

    if no_update:
        return False

    if update_dns(domain, public_ip, opts):
        message('Updated DNS record successfully')
        return True

    if domain_ip is None:
        raise JhubNginxError('No DNS record for {}, and no way to update'.format(domain))
    else:
        raise JhubNginxError("DNS record doesn't match public IP: {} is {} should be {}".format(
            domain, domain_ip, public_ip))
