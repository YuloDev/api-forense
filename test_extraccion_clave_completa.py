#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar la extracción completa de claves de acceso
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.invoice_capture_parser import parse_capture_from_bytes, extract_sri_access_key, validate_sri_access_key, parse_sri_access_key

def test_extraccion_completa():
    """Prueba la extracción completa de claves de acceso"""
    print("🔬 PROBANDO EXTRACCIÓN COMPLETA DE CLAVES DE ACCESO")
    print("=" * 70)
    
    # Buscar imagen de prueba
    img_folder = "helpers/IMG"
    if not os.path.exists(img_folder):
        print(f"❌ Carpeta {img_folder} no existe")
        return False
    
    import glob
    img_files = glob.glob(os.path.join(img_folder, "*.png")) + glob.glob(os.path.join(img_folder, "*.jpg"))
    
    if not img_files:
        print(f"❌ No se encontraron archivos de imagen en {img_folder}")
        return False
    
    img_path = img_files[0]
    print(f"🔄 Procesando: {img_path}")
    
    try:
        # Leer imagen
        with open(img_path, 'rb') as f:
            img_bytes = f.read()
        
        print(f"✅ Imagen leída: {len(img_bytes)} bytes")
        
        # Parsear imagen
        result = parse_capture_from_bytes(img_bytes, os.path.basename(img_path))
        
        print(f"\n📋 RESULTADO DEL PARSING:")
        print(f"   - Clave acceso final: {result.metadata.access_key}")
        print(f"   - RUC: {result.metadata.ruc}")
        print(f"   - Número factura: {result.metadata.invoice_number}")
        print(f"   - Autorización: {result.metadata.authorization}")
        print(f"   - Ambiente: {result.metadata.environment}")
        print(f"   - Fecha emisión: {result.metadata.issue_datetime}")
        print(f"   - Comprador: {result.metadata.buyer_name}")
        print(f"   - ID comprador: {result.metadata.buyer_id}")
        print(f"   - Emisor: {result.metadata.emitter_name}")
        
        # Verificar clave parseada
        if result.access_key_parsed:
            print(f"\n🔑 CLAVE PARSEADA:")
            parsed = result.access_key_parsed
            print(f"   - Válida: {parsed.get('valida', False)}")
            print(f"   - Fecha: {parsed.get('fecha_emision')}")
            print(f"   - RUC: {parsed.get('ruc_emisor')}")
            print(f"   - Tipo: {parsed.get('tipo_comprobante', {}).get('descripcion')}")
            print(f"   - Serie: {parsed.get('serie')}")
            print(f"   - Secuencial: {parsed.get('secuencial')}")
            print(f"   - Emisión: {parsed.get('tipo_emision', {}).get('descripcion')}")
        else:
            print(f"\n🔑 CLAVE PARSEADA: No disponible")
        
        # Verificar códigos de barras
        print(f"\n📊 CÓDIGOS DE BARRAS:")
        print(f"   - Detectados: {len(result.barcodes)}")
        for i, bc in enumerate(result.barcodes, 1):
            print(f"   - {i}. {bc.get('type', 'N/A')}: {bc.get('data', 'N/A')}")
        
        # Verificar validación
        if result.metadata.access_key:
            es_valida = validate_sri_access_key(result.metadata.access_key)
            print(f"\n✅ VALIDACIÓN:")
            print(f"   - Clave válida: {es_valida}")
            if es_valida:
                print(f"   - Longitud correcta: {len(result.metadata.access_key) == 49}")
                print(f"   - Solo dígitos: {result.metadata.access_key.isdigit()}")
            else:
                print(f"   - Clave inválida: {result.metadata.access_key}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error procesando imagen: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def test_extraccion_texto():
    """Prueba la extracción solo del texto OCR"""
    print("\n" + "=" * 70)
    print("🔍 PROBANDO EXTRACCIÓN SOLO DE TEXTO OCR")
    print("=" * 70)
    
    # Texto OCR de prueba
    texto_ocr = """
    R.U.C.: 1790710319001
    FACTURA No. 026-200-000021384
    NUMERO DE AUTORIZACION
    0807202501179071031900120262000000213845658032318
    AMBIENTE: PRODUCCION
    """
    
    print("📝 Texto OCR:")
    print(texto_ocr)
    
    # Extraer clave del texto
    clave_texto = extract_sri_access_key(texto_ocr)
    print(f"\n🔑 Clave extraída del texto: {clave_texto}")
    
    if clave_texto:
        es_valida = validate_sri_access_key(clave_texto)
        print(f"✅ Clave válida: {es_valida}")
        
        if es_valida:
            parsed = parse_sri_access_key(clave_texto)
            print(f"\n📋 CLAVE PARSEADA:")
            print(f"   - Fecha: {parsed.get('fecha_emision')}")
            print(f"   - RUC: {parsed.get('ruc_emisor')}")
            print(f"   - Tipo: {parsed.get('tipo_comprobante', {}).get('descripcion')}")
            print(f"   - Serie: {parsed.get('serie')}")
            print(f"   - Secuencial: {parsed.get('secuencial')}")
            print(f"   - Emisión: {parsed.get('tipo_emision', {}).get('descripcion')}")
    
    return clave_texto is not None

def main():
    print("🔬 TEST EXTRACCIÓN COMPLETA DE CLAVES DE ACCESO")
    print("=" * 80)
    
    # Probar extracción de texto
    success1 = test_extraccion_texto()
    
    # Probar extracción completa
    success2 = test_extraccion_completa()
    
    print("\n" + "=" * 80)
    print("📊 RESUMEN:")
    print(f"   Extracción de texto: {'✅' if success1 else '❌'}")
    print(f"   Extracción completa: {'✅' if success2 else '❌'}")
    
    if success1 and success2:
        print("\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON")

if __name__ == "__main__":
    main()
