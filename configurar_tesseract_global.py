#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para configurar Tesseract globalmente antes de importar otros módulos
"""

import os
import sys

# Configurar Tesseract ANTES de importar cualquier módulo que lo use
def configurar_tesseract():
    """Configura Tesseract para Windows (desarrollo) y Linux (Docker/producción)"""
    try:
        import pytesseract
        import subprocess
        
        if os.name == 'nt':  # Windows
            tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            tessdata_dir = r"C:\Program Files\Tesseract-OCR\tessdata"
            
            if os.path.exists(tesseract_path):
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                if os.path.exists(tessdata_dir):
                    os.environ["TESSDATA_PREFIX"] = tessdata_dir
                print(f"✅ Tesseract configurado para Windows: {tesseract_path}")
                print(f"✅ TESSDATA_PREFIX configurado: {tessdata_dir}")
            else:
                print("⚠️ Tesseract no encontrado en Windows, usando configuración por defecto")
        else:  # Linux (Docker/producción)
            possible_paths = [
                'tesseract',
                '/usr/bin/tesseract',
                '/usr/local/bin/tesseract',
                '/opt/homebrew/bin/tesseract'  # macOS con Homebrew
            ]
            
            tesseract_found = False
            for path in possible_paths:
                try:
                    result = subprocess.run([path, '--version'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        pytesseract.pytesseract.tesseract_cmd = path
                        print(f"✅ Tesseract configurado para Linux: {path}")
                        tesseract_found = True
                        break
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    continue
            
            if not tesseract_found:
                print("⚠️ Tesseract no encontrado en Linux, usando configuración por defecto")
                pytesseract.pytesseract.tesseract_cmd = 'tesseract'
                
    except Exception as e:
        print(f"❌ Error configurando Tesseract: {e}")

# Ejecutar configuración
configurar_tesseract()

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
