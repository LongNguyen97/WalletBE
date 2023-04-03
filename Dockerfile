FROM python:3.8-slim-buster
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1  

RUN mkdir backend
WORKDIR /backend

COPY requirements.txt /backend

RUN pip install --upgrade pip  
RUN pip install -r requirements.txt

COPY . /backend

EXPOSE 8000
