#!/usr/bin/env python
import docker
import os
import urllib.request
import requests
import time
import argparse
import sys
import re
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Update Docker containers')
parser.add_argument('--force', dest='forceUpdate', action='store_true',
                    help='Forces updating of the container, skipping checks for things like Plex streams',
                    required=False)
parser.add_argument('--dry-run', dest='dryRun', action='store_true',
                    help='Prints what the script would do, without updating or restarting containers', required=False)
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--name', dest='containerName', help='The container name you want to update', required=False)
group.add_argument('--all', dest='allContainers', action='store_true',
                   help='Update all containers found on this system', required=False)
args = parser.parse_args()

d = docker.from_env()
url = "https://gotify.yourdomain.com/message?token=???????????"
dockerPath = '/docker/'

plexToken = "????????????????"


def log(title, message, priority):
    # Used for logging to Gotify
    try:
        resp = requests.post(url, json={
            "message": message,
            "priority": priority,
            "title": title
        })
        if priority == 10:
            sys.exit()
        return 0
    except requests.exceptions.ConnectionError as e:
        print("Error logging to Gotify")
        


def checkPlexUsage():
    try:
        plexStatusHtml = urllib.request.urlopen("http://localhost:32400/status/sessions?X-Plex-Token=" + plexToken)
        plexStatus = plexStatusHtml.read()
        tree = ET.fromstring(plexStatus)
        return len(tree)

    except urllib.error.URLError as e:
        print(e.reason)


def getContainers():
    cList = d.containers.list()
    return cList


def printContainerStats(name):
    print("Name: " + name.name)
    print("ID: " + name.short_id)
    print("Image: " + name.attrs['Config']['Image'])
    print(" ")


def findDockerCompose(image, name):
    dirs = os.listdir(dockerPath)
    for dir in dirs:
        try:
            with open(dockerPath + dir + "/docker-compose.yml") as f:
                for line in f:
                    if name + ":" in line:
                        composePath = dockerPath + dir + "/docker-compose.yml"
                        return composePath
        except FileNotFoundError:
            pass
        except NotADirectoryError:
            pass


def getComposeVersion(image, name):
    composeFile = findDockerCompose(image, name)
    composeImage = []
    try:
        with open(composeFile) as f:
            for line in f:
                if "image:" in line and "#" not in line:
                    composeImage.append(re.split(r"image: ", line)[1].split('\n')[0])
        if type(composeImage) == list:
            for i in composeImage:
                if "/" in i:
                    if i.split('/')[1][0:] == image.split('/')[1][0:]:
                        composeImage = i
                        return composeImage
                else:
                    if i == image:
                        composeImage = i                                                                                               
                        return composeImage                                                                                            
            return "None"
        else:
            return str(composeImage)

    except Exception as e:
        print("Error looking for compose image.")
        return None


def restartContainer(image, name):
    composeFile = findDockerCompose(image, name)
    composeDir = composeFile.replace("docker-compose.yml", "")
    command = "docker-compose --project-directory " + composeDir + " -f " + str(composeFile) + " up -d --force-recreate"
    if not args.dryRun:
        os.system(command)
    message = "Container: " + str(name)
    log("Restarted", message, 5)
    return 0


def updateContainer(name):
    if str("k8s_") in str(name.name.lower()):
        return False
    if str("plex").lower() in str(name.name.lower()):
        if not args.forceUpdate:
            print("Container is Plex, checking for streams...")
            plexStreams = checkPlexUsage()
            if plexStreams > 0:
                print("Streaming: " + str(plexStreams))
                return False
    img = name.attrs['Config']['Image']
    composeImage = getComposeVersion(img, name.name)
    if composeImage is None:
        return False
    if img is composeImage:
        print("Running version is different from composer version")
        img = composeImage
    print("PRE Image: " + img)
    if ":" not in composeImage:
        latestImg = composeImage + ":latest"
    else:
        latestImg = composeImage
    if "None" in latestImg:
        print("Unable to find image in compose-file")
        return False
    print("POST Image: " + latestImg + "\n")
    try:
        oldImg = d.images.get(composeImage)
    except requests.exceptions.HTTPError as e:                                                                                     
            print("Error downloading image: " + str(e))  
            return False
    newImg = oldImg
    if not args.dryRun:
        try:
            newImg = d.images.pull(latestImg) 
        except docker.errors.ImageNotFound as e:
            print("Error pulling image: " + str(e))
            return False
    oldID = oldImg.id
    newID = newImg.id
    createTime = newImg.attrs['Created']
    if oldID != newID:
        print("New image found, updating...")
        createTime = createTime.split('.')[0].replace("T", " ")
        message = "Container: " + name.name + " | Image released: " + createTime + " | Tag: " + str(
            latestImg.split(':')[1])
        log("Updated", message, 5)
        restartContainer(img, name.name)
        return True
    else:
        return False


cList = getContainers()

if args.dryRun:
    print("Running in DRY RUN mode... No updates or restarts will be performed")

if args.containerName:
    for i in range(len(cList)):
        if str(args.containerName).lower() in str(cList[i].name).lower():
            printContainerStats(cList[i])
            updateContainer(cList[i])

if args.allContainers:
    for i in range(len(cList)):
        printContainerStats(cList[i])
        updateContainer(cList[i])
