#!/usr/bin/env python3
"""
Test simple para debuggear la función validar_xades
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from helpers.validacion_xades import validar_xades

# XML de prueba con firma XAdES (simplificado)
xml_test = '''<?xml version="1.0" encoding="utf-8"?>
<factura id="comprobante" version="1.1.0">
  <infoTributaria>
    <ambiente>2</ambiente>
    <tipoEmision>1</tipoEmision>
    <razonSocial>NEXTI BUSINESS SOLUTIONS SA</razonSocial>
    <ruc>1793131336001</ruc>
    <claveAcceso>1509202501179313133600120011010000003661234567811</claveAcceso>
  </infoTributaria>
  <infoFactura>
    <fechaEmision>15/09/2025</fechaEmision>
    <importeTotal>12470.6</importeTotal>
  </infoFactura>
  <ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#" Id="Signature-test">
    <ds:SignedInfo>
      <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315" />
      <ds:SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1" />
      <ds:Reference URI="#comprobante">
        <ds:DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1" />
        <ds:DigestValue>test</ds:DigestValue>
      </ds:Reference>
    </ds:SignedInfo>
    <ds:SignatureValue>test</ds:SignatureValue>
    <ds:KeyInfo>
      <ds:X509Data>
        <ds:X509Certificate>test</ds:X509Certificate>
      </ds:X509Data>
    </ds:KeyInfo>
  </ds:Signature>
</factura>'''

def test_validar_xades():
    print("=== Test validar_xades ===")
    print(f"XML length: {len(xml_test)}")
    
    try:
        resultado = validar_xades(xml_test)
        print(f"Resultado type: {type(resultado)}")
        print(f"Resultado keys: {list(resultado.keys()) if isinstance(resultado, dict) else 'No es dict'}")
        print(f"Resultado: {resultado}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_validar_xades()
