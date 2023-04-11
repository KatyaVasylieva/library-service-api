FROM python:3.10-alpine
LABEL maintainer="katevvasylyeva@gmail.com"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install -r requirements.txt

COPY . /code/

RUN adduser \
    --disabled-password \
    --no-create-home \
    django-user

USER django-user
