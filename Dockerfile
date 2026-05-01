FROM python:3.12-slim AS builder
WORKDIR /EEW

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  cmake \
  libffi-dev \
  libgdal-dev \
  libgeos-dev \
  libproj-dev \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel && \
  pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /EEW

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PROJ_DATA=/usr/share/proj \
  PATH="/opt/venv/bin:$PATH"

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  libgeos-c1v5 \
  libproj22 \
  libpq5 \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

COPY . .

CMD ["python", "main.py"]