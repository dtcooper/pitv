FROM debian:bullseye

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        lirc \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/run/lirc \
    && rm /etc/lirc/lircd.conf.d/*

COPY argon.lircd.conf /etc/lirc/lircd.conf.d/

CMD ["lircd", "--nodaemon", "--driver=default", "--listen=0.0.0.0:8765"]
