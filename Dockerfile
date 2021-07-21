FROM python:3.9.6-slim

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN apt-get update
RUN apt-get -y install libsystemd-dev gcc python3-dev pkg-config
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH=/usr/src/app

COPY . .

CMD [ "sbin/flowd", "--fg" ]
