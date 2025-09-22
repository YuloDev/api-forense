# Configurar Tesseract ANTES de importar cualquier módulo
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import health, validar, validar_documento, config, risk_levels, alineacion, reclamos, deteccion_texto, validacion_firma_universal, validar_imagen, validar_factura, validar_factura_fast, validar_factura_nuevo
 
app = FastAPI(
    title="Validador SRI + OCR + Comparación productos + Riesgo",
    version="1.50.0-risk"
)
 
# Middleware CORS - Configuración mejorada para desarrollo y producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
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
 
 