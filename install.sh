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
  -o, --offline-only
                    Perform an offline installation (assumes Docker installed)
  -n, --dry-run                     Dry run, don't actually install
  -v, --verbose                     Run verbosely
  -h, --help                        Show this help screen
EOF
    exit 0
}

LOCAL_IMAGE=
FORCE_DOCKER=
OFFLINE_ONLY=
DRY_RUN=
VERBOSE=
while [ $# -gt 0 ]; do
    case "$1" in
        --local-image|-l)
            LOCAL_IMAGE="$2"
            shift
            ;;
        --force-docker)
            FORCE_DOCKER=1
            ;;
        -o|--offline-only)
            OFFLINE_ONLY=1
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
        if [ -z "$OFFLINE_ONLY" ]; then
            echo 'Docker appears to already be installed. Skipping Docker installation!'
        fi
    elif [ "$OFFLINE_ONLY" ]; then
        echo "Docker required for installation, but can't install in offline only mode."
        exit 1
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

load_image() {
    if [ "$LOCAL_IMAGE" ]; then
        echo "Loading local Docker image from file: ${LOCAL_IMAGE}"
        sh_exec docker load -i "${LOCAL_IMAGE}"
    fi
}

start_pitv() {
    if [ "$OFFLINE_ONLY" ]; then
        sh_exec docker compose up --pull never -d
    else
        sh_exec docker compose up -d
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

if [ "$OFFLINE_ONLY" ] && [ "$FORCE_DOCKER" ]; then
    echo "Can't run in offline only mode and force Docker installion (requires network)"
    exit 1
fi

install_docker
load_image
start_pitv
