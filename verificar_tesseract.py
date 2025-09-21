#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script simple para verificar si Tesseract está funcionando
"""

def verificar_tesseract():
    """Verifica si Tesseract está instalado y funcionando"""
    print("🔍 VERIFICANDO TESSERACT")
    print("=" * 30)
    
    try:
        import pytesseract
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        print("✅ pytesseract importado correctamente")
        
        # Crear imagen de prueba simple
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((20, 30), "HELLO WORLD", fill='black', font=font)
        draw.text((20, 60), "123456789", fill='black', font=font)
        
        print("✅ Imagen de prueba creada")
        
        # Probar OCR básico
        try:
            text = pytesseract.image_to_string(img, lang='eng')
            print(f"✅ OCR funcionando: '{text.strip()}'")
            
            if len(text.strip()) > 5:
                print("🎉 Tesseract está funcionando correctamente")
                return True
            else:
                print("⚠️  Tesseract extrajo poco texto")
                return False
                
        except Exception as e:
            print(f"❌ Error en OCR: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Error importando: {e}")
        return False

def verificar_configuracion_windows():
    """Verifica la configuración específica de Windows"""
    print("\n🔧 VERIFICANDO CONFIGURACIÓN WINDOWS")
    print("=" * 40)
    
    try:
        import pytesseract
        import os
        
        # Verificar si pytesseract tiene la ruta configurada
        tesseract_cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', None)
        print(f"   Comando Tesseract: {tesseract_cmd}")
        
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            print("✅ Ruta de Tesseract configurada y existe")
            return True
        else:
            print("⚠️  Ruta de Tesseract no configurada o no existe")
            
            # Buscar Tesseract en ubicaciones comunes
            ubicaciones = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\{}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME', '')),
            ]
            
            for ubicacion in ubicaciones:
                if os.path.exists(ubicacion):
                    print(f"✅ Tesseract encontrado en: {ubicacion}")
                    pytesseract.pytesseract.tesseract_cmd = ubicacion
                    return True
            
            print("❌ Tesseract no encontrado en ubicaciones comunes")
            return False
            
    except Exception as e:
        print(f"❌ Error verificando configuración: {e}")
        return False

def main():
    print("🔍 VERIFICACIÓN COMPLETA DE TESSERACT")
    print("=" * 50)
    
    # Verificar configuración
    config_ok = verificar_configuracion_windows()
    
    # Verificar funcionamiento
    funcionamiento_ok = verificar_tesseract()
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN:")
    print(f"   Configuración: {'✅' if config_ok else '❌'}")
    print(f"   Funcionamiento: {'✅' if funcionamiento_ok else '❌'}")
    
    if config_ok and funcionamiento_ok:
        print("\n🎉 ¡Tesseract está funcionando perfectamente!")
    else:
        print("\n⚠️  Tesseract necesita configuración")
        print("\n📋 SOLUCIONES:")
        
        if not config_ok:
            print("1. Instalar Tesseract:")
            print("   - Descargar de: https://github.com/UB-Mannheim/tesseract/wiki")
            print("   - O ejecutar: python configurar_tesseract_windows.py")
        
        if not funcionamiento_ok:
            print("2. Verificar idiomas instalados:")
            print("   - Ejecutar: tesseract --list-langs")
            print("   - Instalar español si es necesario")
        
        print("3. Reiniciar terminal/IDE después de instalar")

if __name__ == "__main__":
    main()
