# Raspberry Pi Video Player

Repository for my home project, a video player an old CRT TV using the Raspberry
PI. I use a 3 B+, but it should work on any one supporting amd64.

## Steps to install

### On the Raspberry Pi

1. Install Raspberry Pi Lite 64-bit version
2. Install Docker and Docker Compose
3. Edit `pi/.env` file
4. Symlink `pi/docker-compose.pi.yml` to `pi/docker-compose.overide.yml`
5. Build and run,

```bash
cd pi
docker compose build
docker compose up -d
```
