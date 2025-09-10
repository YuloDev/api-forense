# Imagen base ligera con Python 3.12
FROM python:3.12-slim

# Evitar prompts en apt
ENV DEBIAN_FRONTEND=noninteractive

# Dependencias del sistema (certificados TLS, build tools y libGL por si EasyOCR/opencv lo requieren)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# Mejorar pip y herramientas de build
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Directorio de la app
WORKDIR /app

# Instalar dependencias de Python primero para aprovechar cache
COPY requerimientos.txt .
RUN pip install --no-cache-dir -r requerimientos.txt

# Copiar tu aplicación
COPY prueba.py /app/prueba.py

# Variables por defecto (puedes sobreescribirlas con -e)
ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    # Ajustes de tu app
    EASYOCR_GPU=false \
    EASYOCR_LANGS=es,en \
    RENDER_DPI=250 \
    MAX_PDF_BYTES=10485760 \
    SRI_TIMEOUT=12 \
    TEXT_MIN_LEN_FOR_DOC=50

# Exponer puerto
EXPOSE 8000

# (Opcional pero recomendado) usuario no root
RUN useradd -ms /bin/bash appuser && chown -R appuser /app
USER appuser

# Comando de arranque
CMD ["uvicorn", "prueba:app", "--host", "0.0.0.0", "--port", "8000"]
