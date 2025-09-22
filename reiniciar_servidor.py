#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para reiniciar el servidor con la configuración correcta de Tesseract
"""

import os
import sys
import subprocess
import time

def reiniciar_servidor():
    """Reinicia el servidor con la configuración correcta"""
    
    print("🔄 REINICIANDO SERVIDOR CON CONFIGURACIÓN CORRECTA")
    print("=" * 60)
    
    # 1. Detener procesos de Python
    print("1️⃣ Deteniendo procesos de Python...")
    try:
        subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                      capture_output=True, text=True)
        print("✅ Procesos de Python detenidos")
    except Exception as e:
        print(f"⚠️ Error deteniendo procesos: {e}")
    
    # 2. Esperar un momento
    print("2️⃣ Esperando 3 segundos...")
    time.sleep(3)
    
    # 3. Verificar que no hay procesos en el puerto 8001
    print("3️⃣ Verificando puerto 8001...")
    try:
        result = subprocess.run(["netstat", "-an"], capture_output=True, text=True)
        if ":8001" in result.stdout:
            print("⚠️ Puerto 8001 aún en uso, esperando...")
            time.sleep(2)
        else:
            print("✅ Puerto 8001 libre")
    except Exception as e:
        print(f"⚠️ Error verificando puerto: {e}")
    
    # 4. Iniciar servidor con configuración correcta
    print("4️⃣ Iniciando servidor con Tesseract configurado...")
    
    # Configurar Tesseract ANTES de importar
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    print("✅ Tesseract configurado")
    
    # Importar y ejecutar
    import uvicorn
    from main import app
    
    print("✅ Servidor iniciado correctamente")
    print("   Host: 127.0.0.1")
    print("   Puerto: 8001")
    print("   Tesseract: ✅ Configurado")
    print("   Modo: reload")
    
    # Ejecutar servidor
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    reiniciar_servidor()
