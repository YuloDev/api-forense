# Configurar Tesseract ANTES de importar cualquier módulo
import os
import pytesseract

# Configuración de Tesseract para Windows y Linux
def configurar_tesseract():
    """Configura Tesseract para Windows (desarrollo) y Linux (Docker/producción)"""
    if os.name == 'nt':  # Windows
        # Ruta de Windows (desarrollo local)
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"✅ Tesseract configurado para Windows: {tesseract_path}")
        else:
            print("⚠️ Tesseract no encontrado en Windows, usando configuración por defecto")
    else:  # Linux (Docker/producción)
        # En Linux, Tesseract debe estar instalado en el PATH
        # Comandos típicos: tesseract, /usr/bin/tesseract, /usr/local/bin/tesseract
        possible_paths = [
            'tesseract',
            '/usr/bin/tesseract',
            '/usr/local/bin/tesseract',
            '/opt/homebrew/bin/tesseract'  # macOS con Homebrew
        ]
        
        tesseract_found = False
        for path in possible_paths:
            try:
                # Verificar si el comando existe
                import subprocess
                result = subprocess.run([path, '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✅ Tesseract configurado para Linux: {path}")
                    tesseract_found = True
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        if not tesseract_found:
            print("⚠️ Tesseract no encontrado en Linux, usando configuración por defecto")
            # En Docker, Tesseract debería estar en el PATH por defecto
            pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# Configurar Tesseract
configurar_tesseract()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from routes import health, validar, validar_documento, config, risk_levels, alineacion, reclamos, deteccion_texto, validacion_firma_universal, validar_imagen, validar_factura, validar_factura_fast, validar_factura_nuevo
 
app = FastAPI(
    title="Validador SRI + OCR + Comparación productos + Riesgo",
    version="1.50.0-risk"
)
 
origins = [
    "http://localhost:4028",            # tu frontend en dev
    "https://claims-app.nextisolutions.com",  # frontend en producción
    "https://api-forense.nextisolutions.com", # API en producción
    "*"  # Permitir todos los orígenes temporalmente para debug
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes temporalmente
    allow_credentials=False,  # Debe ser False cuando allow_origins=["*"]
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Endpoint para manejar peticiones OPTIONS (CORS preflight)
@app.options("/{path:path}")
async def options_handler(path: str):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400"
        }
    )

# Registrar rutas
app.include_router(health.router)
app.include_router(validar.router)
app.include_router(validar_documento.router)
app.include_router(config.router)
app.include_router(risk_levels.router)
app.include_router(alineacion.router)
app.include_router(reclamos.router)
app.include_router(deteccion_texto.router)
app.include_router(validacion_firma_universal.router)
app.include_router(validar_imagen.router)
app.include_router(validar_factura.router)
app.include_router(validar_factura_fast.router)
app.include_router(validar_factura_nuevo.router)
 
 