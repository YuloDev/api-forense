#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de la nueva implementación de extracción de clave de acceso
con prioridad de códigos de barras y OCR solo-números
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.invoice_capture_parser import (
    extract_access_key_from_barcode,
    ocr_digits_only,
    validate_access_key,
    try_autocorrect_4_confusions,
    sri_mod11_check_digit,
    parse_capture_from_bytes
)

def test_nueva_implementacion():
    """Test de la nueva implementación"""
    print("🔬 TEST NUEVA IMPLEMENTACIÓN DE CLAVE DE ACCESO")
    print("=" * 60)
    
    # Test con la imagen disponible
    img_path = "helpers/IMG/Captura de pantalla 2025-09-19 120741.png"
    
    if not os.path.exists(img_path):
        print(f"❌ No se encontró la imagen: {img_path}")
        return
    
    print(f"📸 Procesando imagen: {img_path}")
    
    # Leer imagen
    with open(img_path, 'rb') as f:
        img_bytes = f.read()
    
    print(f"📊 Tamaño de imagen: {len(img_bytes)} bytes")
    
    # Test 1: Extracción desde código de barras
    print("\n1️⃣ EXTRACCIÓN DESDE CÓDIGO DE BARRAS")
    print("-" * 40)
    clave_barcode = extract_access_key_from_barcode(img_bytes)
    print(f"Clave desde código de barras: {clave_barcode}")
    
    # Test 2: OCR solo-números
    print("\n2️⃣ OCR SOLO-NÚMEROS")
    print("-" * 40)
    clave_ocr = ocr_digits_only(img_bytes)
    print(f"Clave desde OCR solo-números: {clave_ocr}")
    
    # Test 3: Validación y corrección
    print("\n3️⃣ VALIDACIÓN Y CORRECCIÓN")
    print("-" * 40)
    
    # Probar con la clave del OCR
    if clave_ocr:
        digits = clave_ocr
        print(f"Clave original: {digits}")
        print(f"Longitud: {len(digits)}")
        
        if len(digits) == 48:
            digits = digits + sri_mod11_check_digit(digits)
            print(f"Completando DV: {digits}")
        elif len(digits) == 49:
            if validate_access_key(digits):
                print("✅ Clave ya válida")
            else:
                print("❌ Clave inválida, intentando corrección...")
                fixed = try_autocorrect_4_confusions(digits)
                if fixed:
                    digits = fixed
                    print(f"🔧 Clave corregida: {digits}")
                else:
                    print("❌ No se pudo corregir")
        
        if len(digits) == 49 and validate_access_key(digits):
            print("✅ Clave final válida!")
        else:
            print("❌ Clave final inválida")
    
    # Test 4: Procesamiento completo
    print("\n4️⃣ PROCESAMIENTO COMPLETO")
    print("-" * 40)
    
    try:
        result = parse_capture_from_bytes(img_bytes, "fybeca_factura.png")
        print(f"Clave de acceso final: {result.metadata.access_key}")
        print(f"Clave válida: {validate_access_key(result.metadata.access_key) if result.metadata.access_key else False}")
        
        if result.access_key_parsed:
            print(f"Clave parseada: {result.access_key_parsed}")
        else:
            print("Clave no parseada")
            
    except Exception as e:
        print(f"❌ Error en procesamiento completo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_nueva_implementacion()
