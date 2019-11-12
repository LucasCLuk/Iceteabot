FROM python:3.7-alpine

COPY . /opt/iceteabot


WORKDIR /opt/iceteabot

RUN apk add --update --no-cache g++ gcc libxslt-dev libffi-dev python3-dev make && \
	pip install -r requirements.txt

CMD ["python", "bot.py"]
