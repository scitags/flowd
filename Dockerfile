FROM gitlab-registry.cern.ch/linuxsupport/cs9-base:latest

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
RUN yum -y update
RUN yum -y install python3-devel python3-pip 
RUN pip install --no-cache-dir -r requirements.txt
RUN yum -y install python3-bcc python3-systemd
ENV PYTHONPATH=/usr/src/app

COPY . .
RUN sed '1 s|^.*$|#!/usr/bin/env python3|' -i /usr/src/app/sbin/flowd

CMD [ "sbin/flowd", "--fg" ]
