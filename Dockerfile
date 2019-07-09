FROM python:3.6-stretch
COPY requirements.txt .
COPY zappos.py .
RUN ["pip", "install", "-r", "requirements.txt"]
