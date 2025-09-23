#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para configurar Tesseract globalmente para Linux (Docker/producción)
"""

import os
import sys

# Configurar Tesseract ANTES de importar cualquier módulo que lo use
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
    print("✅ Tesseract configurado globalmente para Linux: /usr/bin/tesseract")
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
