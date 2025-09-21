#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para configurar Tesseract en Windows
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def encontrar_tesseract_windows():
    """Busca Tesseract en ubicaciones comunes de Windows"""
    ubicaciones_comunes = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
        r"C:\tesseract\tesseract.exe",
        r"C:\Program Files\Python\Scripts\tesseract.exe"
    ]
    
    for ubicacion in ubicaciones_comunes:
        if os.path.exists(ubicacion):
            return ubicacion
    
    return None

def configurar_pytesseract():
    """Configura pytesseract con la ruta de Tesseract"""
    tesseract_path = encontrar_tesseract_windows()
    
    if tesseract_path:
        print(f"✅ Tesseract encontrado en: {tesseract_path}")
        
        # Configurar pytesseract
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print("✅ pytesseract configurado correctamente")
            return True
        except ImportError:
            print("❌ pytesseract no está instalado")
            return False
    else:
        print("❌ Tesseract no encontrado en ubicaciones comunes")
        return False

def instalar_tesseract_automaticamente():
    """Intenta instalar Tesseract automáticamente usando winget o chocolatey"""
    print("🔧 Intentando instalar Tesseract automáticamente...")
    
    # Intentar con winget (Windows 10/11)
    try:
        result = subprocess.run(['winget', 'install', 'UB-Mannheim.TesseractOCR'], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ Tesseract instalado con winget")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Intentar con chocolatey
    try:
        result = subprocess.run(['choco', 'install', 'tesseract'], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ Tesseract instalado con chocolatey")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    print("❌ No se pudo instalar Tesseract automáticamente")
    return False

def descargar_tesseract_manual():
    """Proporciona instrucciones para descargar Tesseract manualmente"""
    print("\n📥 INSTRUCCIONES PARA INSTALAR TESSERACT MANUALMENTE:")
    print("=" * 60)
    print("1. Ve a: https://github.com/UB-Mannheim/tesseract/wiki")
    print("2. Descarga la versión para Windows (64-bit)")
    print("3. Ejecuta el instalador como administrador")
    print("4. Durante la instalación, asegúrate de:")
    print("   - Marcar 'Add to PATH'")
    print("   - Instalar idiomas adicionales (español)")
    print("5. Reinicia la terminal/IDE después de la instalación")
    print("\n🌐 Enlaces directos:")
    print("   - Windows 64-bit: https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe")
    print("   - Windows 32-bit: https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w32-setup-5.3.3.20231005.exe")

def verificar_instalacion():
    """Verifica si Tesseract está funcionando correctamente"""
    try:
        import pytesseract
        from PIL import Image
        import io
        
        # Crear imagen de prueba
        img = Image.new('RGB', (200, 100), color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        
        # Probar OCR
        text = pytesseract.image_to_string(img, lang='eng')
        print("✅ Tesseract está funcionando correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando Tesseract: {e}")
        return False

def main():
    print("🔧 CONFIGURADOR DE TESSERACT PARA WINDOWS")
    print("=" * 50)
    
    # Verificar sistema operativo
    if platform.system() != "Windows":
        print("❌ Este script es solo para Windows")
        return
    
    # Buscar Tesseract existente
    tesseract_path = encontrar_tesseract_windows()
    
    if tesseract_path:
        print(f"✅ Tesseract encontrado en: {tesseract_path}")
        
        # Configurar pytesseract
        if configurar_pytesseract():
            # Verificar funcionamiento
            if verificar_instalacion():
                print("\n🎉 ¡Tesseract está configurado y funcionando!")
                return
            else:
                print("\n⚠️  Tesseract encontrado pero no funciona correctamente")
        else:
            print("\n❌ Error configurando pytesseract")
    else:
        print("❌ Tesseract no encontrado")
        
        # Intentar instalar automáticamente
        if instalar_tesseract_automaticamente():
            # Buscar nuevamente después de la instalación
            tesseract_path = encontrar_tesseract_windows()
            if tesseract_path and configurar_pytesseract():
                if verificar_instalacion():
                    print("\n🎉 ¡Tesseract instalado y configurado correctamente!")
                    return
    
    # Si llegamos aquí, necesitamos instalación manual
    descargar_tesseract_manual()
    
    print("\n" + "=" * 50)
    print("📋 PRÓXIMOS PASOS:")
    print("1. Instala Tesseract siguiendo las instrucciones")
    print("2. Reinicia tu terminal/IDE")
    print("3. Ejecuta: python diagnostico_ocr.py")
    print("4. Si sigue fallando, ejecuta este script nuevamente")

if __name__ == "__main__":
    main()
