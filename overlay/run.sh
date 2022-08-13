#!/bin/sh

if [ -f /.env ]; then
    . /.env
else
    echo "WARNING: Envfile /.env file missing"
fi

CMD="python -m overlay"
if [ "$DEBUG" -a "$DEBUG" != '0' ]; then
    exec watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- $CMD
else
    exec $CMD
fi
