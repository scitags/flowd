# Network flow and packet marking service

**flowd** is a network flow and packet marking service developed in Python (based on the [technical specification](https://docs.google.com/document/d/1x9JsZ7iTj44Ta06IHdkwpv5Q2u4U2QGLWnUeN2Zf5ts/edit) of the [Scitags](https://www.scitags.org/) project).
It provides a pluggable system for testing different flow and packet marking strategies, using *plugins* to retrieve flow identifiers and a set of *backends* to implement the actual marking. In the base case, **flowd** is used to tag packets or network flows for a third party system/process (storage or transfer service). It uses *plugins* to identify the network flows and determine which science domain and activity to use, and *backends* to determine how exactly these flows should be tagged.

The framework is extensible and can be used to implement other use cases. Plugins and backends can be combined to create complex functionality. There is also an initial support for systemd/journal integration (Linux daemon), Docker image and development environment, STUN/TURN IP detection and configuration.  

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

> This project is in beta stage. It has been tested on RHEL8 and 9 compatible systems and Ubuntu 22.04. It requires kernel 4.4+ to run packet marking (ebpf backends). 

## Installation
Containerised version of the flowd is currently provided as the only official distribution (work is in progress to support package distribution for RHEL8/9 compatible systems). Please checkout the repo to start.

**flowd** image can be build with the following command:
```shell
# docker build -t <image>:<tag> .
```

and can be started with:
```shell
# docker run --privileged --network=host -d [-v /<local_fork_path>/flowd:/usr/src/app] 
            [-v <config_path>:/etc/flowd] <image>:<tag>  
```

Before staring the service an initial configuration needs to be mounted under /etc/flowd/flowd.cfg 
(please check an example etc/flowd.cfg) or alternatively as part of the local_fork_path. 
To start the service run:
```shell
# sbin/flowd --debug [-c <config_path>]
```

To run **flowd** as a systemd service, you can install it as any other python package and integrate it via systemd as follows:
```shell
# python setup.py install
# cp etc/flowd.cfg /etc/flowd/flowd-tags.cfg (edit the config)
# cp etc/flowd@.service /etc/systemd/system/ (systemd directory can be os specific)
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
- PLUGIN - plugin that should be enabled (only one plugin can be specified)
- BACKEND - comma separated list of backends to enable 
- FLOW_MAP_API - URL with a list of science domains and activities (see technical spec for json schema and examples)

### Plugins Reference

#### NP_API
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

#### FIREFLY
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

#### NETSTAT
##### Function
This plugin scans existing network connections on the host using netstat, creates event for each and assigns it the configured science domain and activity.

##### Parameters

```shell
NETSTAT_EXPERIMENT - science domain id to use (for all events) 
NETSTAT_ACTIVITY - activity id (for all events)
NETSTAT_INTERNAL_NETWORKS - list of destination networks to ignore
NETSTAT_TIMEOUT - time to wait between scans (poll time) - only via settings
```

##### Defaults
```shell
NETSTAT_TIMEOUT=2
```

##### Example
```shell
NETSTAT_EXPERIMENT=1
NETSTAT_ACTIVITY=1
NETSTAT_INTERNAL_NETWORKS=('192.168.0.0/16')
```

#### NETLINK
##### Function
This plugin scans existing network connections on the host using netlink, creates event for each and assigns it the configured science domain and activity.

##### Parameters

```shell
NETLINK_EXPERIMENT - science domain id to use (for all events) 
NETLINK_ACTIVITY - activity id (for all events)
NETLINK_INTERNAL_NETWORKS - list of destination networks to ignore (see netstat)
NETLINK_TIMEOUT - time to wait between scans (poll time) - only via settings
```

##### Defaults
```shell
NETLINK_TIMEOUT=2
```

#### IPERF
##### Function
This plugin scans existing network connections on the host using netstat, filters iperf connections, creates event for each and assigns them science domain and activity from a pre-configured set at random (This plugin is experimental).

##### Parameters

```shell
IPERF_FLOW_ID - list of tuples with science domain and activity
IPERF_INTERNAL_NETWORKS - list of destination networks to ignore (see netstat)
```

##### Defaults
```shell
NETSTAT_TIMEOUT=2
```

### Backends Reference

#### UDP_FIREFLY
##### Function
This backend implements UDP firefly flow marking. For each event triggered by a plugin it sends a UDP packet with the information about the corresponding science domain and activity. 

##### Parameters

```shell
IP_DISCOVERY_ENABLED - attempts to detect source IP via STUN server (can be tuned via settings). 
                       IP discovered will be used as a source in the UDP firefly metadata
UDP_FIREFLY_IP4_SRC - IPv4 address to be used as a source in the UDP firefly metadata 
UDP_FIREFLY_IP6_SRC - IPv6 address to be used as a source in the UDP firefly metadata
UDP_FIREFLY_NETLINK - add netlink information (scan connections via netlink, retrieve  
                      information for particular connection and add it to the UDP packet).
```

#### EPBF_EL8/EBPF_EL9
##### Function
This backend implements packet marking, it uses eBPF-TC to encode science domain and activity in the IPv6 packet flow label field. Note that this backend requires kernel headers, bcc (ebpf libs) and a working compiler as it will compile and load eBPF-TC program in the kernel.
ebpf_el8 backend should work on RHEL8 compatible systems; ebpf_el9 backend should work on RHEL9 compatible systems. Both backends require at least kernel 4.4+ to work.

##### Parameters

```shell
NETWORK_INTERFACE - network interface on which eBPF-TC program should be loaded (required)
```

##### Example
```shell
NETWORK_INTERFACE='eth0'
```

#### PROMETHEUS
##### Function
This backend exposes network flows visible to flowd to Prometheus.
It will attempt to fetch all related netlink data for each network flow via ss command line tool and will show them
alongside science domain and activity. 

##### Parameters

```shell
PROMETHEUS_SS_PATH - path to ss command
PROMETHEUS_SRV_PORT - port where Prometheus client should listen 
```

##### Example
```shell
PROMETHEUS_SS_PATH='/usr/sbin/ss'
PROMETHEUS_SRV_PORT=9000
```
##### Example

The following is a sample output from Prometheus client: 
```shell
# All metrics start with flow_tcp followed by corresponding netlink metric
# (metrics depend on the kernel version, ss tool version and TCP options enabled)
#
# The following labels are populated:
# exp - science domain
# act - activity
# src/dst - source/destination IPs
# flow - flow src/dst ports
# opts - TCP/IP options used 
#

flow_tcp_skmem_rmem_alloc{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.0
flow_tcp_skmem_rcv_buf{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 131072.0
flow_tcp_skmem_wmem_allow{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.0
flow_tcp_skmem_snd_buf{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 5.778432e+06
flow_tcp_skmem_fwd_alloc{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.0
flow_tcp_skmem_wmem_queued{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.0
flow_tcp_skmem_opt_mem{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.0
flow_tcp_skmem_back_log{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.0
flow_tcp_skmem_sock_drop{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.0
flow_tcp_rto{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 201.0
flow_tcp_rtt{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.361
flow_tcp_rtt_var{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.091
flow_tcp_ato{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 40.0
flow_tcp_mss{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 65464.0
flow_tcp_pmtu{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 65536.0
flow_tcp_rcvmss{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 536.0
flow_tcp_advmss{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 65464.0
flow_tcp_cwnd{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 47.0
flow_tcp_ssthresh{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 21.0
flow_tcp_bytes_sent_total{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 1.61221034e+09
flow_tcp_bytes_acked_total{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 1.61221034e+09
flow_tcp_bytes_received_total{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 5212.0
flow_tcp_segs_out_total{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 26162.0
flow_tcp_segs_in_total{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 4946.0
flow_tcp_data_segs_out_total{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 26153.0
flow_tcp_data_segs_in_total{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 195.0
flow_tcp_send{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 6.8184110803e+010
flow_tcp_lastsnd{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 38.0
flow_tcp_lastrcv{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 43.0
flow_tcp_lastack{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 38.0
flow_tcp_pacing_rate{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 8.1792611416e+010
flow_tcp_delivery_rate{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 2.8156559136e+010
flow_tcp_delivered{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 26154.0
flow_tcp_busy{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 645.0
flow_tcp_rwnd_limited{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 1.0
flow_tcp_rcv_space{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 65464.0
flow_tcp_rcv_ssthresh{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 65464.0
flow_tcp_minrtt{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 0.007
flow_tcp_snd_wnd{act="cache",dst="<ip>",exp="cms",flow="<int:int>",src="<ip>"} 2.0119552e+07
flow_tcp_ca_info{act="cache",dst="<ip>",exp="cms",flow="<int:int>",opts="ts sack cubic wscale:14,14",src="<ip>"} 1.0
```


## Contribution Guide
Extending **flowd** can be done either by implementing a new plugin or a new backend. The core *plugin* interface requires two methods:
```python
def init():
  # used to run any initialisation required (check config sanity, etc.)
  
def run(flow_queue, term_event, ip_config):
  # Implements a particular way to identify network flow and assigns it a  
  # science domain and ctivity.
  # Sends scitags.FlowID object via flow_queue to the backend(s)
  #
  # Parameters:
  # flow_queue - pub/sub queue used to transmit scitags.FlowID to the backends
  # term_event - termination event object
  # ip_config - host IP configuration (ip4 and ip6 addresses)
  #
  while not term_event.is_set():
      # implementation to determine flow_id (see scitags.FlowID for details)
      flow_id = scitags.FlowID(flow_state, proto, src, src_port, dst, dst_port, 
                               exp_id, activity_id, start_time, end_time, netlink)
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




