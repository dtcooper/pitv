#!/bin/sh

if [ -f /.env ]; then
    . /.env
else
    echo "WARNING: Envfile /.env file missing"
fi

# Set backdrop for when omxplayer isn't running
if [ -z "$SKIP_FBI" -o "$SKIP_FBI" = '0' ]; then
    if ! pgrep fbi >/dev/null ; then
        fbi -d /dev/fb0 -T 1 -a --nocomments --noverbose backsplash.png >/dev/null
    fi
fi

EXTRA_ARGS=
if [ "$DEBUG" -a "$DEBUG" != '0' ]; then
    EXTRA_ARGS=--reload
fi

exec uvicorn api.app:app \
    --workers 1 \
    --forwarded-allow-ips '*' \
    --proxy-headers \
    --host 0.0.0.0 \
    --port 8000 \
    $EXTRA_ARGS
