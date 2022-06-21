# Raspberry Pi Video Player

Repository for my home project, a video player an old CRT TV using the Raspberry
PI. I use a 3 B+, but it should work on any one supporting amd64.

## Steps to install

### On the Raspberry Pi 3 or 4

1. Install [Raspberry Pi OS Lite (64-bit version)](https://www.raspberrypi.com/software/operating-systems/).
2. Install Make, Docker and Docker Compose
    ```bash
    # Install Docker
    curl -fsSL https://get.docker.com | sh

    # Install latest Compose
    sudo mkdir -p /usr/local/lib/docker/cli-plugins/
    sudo curl -fsSL -o /usr/local/lib/docker/cli-plugins/docker-compose \
        "$(curl -fsSL https://api.github.com/repos/docker/compose/releases/latest | grep browser_download_url | cut -d '"' -f 4 | grep -i "$(uname -s)-$(arch)$")"
    sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    ```
3. Clone repo, build containers
    ```bash
    git clone https://github.com/dtcooper/raspvid.git
    cd raspvid
    make build
    ```
4. Copy over and edit the `.env` file
    ```bash
    cp .env.sample .env
    ```
5. Build and run,
    ```bash
    docker compose build
    docker compose up -d
    ```
