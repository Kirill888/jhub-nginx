import requests
import socket
import yaml
import os
from pydash import map_values_deep, defaults_deep
from ._templates import DEFAULT_CFG


class JhubNginxError(Exception):
    def __init___(self, opts=None, *args):
        Exception.__init__(self, *args)


def resolve_hostname(domain):
    try:
        return socket.gethostbyname(domain)
    except IOError:
        return None


def public_ip():
    endpoints = [
        ('http://instance-data/latest/meta-data/public-ipv4', None),  # AWS
        ('http://metadata/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip',
         {"Metadata-Flavor": "Google"}),  # GCE
        ('https://api.ipify.org', None),  # all other
    ]

    for (url, hdrs) in endpoints:
        try:
            with requests.get(url, headers=hdrs, timeout=1) as req:
                if req:
                    return req.text
        except IOError:
            pass

    return None


def slurp(filename):
    try:
        with open(filename, 'r') as f:
            return f.read()
    except IOError:
        return None


def file_needs_update(filename, content):
    return slurp(filename) != content


def write_if_different(filename, content):
    if not file_needs_update(filename, content):
        return False

    with open(filename, 'w') as f:
        f.write(content)

    return True


def default_opts(opts=None):
    default_opts = yaml.load(DEFAULT_CFG)
    if opts is None:
        return default_opts

    return defaults_deep({}, opts, default_opts)


def opts_from_file(filename, ignore_missing=False):
    txt = slurp(filename)

    if txt is None:
        if ignore_missing:
            return default_opts()
        else:
            return None

    try:
        return default_opts(yaml.load(txt))
    except yaml.YAMLError as e:
        print(e)
        return None


def resolve_env(v, prefix='env/'):
    if isinstance(v, str) and v.startswith(prefix):
        env_name = v[len(prefix):]
        return os.environ.get(env_name)

    return v


def opts_update_from_env(opts):
    return map_values_deep(opts, lambda x: resolve_env(x, prefix='env/'))
