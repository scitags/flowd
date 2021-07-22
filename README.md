# Network flow and packet marking service

**flowd** is a network flow and packet marking service developed based on the [technical specification](https://docs.google.com/document/d/1x9JsZ7iTj44Ta06IHdkwpv5Q2u4U2QGLWnUeN2Zf5ts/edit).
It provides a pluggable system to test different flow/packet marking strategies using various plugins to generate flow 
identifiers and a set of backends that implement the actual packet and flow marking. Plugins and backends run in 
parallel and are synchronised using a multiprocessing queue (this can be extended to process pools in the future). 
There is also initial support for systemd/journal integration (Linux daemon), docker image and development
environment, STUN/TURN IP detection and configuration.  

The following plugins are provided:
- netstat - scans the network connections on a host, filters out private/local network and issues a partial flow tag with 
experiment provided in the configuration (flowd.cfg).
- np_api - API based on named pipe (/var/run/flowd) that can be used for testing purposes or by other systems to directly 
  pass the flow identifiers.
  
The following backends are provided:
- udp-firefly - initial implementation of the UDP firefly packets.

> This project is in alpha stage and does not have any official release yet. 

## Development environment
Containerised version of the flowd development environment is provided for a quick start. Please fork the flowd repository
and add the mainstream as an additional remote in order to be able to submit a merge request later. 

**flowd** can be build with the following command:
```buildoutcfg
docker build -t <image>:<tag> .
```

and can be started with:
```buildoutcfg
docker run --privileged --network=host -it -v /<local_fork_path>/flowd:/usr/src/app --entrypoint=/bin/bash <image>:<tag>  
```

Before staring the service an initial configuration needs to be added in /etc/flowd/flowd.cfg 
(please check an example etc/flowd.cfg). To start the service run:
```buildoutcfg
sbin/flowd --debug
```

## Contribution guide
TBA




