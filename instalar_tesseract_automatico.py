#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para instalar Tesseract automáticamente en Windows
Intenta usar winget, choco, o descarga directa
"""

import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from pathlib import Path

def ejecutar_comando(comando, descripcion):
    """Ejecuta un comando y retorna True si fue exitoso"""
    try:
        print(f"🔄 {descripcion}...")
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=300)
        if resultado.returncode == 0:
            print(f"✅ {descripcion} - Exitoso")
            return True
        else:
            print(f"❌ {descripcion} - Error: {resultado.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏰ {descripcion} - Timeout")
        return False
    except Exception as e:
        print(f"❌ {descripcion} - Excepción: {e}")
        return False

def verificar_tesseract_instalado():
    """Verifica si Tesseract ya está instalado"""
    ubicaciones = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
    ]
    
    for ubicacion in ubicaciones:
        if os.path.exists(ubicacion):
            print(f"✅ Tesseract ya está instalado en: {ubicacion}")
            return ubicacion
    
    return None

def instalar_con_winget():
    """Intenta instalar Tesseract con winget"""
    return ejecutar_comando(
        "winget install UB-Mannheim.TesseractOCR",
        "Instalando Tesseract con winget"
    )

def instalar_con_choco():
    """Intenta instalar Tesseract con Chocolatey"""
    return ejecutar_comando(
        "choco install tesseract -y",
        "Instalando Tesseract con Chocolatey"
    )

def instalar_con_scoop():
    """Intenta instalar Tesseract con Scoop"""
    return ejecutar_comando(
        "scoop install tesseract",
        "Instalando Tesseract con Scoop"
    )

def descargar_e_instalar_manual():
    """Descarga e instala Tesseract manualmente"""
    print("📥 Descargando Tesseract manualmente...")
    
    # URL de descarga (versión estable)
    url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
    archivo_instalador = "tesseract-installer.exe"
    
    try:
        print("🔄 Descargando instalador...")
        urllib.request.urlretrieve(url, archivo_instalador)
        print("✅ Descarga completada")
        
        print("🔄 Ejecutando instalador...")
        print("⚠️  IMPORTANTE: Durante la instalación, asegúrate de:")
        print("   1. Instalar en la ubicación por defecto")
        print("   2. Marcar 'Add to PATH' si aparece la opción")
        print("   3. Instalar los datos de idioma (español)")
        
        # Ejecutar instalador
        resultado = subprocess.run([archivo_instalador, "/S"], shell=True)
        
        if resultado.returncode == 0:
            print("✅ Instalador ejecutado exitosamente")
            return True
        else:
            print("❌ Error ejecutando instalador")
            return False
            
    except Exception as e:
        print(f"❌ Error en descarga manual: {e}")
        return False
    finally:
        # Limpiar archivo temporal
        if os.path.exists(archivo_instalador):
            os.remove(archivo_instalador)

def verificar_idiomas():
    """Verifica que los idiomas necesarios estén instalados"""
    ubicacion_tesseract = verificar_tesseract_instalado()
    if not ubicacion_tesseract:
        return False
    
    tessdata_dir = os.path.join(os.path.dirname(ubicacion_tesseract), "tessdata")
    idiomas_requeridos = ["spa.traineddata", "eng.traineddata"]
    
    print("🔍 Verificando idiomas instalados...")
    idiomas_faltantes = []
    
    for idioma in idiomas_requeridos:
        ruta_idioma = os.path.join(tessdata_dir, idioma)
        if os.path.exists(ruta_idioma):
            print(f"✅ {idioma} - Instalado")
        else:
            print(f"❌ {idioma} - Faltante")
            idiomas_faltantes.append(idioma)
    
    if idiomas_faltantes:
        print(f"⚠️  Idiomas faltantes: {', '.join(idiomas_faltantes)}")
        print("📋 Para instalar idiomas:")
        print("   1. Descarga desde: https://github.com/tesseract-ocr/tessdata")
        print("   2. Copia a:", tessdata_dir)
        return False
    
    return True

def main():
    print("🔧 INSTALADOR AUTOMÁTICO DE TESSERACT")
    print("=" * 50)
    
    # Verificar si ya está instalado
    ubicacion = verificar_tesseract_instalado()
    if ubicacion:
        if verificar_idiomas():
            print("🎉 Tesseract ya está instalado y configurado correctamente!")
            return True
        else:
            print("⚠️  Tesseract instalado pero faltan idiomas")
    
    print("🚀 Iniciando instalación...")
    
    # Intentar diferentes métodos de instalación
    metodos = [
        ("winget", instalar_con_winget),
        ("chocolatey", instalar_con_choco),
        ("scoop", instalar_con_scoop),
        ("descarga manual", descargar_e_instalar_manual)
    ]
    
    for nombre, metodo in metodos:
        print(f"\n🔄 Intentando con {nombre}...")
        if metodo():
            # Verificar instalación
            ubicacion = verificar_tesseract_instalado()
            if ubicacion:
                print(f"✅ Tesseract instalado exitosamente con {nombre}")
                if verificar_idiomas():
                    print("🎉 Instalación completa!")
                    return True
                else:
                    print("⚠️  Instalado pero faltan idiomas")
                    break
            else:
                print(f"❌ {nombre} no funcionó correctamente")
        else:
            print(f"❌ {nombre} falló")
    
    print("\n📋 INSTALACIÓN MANUAL REQUERIDA")
    print("=" * 40)
    print("1. Descarga Tesseract desde:")
    print("   https://github.com/UB-Mannheim/tesseract/wiki")
    print("2. Instala en ubicación por defecto")
    print("3. Asegúrate de instalar idioma español")
    print("4. Reinicia tu terminal/IDE")
    
    return False

if __name__ == "__main__":
    main()
