import socket
import requests
import ipaddress
import logging

import scitags.settings
import scitags.stun

log = logging.getLogger('scitags')


def get_ip4():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(scitags.settings.IP4_DISCOVERY)
        log.debug('    IPv4:{}'.format(s.getsockname()[0]))
        return s.getsockname()[0]
    except Exception as e:
        log.debug('Failed to detect internal IPv4 with {}'.format(e))
        return None


def get_ip6():
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        s.connect(scitags.settings.IP6_DISCOVERY)
        return s.getsockname()[0]
    except Exception as e:
        log.debug('Failed to detect internal IPv6 with {}'.format(e))
        return None


def get_stun_ip():
    for stun_s in scitags.settings.STUN_SERVERS:
        nat_type, external_ip, external_port = scitags.stun.get_ip_info(stun_host=stun_s[0], stun_port=stun_s[1])
        log.debug('    STUN {}/{}: {} {} {}'.format(stun_s[0], stun_s[1], nat_type, external_ip, external_port))
        if external_ip:
            return external_ip
    return None


def get_my_ip(ip_ver=4):
    ip = requests.get('https://api{}.my-ip.io/ip'.format(ip_ver))
    if ip.status_code == 200 and ip.text:
        log.debug('    MY-IP: {}'.format(ip.text))
        return ip.text
    else:
        return None


def get_ext_ip():
    # p_ - public/i_ - internal (on device)
    # note: this algorithm will not work if there are multiple public IPs and/or source routing
    #
    p_ip4, i_ip4, p_ip6, i_ip6 = (None, None, None, None)
    i_ip4 = get_ip4()
    i_ip6 = get_ip6()
    if i_ip4 and ipaddress.ip_address(u'{}'.format(i_ip4)).is_private:
        ip_ext = get_stun_ip()
        if not ip_ext:
            ip_ext = get_my_ip()
        if ip_ext:
            p_ip4 = ip_ext
            i_ip4 = i_ip4
    if i_ip6 and ipaddress.ip_address(u'{}'.format(i_ip6)).is_private:
        # todo: ip6 stun (p_ip6)
        ip_ext = get_my_ip(ip_ver=6)
        if ip_ext:
            p_ip6 = ip_ext
    return p_ip4, i_ip4, p_ip6, i_ip6


