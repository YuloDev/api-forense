from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import health, validar
from routes import health, validar, validar_documento, config, risk_levels, alineacion

app = FastAPI(
    title="Validador SRI + OCR + Comparación productos + Riesgo",
    version="1.50.0-risk"
)
 
# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# Registrar rutas
app.include_router(health.router)
app.include_router(validar.router)
app.include_router(validar_documento.router)
app.include_router(config.router)
app.include_router(risk_levels.router)
app.include_router(alineacion.router)

