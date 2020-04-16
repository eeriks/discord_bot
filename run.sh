#!/bin/bash
source venv/bin/activate
echo "Checking queries..."
python -m unittest
echo "Starting Discord bot..."
python discord_bot.py &
sleep 10
disown -h %1
echo "Done!"

