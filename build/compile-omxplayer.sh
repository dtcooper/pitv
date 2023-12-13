#!/bin/sh

set -e

if [ ! -e /.dockerenv ]; then
    cd "$(dirname "$0")"
    docker run --rm -v "$(pwd):/mnt" --platform linux/arm debian:bullseye /mnt/compile-omxplayer.sh
    exit 0
fi

if [ "$(dpkg --print-architecture)" != armhf ]; then
    echo 'Incorrect architecture (must be armhf)!'
    exit 1
fi

# Various versions we'll be using
FIRMWARE_VC_LIBS_VERSION=7e6decce72
OMXPLAYER_VERSION=c8a89d8b84
OMXPLAYER_REPO=mjfwalsh/omxplayer

# Add Rasbpberry Pi apt sources
apt-get -y update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
        ca-certificates \
        curl \
        gpg
curl -sL https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | gpg --dearmor > /etc/apt/trusted.gpg.d/raspi.gpg
echo "deb http://archive.raspberrypi.org/debian/ $(sh -c '. /etc/os-release; echo $VERSION_CODENAME') main" > /etc/apt/sources.list.d/raspi.list

# Install requirements
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    checkinstall \
    libasound2-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libboost-dev \
    libcairo2-dev \
    libdbus-1-dev \
    libdvdread-dev \
    libpcre2-dev \
    libraspberrypi-dev \
    libswresample-dev

cd /tmp

# Install libbcm_host and other requirements
mkdir firmware
curl -sL "https://github.com/raspberrypi/firmware/tarball/${FIRMWARE_VC_LIBS_VERSION}" | tar xz --strip-components=1 -C firmware
mv -v firmware/opt/vc /opt/vc
rm -rf firmware

# Compile omxplayer
mkdir build
curl -sL "https://github.com/${OMXPLAYER_REPO}/tarball/${OMXPLAYER_VERSION}" | tar xz --strip-components=1 -C build
cd build
CFLAGS=-marm make -j "$(nproc)"
make dist
mv -v omxplayer-dist.tgz /mnt
