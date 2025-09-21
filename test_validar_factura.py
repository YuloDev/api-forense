#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para probar el endpoint validar_factura
"""

import requests
import json
import os

def test_validar_factura():
    """Prueba el endpoint validar_factura con un PDF de prueba"""
    print("🔬 PROBANDO ENDPOINT VALIDAR_FACTURA")
    print("=" * 50)
    
    # URL del endpoint
    url = "http://localhost:8001/validar-factura"
    
    # Buscar un PDF de prueba en la carpeta helpers/IMG
    pdf_folder = "helpers/IMG"
    if not os.path.exists(pdf_folder):
        print(f"❌ Carpeta {pdf_folder} no existe")
        return False
    
    # Buscar archivos PDF
    import glob
    pdf_files = glob.glob(os.path.join(pdf_folder, "*.pdf"))
    
    if not pdf_files:
        print(f"❌ No se encontraron archivos PDF en {pdf_folder}")
        print("   Archivos soportados: .pdf")
        return False
    
    print(f"✅ Encontrados {len(pdf_files)} archivos PDF:")
    for i, file in enumerate(pdf_files, 1):
        print(f"   {i}. {file}")
    
    # Usar el primer archivo encontrado
    pdf_path = pdf_files[0]
    print(f"\n🔄 Procesando: {pdf_path}")
    
    try:
        # Leer el PDF
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        print(f"✅ PDF leído: {len(pdf_bytes)} bytes")
        
        # Preparar request
        files = {
            'archivo': ('test.pdf', pdf_bytes, 'application/pdf')
        }
        data = {
            'validar_sri': True
        }
        
        print("📡 Enviando request al endpoint...")
        response = requests.post(url, files=files, data=data, timeout=120)
        
        if response.status_code == 200:
            print("✅ Request exitoso")
            data = response.json()
            
            # Verificar campos principales
            print(f"\n📋 RESULTADOS:")
            print(f"   - SRI Verificado: {data.get('sri_verificado', False)}")
            print(f"   - Tipo Archivo: {data.get('tipo_archivo', 'N/A')}")
            print(f"   - Coincidencia: {data.get('coincidencia', 'N/A')}")
            
            # Verificar factura
            factura = data.get("factura", {})
            print(f"\n📄 CAMPOS DE FACTURA:")
            print(f"   - RUC: {factura.get('ruc')}")
            print(f"   - Razón Social: {factura.get('razonSocial')}")
            print(f"   - Fecha Emisión: {factura.get('fechaEmision')}")
            print(f"   - Total: {factura.get('importeTotal')}")
            print(f"   - Clave Acceso: {factura.get('claveAcceso')}")
            
            # Verificar parser avanzado
            parser_avanzado = data.get("parser_avanzado", {})
            print(f"\n🔍 PARSER AVANZADO:")
            print(f"   - Disponible: {parser_avanzado.get('disponible', False)}")
            print(f"   - Barcodes detectados: {parser_avanzado.get('barcodes_detectados', 0)}")
            print(f"   - Items detectados: {parser_avanzado.get('items_detectados', 0)}")
            
            # Verificar metadatos avanzados
            metadatos = parser_avanzado.get('metadatos_avanzados', {})
            print(f"\n📊 METADATOS AVANZADOS:")
            print(f"   - Páginas procesadas: {metadatos.get('pages_processed', 0)}")
            print(f"   - Métodos de texto: {metadatos.get('text_methods', [])}")
            print(f"   - Longitud texto: {metadatos.get('text_length', 0)}")
            print(f"   - Clave acceso encontrada: {metadatos.get('access_key_found', False)}")
            print(f"   - Códigos de barras encontrados: {metadatos.get('barcodes_found', False)}")
            
            # Verificar riesgo
            riesgo = data.get("riesgo", {})
            print(f"\n⚠️  ANÁLISIS DE RIESGO:")
            print(f"   - Score: {riesgo.get('score', 0)}")
            print(f"   - Nivel: {riesgo.get('nivel', 'N/A')}")
            print(f"   - Es falso probable: {riesgo.get('es_falso_probable', False)}")
            
            # Verificar texto extraído
            texto_extraido = data.get("texto_extraido", "")
            print(f"\n📝 TEXTO EXTRAÍDO:")
            print(f"   - Longitud: {len(texto_extraido)} caracteres")
            print(f"   - Primeros 300 chars: {texto_extraido[:300]}...")
            
            return True
            
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error en request: {e}")
        return False

def main():
    print("🔬 TEST ENDPOINT VALIDAR_FACTURA")
    print("=" * 60)
    
    # Probar endpoint
    success = test_validar_factura()
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN:")
    print(f"   Endpoint: {'✅' if success else '❌'}")
    
    if not success:
        print("\n⚠️  PROBLEMAS:")
        print("   - Verificar que el servidor esté ejecutándose")
        print("   - Verificar que haya archivos PDF en helpers/IMG/")
        print("   - Revisar logs del servidor")
    else:
        print("\n🎉 ¡ENDPOINT FUNCIONANDO CORRECTAMENTE!")

if __name__ == "__main__":
    main()

