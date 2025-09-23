#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para iniciar el servidor con configuración global de Tesseract
Específicamente para análisis forense
"""

# Configurar Tesseract ANTES de importar cualquier módulo
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

import uvicorn
import sys
import os

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def verificar_tesseract():
    """Verifica que Tesseract esté funcionando correctamente"""
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract versión: {version}")
        return True
    except Exception as e:
        print(f"❌ Error con Tesseract: {e}")
        return False

if __name__ == "__main__":
    print("🚀 INICIANDO SERVIDOR DE ANÁLISIS FORENSE")
    print("=" * 60)
    
    # Verificar Tesseract
    if not verificar_tesseract():
        print("⚠️ Tesseract no está funcionando correctamente")
        print("   El análisis forense puede fallar")
        print("   Verifica la instalación en: C:\\Program Files\\Tesseract-OCR\\tesseract.exe")
    
    print("\n🔧 Configuración del servidor:")
    print("   Host: 0.0.0.0")
    print("   Puerto: 8001")
    print("   Modo: reload (desarrollo)")
    print("   Tesseract: Configurado globalmente")
    
    print("\n📋 Endpoints disponibles:")
    print("   POST /analizar-imagen-forense - Análisis forense completo")
    print("   GET /analisis-forense-info - Información del endpoint")
    print("   GET /health - Estado del servidor")
    
    print("\n🧪 Scripts de prueba:")
    print("   python probar_tesseract_forense.py - Probar Tesseract")
    print("   python probar_analisis_forense.py - Prueba completa")
    print("   python probar_deteccion_texto_superpuesto.py - Probar detección de texto")
    
    print("\n🚀 Iniciando servidor...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
