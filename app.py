# La configuración de Tesseract se maneja globalmente
# Importar pytesseract sin configurar para evitar conflictos
import pytesseract

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from routes import health, validar, validar_documento, config, risk_levels, alineacion, reclamos, validacion_firma_universal, validar_imagen, validar_factura, validar_factura_nuevo
 
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
app.include_router(validacion_firma_universal.router)
app.include_router(validar_imagen.router)
app.include_router(validar_factura.router)
app.include_router(validar_factura_nuevo.router)
 
 