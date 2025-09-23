# Usar configuración global de Tesseract
import configurar_tesseract_global

from app import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
