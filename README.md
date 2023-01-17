# Network flow and packet marking service

**flowd** is a network flow and packet marking service developed in Python (based on the [technical specification](https://docs.google.com/document/d/1x9JsZ7iTj44Ta06IHdkwpv5Q2u4U2QGLWnUeN2Zf5ts/edit)).
It provides a pluggable system to test different flow and packet marking strategies using  *plugins* to get the flow 
identifiers and a set of *backends* that implement the actual packet and flow marking. Plugins and backends can be combined to create complex functionality, plugins/backeds  run in parallel and are synchronised using a pub/sub queue. There is an initial support for 
systemd/journal integration (Linux daemon), docker image and development environment, STUN/TURN IP detection and configuration.  

The following *plugins* are currently available:
- **np_api** - simple API which accepts flow identifiers via named pipe
- **firefly** - listens for incoming UDP firefly packets and uses information contained in the packet as flow identifier
- **netlink** - scans the network connections on a host (using netlink/ss) and generates a flow identifier with the science domain as provided in the configuration file (only fixed/partial tagging)
- **netstat** - scans the network connections on a host (using netstat) and generates a flow identifier 
  with the science domain provided in the configuration (only fixed/partial tagging).
- **iperf** - clone of the netstat plugin, which only scans for iperf3 connections 
  
The following *backends* are currently available:
- **udp-firefly** - implementation of the UDP firefly packets.
- **ebpf_el8 and epbf_el9** - implementation of the IPv6 packet marking (encodes science domain and activity in the IPv6 flow label, see technical spec for details)
- **prometheus** - exposes all network flows seen by flowd (including science domain and activity fields) via prometheus client API

> This project is in beta stage. It has been tested on RHEL8 and 9 compatible systems and Ubuntu 20. It requires kernel 4.4+ to run packet marking (ebpf backends). 

## Development environment
Containerised version of the flowd development environment is provided for a quick start. Please fork the flowd repository
and add the mainstream as an additional remote in order to be able to submit a merge request later. 

**flowd** can be build with the following command:
```buildoutcfg
docker build -t <image>:<tag> .
```

and can be started with:
```buildoutcfg
docker run --privileged --network=host -it [-v /<local_fork_path>/flowd:/usr/src/app] [-v <config_path>:/etc/flowd] \
           --entrypoint=/bin/bash <image>:<tag>  
```

Before staring the service an initial configuration needs to be added in /etc/flowd/flowd.cfg 
(please check an example etc/flowd.cfg). To start the service run:
```buildoutcfg
sbin/flowd --debug [-c <config_path>]
```

## Documentation
**flowd** command synopsis:
```
# sbin/flowd --help
usage: flowd [-h] [--version] [-c CONFIG] [-d] [-f]

flowd - flow and packet marking daemon

optional arguments:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -c CONFIG, --config CONFIG
                        Specify path of the configuration file (defaults to /etc/flowd/flowd.cfg)
  -d, --debug           Debug mode
```
**flowd** configuration file is a simple list of key-value pairs, the following parameters are mandatory:
```
PLUGIN='netstat'
BACKEND='udp_firefly,prometheus'
FLOW_MAP_API='<url>'
```

PLUGIN - refers to the name of the plugin that should be enabled (only plugin can be enabled)
BACKEND - comma separated list of backends to enable 
FLOW_MAP_API - URL with a list of science domains and activities (see technical spec for json schema and examples)

### Plugins Reference


### Backends Reference




