#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar localmente el parsing de clave de acceso SRI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.invoice_capture_parser import parse_capture_from_bytes, parse_sri_access_key, validate_sri_access_key

def test_parsing_clave():
    """Prueba el parsing de clave de acceso SRI"""
    print("🔬 PROBANDO PARSING DE CLAVE DE ACCESO SRI")
    print("=" * 60)
    
    # Clave de prueba (de la imagen de Fybeca)
    clave_prueba = "0807202501179071031900120262000000213845658032318"
    
    print(f"🔑 Clave de prueba: {clave_prueba}")
    print(f"   Longitud: {len(clave_prueba)} dígitos")
    
    # Validar clave
    es_valida = validate_sri_access_key(clave_prueba)
    print(f"✅ Clave válida: {es_valida}")
    
    if es_valida:
        # Parsear clave
        parsed = parse_sri_access_key(clave_prueba)
        print(f"\n📋 CLAVE PARSEADA:")
        print(f"   - Válida: {parsed.get('valida', False)}")
        print(f"   - Fecha emisión: {parsed.get('fecha_emision')}")
        print(f"   - RUC emisor: {parsed.get('ruc_emisor')}")
        print(f"   - Tipo comprobante: {parsed.get('tipo_comprobante', {}).get('descripcion')}")
        print(f"   - Serie: {parsed.get('serie')}")
        print(f"   - Secuencial: {parsed.get('secuencial')}")
        print(f"   - Tipo emisión: {parsed.get('tipo_emision', {}).get('descripcion')}")
        print(f"   - Código numérico: {parsed.get('codigo_numerico')}")
        print(f"   - Dígito verificador: {parsed.get('digito_verificador')}")
        
        # Verificar que los datos son correctos
        print(f"\n🔍 VERIFICACIÓN:")
        print(f"   - Fecha: {parsed.get('fecha_emision')} (debería ser 2025-07-08)")
        print(f"   - RUC: {parsed.get('ruc_emisor')} (debería ser 1790710319001)")
        print(f"   - Tipo: {parsed.get('tipo_comprobante', {}).get('descripcion')} (debería ser Factura)")
        print(f"   - Serie: {parsed.get('serie')} (debería ser 026)")
        print(f"   - Secuencial: {parsed.get('secuencial')} (debería ser 200000021384)")
        print(f"   - Emisión: {parsed.get('tipo_emision', {}).get('descripcion')} (debería ser Normal)")
        
        return True
    else:
        print("❌ La clave no es válida")
        return False

def test_con_imagen():
    """Prueba el parsing con una imagen real"""
    print("\n" + "=" * 60)
    print("🖼️  PROBANDO CON IMAGEN REAL")
    print("=" * 60)
    
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
        print(f"   - RUC: {result.metadata.ruc}")
        print(f"   - Número factura: {result.metadata.invoice_number}")
        print(f"   - Autorización: {result.metadata.authorization}")
        print(f"   - Clave acceso: {result.metadata.access_key}")
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
        
        return True
        
    except Exception as e:
        print(f"❌ Error procesando imagen: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def main():
    print("🔬 TEST PARSING DE CLAVE DE ACCESO SRI")
    print("=" * 80)
    
    # Probar parsing de clave
    success1 = test_parsing_clave()
    
    # Probar con imagen
    success2 = test_con_imagen()
    
    print("\n" + "=" * 80)
    print("📊 RESUMEN:")
    print(f"   Parsing de clave: {'✅' if success1 else '❌'}")
    print(f"   Parsing con imagen: {'✅' if success2 else '❌'}")
    
    if success1 and success2:
        print("\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON")

if __name__ == "__main__":
    main()
