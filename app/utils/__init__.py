import subprocess
import shlex
import random
import string
import re
import hashlib
from celery.utils.log import get_task_logger
import colorlog
import logging
import dns.resolver
from tld import get_tld
from .conn import http_req, conn_db
from .http import get_title, get_headers
from .domain import check_domain_black, is_valid_domain
from .ip import is_vaild_ip_target, not_in_black_ips, get_ip_asn, get_ip_city, get_ip_type
from .arl import arl_domain
from .time import curr_date
from .url import rm_similar_url, get_hostname, normal_url, same_netloc, verify_cert
from .cert import get_cert

def load_file(path):
    with open(path, "r+", encoding="utf-8") as f:
        return f.readlines()

def exec_system(cmd, **kwargs):
    cmd = " ".join(cmd)
    timeout = 4 * 60 * 60

    if kwargs.get('timeout'):
        timeout = kwargs['timeout']

    completed = subprocess.run(shlex.split(cmd), timeout=timeout, check=False, close_fds=True, **kwargs)

    return completed


def check_output(cmd, **kwargs):
    cmd = " ".join(cmd)
    timeout = 4 * 60 * 60

    if kwargs.get('timeout'):
        timeout = kwargs.pop('timeout')

    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')


    output = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, timeout=timeout, check=False,
               **kwargs).stdout
    return output

def random_choices(k = 6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=k))


def gen_md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def init_logger():
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        fmt = '%(log_color)s[%(asctime)s] [%(levelname)s] '
              '[%(threadName)s] [%(filename)s:%(lineno)d] %(message)s', datefmt = "%Y-%m-%d %H:%M:%S"))

    logger = colorlog.getLogger('arlv2')

    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False


import sys

def get_logger():
    if 'celery' in sys.argv[0]:
        task_logger = get_task_logger(__name__)
        return task_logger

    logger = logging.getLogger('arlv2')
    if not logger.handlers:
        init_logger()

    return  logging.getLogger('arlv2')




def get_ip(domain, log_flag = True):
    domain = domain.strip()
    logger = get_logger()
    ips = []
    try:
        answers = dns.resolver.query(domain, 'A')
        for rdata in answers:
            ips.append(rdata.address)
    except dns.resolver.NXDOMAIN as e:
        if log_flag:
            logger.info("{} {}".format(domain, e))

    except Exception as e:
        if log_flag:
            logger.warning("{} {}".format(domain, e))

    return ips

def get_cname(domain, log_flag = True):
    logger = get_logger()
    cnames = []
    try:
        answers = dns.resolver.query(domain, 'CNAME')
        for rdata in answers:
            cnames.append(str(rdata.target).strip(".").lower())
    except dns.resolver.NoAnswer as e:
        if log_flag:
            logger.debug(e)
    except Exception as e:
        if log_flag:
            logger.warning("{} {}".format(domain, e))
    return cnames



def domain_parsed(domain, fail_silently = True):
    domain = domain.strip()
    logger = get_logger()
    try:
        res = get_tld(domain, fix_protocol=True,  as_object=True)
        item = {
            "subdomain": res.subdomain,
            "domain":res.domain,
            "fld": res.fld
        }
        return item
    except Exception as e:
        if not fail_silently:
            raise e



def get_fld(domain):
    res = domain_parsed(domain)
    if res:
        return  res["fld"]



def gen_filename(site):
    filename = site.replace('://', '_')

    return re.sub('[^\w\-_\. ]', '_', filename)



from .user import user_login, user_login_header, auth, user_logout



