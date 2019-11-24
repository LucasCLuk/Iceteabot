FROM gorialis/discord.py:3.7-pypi-minimal

COPY . /opt/iceteabot


WORKDIR /opt/iceteabot

RUN pip install -r requirements.txt


CMD ["python", "bot.py"]
