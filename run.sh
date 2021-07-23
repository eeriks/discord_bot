#!/bin/bash
source venv/bin/activate
echo "Checking queries..."
python -m unittest
echo "Starting Discord bot..."
python discord_bot.py &
disown -h %1
sleep 10
echo "Done!"

