# --- Stage de compilation de LibreDWG (dwg2dxf) ---------------------------
# LibreDWG n'est pas packagé dans les dépôts Debian de l'image slim ; on compile
# l'outil dwg2dxf (statique) depuis la release officielle. Il convertit les plans
# DWG → DXF pour le relevé thermique / métrés 2D (mesure géométrique).
#
# La source est VENDORÉE dans le repo (backend/vendor/) : le builder Render
# n'accède pas toujours aux assets GitHub (redirigés vers une CDN) → on évite
# tout téléchargement réseau au build (cause d'échec déterministe). La
# compilation est volontairement limitée à -j2 : les gros fichiers générés
# (dynapi.c…) compilés en parallèle massif font sauter la mémoire du builder
# (OOM → exit 2). pcre2/perl ne sont PAS requis (vérifié : build OK sans eux).
FROM python:3.12-slim AS dwgbuild
ARG LIBREDWG_VERSION=0.13.3
ARG LIBREDWG_SHA256=83f1f6e78a744777a481ff4520e4cef3f8ac4b2c1c25671077ca12fe81e8816e
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential xz-utils \
    && rm -rf /var/lib/apt/lists/*
COPY vendor/libredwg-${LIBREDWG_VERSION}.tar.xz /tmp/libredwg.tar.xz
RUN echo "${LIBREDWG_SHA256}  /tmp/libredwg.tar.xz" | sha256sum -c - \
    && mkdir -p /tmp/ld && tar xf /tmp/libredwg.tar.xz -C /tmp/ld --strip-components=1 \
    && cd /tmp/ld \
    && ./configure --disable-bindings --disable-shared --enable-static --disable-dependency-tracking \
    && make -C src -j2 \
    && make -C programs dwg2dxf -j2 \
    && install -m 0755 programs/dwg2dxf /usr/local/bin/dwg2dxf \
    && /usr/local/bin/dwg2dxf --version

# --- Image applicative ----------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dépendances système : Tesseract (OCR fr+en), WeasyPrint (Pango/Cairo), IfcOpenShell
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    libffi-dev \
    libxml2 \
    libxslt1.1 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Binaire dwg2dxf (LibreDWG) compilé au stage précédent → conversion DWG→DXF.
COPY --from=dwgbuild /usr/local/bin/dwg2dxf /usr/local/bin/dwg2dxf

WORKDIR /app

# Install deps d'abord pour cache Docker
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Health + user non-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Gunicorn + Uvicorn workers (prod)
CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "2", \
     "-b", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
