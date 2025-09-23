#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para configurar Tesseract globalmente para Linux (Docker/producción)
"""

import os
import sys

# Configurar Tesseract para Linux (Docker/producción)
def configurar_tesseract():
    """Configura Tesseract para Linux"""
    try:
        import pytesseract
        
        # Configurar para Linux
        pytesseract.pytesseract.tesseract_cmd = 'tesseract'
        print("✅ Tesseract configurado para Linux: tesseract")
                
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
