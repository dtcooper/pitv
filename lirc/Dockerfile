FROM ghcr.io/dtcooper/raspberrypi-os:bullseye AS base

FROM base AS builder

ARG IGUANAIR_REPO="https://github.com/iguanaworks/iguanair.git" \
    IGUANAIR_GIT_VERSION="c6284e5c"

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        debhelper \
        git \
        liblircclient-dev \
        libsystemd-dev \
        libusb-1.0-0-dev \
        pkg-config \
        python-dev \
        python3-dev \
        swig \
        systemd \
        udev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /build \
    && cd /build \
    && git clone "$IGUANAIR_REPO" iguanair \
    && cd iguanair \
    && git checkout "$IGUANAIR_GIT_VERSION" \
    && sed -i 's/\(#!\/usr\/bin\/python\)/\13/' mkChangelog \
    && ./mkChangelog -d stable --b 1 -o debian/changelog \
    && sed -i "s/${IGUANAIR_VERSION}-stable/${IGUANAIR_VERSION}/" debian/changelog \
    && sed -i '/dh-systemd/d' debian/control \
    && sed -i '/systemctl daemon-reload/d' debian/iguanair.post* \
    && dpkg-buildpackage -b


FROM base AS final

ARG MULTIRUN_VERSION=1.1.3

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && cd /usr/local/bin \
    && curl -sSL "https://github.com/nicolas-van/multirun/releases/download/${MULTIRUN_VERSION}/multirun-$(arch)-linux-gnu-${MULTIRUN_VERSION}.tar.gz" \
        | tar xz \
    && apt-get purge -y \
        ca-certificates \
        curl \
    && apt-get autoremove -y --purge \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /run/lirc

COPY --from=builder /build/iguanair_*.deb /build/libiguanair0_*.deb /build/lirc-drv-iguanair_*.deb /tmp/

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
        /tmp/*.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/*.deb /etc/lirc/lircd.conf.d/*.lircd.conf

COPY *.lircd.conf /etc/lirc/lircd.conf.d/

CMD [ \
        "multirun", \
        "igdaemon --driver=libusb --log-level=1 --send-timeout=1000 --receive-timeout=1000 --no-daemon", \
        "lircd --nodaemon --driver=iguanair --output=/run/lirc/lircd --pidfile=/run/lircd.pid --listen=0.0.0.0:8765" \
    ]
