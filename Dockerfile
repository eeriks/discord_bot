FROM python:3.9-slim
WORKDIR /app
COPY ./run.sh /run.sh
RUN groupadd -g 1000 discordbot \
 && useradd -u 1000 -g 1000 discordbot \
 && mkdir /home/discordbot \
 && chown -R discordbot:discordbot /app \
 && chown -R discordbot:discordbot /home/discordbot \
 && chmod +x /run.sh

USER discordbot
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
ENV PYTHONPATH=$PYTHONPATH:/app/dbot
#CMD python discord_bot.py
ENTRYPOINT ["/usr/local/bin/python", "/app/dbot/discord_bot.py"]
