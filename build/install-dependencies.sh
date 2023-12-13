#!/bin/sh

set -e

tar --skip-old-files --absolute-names -xf /mounted-github-repo/build/omxplayer-dist.tgz

# TODO: Only do on arm64
dpkg --add-architecture armhf

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    fonts-freefont-ttf \
    libasound2:armhf \
    libavcodec58:armhf \
    libavformat58:armhf \
    libc6:armhf \
    libdbus-1-3:armhf \
    libdvdread8:armhf \
    libraspberrypi0:armhf

# TODO: Only do on arm64
for lib in bcm_host vchiq_arm vcos; do
    sudo ln -vs "/usr/lib/arm-linux-gnueabihf/lib${lib}.so.0" "/usr/lib/arm-linux-gnueabihf/lib${lib}.so"
done
