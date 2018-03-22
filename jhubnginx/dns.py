import requests
from . import utils
from .utils import JhubNginxError
from pydash import get as _get

try:
    import boto3
except ImportError:
    boto3 = None

try:
    import libcloud
except ImportError:
    libcloud = None

DEFAULT_TTL = 300


def credentials_from_boto3():
    if boto3 is None:
        raise JhubNginxError("Need boto3 library to query AWS credentials")

    creds = boto3.Session().get_credentials().get_frozen_credentials()
    out = dict(key=creds.access_key,
               secret=creds.secret_key)
    if hasattr(creds, 'token'):
        out['token'] = creds.token
    return out


def update_dns_libcloud(domain, public_ip, opts):
    domain = domain.rstrip('.')

    cfg = opts.get('dns')
    driver_type = cfg.get('type')

    if driver_type == 'route53' and cfg.get('key') is None:
        creds = credentials_from_boto3()
    else:
        creds = {k: cfg[k] for k in ['key', 'secret', 'token']
                 if k in cfg}

    driver = libcloud.dns.providers.get_driver(driver_type)(**creds)

    zones = [z for z in driver.list_zones()
             if domain.endswith(z.domain.rstrip('.'))]

    if len(zones) < 1:
        raise JhubNginxError("No zone for domain: %s" % domain)
    if len(zones) > 1:
        raise JhubNginxError("More than one zone for domain: %s" % domain)

    zone = zones[0]
    name = domain[:-len(zone.domain.rstrip('.'))-1]

    recs = [rec for rec in zone.list_records() if rec.name == name]
    if len(recs) == 0:
        rec = zone.create_record(name,
                                 type='A',
                                 data=public_ip,
                                 extra={'ttl': DEFAULT_TTL})
    else:
        rec = recs[0]
        rec.update(data=public_ip)

    return True


def update_duck_dns(domain, public_ip, opts):

    token = _get(opts, 'dns.token',
                 _get(opts, 'dns.key',
                      _get(opts, 'duckdns.token', None)))

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


def update_dns(domain, public_ip, opts):
    if domain.endswith('.duckdns.org'):
        return update_duck_dns(domain, public_ip, opts)

    if libcloud is not None and _get(opts, 'dns.type') is not None:
        return update_dns_libcloud(domain, public_ip, opts)

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

    DNS providers supported by apache-libcloud:
       opts['dns']['type'] -- e.g. 'route53'|'cloudflare'| ... etc
       opts['dns']['key'] -- e.g. AWS_ACCESS_KEY for route53, email for cloudflare
       opts['dns']['secret'] -- (optional), AWS_SECRET_KEY for route53
       opts['dns']['token'] -- (optional), AWS_SESSION_TOKEN route53 IAM roles need that

    For EC2+route53 users it's best to leave key|secret|token un-configured,
    they will be queried using boto3 library.

    DuckDNS:
       opts['dns']['token'] <-- Put your duckdns token here

    '''
    opts = opts if opts else utils.default_opts()

    if public_ip is None:
        public_ip = utils.public_ip()
        if public_ip is None:
            raise JhubNginxError("Can't find public IP of this host")

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
