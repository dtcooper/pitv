#!/bin/sh

# Set backdrop for when omxplayer isn't running
if ! pgrep fbi >/dev/null ; then
    fbi -d /dev/fb0 -T 1 -a --nocomments --noverbose backsplash.png >/dev/null
fi

cd api

if [ "$DEBUG" -a "$DEBUG" != '0' ]; then
    watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- python app.py
else
    gunicorn \
            --bind 0.0.0.0:8080 \
            --worker-class aiohttp.worker.GunicornWebWorker \
            --forwarded-allow-ips '*' \
            --capture-output \
            --error-logfile - \
            --access-logformat '%a %t "%r" %s %b "%{Referer}i" "%{User-Agent}i"' \
            --access-logfile - \
        app:app
fi
