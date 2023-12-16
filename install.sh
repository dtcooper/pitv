#!/bin/sh

set -e

CMD="$0"
usage() {
    cat <<EOF
Usage: ${CMD} [--local-image <path>] [--yes] [--dry-run]

Script to install PiTV player on your Raspberry Pi

Arguments:
  -l <path>, --local-image <path>  Usage local image at <path>, don't pull one
  -y, --yes                        Answer yes to all prompts
  -n, --dry-run                    Dry run, don't actually install
  -v, --verbose                    Run verbosely
  -h, --help                       Show this help screen
EOF
    exit 0
}


LOCAL_IMAGE=
DRY_RUN=
VERBOSE=
YES=
while [ $# -gt 0 ]; do
    case "$1" in
        --local-image|-l)
            LOCAL_IMAGE="$2"
            shift
            ;;
        --yes|-y)
            YES=1
            ;;
        --dry-run|-n)
            DRY_RUN=1
            ;;
        --verbose|-v)
            VERBOSE=1
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Invalid argument: $1"
            exit 1
        ;;
    esac
    if [ $# -gt 0 ]; then
        shift
    fi
done

sh_exec() {
    if [ "$DRY_RUN" ]; then
        echo "++ WOULD EXECUTE: $@"
    else
        if [ "$VERBOSE" ]; then
            echo "++ EXECUTING: $@"
        fi
        "$@"
    fi
}

if [ "$(id -u)" -ne 0 ]; then
    echo 'You must run this script as root! (Try it with sudo)'
    exit 1
fi

echo "LOCAL_IMAGE=${LOCAL_IMAGE}"
echo "DRY_RUN=${DRY_RUN}"
echo "VERBOSE=${VERBOSE}"
echo "YES=${YES}"
