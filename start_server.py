#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para iniciar el servidor con la configuración correcta
"""

# Configurar Tesseract ANTES de importar cualquier módulo
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

import uvicorn
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Iniciando servidor FastAPI...")
    print("   Host: 0.0.0.0")
    print("   Puerto: 8001")
    print("   Modo: reload (desarrollo)")
    print("   Configuración Tesseract: ✅")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
