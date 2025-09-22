#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script simple para iniciar el servidor con configuración correcta
"""

# Configurar Tesseract ANTES de cualquier importación
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Importar y ejecutar
import uvicorn
from main import app

if __name__ == "__main__":
    print("🚀 Iniciando servidor FastAPI con Tesseract configurado...")
    print("   Host: 0.0.0.0")
    print("   Puerto: 8001")
    print("   Tesseract: ✅ Configurado")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,  # Desactivar reload para evitar problemas
        log_level="info"
    )
