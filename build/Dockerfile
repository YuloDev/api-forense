FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema
# qpdf y libstdc++6 son necesarios para pikepdf
# tesseract-ocr y dependencias para OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    libjpeg62-turbo \
    zlib1g \
    libfreetype6 \
    libharfbuzz0b \
    qpdf \
    libstdc++6 \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    libzbar0 \
  && rm -rf /var/lib/apt/lists/*

# Actualizar pip y herramientas de instalación
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app

# Instalar dependencias de Python primero para aprovechar cache
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Las dependencias ya están instaladas y verificadas

# Copiar toda la aplicación
COPY . .

# Variables de entorno por defecto
ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    EASYOCR_GPU=false \
    EASYOCR_LANGS=es,en \
    RENDER_DPI=250 \
    MAX_PDF_BYTES=10485760 \
    SRI_TIMEOUT=12 \
    TEXT_MIN_LEN_FOR_DOC=50 \
    AWS_DEFAULT_REGION=us-east-1

EXPOSE 8000

# Crear usuario no root
RUN useradd -ms /bin/bash appuser && chown -R appuser /app
USER appuser

# Arranque de la aplicación
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]