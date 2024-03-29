#!/bin/sh

if [ -f /.env ]; then
    . /.env
else
    echo "WARNING: Envfile /.env file missing"
fi


EXTRA_ARGS=
if [ "$DEBUG" -a "$DEBUG" != '0' ]; then
    EXTRA_ARGS=--reload

    # dbus inherits open file descriptor (listening port) from uvicorn when --reload is on
    killall dbus-daemon 2>/dev/null
fi

exec uvicorn api.app:app \
    --workers 1 \
    --forwarded-allow-ips '*' \
    --proxy-headers \
    --host 0.0.0.0 \
    --port 8000 \
    $EXTRA_ARGS
