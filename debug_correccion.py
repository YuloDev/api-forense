#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para debuggear la corrección de clave de acceso
"""

import re

def _norm_ocr_text_debug(t: str) -> str:
    print(f"🔍 Texto original: {t}")
    
    # Corregir confusiones comunes del OCR
    replacements = {
        'O': '0', 'o': '0', 'S': '5', 's': '5', 'I': '1', 'l': '1', '|': '1', 'B': '8',
        ''': '', ''': '', '"': '', '"': '', '«': '', '»': '', '·': '', '—': '-', '–': '-'
    }
    
    for old, new in replacements.items():
        t = t.replace(old, new)
    
    print(f"🔧 Después de replacements básicos: {t}")
    
    # Corrección específica para claves de acceso SRI
    # Buscar secuencias de 49 dígitos que podrían ser claves de acceso
    clave_pattern = r'\d{49}'
    matches = re.findall(clave_pattern, t)
    
    print(f"🔍 Claves encontradas: {matches}")
    
    for clave in matches:
        print(f"🔍 Procesando clave: {clave}")
        # Verificar si es una clave de acceso SRI válida
        if len(clave) == 49 and clave.isdigit():
            # Extraer componentes
            fecha = clave[0:8]
            ruc = clave[8:21]
            resto = clave[21:]
            
            print(f"🔍 Fecha: {fecha}")
            print(f"🔍 RUC: {ruc}")
            print(f"🔍 Resto: {resto}")
            
            # Verificar si el RUC empieza con 1790 (común en Ecuador)
            # También verificar si empieza con 041790 (confusión común del OCR)
            if ruc.startswith('1790') or ruc.startswith('041790'):
                print(f"🔍 RUC empieza con 1790 o 041790")
                
                # Si empieza con 041790, corregir a 1790
                if ruc.startswith('041790'):
                    ruc_corregido = '1' + ruc[1:]  # Cambiar 0 por 1 al inicio
                    print(f"🔧 Corregido inicio del RUC: {ruc} -> {ruc_corregido}")
                else:
                    ruc_corregido = ruc
                
                # Si el 9no dígito es 4, probablemente debería ser 1
                if len(ruc_corregido) >= 9 and ruc_corregido[8] == '4':
                    ruc_corregido = ruc_corregido[:8] + '1' + ruc_corregido[9:]
                    print(f"🔧 Corregido 9no dígito del RUC: 4 -> 1")
                
                # Aplicar corrección si hubo cambios
                if ruc_corregido != ruc:
                    clave_corregida = fecha + ruc_corregido + resto
                    t = t.replace(clave, clave_corregida)
                    print(f"🔧 Clave completa corregida: {clave} -> {clave_corregida}")
                    break
            else:
                print(f"🔍 RUC no empieza con 1790 o 041790: {ruc}")
        else:
            print(f"🔍 Clave no es válida: len={len(clave)}, isdigit={clave.isdigit()}")
    
    # Eliminar caracteres de ancho cero
    t = re.sub(r'[\u200b\ufeff]', '', t)
    print(f"🔧 Texto final: {t}")
    return t

def test_correccion():
    """Prueba la corrección de la clave de acceso"""
    print("🔬 DEBUGGING CORRECCIÓN DE CLAVE DE ACCESO")
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
    
    # Aplicar normalización con debug
    texto_normalizado = _norm_ocr_text_debug(texto_ocr)
    
    print(f"\n✅ Texto normalizado final:")
    print(texto_normalizado)

if __name__ == "__main__":
    test_correccion()
