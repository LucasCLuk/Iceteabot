FROM gorialis/discord.py:3.7.4-alpine-pypi-full

COPY . /opt/iceteabot


WORKDIR /opt/iceteabot

RUN apk add --update --no-cache g++ gcc libxslt-dev libffi-dev python3-dev make && \
	pip install -r requirements.txt

CMD ["python", "bot.py"]
