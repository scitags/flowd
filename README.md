# Network flow and packet marking service

**flowd** is a network flow and packet marking service developed in Python (based on the [technical specification](https://docs.google.com/document/d/1x9JsZ7iTj44Ta06IHdkwpv5Q2u4U2QGLWnUeN2Zf5ts/edit)).
It provides a pluggable system to test different flow and packet marking strategies using  *plugins* to get the flow 
identifiers and a set of *backends* that implement the actual marking. In the base case **flowd** is used to mark packets or network flows for a third party system/process (storage or transfer service). It uses *plugins* to identify the network flows to mark and determine what science domain and activity to use and *backends* to determine how exaclty these flows should be marked. 

The framework is extensible and can be used to implement other use cases. Plugins and backends can be combined to create complex functionality, they run in parallel and are synchronised using a pub/sub queue. There is an initial support for systemd/journal integration (Linux daemon), docker image and development environment, STUN/TURN IP detection and configuration.  

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

## Installation
Containerised version of the flowd is currently provided as the only official distribution (work is in progress to support package distribution for RHEL8/9 compatible systems). Please checkout the repo to start.

**flowd** image can be build with the following command:
```shell
# docker build -t <image>:<tag> .
```

and can be started with:
```shell
# docker run --privileged --network=host -d [-v /<local_fork_path>/flowd:/usr/src/app] [-v <config_path>:/etc/flowd] \
           <image>:<tag>  
```

Before staring the service an initial configuration needs to be mounted under /etc/flowd/flowd.cfg 
(please check an example etc/flowd.cfg) or alternatively as part of the local_fork_path. 
To start the service run:
```shell
# sbin/flowd --debug [-c <config_path>]
```

To run **flowd** as a system service, you can install it as any other python package and integrate it via systemd as follows:
```shell
# python setup.py install
# cp etc/flowd.cfg /etc/flowd/flowd-tags.cfg (edit the config)
# cp etc/flowd@.service /etc/systemd/system/ (note that this directory is os specific)
# systemctl daemon-reload
# systemctl enable flowd@tags
# systemctl start flowd@tags
```

## Documentation
**flowd** command synopsis:
```shell
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
```python
PLUGIN='netstat'
BACKEND='udp_firefly,prometheus'
FLOW_MAP_API='<url>'
```
- PLUGIN - refers to the name of the plugin that should be enabled (only plugin can be enabled)
- BACKEND - comma separated list of backends to enable 
- FLOW_MAP_API - URL with a list of science domains and activities (see technical spec for json schema and examples)

### Plugins Reference

#### np_api
##### Function
This plugin creates a named pipe which can be used to submit information about a network flow from another process. It expects a space separated entry followed by a new line (one line per flow) with the following syntax:
```shell
state prot src_ip src_port dst_ip dst_port exp act
```
Notes: The named pipe is opened as non-blocking, so it should be safe to write from multiple processes. It is expected that third party process will check existance of the file (named pipe), checks if it's a pipe and tries to write a sample message before sending any production markings. Sending sample message to a non-connected pipe should end up with an exception, which can be used to determine if flowd is running/listening or not.

##### Parameters

```shell
NP_API_FILE - controlled via settings only
```

##### Defaults
```shell
NP_API_FILE=/var/run/flowd
```

##### Example

```shell
A sample interaction would like this:
# echo "start tcp 192.168.0.1 2345 192.168.0.2 5777 1 2" > /var/run/flowd
# echo "end tcp 192.168.0.1 2345 192.168.0.2 5777 1 2" > /var/run/flowd
```

#### firefly
##### Function
This plugin listens for incoming UDP fireflies, parses the information it contains and creates a new event which is sent to the backend(s). 

##### Parameters

```shell
FIREFLY_LISTENER_HOST - host to be used to open listen socket 
FIREFLY_LISTENER_PORT - port 
```

##### Defaults
```shell
FIREFLY_LISTENER_HOST="0.0.0.0"
FIREFLY_LISTENER_PORT=10514
```

#### netstat
##### Function
This plugin scans existing network connections on the host, creates event for each and assigns it the configured science domain and activity. 

##### Parameters

```shell
NETSTAT_EXPERIMENT - science domain id to use (for all events)
NETSTAT_ACTIVITY - activity id (for all events)
NETSTAT_INTERNAL_NETWORKS - 
NETSTAT_TIMEOUT - time to wait between scans (poll time) - only via settings

```

##### Defaults
```shell
FIREFLY_LISTENER_HOST="0.0.0.0"
FIREFLY_LISTENER_PORT=10514
```

### Backends Reference

## Contribution Guide
Extending **flowd** can be done either by implementing a new plugin or a new backend. The core *plugin* interface requires two methods:
```python
def init():
  # used to run any initialisation required (check config sanity, etc.)
  
def run(flow_queue, term_event, ip_config):
  # Implements a particular way to identify network flow and assigns it a science domain and activity.
  # Sends scitags.FlowID object via flow_queue to the backend(s)
  #
  # Parameters:
  # flow_queue - pub/sub queue used to transmit scitags.FlowID to the backends
  # term_event - termination event object
  # ip_config - host IP configuration (ip4 and ip6 addresses)
  #
  while not term_event.is_set():
      # implementation to determine flow_id (see scitags.FlowID for details)
      flow_id = scitags.FlowID(flow_state, proto, src, src_port, dst, dst_port, exp_id, activity_id,
                                     start_time, end_time, netlink)
      flow_queue.put(flow_id)

```

Backend is expected to parse the information contained in the FlowID object and implement a mechanism how to pass it to the network layer.
```python
def run(flow_queue, term_event, flow_map, ip_config):
  # Implements a particular network flow or packet tagging mechanism 
  # Uses scitags.FlowID object to identify the flow, its science domain and activity 
  #
  while not term_event.is_set():
    try:
        flow_id = flow_queue.get(block=True, timeout=0.5)
    except queue.Empty:
        continue
    # implementation
```




