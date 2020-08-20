# Docker Updater
This script will check for updates of all running Docker containers, comparing the image specified in the docker-compose.yaml file, to the latest available image.

If a container named Plex is found, it will check for streams (if the --force flag isn't specified), if there is no stream active, it will update.

It can also send update and restart notices to Gotify.

## Usage
```
docker-updater.py [-h] [--force] [--dry-run] (--name CONTAINERNAME | --all)
optional arguments:
  -h, --help              Show this help message and exit
  --force                 Forces updating of the container, skipping checks for things like Plex streams
  --dry-run               Prints what the script would do, without updating or restarting containers
  --name <CONTAINERNAME>  The container name you want to update
  --all                   Update all containers found on this system
```
