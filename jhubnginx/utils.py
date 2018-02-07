import requests
import subprocess
import socket


class JhubNginxError(Exception):
    def __init___(self, opts=None, *args):
        Exception.__init__(self, *args)


def resolve_hostname(domain):
    try:
        return socket.gethostbyname(domain)
    except IOError:
        return None


def public_ip():
    try:
        return subprocess.check_output(['ec2metadata',
                                        '--public-ipv4']).decode('ascii').rstrip()
    except IOError:
        pass

    try:
        with requests.get('https://api.ipify.org') as req:
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
    from ._templates import DEFAULT_CFG
    import yaml
    import pydash

    default_opts = yaml.load(DEFAULT_CFG)
    if opts is None:
        return default_opts

    return pydash.defaults_deep({}, opts, default_opts)
