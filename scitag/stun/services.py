import socket
import requests
import ipaddress
import logging

import scitag.settings
import scitag.stun

log = logging.getLogger('scitag')


def get_ip4():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(scitag.settings.IP4_DISCOVERY)
    log.debug('    IPv4:{}'.format(s.getsockname()[0]))
    return s.getsockname()[0]


def get_ip6():
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    s.connect(scitag.settings.IP6_DISCOVERY)
    return s.getsockname()[0]


def get_stun_ip():
    for stun_s in scitag.settings.STUN_SERVERS:
        nat_type, external_ip, external_port = scitag.stun.get_ip_info(stun_host=stun_s[0], stun_port=stun_s[1])
        log.debug('    STUN {}/{}: {} {} {}'.format(stun_s[0], stun_s[1], nat_type, external_ip, external_port))
        if external_ip:
            return external_ip
    return None


def get_my_ip():
    ip = requests.get('https://api.my-ip.io/ip')
    if ip.status_code == 200 and ip.text:
        log.debug('    MY-IP: {}'.format(ip.text))
        return ip.text
    else:
        return None


def get_ext_ip():
    # todo: ip6 + error handling
    ip4_local = get_ip4()
    if ipaddress.ip_address(ip4_local).is_private:
        ip_ext = get_stun_ip()
        if ip_ext:
            return ip4_local, ip_ext
        else:
            ip_ext = get_my_ip()
            if ip_ext:
                return ip4_local, ip_ext
            else:
                return None, None
