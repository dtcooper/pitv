FROM --platform=linux/arm64 python:3.10

ARG OMXPLAYER_DEB_URL="http://archive.raspberrypi.org/debian/pool/main/o/omxplayer/omxplayer_20190723+gitf543a0d-1+bullseye_armhf.deb"
ARG FIRMWARE_VC_LIBS_VERSION="a4040b25"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VERSION=1.1.13

RUN mkdir /tmp/firmware \
    && wget -qO - "https://github.com/raspberrypi/firmware/tarball/${FIRMWARE_VC_LIBS_VERSION}" \
        | tar xz --strip=1 -C /tmp/firmware \
    && mv /tmp/firmware/opt/vc /opt \
    && rm -rf /tmp/firmware

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
ENV PATH="/root/.poetry/bin:${PATH}"

# Need to add armhf because omxplayer is armhf, not arm64
RUN dpkg --add-architecture armhf \
    && apt-get update \
    && wget -qO /tmp/omxplayer.deb "$OMXPLAYER_DEB_URL" \
    && apt-get install --no-install-recommends -y \
        fbi \
        ffmpeg \
        /tmp/omxplayer.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/omxplayer.deb

COPY pyproject.toml poetry.lock /app/
WORKDIR /app
RUN poetry install \
    ### XXX for development
    && poetry update

COPY . /app
CMD ["./run.sh"]
