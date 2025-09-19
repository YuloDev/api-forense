from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import health, validar, validar_documento, config, risk_levels, alineacion, reclamos, deteccion_texto, validacion_firma_universal, validar_imagen
 
app = FastAPI(
    title="Validador SRI + OCR + Comparación productos + Riesgo",
    version="1.50.0-risk"
)
 
# Middleware CORS - Configuración mejorada para desarrollo y producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React/Vite dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Vue dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8001",  # Mismo servidor
        "http://localhost:8001",
        "https://claims-app.nextisolutions.com",  # Aplicación de reclamos
        "https://api-forense.nextisolutions.com",  # API forense
        "https://nextisolutions.com",  # Dominio principal
        "https://*.nextisolutions.com",  # Subdominios de Nexti
        "*"  # Fallback para desarrollo
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
 
 