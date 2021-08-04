#!/bin/bash
D=test "$1" = "docker"
if test !$D ; then
  source venv/bin/activate
fi
echo "Checking queries..."
python -m unittest 
echo "Starting Discord bot..."
if test !$D ; then
  export $(sed ':a;N;$!ba;s/\n/ /g' .env)
  python dbot/discord_bot.py 
  disown -h %1
  sleep 10
else
  /usr/local/bin/python /app/discord_bot.py
fi
echo "Done!"

