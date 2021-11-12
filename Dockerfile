FROM python:3.8

ARG SPARQL_ENDPOINT
ARG VECTORS_API

ENV SPARQL_ENDPOINT $SPARQL_ENDPOINT
ENV VECTORS_API $VECTORS_API

WORKDIR /usr/src/app
COPY . ./

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD python main.py -p 8010