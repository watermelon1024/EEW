FROM python:3.12-alpine AS base

FROM base AS builder
WORKDIR /EEW

RUN apk add --no-cache \
  build-base \
  cmake \
  python3-dev \
  musl-dev \
  libffi-dev \
  gdal-dev \
  geos-dev \
  proj \
  proj-dev \
  proj-util \
  postgresql-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

FROM base
WORKDIR /EEW

ENV PROJ_DATA=/usr/share/proj
RUN apk add --no-cache geos proj
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12

COPY . .

CMD ["python", "main.py"]
