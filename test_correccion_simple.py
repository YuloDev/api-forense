#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script simple para probar la corrección de clave de acceso
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.invoice_capture_parser import _norm_ocr_text, validate_sri_access_key, parse_sri_access_key

def test_correccion_simple():
    """Prueba la corrección simple de clave de acceso"""
    print("🔬 PROBANDO CORRECCIÓN SIMPLE DE CLAVE DE ACCESO")
    print("=" * 60)
    
    # Texto OCR con la clave incorrecta (como en la imagen real)
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
    print(f"\n🔧 Texto normalizado:")
    print(texto_normalizado)
    
    # Extraer clave de acceso del texto normalizado
    import re
    clave_pattern = r'\d{49}'
    matches = re.findall(clave_pattern, texto_normalizado)
    
    if matches:
        clave_extraida = matches[0]
        print(f"\n🔑 Clave extraída: {clave_extraida}")
        
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
            
            return True
        else:
            print("❌ La clave no es válida después de la corrección")
            return False
    else:
        print("❌ No se encontró clave de acceso en el texto")
        return False

def main():
    print("🔬 TEST CORRECCIÓN SIMPLE DE CLAVE DE ACCESO")
    print("=" * 80)
    
    # Probar corrección
    success = test_correccion_simple()
    
    print("\n" + "=" * 80)
    print("📊 RESUMEN:")
    print(f"   Corrección: {'✅' if success else '❌'}")
    
    if success:
        print("\n🎉 ¡CORRECCIÓN EXITOSA!")
    else:
        print("\n⚠️  LA CORRECCIÓN FALLÓ")

if __name__ == "__main__":
    main()
