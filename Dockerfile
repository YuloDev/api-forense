FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

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
  && rm -rf /var/lib/apt/lists/*


RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app

# Instalar dependencias primero para aprovechar cache
COPY requerimientos.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar toda la aplicación (ya que está en raíz)
COPY . .

# Variables por defecto (puedes sobreescribir con -e)
ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    EASYOCR_GPU=false \
    EASYOCR_LANGS=es,en \
    RENDER_DPI=250 \
    MAX_PDF_BYTES=10485760 \
    SRI_TIMEOUT=12 \
    TEXT_MIN_LEN_FOR_DOC=50

EXPOSE 8000

# Usuario no root
RUN useradd -ms /bin/bash appuser && chown -R appuser /app
USER appuser

# Comando de arranque con Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
