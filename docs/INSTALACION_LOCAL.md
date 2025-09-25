# Guía de Instalación Local - API Forense

## Requisitos Previos

### 1. Instalar Python 3.12+

**Opción A: Desde python.org (Recomendado)**
1. Ve a https://www.python.org/downloads/
2. Descarga Python 3.12 o superior
3. Durante la instalación, **marca la casilla "Add Python to PATH"**
4. Instala con las opciones por defecto

**Opción B: Desde Microsoft Store**
1. Abre Microsoft Store
2. Busca "Python 3.12"
3. Instala la versión más reciente

### 2. Verificar Instalación
Abre PowerShell o CMD y ejecuta:
```bash
python --version
# o si no funciona:
py --version
```

## Instalación del Proyecto

### 1. Crear Entorno Virtual
```bash
# Navegar al directorio del proyecto
cd C:\Users\Nexti\sources\api-forense

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
.\venv\Scripts\activate

# Verificar que está activado (debería aparecer (venv) al inicio)
```

### 2. Instalar Dependencias
```bash
# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias del proyecto
pip install -r requerimientos.txt
```

### 3. Configurar Variables de Entorno (Opcional)
Crea un archivo `.env` en la raíz del proyecto:
```env
# Configuración SRI
SRI_TIMEOUT=12
MAX_PDF_BYTES=10485760

# Configuración OCR
EASYOCR_GPU=false
EASYOCR_LANGS=es,en
RENDER_DPI=250

# Configuración AWS (requerido para /aws-textract-ocr)
AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1

# Configuración de comparación
CMP_QTY_EPS=0.001
CMP_PRICE_EPS=0.01
CMP_TOTAL_EPS=0.02
CMP_MATCH_THRESHOLD=0.60

# Configuración de análisis
TEXT_MIN_LEN_FOR_DOC=50
MAX_DIAS_CREACION_EMISION_OK=30
MAX_DIAS_MOD_VS_CREACION_OK=10
```

**⚠️ Para usar AWS Textract**, debes configurar las credenciales. Ver guía completa: [AWS_SETUP.md](AWS_SETUP.md)

### 4. Levantar el Servidor
```bash
# Opción 1: Usando el script main.py
python main.py

# Opción 2: Usando uvicorn directamente
uvicorn app:app --host 127.0.0.1 --port 8005 --reload

# Opción 3: Para desarrollo con recarga automática
uvicorn app:app --reload --port 8005
```

## Verificar que Funciona

### 1. Endpoint de Health
Abre tu navegador y ve a:
```
http://127.0.0.1:8005/health
```

Deberías ver una respuesta JSON como:
```json
{
  "ok": true,
  "mode": "json + easyocr + compare-products + risk",
  "app_version": "1.50.0-risk",
  ...
}
```

### 2. Documentación Automática
- Swagger UI: http://127.0.0.1:8005/docs
- ReDoc: http://127.0.0.1:8005/redoc

## Endpoints Disponibles

### POST /validar-factura
Validación completa con verificación SRI
```json
{
  "pdfbase64": "base64_encoded_pdf_content"
}
```

### POST /validar-documento  
Análisis local sin consulta SRI
```json
{
  "pdfbase64": "base64_encoded_pdf_content"
}
```

### GET /config/risk-weights
Obtener configuración de pesos de riesgo

### PUT /config/risk-weights
Actualizar pesos de riesgo
```json
{
  "RISK_WEIGHTS": {
    "fecha_creacion_vs_emision": 15,
    "fecha_mod_vs_creacion": 12,
    ...
  }
}
```

## Solución de Problemas

### Error: "No module named 'torch'"
```bash
# Reinstalar PyTorch
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### Error: "Microsoft Visual C++ 14.0 is required"
1. Instala Visual Studio Build Tools
2. O instala Visual Studio Community con C++ tools

### Error de memoria con EasyOCR
```bash
# Configurar para usar CPU en lugar de GPU
set EASYOCR_GPU=false
```

### Puerto ocupado
```bash
# Cambiar puerto
uvicorn app:app --port 8006
```

## Desarrollo

### Estructura del Proyecto
```
api-forense/
├── app.py              # Aplicación FastAPI principal
├── main.py             # Script de arranque
├── config.py           # Configuración
├── ocr.py              # Procesamiento OCR
├── pdf_extract.py      # Extracción de datos PDF
├── sri.py              # Integración con SRI
├── riesgo.py           # Análisis de riesgo
├── utils.py            # Utilidades
├── risk_weights.json   # Configuración de pesos
├── routes/             # Endpoints organizados
│   ├── health.py
│   ├── validar.py
│   ├── validar_documento.py
│   └── config.py
└── requerimientos.txt  # Dependencias
```

### Comandos Útiles
```bash
# Activar entorno virtual
.\venv\Scripts\activate

# Desactivar entorno virtual
deactivate

# Ver dependencias instaladas
pip list

# Actualizar dependencias
pip install --upgrade -r requerimientos.txt

# Ejecutar con logs detallados
uvicorn app:app --log-level debug --reload
```

## Notas Importantes

1. **Primera ejecución**: EasyOCR descargará modelos (~100MB), puede tardar unos minutos
2. **Memoria**: El OCR puede usar bastante RAM, especialmente con PDFs grandes
3. **Red**: Necesitas conexión a internet para consultas al SRI
4. **Certificados**: En algunos entornos corporativos pueden haber problemas con certificados SSL

¡El proyecto debería estar funcionando en http://127.0.0.1:8005!
