FROM docker.io/python:3.11

WORKDIR /app

# --- [Install dependencies] ---
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y python3 python3-pip git build-essential libsqlcipher-dev
COPY . /app

RUN pip install -r requirements.txt
RUN pip install gunicorn

ENV GUNICORN_CMD_ARGS="--workers=2 --bind=0.0.0.0:8087"

EXPOSE 8087

CMD [ "gunicorn", "main:app" ]
