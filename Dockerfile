FROM python:3.9-slim
WORKDIR /app
RUN groupadd -g 1000 discordbot \
 && useradd -u 1000 -g 1000 discordbot \
 && mkdir /home/discordbot \
 && chown -R discordbot:discordbot /app \
 && chown -R discordbot:discordbot /home/discordbot

USER discordbot
COPY requirements.txt /app/requirements.txt
COPY ./run.sh /run.sh
RUN pip install -r requirements.txt && chmod +x /run.sh

#CMD python discord_bot.py
ENTRYPOINT ['/run.sh', 'docker']
