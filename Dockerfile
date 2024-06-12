FROM python:3.12.3-alpine3.20 AS base

FROM base AS builder
WORKDIR /EEW

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

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base
WORKDIR /EEW

ENV PROJ_DATA=/usr/share/proj
RUN apk add --no-cache geos proj
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12

COPY . .

CMD ["python", "main.py"]
