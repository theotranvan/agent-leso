# --- Stage de compilation de LibreDWG (dwg2dxf) ---------------------------
# LibreDWG n'est pas packagé dans les dépôts Debian de l'image slim ; on compile
# l'outil dwg2dxf (statique) depuis la release officielle. Il convertit les plans
# DWG → DXF pour le relevé thermique / métrés 2D (mesure géométrique).
FROM python:3.12-slim AS dwgbuild
ARG LIBREDWG_VERSION=0.13.3
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl xz-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL -o /tmp/libredwg.tar.xz \
      "https://github.com/LibreDWG/libredwg/releases/download/${LIBREDWG_VERSION}/libredwg-${LIBREDWG_VERSION}.tar.xz" \
    && mkdir -p /tmp/ld && tar xf /tmp/libredwg.tar.xz -C /tmp/ld --strip-components=1 \
    && cd /tmp/ld \
    && ./configure --disable-bindings --disable-shared --enable-static --disable-dependency-tracking \
    && make -C src -j"$(nproc)" \
    && make -C programs dwg2dxf -j"$(nproc)" \
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
