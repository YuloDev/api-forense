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
    import os
    
    # Configurar ruta de Tesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    # Configurar TESSDATA_PREFIX para que encuentre los archivos de idioma
    tessdata_dir = r"C:\Program Files\Tesseract-OCR\tessdata"
    if os.path.exists(tessdata_dir):
        os.environ["TESSDATA_PREFIX"] = tessdata_dir
        print("✅ Tesseract configurado globalmente")
        print(f"✅ TESSDATA_PREFIX configurado: {tessdata_dir}")
    else:
        print(f"⚠️ Directorio tessdata no encontrado: {tessdata_dir}")
        print("   Verifica que Tesseract esté instalado correctamente")
        
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
