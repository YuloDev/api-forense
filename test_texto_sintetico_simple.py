#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Probar solo la detección de texto sintético
"""

import requests
import json
import base64
import os
import fitz

def test_texto_sintetico():
    """Probar solo la detección de texto sintético"""
    print("🔍 PROBANDO DETECCIÓN DE TEXTO SINTÉTICO")
    print("=" * 50)
    
    # Usar la factura PDF
    pdf_path = r"C:\Users\Nexti\sources\api-forense\helpers\IMG\Factura_imagen.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ Archivo no encontrado: {pdf_path}")
        return
    
    # Convertir PDF a imagen
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)  # Zoom 2x
        pix = page.get_pixmap(matrix=mat, alpha=False)
        imagen_bytes = pix.tobytes("jpeg")
        doc.close()
    except Exception as e:
        print(f"❌ Error al convertir PDF a imagen: {e}")
        return

    imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
    
    url = "http://localhost:8001/validar-imagen"
    headers = {"Content-Type": "application/json"}
    payload = {"imagen_base64": imagen_base64}
    
    print(f"✅ PDF convertido a imagen: {len(imagen_bytes)} bytes")

    try:
        print("\n🚀 Enviando petición...")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        print("✅ Petición exitosa.")
        
        # Buscar específicamente el análisis de texto sintético
        analisis_forense = data.get("analisis_forense_profesional", {})
        if analisis_forense:
            texto_sintetico = analisis_forense.get("texto_sintetico", {})
            print("\n🔬 Análisis de Texto Sintético:")
            print(json.dumps(texto_sintetico, indent=2))
            
            if texto_sintetico.get("tiene_texto_sintetico"):
                print("🚨 ¡TEXTO SINTÉTICO DETECTADO!")
            else:
                print("✅ No se detectó texto sintético")
        else:
            print("❌ No se encontró análisis forense en la respuesta")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_texto_sintetico()

