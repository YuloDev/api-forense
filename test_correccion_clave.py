#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar la corrección de la clave de acceso SRI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.invoice_capture_parser import _norm_ocr_text, validate_sri_access_key, parse_sri_access_key

def test_correccion_clave():
    """Prueba la corrección de la clave de acceso"""
    print("🔬 PROBANDO CORRECCIÓN DE CLAVE DE ACCESO")
    print("=" * 60)
    
    # Texto OCR con la clave incorrecta
    texto_ocr = """
    R.U.C.: 1790710319001
    FACTURA No. 026-200-000021384
    NUMERO DE AUTORIZACION
    0807202504179071031900120262000000213845658032318
    AMBIENTE: PRODUCCION
    """
    
    print("📝 Texto OCR original:")
    print(texto_ocr)
    
    # Aplicar normalización
    texto_normalizado = _norm_ocr_text(texto_ocr)
    print("\n🔧 Texto normalizado:")
    print(texto_normalizado)
    
    # Extraer clave de acceso
    from helpers.invoice_capture_parser import extract_sri_access_key
    clave_extraida = extract_sri_access_key(texto_normalizado)
    
    print(f"\n🔑 Clave extraída: {clave_extraida}")
    
    if clave_extraida:
        # Validar clave
        es_valida = validate_sri_access_key(clave_extraida)
        print(f"✅ Clave válida: {es_valida}")
        
        if es_valida:
            # Parsear clave
            parsed = parse_sri_access_key(clave_extraida)
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
            print("❌ La clave no es válida después de la corrección")
            return False
    else:
        print("❌ No se pudo extraer la clave de acceso")
        return False

def test_con_imagen_real():
    """Prueba con la imagen real"""
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
        from helpers.invoice_capture_parser import parse_capture_from_bytes
        result = parse_capture_from_bytes(img_bytes, os.path.basename(img_path))
        
        print(f"\n📋 RESULTADO DEL PARSING:")
        print(f"   - Clave acceso: {result.metadata.access_key}")
        
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
        
        return True
        
    except Exception as e:
        print(f"❌ Error procesando imagen: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

def main():
    print("🔬 TEST CORRECCIÓN DE CLAVE DE ACCESO SRI")
    print("=" * 80)
    
    # Probar corrección de clave
    success1 = test_correccion_clave()
    
    # Probar con imagen real
    success2 = test_con_imagen_real()
    
    print("\n" + "=" * 80)
    print("📊 RESUMEN:")
    print(f"   Corrección de clave: {'✅' if success1 else '❌'}")
    print(f"   Parsing con imagen: {'✅' if success2 else '❌'}")
    
    if success1 and success2:
        print("\n🎉 ¡TODAS LAS PRUEBAS EXITOSAS!")
    else:
        print("\n⚠️  ALGUNAS PRUEBAS FALLARON")

if __name__ == "__main__":
    main()
