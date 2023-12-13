#!/bin/sh

set -e

PYTHON_VERSION=3.12.1

tar --skip-old-files --absolute-names -xf /mounted-github-repo/build/omxplayer-dist.tgz

# TODO: Only do on arm64
dpkg --add-architecture armhf

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    fonts-freefont-ttf \
    libasound2:armhf \
    libavcodec58:armhf \
    libavformat58:armhf \
    libc6:armhf \
    libdbus-1-3:armhf \
    libdvdread8:armhf \
    libraspberrypi0:armhf \
    build-essential \
    libbz2-dev \
    libc6-dev \
    libffi-dev \
    libgdbm-dev \
    liblzma-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libnss3-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    lzma-dev \
    openssl \
    uuid-dev \
    zlib1g-dev

# TODO: Only do on arm64
for lib in bcm_host vchiq_arm vcos; do
    sudo ln -vs "/usr/lib/arm-linux-gnueabihf/lib${lib}.so.0" "/usr/lib/arm-linux-gnueabihf/lib${lib}.so"
done

# Install newest version of Python
mkdir -p /tmp/python
cd /tmp/python
curl -sL "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz" | tar xJ --strip-components=1
./configure --enable-optimizations --with-lto
make -j "$(nproc)"
make altinstall
cd /tmp
rm -rf /tmp/python
