ARG DEBIAN_VERSION=bullseye \
    PLATFORM=

FROM --platform=linux/armhf "debian:${DEBIAN_VERSION}" AS omxplayer-builder

RUN apt-get -y update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gpg \
    && curl -sSL https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | gpg --dearmor > /etc/apt/trusted.gpg.d/raspi.gpg \
    && echo "deb http://archive.raspberrypi.org/debian/ $(sh -c '. /etc/os-release; echo "${VERSION_CODENAME}"') main" \
        > /etc/apt/sources.list.d/raspi.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential \
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

ARG ARG FIRMWARE_VC_LIBS_VERSION=7e6decce72
RUN cd /tmp && mkdir firmware \
    && curl -sSL "https://github.com/raspberrypi/firmware/tarball/${FIRMWARE_VC_LIBS_VERSION}" \
        | tar xz --strip-components=1 -C firmware \
    && mv -v firmware/opt/vc /opt/vc \
    && rm -rf firmware

ARG OMXPLAYER_REPO=mjfwalsh/omxplayer \
    OMXPLAYER_VERSION=c8a89d8b84
RUN mkdir /build && cd /build \
    && curl -sSL "https://github.com/${OMXPLAYER_REPO}/tarball/${OMXPLAYER_VERSION}" | tar xz --strip-components=1 \
    && CFLAGS=-marm make -j "$(nproc)" \
    && make dist


FROM --platform=linux/arm64 "python:3.12-slim-${DEBIAN_VERSION}"

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gpg \
    && curl -sSL https://archive.raspberrypi.org/debian/raspberrypi.gpg.key \
        | gpg --dearmor > /etc/apt/trusted.gpg.d/raspi.gpg \
    && echo "deb http://archive.raspberrypi.org/debian/ $(sh -c '. /etc/os-release; echo "${VERSION_CODENAME}"') main" \
        > /etc/apt/sources.list.d/raspi.list \
    && DEBIAN_FRONTEND=noninteractive apt-get remove -y --purge gpg \
    && DEBIAN_FRONTEND=noninteractive apt-get autoremove -y --purge \
    && dpkg --add-architecture armhf \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        dbus \
        fonts-freefont-ttf \
        libasound2:armhf \
        libavcodec58:armhf \
        libavformat58:armhf \
        libc6:armhf \
        libdbus-1-3:armhf \
        libdvdread8:armhf \
        libraspberrypi0:armhf \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir /app \
    # These libs don't seem to get properly symlinked on arm64
    && cd /usr/lib/arm-linux-gnueabihf \
    && for lib in bcm_host vchiq_arm vcos; do \
        if [ ! -e "lib${lib}.so" ]; then \
            ln -vs "lib${lib}.so.0" "lib${lib}.so" \
        ; fi \
    ; done

WORKDIR /app

ARG POETRY_VERSION=1.7.1
# Rust needed for armhf poetry install (package: cryptography)
RUN curl -sSL https://install.python-poetry.org | python -

ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml poetry.lock /app/
ARG DEBUG=
RUN poetry install $([ -z "$DEBUG" -o "$DEBUG" = '0' ] && echo '--without=dev')

COPY --from=omxplayer-builder /build/omxplayer-dist.tgz /
RUN tar --skip-old-files --absolute-names -xf /omxplayer-dist.tgz && rm /omxplayer-dist.tgz
