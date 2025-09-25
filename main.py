# Usar configuración global de Tesseract desde config
import config

from app import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8001, reload=True)
