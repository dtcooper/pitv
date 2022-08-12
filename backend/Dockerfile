FROM ghcr.io/dtcooper/raspberrypi-os:python3.10

ARG OMXPLAYER_DEB_URL="http://archive.raspberrypi.org/debian/pool/main/o/omxplayer/omxplayer_20190723+gitf543a0d-1+bullseye_armhf.deb" \
    FIRMWARE_VC_LIBS_VERSION="915a7080" \
    POETRY_VERSION=1.1.14

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN mkdir -p /tmp/firmware \
    && wget -qO - "https://github.com/raspberrypi/firmware/tarball/${FIRMWARE_VC_LIBS_VERSION}" \
        | tar xz --strip=1 -C /tmp/firmware \
    && mv -v /tmp/firmware/opt/vc /opt/vc \
    && rm -rf /tmp/firmware

RUN curl -sSL https://install.python-poetry.org | python -
ENV PATH="/root/.local/bin:${PATH}"

RUN apt-get update \
    && apt-get upgrade -y \
    && wget -qO /tmp/omxplayer.deb "$OMXPLAYER_DEB_URL" \
    && apt-get install --no-install-recommends -y \
        /tmp/omxplayer.deb \
        # To mute/unmute
        alsa-utils \
        # For "killall"
        psmisc \
    && rm -rf /var/lib/apt/lists/* /tmp/omxplayer.deb

COPY pyproject.toml poetry.lock /app/
WORKDIR /app
RUN poetry install

COPY . /app
CMD ["./run.sh"]
