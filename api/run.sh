#!/bin/sh

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
