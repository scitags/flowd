# Copyright and licence statements come from simple_tc.py from bcc repo
# Copyright (c) PLUMgrid, Inc.
# Licensed under the Apache License, Version 2.0 (the "License")


import logging

try:
    import queue
except ImportError:
    import Queue as queue

from scitags.config import config
import scitags.settings

# Needed for eBPF backend

from pyroute2 import IPRoute
import ctypes
import ipaddress
import random
import sys

log = logging.getLogger('scitags')

try:
    from bcc import BPF
except ImportError as e:
    log.error("Unable to import ebpf/bcc library, please install via python3-bcc package or pip install flowd[bcc]")
    sys.exit(-1)

ipr = IPRoute()

text = """
#include <uapi/linux/ptrace.h>
#include <net/sock.h>
#include <bcc/proto.h>
#include <linux/bpf.h>

struct fourtuple
{
    u64 ip6_hi;
    u64 ip6_lo;
    u16 dport;
    u16 sport;
};


BPF_HASH(flowlabel_table, struct fourtuple, u64, 100000);
BPF_HASH(tobedeleted, struct fourtuple, u64, 100000);

int set_flow_label(struct __sk_buff *skb)
{
    u8 *cursor = 0;
    struct ethernet_t *ethernet = cursor_advance(cursor, sizeof(*ethernet));

    // IPv6
    if (ethernet->type == 0x86DD)
    {
        struct ip6_t *ip6 = cursor_advance(cursor, sizeof(*ip6));

        struct fourtuple addrport;

        // This is necessary for some reason to do with compiler padding
        __builtin_memset(&addrport, 0, sizeof(addrport));

        addrport.ip6_hi = ip6->dst_hi;
        addrport.ip6_lo = ip6->dst_lo;

        // TCP
        if (ip6->next_header == 6)
        {
            struct tcp_t *tcp = cursor_advance(cursor, sizeof(*tcp));

            addrport.dport = tcp->dst_port;
            addrport.sport = tcp->src_port;

            u64 *delete = tobedeleted.lookup(&addrport);

            u64 *flowlabel = flowlabel_table.lookup(&addrport);

            if (delete)
            {
                flowlabel_table.delete(&addrport);
                tobedeleted.delete(&addrport);
            }
            else if (flowlabel)
            {
                ip6->flow_label = *flowlabel;
            }
        }

        return -1;
    }
    else
    {
        return -1;
    }
}

"""


class NetFlowId(ctypes.Structure):
    _fields_ = [("ip6_hi", ctypes.c_ulong), ("ip6_lo", ctypes.c_ulong), ("dport", ctypes.c_ushort), ("sport", ctypes.c_ushort)]


def ebpf_init():
    global flowlabel_table, tobedeleted, idx
    # Load eBPF program
    log.debug('Loading eBPF')
    b = BPF(text=text, debug=0)
    flowlabel_table = b.get_table('flowlabel_table')
    tobedeleted = b.get_table('tobedeleted')
    fn = b.load_func("set_flow_label", BPF.SCHED_CLS)
    log.debug('eBPF load completed')
    # Attach to network interface (get from config)
    log.debug('Attaching to network interface {}'.format(config['NETWORK_INTERFACE']))
    if 'NETWORK_INTERFACE' in config.keys():
        interface = config['NETWORK_INTERFACE']
        idx = ipr.link_lookup(ifname=interface)[0]
    else:
        err = 'eBPF backend requires network interface to be specified'
        log.error(err)
        raise scitags.FlowIdException(err)
    log.debug('eBPF attached')
    # Clean up, in case backend crashed last time
    try:
        ipr.tc("del", "sfq", idx, "1:")
    except:
        pass
    ipr.tc("add", "sfq", idx, "1:")
    ipr.tc("add-filter", "bpf", idx, ":1", fd=fn.fd,
           name=fn.name, parent="1:", action="ok", classid=1)
    log.debug('ipr.tc add-filter success')


# Function to put together flow label including entropy bits
def bitpattern(exp_id, act_id):
    # Force exp_id to have 9 binary digits
    exp_id = format(exp_id, '#011b')
    # Force act_id to have 6 binary digits
    act_id = format(act_id, '#08b')

    # exp_id is supposed to be little-endian
    exp_id_swapped = "0b"
    for i in range(-1, -10, -1):
        exp_id_swapped = exp_id_swapped + exp_id[i]

    exp_id = exp_id_swapped

    # Packet marking specification wants 3 random numbers
    # First is two bits, second is one bit, third is two bits
    random1 = random.randrange(4)
    random2 = random.randrange(2)
    random3 = random.randrange(4)
    random1 = format(random1, '#04b')
    random2 = format(random2, '#03b')
    random3 = format(random3, '#04b')

    # Stitch the 20-digit binary number together, Frankenstyle
    log.debug('flow binary: 00'+exp_id[2:]+'0'+act_id[2:]+'00')
    log.debug('flow decimal: {}'.format(int('00'+exp_id[2:]+'0'+act_id[2:]+'00', 2)))
    flowlabel = random1 + exp_id[2:] + random2[2:] + act_id[2:] + random3[2:]
    log.debug(hex(int(flowlabel, 2)))

    # Return as integer
    return int(flowlabel, 2)


def run(flow_queue, term_event, flow_map, ip_config):
    ebpf_init()
    while not term_event.is_set():
        try:
            flow_id = flow_queue.get(block=True, timeout=0.5)
        except queue.Empty:
            continue

        if flow_id.state == "start":
            exp_id = flow_id.exp

            if not flow_id.act:
                act_id = 0
            else:
                act_id = flow_id.act

            # New stuff starts here
            try:
                # Need to break up the IPv6 address into halves
                log.debug(flow_id)
                ip6 = ipaddress.IPv6Address(flow_id.dst).exploded
                ip6_hi = int(ip6[0:4] + ip6[5:9] + ip6[10:14] + ip6[15:19], 16)
                ip6_lo = int(ip6[20:24] + ip6[25:29] + ip6[30:34] + ip6[35:39], 16)
                dport = flow_id.dst_port
                sport = flow_id.src_port

                key = NetFlowId(ip6_hi, ip6_lo, dport, sport)

                # Get the bitpattern, including entropy bits
                flowlabel = bitpattern(exp_id, act_id)

                # Fill the BPF hash with each half of the IP pointing to the flow label
                flowlabel_table[key] = ctypes.c_ulong(flowlabel)
                log.info(ip6 + " added to flowlabel table")
                log.debug("Source port is " + str(sport))
                log.debug("Destination port is " + str(dport))
                log.debug("Flowlabel is " + str(flowlabel))

            except ipaddress.AddressValueError:
                err = 'Flow label marking only possible with IPv6'
                log.error(err)
                continue
                # I don't think we want the backend to crash here?
                #raise scitags.FlowIdException(err)

        elif flow_id.state == "end":
            try:
                ip6 = ipaddress.IPv6Address(flow_id.dst).exploded
                ip6_hi = int(ip6[0:4] + ip6[5:9] + ip6[10:14] + ip6[15:19], 16)
                ip6_lo = int(ip6[20:24] + ip6[25:29] + ip6[30:34] + ip6[35:39], 16)
                dport = flow_id.dst_port
                sport = flow_id.src_port

                key = NetFlowId(ip6_hi, ip6_lo, dport, sport)

                # Remove IP from BPF hash
                # This needs kernel 5.6 at least; have to do it differently for RHEL 8
                #flowlabel_table.items_delete_batch(ip6_hi, ip6_lo)

                # Remove IP from hash on C side instead of python side
                tobedeleted[key] = ctypes.c_ulong(flowlabel)
                log.info(ip6 + " removed from flowlabel table")
                log.debug("Source port is " + str(sport))
                log.debug("Destination port is " + str(dport))

            except ipaddress.AddressValueError:
                err = 'Flow label marking only possible with IPv6'
                log.error(err)
                continue
                # I don't think we want the backend to crash here?
                #raise scitags.FlowIdException(err)

    # Clean up
    ipr.tc("del", "sfq", idx, "1:")