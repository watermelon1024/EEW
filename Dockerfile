FROM python:3.12.3-alpine3.20 AS base

FROM base AS builder
RUN apk add --no-cache \
    musl-dev \
    libffi-dev \
    gdal-dev \
    gcc \
    g++ \
    geos-dev \
    proj \
    proj-dev \
    proj-util \
    postgresql-dev

WORKDIR /EEW
COPY requirements.txt /EEW/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM base
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
RUN apk add --no-cache openssl-dev gdal-dev && pip install --no-cache-dir geos proj==0.2.0
ENV PROJ_DATA=/usr/share/proj
WORKDIR /EEW
COPY . /EEW
ENTRYPOINT ["python", "main.py"]
