#!/bin/sh

set -e

CONTAINER_NAME=ghcr.io/dtcooper/pitv-player

CMD="$0"
usage() {
    cat <<EOF
Usage: ${CMD} [-l <path>] [--force-docker] [-y] [-n] [-h]

Script to install PiTV player on your Raspberry Pi

Arguments:
  -l <path>, --local-image <path>   Usage local image at <path>, don't pull one
  --force-docker                    Force Docker installation, even it exists
  -y, --yes                         Answer yes to all prompts
  -n, --dry-run                     Dry run, don't actually install
  -v, --verbose                     Run verbosely
  -h, --help                        Show this help screen
EOF
    exit 0
}

LOCAL_IMAGE=
FORCE_DOCKER=
DRY_RUN=
VERBOSE=
YES=
while [ $# -gt 0 ]; do
    case "$1" in
        --local-image|-l)
            LOCAL_IMAGE="$2"
            shift
            ;;
        --force-docker)
            FORCE_DOCKER=1
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

test_cmd() {
    which "$1" > /dev/null
}

install_docker() {
    if [ -z "$FORCE_DOCKER" ] && test_cmd docker; then
        echo 'Docker appears to already be installed. Skipping Docker installation!'
    else
        if [ "$DRY_RUN" ]; then
            DOCKER_INSTALL_SCRIPT=/tmp/install-docker.sh
        else
            DOCKER_INSTALL_SCRIPT="$(mktemp -t install-docker-XXXXXXXX.sh)"
        fi
        sh_exec curl -fsSLo "${DOCKER_INSTALL_SCRIPT}" https://get.docker.io/
        sh_exec sh "${DOCKER_INSTALL_SCRIPT}"
        sh_exec rm "${DOCKER_INSTALL_SCRIPT}"
    fi
}

load_container() {
    if [ "$LOCAL_IMAGE" ]; then
        sh_exec docker load -i "${LOCAL_IMAGE}"
    else
        sh_exec docker pull "${CONTAINER_NAME}"
    fi
}

cd "$(dirname "${CMD}")"

if [ "$(id -u)" -ne 0 ]; then
    echo 'You must run this script as root! (Try it with sudo)'
    exit 1
fi

if [ ! -e docker-compose.yml ]; then
    echo "Could not find docker-compose.yml. Are you sure you're in the PiTV repo?"
    exit 1
fi

install_docker
load_container
