#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para configurar Tesseract globalmente para Windows y Linux
"""

import os
import sys
import platform

# Configurar Tesseract ANTES de importar cualquier módulo que lo use
try:
    import pytesseract
    
    # Detectar el sistema operativo
    sistema = platform.system().lower()
    
    if sistema == "windows":
        # Configuración para Windows
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
            "tesseract"  # Si está en PATH
        ]
        
        tesseract_found = False
        for path in tesseract_paths:
            if os.path.exists(path) or path == "tesseract":
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"✅ Tesseract configurado para Windows: {path}")
                tesseract_found = True
                break
        
        if not tesseract_found:
            print("❌ Tesseract no encontrado en Windows. Instala Tesseract-OCR")
            pytesseract.pytesseract.tesseract_cmd = "tesseract"  # Fallback
            
    else:
        # Configuración para Linux (Docker/producción)
        pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
        print("✅ Tesseract configurado para Linux: /usr/bin/tesseract")
        
except Exception as e:
    print(f"❌ Error configurando Tesseract: {e}")
    # Fallback
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = "tesseract"
    except:
        pass

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
