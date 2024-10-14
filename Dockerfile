FROM fedora:40

WORKDIR /usr/local/src/app

COPY requirements.txt ./
RUN yum -y update
RUN yum -y install python3-devel python3-pip iproute-tc
RUN pip install --no-cache-dir -r requirements.txt
RUN yum -y install python3-bcc python3-systemd
ENV PYTHONPATH=/usr/local/src/app

COPY . .
RUN sed '1 s|^.*$|#!/usr/bin/env python3|' -i /usr/local/src/app/sbin/flowd

CMD [ "sbin/flowd", "--debug", "--fg" ]
