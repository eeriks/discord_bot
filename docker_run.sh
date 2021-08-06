#!/bin/sh
docker rm -f discord_bot
set -e
docker build --tag discord_epicbot .
docker run --detach -v $PWD/dbot:/app -v $PWD/debug:/app/debug --env-file=".env" --env PRODUCTION=1 --restart=always --name discord_bot discord_epicbot

