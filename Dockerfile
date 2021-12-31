FROM python:3.9-slim

RUN pip3 install --upgrade pip setuptools
RUN pip3 install --upgrade pip

COPY requirements.txt .
RUN pip3 install -r requirements.txt

EXPOSE 8050

VOLUME /fetch_chess_data
VOLUME /dashboard
VOLUME /data
COPY run.py .
