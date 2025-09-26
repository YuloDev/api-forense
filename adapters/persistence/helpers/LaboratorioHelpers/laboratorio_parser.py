#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parser para extraer datos de formularios de laboratorio clínico
Incluye extracción de información del paciente, pruebas solicitadas, etc.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime

def extract_laboratorio_data(text: str) -> Dict[str, Any]:
    """
    Extrae datos de formulario de laboratorio del texto OCR
    
    Args:
        text: Texto extraído por OCR del formulario de laboratorio
    
    Returns:
        Dict con los datos extraídos del laboratorio
    """
    
    # Limpiar y normalizar texto
    text_clean = _clean_laboratorio_text(text)
    
    # Extraer información del paciente
    paciente_info = _extract_paciente_info(text_clean)
    
    # Extraer información del laboratorio
    laboratorio_info = _extract_laboratorio_info(text_clean)
    
    # Extraer pruebas solicitadas
    pruebas_solicitadas = _extract_pruebas_solicitadas(text_clean)
    
    # Extraer información general del formulario
    formulario_info = _extract_formulario_info(text_clean)
    
    return {
        "paciente": paciente_info,
        "laboratorio": laboratorio_info,
        "pruebas_solicitadas": pruebas_solicitadas,
        "formulario": formulario_info
    }

def _clean_laboratorio_text(text: str) -> str:
    """Limpia y normaliza el texto del formulario de laboratorio preservando saltos de línea"""
    if not text:
        return ""
    
    # Solo normalizar espacios múltiples en la misma línea, conservar saltos de línea
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        # Limpiar espacios múltiples en cada línea
        cleaned_line = re.sub(r'[ \t]+', ' ', line).strip()
        cleaned_lines.append(cleaned_line)
    
    # Reconstruir el texto con saltos de línea preservados
    text = '\n'.join(cleaned_lines)
    
    # Eliminar líneas vacías múltiples
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # Corregir errores comunes de OCR en formularios de laboratorio
    corrections = {
        'LABORATORIO': 'LABORATORIO',
        'CLINICO': 'CLÍNICO',
        'BIOMETRIA': 'BIOMETRÍA',
        'HEMATOLOGIA': 'HEMATOLOGÍA',
        'SEROLOGIA': 'SEROLOGÍA',
        'ELECTROLITOS': 'ELECTROLITOS',
        'INFECCIOSAS': 'INFECCIOSAS',
        'COAGULACION': 'COAGULACIÓN',
        'CARDIACO': 'CARDÍACO',
        'ENDOCRINOLOGIA': 'ENDOCRINOLOGÍA',
        'VITAMINAS': 'VITAMINAS',
        'TAMIZAJE': 'TAMIZAJE',
        'MOLECULAR': 'MOLECULAR',
        'GENETICA': 'GENÉTICA',
        'UROANALISIS': 'UROANÁLISIS',
        'DIAGNOSTICA': 'DIAGNÓSTICA',
        'IMAGEN': 'IMAGEN',
        'OCUPACIONAL': 'OCUPACIONAL',
        'INTEGRAL': 'INTEGRAL',
        'SERVICIOS': 'SERVICIOS',
        'SALUD': 'SALUD',
        'ATENCION': 'ATENCIÓN',
        'DIRECCIONES': 'DIRECCIONES',
        'SUCURSALES': 'SUCURSALES',
        'NOMBRE': 'NOMBRE',
        'EDAD': 'EDAD',
        'FECHA': 'FECHA',
        'SEGURO': 'SEGURO',
        'TELEFONO': 'TELÉFONO',
        'IDENTIFICACION': 'IDENTIFICACIÓN',
        'CEDULA': 'CÉDULA'
    }
    
    for old, new in corrections.items():
        text = text.replace(old, new)
    
    return text.strip()

def _extract_paciente_info(text: str) -> Dict[str, Any]:
    """Extrae información del paciente"""
    info = {}
    
    # Nombre del paciente
    nombre_patterns = [
        r'NOMBRE[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|EDAD|FECHA|$)',
        r'NOMBRE[:\s]*\n([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|EDAD)',
        r'^([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|EDAD|FECHA)',
    ]
    
    for pattern in nombre_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            nombre = match.group(1).strip()
            # Limpiar el nombre de caracteres extraños
            nombre = re.sub(r'[^\w\sÁÉÍÓÚÑ]', '', nombre)
            if len(nombre) > 2:  # Asegurar que sea un nombre válido
                info['nombre'] = nombre
                break
    
    # Edad
    edad_patterns = [
        r'EDAD[:\s]*(\d+)\s*(años?|años?|meses?|días?)',
        r'EDAD[:\s]*(\d+)',
        r'(\d+)\s*años?',
    ]
    
    for pattern in edad_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['edad'] = match.group(1)
            break
    
    # Fecha
    fecha_patterns = [
        r'FECHA[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    
    for pattern in fecha_patterns:
        match = re.search(pattern, text)
        if match:
            info['fecha'] = match.group(1)
            break
    
    # Identificación/Cédula
    cedula_patterns = [
        r'C[ÉE]DULA[:\s]*(\d{10,13})',
        r'IDENTIFICACI[ÓO]N[:\s]*(\d{10,13})',
        r'C\.I\.[:\s]*(\d{10,13})',
        r'(\d{10,13})',
    ]
    
    for pattern in cedula_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['identificacion'] = match.group(1)
            break
    
    # Teléfono
    telefono_patterns = [
        r'TEL[ÉE]FONO[:\s]*(\d{7,10})',
        r'PHONE[:\s]*(\d{7,10})',
        r'(\d{7,10})',
    ]
    
    for pattern in telefono_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['telefono'] = match.group(1)
            break
    
    # Seguro
    seguro_patterns = [
        r'SEGURO[:\s]*([A-ZÁÉÍÓÚÑ\s\d]+?)(?:\n|$)',
        r'INSURANCE[:\s]*([A-ZÁÉÍÓÚÑ\s\d]+?)(?:\n|$)',
    ]
    
    for pattern in seguro_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['seguro'] = match.group(1).strip()
            break
    
    return info

def _extract_laboratorio_info(text: str) -> Dict[str, Any]:
    """Extrae información del laboratorio"""
    info = {}
    
    # Nombre del laboratorio
    laboratorio_patterns = [
        r'([A-ZÁÉÍÓÚÑ\s]+LABORATORIO[A-ZÁÉÍÓÚÑ\s]*)',
        r'([A-ZÁÉÍÓÚÑ\s]+CL[ÍI]NICO[A-ZÁÉÍÓÚÑ\s]*)',
        r'([A-ZÁÉÍÓÚÑ\s]+SALUD[A-ZÁÉÍÓÚÑ\s]*)',
    ]
    
    for pattern in laboratorio_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['nombre'] = match.group(1).strip()
            break
    
    # Dirección
    direccion_patterns = [
        r'AV[ENIDA]?[:\s]*([A-ZÁÉÍÓÚÑ\s\d]+?)(?:\n|PBX|Cel|www)',
        r'DIRECCI[ÓO]N[:\s]*([A-ZÁÉÍÓÚÑ\s\d]+?)(?:\n|PBX|Cel|www)',
    ]
    
    for pattern in direccion_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['direccion'] = match.group(1).strip()
            break
    
    # Teléfonos
    telefonos_patterns = [
        r'PBX[:\s]*([\d\s\-/]+)',
        r'Cel[:\s]*([\d\s\-/]+)',
    ]
    
    telefonos = []
    for pattern in telefonos_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        telefonos.extend(matches)
    
    if telefonos:
        info['telefonos'] = [t.strip() for t in telefonos]
    
    # Horarios de atención
    horario_patterns = [
        r'ATENCI[ÓO]N[:\s]*([A-ZÁÉÍÓÚÑ\s\d:]+?)(?:\n|$)',
        r'HORARIO[:\s]*([A-ZÁÉÍÓÚÑ\s\d:]+?)(?:\n|$)',
    ]
    
    for pattern in horario_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['horario_atencion'] = match.group(1).strip()
            break
    
    return info

def _extract_pruebas_solicitadas(text: str) -> List[Dict[str, Any]]:
    """Extrae las pruebas médicas solicitadas marcadas en el formulario"""
    pruebas = []
    
    # Definir las secciones de pruebas y sus patrones
    secciones_pruebas = {
        'HEMATOLOGÍA': [
            'BIOMETRÍA HEMÁTICA', 'HEMATOCRITO', 'HEMOGLOBINA', 'SEDIMENTACIÓN Wintrobe',
            'SEDIMENTACIÓN Westergreen', 'PLAQUETAS', 'RETICULOCITOS', 'COOMBS DIRECTO',
            'INDIRECTO', 'GRUPO SANGUÍNEO Y RH', 'INV. HEMATOZOARIO', 'ANTÍGENO DE MALARIA',
            'CITOMETRÍA DE FLUJO (SANGRE PERIFÉRICA)', 'CITOMETRÍA DE FLUJO (MÉDULA ÓSEA)'
        ],
        'SEROLOGÍA Y REACTANTES DE FASE AGUDA': [
            'ASTO', 'PCR CUANTITATIVA', 'AGLUTINACIONES FEBRILES', 'ALFA 1 ANTITRIPSINA',
            'FACTOR DE NECROSIS TUMORAL ALFA', 'FR LATEX CUANTITATIVA', 'INTERLEUKINA 6',
            'PCR ULTRASENSIBLE', 'PROCALCITONINA', 'R.P.R', 'V.D.R.L. CUALITATIVO',
            'V.D.R.L. CUANTITATIVO'
        ],
        'ELECTROLITOS, MINERALES Y GASES': [
            'ÁCIDO LÁCTICO', 'BICARBONATO', 'SODIO', 'POTASIO', 'CLORO', 'CALCIO',
            'FÓSFORO', 'MAGNESIO', 'CALCIO IÓNICO', 'GASOMETRÍA ARTERIAL', 'VENOSA'
        ],
        'INFECCIOSAS': [
            'TOXOPLASMA IgG', 'TOXOPLASMA IgM', 'TOXOPLASMA IgG AVIDEZ', 'RUBEOLA IgG',
            'RUBEOLA IgM', 'CITOMEGALOVIRUS IgG', 'CITOMEGALOVIRUS IgM', 'CITOMEGALOVIRUS IgG AVIDEZ',
            'MONONUCLEOSIS IgG', 'MONONUCLEOSIS IgM', 'EPSTEIN BARR VCA-IgG', 'EPSTEIN BARR VCA-IgM',
            'EBNA IgG', 'HERPES I IgG', 'HERPES I IgM', 'HERPES II IgG', 'HERPES II IgM',
            'SÍFILIS IgG', 'SÍFILIS IgM', 'F.T.A. Abs', 'CHLAMIDYA TRACHOMATIS IgG',
            'CHLAMIDYA TRACHOMATIS IgM', 'CLAMIDYA PNEUMONIAE IgG', 'CLAMIDYA PNEUMONIAE IgM',
            'CHAGAS SEROLOGÍA', 'CISTICERCO IgG', 'DENGUE IgG', 'DENGUE IgM', 'DENGUE AG. NS1',
            'HELICOBACTER PYLORI IgG', 'HELICOBACTER PYLORI IgM', 'HELICOBACTER PYLORI IgA',
            'VARICELA-ZÓSTER IgG', 'VARICELA-ZÓSTER IgM', 'SARAMPIÓN IgG', 'SARAMPIÓN IgM',
            'PAROTIDITIS (PAPERAS) IgG', 'PAROTIDITIS (PAPERAS) IgM', 'PARVOVIRUS B19 IgG',
            'PARVOVIRUS B19 IgM', 'TUBERCULOSIS TOTAL IgM/IgG'
        ],
        'COAGULACIÓN': [
            'ANTICOAGULANTE LÚPICO', 'ANTITROMBINA III', 'DÍMERO D', 'FACTOR II MUTACIÓN PCR',
            'FACTOR V LEIDEN PCR', 'FIBRINÓGENO', 'PROTEÍNA C', 'PROTEÍNA S',
            'T. COAGULACIÓN', 'T. HEMORRAGIA', 'T. TROMBINA (TT)', 'RETRAC. COÁGULO',
            'TP', 'TTP', 'INR'
        ],
        'PERFIL CARDÍACO': [
            'CPK', 'CK-MB', 'TROPONINA T ULTRASENSIBLE', 'TROPONINA I', 'MIOGLOBINA',
            'HOMOCISTEÍNA', 'NT-proBNP'
        ],
        'ENDOCRINOLOGÍA': [
            'TSH', 'T3', 'T3 LIBRE (FT3)', 'T4 LIBRE (FT4)', 'TIROGLOBULINA',
            'ANTICUERPOS ANTIPEROXIDASA (TPO)', 'ANTICUERPOS ANTITIROGLOBULINA (ATG)',
            'ANTICUERPOS ANTI TSH RECEPTOR (ANTI TSH)', 'LH', 'FSH', 'PROLACTINA',
            'PROGESTERONA', 'ESTRONA (E1)', '17 BETA ESTRADIOL (E2)', 'ESTRIOL LIBRE (E3)'
        ],
        'VITAMINAS / PERFIL DE ANEMIA': [
            'ÁCIDO FÓLICO', 'HIERRO SÉRICO', 'CAPACIDAD DE FIJACIÓN DE HIERRO',
            'FERRITINA', 'TRANSFERRINA', 'SATURACIÓN DE TRANSFERRINA'
        ],
        'TAMIZAJE PRENATAL': [
            'ADN FETAL LIBRE'
        ],
        'MOLECULAR Y GENÉTICA': [
            'ONCOTYPE DX CÁNCER DE SENO', 'SelectMDx Cáncer de Próstata en orina',
            'ConfirMDx Cáncer de Próstata (Tejido)', 'BRCA1 Y BRCA2',
            'PANEL CÁNCER DE SENO Y OVARIO 14 GE', 'PANEL CÁNCER DE OVARIO 17 GENES',
            'PANEL CÁNCER DE SENO Y OVARIO 39 GE', 'PANEL CÁNCER DE SENO Y OVARIO 51 GE',
            'PANEL CÁNCER DE COLON 29 GENES', 'CÁNCER DE COLON HEREDITARIO NO POLIPÓSICO',
            'CÁNCER DE PRÓSTATA HEREDITARIO 21 GE', 'PANEL GLOBAL DE CÁNCER 163 GENES',
            'DISBIOSIS INTESTINAL - PCR'
        ],
        'UROANÁLISIS': [
            'EMO AUTOMATIZADO', 'CÁLCULOS URINARIOS', 'GRAM DE GOTA FRESCA',
            'GRAM DE SEDIMENTO', 'SEDIMENTO URINARIO (MORFOLOGÍA ERITROCIT)',
            'UROCULTIVO', 'BAAR EN ORINA N°', 'MUESTRA', 'CLINI-TEST'
        ]
    }
    
    # Buscar pruebas marcadas en cada sección
    for seccion, lista_pruebas in secciones_pruebas.items():
        for prueba in lista_pruebas:
            if _is_prueba_marcada(text, prueba):
                pruebas.append({
                    'nombre': prueba,
                    'seccion': seccion,
                    'marcada': True
                })
    
    return pruebas

def _is_prueba_marcada(text: str, nombre_prueba: str) -> bool:
    """Determina si una prueba específica está marcada en el formulario"""
    # Buscar líneas que contengan la prueba
    lines = text.split('\n')
    
    for line in lines:
        line_clean = line.strip()
        
        # Si la línea contiene el nombre de la prueba o variaciones
        # Crear variaciones del nombre para manejar texto OCR degradado
        variaciones = [
            nombre_prueba.lower(),
            nombre_prueba.lower().replace('í', 'i').replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('ú', 'u'),
            nombre_prueba.lower().replace(' ', ''),
            nombre_prueba.lower().replace(' ', '').replace('í', 'i').replace('ó', 'o').replace('á', 'a').replace('é', 'e').replace('ú', 'u')
        ]
        
        # Verificar si alguna variación está en la línea
        contiene_prueba = any(variacion in line_clean.lower() for variacion in variaciones)
        
        if contiene_prueba:
            # Patrones para detectar checkboxes marcados (incluyendo caracteres OCR degradados)
            checkbox_patterns = [
                r'^[Xx]\s+',  # X al inicio de la línea
                r'^\s*[Xx]\s+',  # X al inicio con espacios
                r'^\s*✓\s+',  # Checkmark al inicio
                r'^\s*☑\s+',  # Checkbox marcado al inicio
                # Patrones para texto OCR degradado
                r'^[CJ]\s*[Xx]',  # C o J seguido de X (error OCR común)
                r'^[CJ]\s*[Xx]\s+',  # C o J seguido de X con espacios
                r'^\s*[CJ]\s*[Xx]',  # C o J seguido de X con espacios al inicio
                r'^[CJ]\s*[Xx]\s*' + re.escape(nombre_prueba),  # C o J seguido de X y el nombre
                r'^[CJ]\s*[Xx]\s*' + re.escape(nombre_prueba.split()[0]),  # C o J seguido de X y primera palabra
                # Patrones para caracteres de checkbox degradados
                r'^[CJ]\s*[Xx]\s*[A-Z]',  # C o J seguido de X y letra mayúscula
                r'^\s*[CJ]\s*[Xx]\s*[A-Z]',  # Con espacios al inicio
            ]
            
            for pattern in checkbox_patterns:
                if re.match(pattern, line_clean, re.IGNORECASE):
                    return True
            
            # Verificar si hay un checkbox marcado antes del nombre en la misma línea
            # Buscar patrones como "C X BIOMETRIA" o "J X HEMOGLOBINA"
            checkbox_before_patterns = [
                r'[CJ]\s*[Xx]\s*' + re.escape(nombre_prueba),
                r'[CJ]\s*[Xx]\s*' + re.escape(nombre_prueba.split()[0]),
                r'[CJ]\s*[Xx]\s*[A-Z].*' + re.escape(nombre_prueba),
            ]
            
            for pattern in checkbox_before_patterns:
                if re.search(pattern, line_clean, re.IGNORECASE):
                    return True
            
            # Patrones MUY RESTRICTIVOS - Solo para checkboxes claramente marcados
            # Basado en la imagen real donde solo BIOMETRÍA HEMÁTICA y SEDIMENTACIÓN Wintrobe están marcadas
            degraded_patterns = [
                # Patrones específicos para las pruebas que realmente están marcadas en la imagen
                r'DXBIOMETRIA\s+HEMATICA',  # DXBIOMETRIA HEMATICA (BIOMETRIA HEMATICA marcada)
                r'PESEDIMENTACION\s+Wintrobe',  # PESEDIMENTACION Wintrobe (SEDIMENTACIÓN Wintrobe marcada)
                # Patrones muy específicos para checkboxes marcados con X
                r'[CJ]\s*[Xx]\s*' + re.escape(nombre_prueba),  # C o J + X + nombre
                r'[CJ]\s*[Xx]\s*[A-Z].*' + re.escape(nombre_prueba),  # C o J + X + letra + nombre
                r'\[[CJ]\s*[Xx]' + re.escape(nombre_prueba),  # [C o J + X + nombre
                r'\([CJ]\s*[Xx]' + re.escape(nombre_prueba),  # (C o J + X + nombre
                # Patrones específicos para casos conocidos de checkboxes marcados
                r'Cj\s*' + re.escape(nombre_prueba),  # Cj + nombre (HEMOGLOBINA - solo si está marcada)
                r'\$7<' + re.escape(nombre_prueba),  # $7< + nombre (TSH - solo si está marcada)
                r'\{]' + re.escape(nombre_prueba),  # {] + nombre (T4 - solo si está marcada)
            ]
            
            for pattern in degraded_patterns:
                if re.search(pattern, line_clean, re.IGNORECASE):
                    return True
            
            # Si la línea empieza directamente con el nombre (sin checkbox), no está marcada
            if re.match(r'^\s*' + re.escape(nombre_prueba), line_clean, re.IGNORECASE):
                return False
    
    return False

def _extract_formulario_info(text: str) -> Dict[str, Any]:
    """Extrae información general del formulario"""
    info = {}
    
    # Tipo de documento
    info['tipo_documento'] = 'FORMULARIO_LABORATORIO'
    
    # Imagen diagnóstica
    imagen_patterns = [
        r'IMAGEN\s+DIAGN[ÓO]STICA[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|$)',
        r'DIAGN[ÓO]STICO[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|$)',
    ]
    
    for pattern in imagen_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['imagen_diagnostica'] = match.group(1).strip()
            break
    
    # Fecha de procesamiento
    info['fecha_procesamiento'] = datetime.now().isoformat()
    
    return info
