#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para configurar Tesseract globalmente antes de importar otros módulos
"""

import os
import sys

# Configurar Tesseract ANTES de importar cualquier módulo que lo use
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    print("✅ Tesseract configurado globalmente")
except Exception as e:
    print(f"❌ Error configurando Tesseract: {e}")

# Ahora importar y ejecutar el servidor
if __name__ == "__main__":
    import uvicorn
    from main import app
    
    print("🚀 Iniciando servidor con Tesseract configurado...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
