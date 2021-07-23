#!/bin/sh
docker rm -f discord_bot
set -e
docker build --tag discord_epicbot .
docker run --detach -v $PWD:/app --restart=always --name discord_bot discord_epicbot

