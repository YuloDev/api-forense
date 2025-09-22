#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar directamente el parser de facturas PDF
"""

import base64
from helpers.pdf_factura_parser import extraer_datos_factura_pdf

def test_parser_directo():
    """Prueba el parser de facturas PDF directamente"""
    
    # Leer el PDF de prueba
    pdf_path = "helpers/IMG/Factura_imagen.pdf"
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        print(f"✅ PDF leído: {len(pdf_bytes)} bytes")
        
        # Usar el parser directamente
        print("🔍 Ejecutando parser de facturas PDF...")
        datos = extraer_datos_factura_pdf(pdf_bytes)
        
        print(f"\n📊 RESULTADO DEL PARSER:")
        print(f"   RUC: {datos.get('ruc', 'No encontrado')}")
        print(f"   Razón Social: {datos.get('razonSocial', 'No encontrado')}")
        print(f"   Fecha Emisión: {datos.get('fechaEmision', 'No encontrado')}")
        print(f"   Número Factura: {datos.get('numeroFactura', 'No encontrado')}")
        print(f"   Clave Acceso: {datos.get('claveAcceso', 'No encontrado')}")
        print(f"   Total: {datos.get('total', 'No encontrado')}")
        print(f"   Subtotal 0%: {datos.get('subtotal_0', 'No encontrado')}")
        print(f"   Subtotal 15%: {datos.get('subtotal_15', 'No encontrado')}")
        print(f"   IVA 15%: {datos.get('iva_15', 'No encontrado')}")
        
        print(f"\n📝 TEXTO OCR (primeros 500 caracteres):")
        print(f"{datos.get('texto_ocr', '')[:500]}")
        
        print(f"\n🔍 FUENTES:")
        fuentes = datos.get('fuentes', {})
        print(f"   Barcode: {fuentes.get('barcode', False)}")
        print(f"   OCR: {fuentes.get('ocr', False)}")
        print(f"   Claves Barcode: {fuentes.get('claves_barcode', [])}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parser_directo()
