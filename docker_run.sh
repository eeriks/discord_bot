#!/bin/sh
docker rm -f discord_bot

set -e
docker build --tag discord_epicbot .
docker run --detach -v ./src:/app -v ./debug:/app/debug --env-file=".env" --restart=always --name discord_bot discord_epicbot

