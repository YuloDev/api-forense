#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de prueba específico para las mejoras de OCR
"""

import base64
import io
from PIL import Image, ImageDraw, ImageFont
from helpers.invoice_capture_parser import ocr_image, enhance_for_ocr, flatten_rgba_to_white

def crear_imagen_prueba_rgba():
    """Crea una imagen PNG RGBA con transparencia para probar el aplanado"""
    # Crear imagen RGBA con transparencia
    img = Image.new('RGBA', (400, 300), (255, 255, 255, 0))  # Transparente
    
    # Dibujar texto en la imagen
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Texto de prueba
    draw.text((20, 50), "FACTURA No. 001-001-000123456", fill=(0, 0, 0, 255), font=font)
    draw.text((20, 80), "RUC: 1234567890001", fill=(0, 0, 0, 255), font=font)
    draw.text((20, 110), "TOTAL: $115.00", fill=(0, 0, 0, 255), font=font)
    
    return img

def crear_imagen_baja_resolucion():
    """Crea una imagen de baja resolución para probar el escalado"""
    # Imagen pequeña (simula captura de baja resolución)
    img = Image.new('RGB', (200, 300), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 12)  # Fuente pequeña
    except:
        font = ImageFont.load_default()
    
    # Texto pequeño
    draw.text((10, 20), "FARMACIAS FYBECA", fill='black', font=font)
    draw.text((10, 40), "RUC: 1234567890001", fill='black', font=font)
    draw.text((10, 60), "FACTURA No. 001-001-000123456", fill='black', font=font)
    draw.text((10, 80), "Clave de Acceso:", fill='black', font=font)
    draw.text((10, 100), "1234567890123456789012345678901234567890123456789", fill='black', font=font)
    draw.text((10, 120), "Fecha: 2024-01-15 10:30:00", fill='black', font=font)
    draw.text((10, 150), "SUBTOTAL 15%: $100.00", fill='black', font=font)
    draw.text((10, 170), "IVA 15%: $15.00", fill='black', font=font)
    draw.text((10, 190), "TOTAL: $115.00", fill='black', font=font)
    
    return img

def probar_aplanado_rgba():
    """Prueba el aplanado de transparencia RGBA"""
    print("🧪 Probando aplanado RGBA...")
    
    # Crear imagen RGBA
    img_rgba = crear_imagen_prueba_rgba()
    print(f"   Imagen original: {img_rgba.mode} {img_rgba.size}")
    
    # Aplanar a fondo blanco
    img_flattened = flatten_rgba_to_white(img_rgba)
    print(f"   Imagen aplanada: {img_flattened.mode} {img_flattened.size}")
    
    # Probar OCR en ambas
    print("   Probando OCR en imagen RGBA original...")
    text_original = ocr_image(img_rgba)
    print(f"   Caracteres extraídos (original): {len(text_original)}")
    
    print("   Probando OCR en imagen aplanada...")
    text_flattened = ocr_image(img_flattened)
    print(f"   Caracteres extraídos (aplanada): {len(text_flattened)}")
    
    if len(text_flattened) > len(text_original):
        print("   ✅ Aplanado mejoró la extracción de texto")
    else:
        print("   ⚠️  Aplanado no mejoró significativamente")
    
    return text_flattened

def probar_escalado():
    """Prueba el escalado de imagen para mejorar OCR"""
    print("\n🔍 Probando escalado de imagen...")
    
    # Crear imagen de baja resolución
    img_small = crear_imagen_baja_resolucion()
    print(f"   Imagen original: {img_small.size}")
    
    # Probar OCR sin escalado
    print("   Probando OCR sin escalado...")
    text_original = ocr_image(img_small)
    print(f"   Caracteres extraídos (sin escalado): {len(text_original)}")
    
    # Probar con escalado manual
    print("   Probando con escalado manual...")
    img_scaled = img_small.resize((img_small.width * 3, img_small.height * 3), Image.LANCZOS)
    text_scaled = ocr_image(img_scaled)
    print(f"   Caracteres extraídos (escalado 3x): {len(text_scaled)}")
    
    if len(text_scaled) > len(text_original):
        print("   ✅ Escalado mejoró la extracción de texto")
    else:
        print("   ⚠️  Escalado no mejoró significativamente")
    
    return text_scaled

def probar_mejoras_combinadas():
    """Prueba todas las mejoras combinadas"""
    print("\n🚀 Probando mejoras combinadas...")
    
    # Crear imagen RGBA de baja resolución (caso más problemático)
    img = Image.new('RGBA', (150, 200), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 10)  # Fuente muy pequeña
    except:
        font = ImageFont.load_default()
    
    # Texto pequeño con transparencia
    draw.text((5, 10), "FACTURA No. 001-001-000123456", fill=(0, 0, 0, 200), font=font)
    draw.text((5, 25), "RUC: 1234567890001", fill=(0, 0, 0, 200), font=font)
    draw.text((5, 40), "TOTAL: $115.00", fill=(0, 0, 0, 200), font=font)
    draw.text((5, 55), "SUBTOTAL 15%: $100.00", fill=(0, 0, 0, 200), font=font)
    draw.text((5, 70), "IVA 15%: $15.00", fill=(0, 0, 0, 200), font=font)
    
    print(f"   Imagen problemática: {img.mode} {img.size}")
    
    # Probar OCR con mejoras
    text_mejorado = ocr_image(img)
    print(f"   Caracteres extraídos (con mejoras): {len(text_mejorado)}")
    
    if len(text_mejorado) > 20:
        print("   ✅ Mejoras combinadas funcionan correctamente")
        print(f"   Texto extraído: '{text_mejorado[:100]}...'")
    else:
        print("   ⚠️  Mejoras no fueron suficientes para esta imagen")
    
    return text_mejorado

def probar_diferentes_configuraciones():
    """Prueba diferentes configuraciones de Tesseract"""
    print("\n⚙️  Probando diferentes configuraciones...")
    
    img = crear_imagen_baja_resolucion()
    
    # Probar diferentes escalas
    escalas = [1.0, 2.0, 2.5, 3.0]
    mejores_resultados = []
    
    for escala in escalas:
        print(f"   Probando escala {escala}x...")
        img_mejorada = enhance_for_ocr(img, scale=escala)
        text = ocr_image(img)
        caracteres = len(text.strip())
        mejores_resultados.append((escala, caracteres, text[:50]))
        print(f"     Caracteres: {caracteres}")
    
    # Encontrar la mejor escala
    mejor_escala, mejor_caracteres, mejor_texto = max(mejores_resultados, key=lambda x: x[1])
    print(f"   ✅ Mejor escala: {mejor_escala}x con {mejor_caracteres} caracteres")
    print(f"   Mejor texto: '{mejor_texto}...'")

def main():
    print("🔬 PRUEBAS DE MEJORAS DE OCR")
    print("=" * 40)
    
    # Probar aplanado RGBA
    text_rgba = probar_aplanado_rgba()
    
    # Probar escalado
    text_escalado = probar_escalado()
    
    # Probar mejoras combinadas
    text_combinado = probar_mejoras_combinadas()
    
    # Probar diferentes configuraciones
    probar_diferentes_configuraciones()
    
    print("\n" + "=" * 40)
    print("📊 RESUMEN DE RESULTADOS:")
    print(f"   RGBA aplanado: {len(text_rgba)} caracteres")
    print(f"   Escalado: {len(text_escalado)} caracteres")
    print(f"   Combinado: {len(text_combinado)} caracteres")
    
    if len(text_combinado) > 50:
        print("\n🎉 ¡Las mejoras de OCR están funcionando correctamente!")
    else:
        print("\n⚠️  Las mejoras pueden necesitar ajustes adicionales")

if __name__ == "__main__":
    main()
