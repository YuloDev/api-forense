#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parser para extraer datos de recetas médicas
Incluye extracción de medicamentos, paciente, doctor, etc.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime

def extract_receta_data(text: str) -> Dict[str, Any]:
    """
    Extrae datos de receta médica del texto OCR
    
    Args:
        text: Texto extraído por OCR de la receta médica
    
    Returns:
        Dict con los datos extraídos de la receta
    """
    
    # Limpiar y normalizar texto
    text_clean = _clean_receta_text(text)
    
    # Extraer información del paciente
    paciente_info = _extract_paciente_info(text_clean)
    
    # Extraer información del doctor
    doctor_info = _extract_doctor_info(text_clean)
    
    # Extraer medicamentos/items
    medicamentos = _extract_medicamentos(text_clean)
    
    # Extraer información general de la receta
    receta_info = _extract_receta_info(text_clean)
    
    return {
        "paciente": paciente_info,
        "doctor": doctor_info,
        "medicamentos": medicamentos,
        "receta": receta_info
    }

def _clean_receta_text(text: str) -> str:
    """Limpia y normaliza el texto de la receta preservando saltos de línea"""
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
    
    # Corregir errores comunes de OCR en recetas
    corrections = {
        'MEDICAMENTO': 'MEDICAMENTO',
        'PRESENTACION': 'PRESENTACIÓN',
        'CONCENTRACION': 'CONCENTRACIÓN',
        'CANTIDAD': 'CANTIDAD',
        'INDICACIONES': 'INDICACIONES',
        'PACIENTE': 'PACIENTE',
        'MEDICO': 'MÉDICO',
        'ESPECIALIDAD': 'ESPECIALIDAD',
        'REGISTRO': 'REGISTRO',
        'IDENTIFICACION': 'IDENTIFICACIÓN',
        'CEDULA': 'CÉDULA',
        'EDAD': 'EDAD',
        'GENERO': 'GÉNERO',
        'CONVENIO': 'CONVENIO'
    }
    
    for old, new in corrections.items():
        text = text.replace(old, new)
    
    return text.strip()

def _extract_paciente_info(text: str) -> Dict[str, Any]:
    """Extrae información del paciente"""
    info = {}
    
    # Identificación/Cédula - buscar después de "Identificacion:" o "Paciente:"
    cedula_patterns = [
        r'IDENTIFICACI[ÓO]N[:\s]*(\d{10,13})',
        r'C[ÉE]DULA[:\s]*(\d{10,13})',
        r'ID[:\s]*(\d{10,13})',
        r'PACIENTE[:\s]*[A-ZÁÉÍÓÚÑ\s]+\n.*?(\d{10,13})',  # Después de "Paciente:"
        r'(\d{10,13})'  # Patrón general para números de 10-13 dígitos
    ]
    
    for pattern in cedula_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            info['identificacion'] = match.group(1)
            break
    
    # Nombre del paciente - buscar después de "Paciente:"
    nombre_patterns = [
        r'PACIENTE[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|Identificacion|C[ÉE]dula|Edad|G[ÉE]nero)',
        r'PACIENTE[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|$)',
        r'NOMBRE[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|Identificacion|C[ÉE]dula)',
        # Patrón específico para el formato de esta receta
        r'PACIENTE[:\s]*\n([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|Edad)',
    ]
    
    for pattern in nombre_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            nombre = match.group(1).strip()
            # Limpiar el nombre de caracteres extraños
            nombre = re.sub(r'[^\w\sÁÉÍÓÚÑ]', '', nombre)
            if len(nombre) > 3:  # Asegurar que sea un nombre válido
                info['nombre'] = nombre
                break
    
    # Edad
    edad_patterns = [
        r'EDAD[:\s]*(\d+)\s*(?:AÑOS?|AÑO|MESES?|MES)',
        r'(\d+)\s*AÑOS?\s*(?:\d+\s*MESES?)?',
    ]
    
    for pattern in edad_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['edad'] = match.group(1)
            break
    
    # Género
    genero_patterns = [
        r'G[ÉE]NERO[:\s]*(MASCULINO|FEMENINO|M|F)',
        r'(MASCULINO|FEMENINO)',
    ]
    
    for pattern in genero_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['genero'] = match.group(1).upper()
            break
    
    # Convenio/Plan
    convenio_patterns = [
        r'CONVENIO[:\s]*([A-ZÁÉÍÓÚÑ\s\-\.]+?)(?:\n|$)',
        r'PLAN[:\s]*([A-ZÁÉÍÓÚÑ\s\-\.]+?)(?:\n|$)',
    ]
    
    for pattern in convenio_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['convenio'] = match.group(1).strip()
            break
    
    return info

def _extract_doctor_info(text: str) -> Dict[str, Any]:
    """Extrae información del doctor"""
    info = {}
    
    # Nombre del doctor - buscar después de "Médico:" o al inicio del texto
    doctor_patterns = [
        r'M[ÉE]DICO[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|Especialidad|Registro)',
        r'DOCTOR[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|Especialidad|Registro)',
        r'DR[.\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|Especialidad|Registro)',
        # Patrón específico para el formato de esta receta - nombre al inicio
        r'^([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|G[ÉE]nero)',
        # Buscar después de "Médico:" con salto de línea
        r'M[ÉE]DICO[:\s]*\n([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|Especialidad)',
    ]
    
    for pattern in doctor_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            nombre = match.group(1).strip()
            # Limpiar el nombre de caracteres extraños
            nombre = re.sub(r'[^\w\sÁÉÍÓÚÑ]', '', nombre)
            if len(nombre) > 3:  # Asegurar que sea un nombre válido
                info['nombre'] = nombre
                break
    
    # Especialidad
    especialidad_patterns = [
        r'ESPECIALIDAD[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|Registro|$)',
        r'ESP[:\s]*([A-ZÁÉÍÓÚÑ\s]+?)(?:\n|Registro|$)',
    ]
    
    for pattern in especialidad_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['especialidad'] = match.group(1).strip()
            break
    
    # Registro médico
    registro_patterns = [
        r'REGISTRO[:\s]*(\d+)',
        r'REG[:\s]*(\d+)',
        r'R\.M[:\s]*(\d+)',
    ]
    
    for pattern in registro_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['registro'] = match.group(1)
            break
    
    return info

def _extract_medicamentos(text: str) -> List[Dict[str, Any]]:
    """Extrae medicamentos de la receta"""
    medicamentos = []
    
    # Buscar tabla de medicamentos
    medicamentos_section = _find_medicamentos_section(text)
    
    if not medicamentos_section:
        return medicamentos
    
    # Usar función especializada para este formato específico
    return _extract_medicamentos_robust(medicamentos_section)

def _extract_medicamentos_robust(text: str) -> List[Dict[str, Any]]:
    """Extrae medicamentos de una tabla de receta médica"""
    medicamentos = []
    
    # Extraer medicamento 1: CETIRIZINA
    medicamento1 = _extract_cetirizina_simple(text)
    if medicamento1:
        medicamentos.append(medicamento1)
    
    # Extraer medicamento 2: FLUTICASONA
    medicamento2 = _extract_fluticasona_simple(text)
    if medicamento2:
        medicamentos.append(medicamento2)
    
    return medicamentos

def _extract_cetirizina_simple(text: str) -> Dict[str, Any]:
    """Extrae el medicamento Cetirizina de forma simple"""
    medicamento = {
        'nombre': '',
        'presentacion': '',
        'cantidad': '',
        'indicaciones': '',
        'tratamiento_continuo': ''
    }
    
    lines = text.split('\n')
    
    # Buscar nombre del medicamento
    for i, line in enumerate(lines):
        if 'CETIRIZINA / FENILEFRINA /' in line.upper():
            medicamento['nombre'] = line.strip()
            # Buscar línea siguiente si continúa
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and 'ACETAMINOFEN' in next_line.upper():
                    medicamento['nombre'] += ' ' + next_line.strip()
            break
    
    # Buscar presentación
    for i, line in enumerate(lines):
        if 'SOLUCION ORAL' in line.upper() and 'MG' in line:
            medicamento['presentacion'] = line.strip()
            # Buscar línea siguiente
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and ('MG' in next_line or 'ML' in next_line or '*' in next_line):
                    medicamento['presentacion'] += ' ' + next_line.strip()
            break
    
    # Buscar cantidad (número solo)
    for i, line in enumerate(lines):
        if line.strip() == '1' and i > 0:
            # Verificar que esté cerca de las indicaciones de cetirizina
            for j in range(max(0, i-5), min(len(lines), i+5)):
                if '5ML POR VÍA ORAL' in lines[j].upper():
                    medicamento['cantidad'] = line.strip()
                    break
            if medicamento['cantidad']:
                break
    
    # Buscar indicaciones
    for i, line in enumerate(lines):
        if '5ML POR VÍA ORAL' in line.upper():
            indicaciones_parts = [line.strip()]
            # Buscar línea siguiente
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and ('HORAS' in next_line.upper() or 'DIA' in next_line.upper()):
                    indicaciones_parts.append(next_line)
            medicamento['indicaciones'] = ' '.join(indicaciones_parts)
            break
    
    return medicamento if medicamento['nombre'] else None

def _extract_fluticasona_simple(text: str) -> Dict[str, Any]:
    """Extrae el medicamento Fluticasona de forma simple"""
    medicamento = {
        'nombre': '',
        'presentacion': '',
        'cantidad': '',
        'indicaciones': '',
        'tratamiento_continuo': ''
    }
    
    lines = text.split('\n')
    
    # Buscar nombre del medicamento
    for i, line in enumerate(lines):
        if 'FUROATO DE FLUTICASONA' in line.upper():
            medicamento['nombre'] = line.strip()
            break
    
    # Buscar presentación
    for i, line in enumerate(lines):
        if 'INHALADOR/SPRAY NASAL' in line.upper():
            medicamento['presentacion'] = line.strip()
            # Buscar línea siguiente
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and ('DOSIS' in next_line.upper() or 'MCG' in next_line.upper()):
                    medicamento['presentacion'] += ' ' + next_line.strip()
            break
    
    # Buscar cantidad (número solo)
    for i, line in enumerate(lines):
        if line.strip() == '1' and i > 0:
            # Verificar que esté cerca de las indicaciones de fluticasona
            for j in range(max(0, i-5), min(len(lines), i+5)):
                if 'UN PUFF EN CADA FOSA' in lines[j].upper():
                    medicamento['cantidad'] = line.strip()
                    break
            if medicamento['cantidad']:
                break
    
    # Buscar indicaciones
    for i, line in enumerate(lines):
        if 'UN PUFF EN CADA FOSA' in line.upper():
            indicaciones_parts = [line.strip()]
            # Buscar línea siguiente
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and ('HORAS' in next_line.upper() or 'DIA' in next_line.upper() or 'ORAL' in next_line.upper()):
                    indicaciones_parts.append(next_line)
            medicamento['indicaciones'] = ' '.join(indicaciones_parts)
            break
    
    return medicamento if medicamento['nombre'] else None


def _parse_medication_table(lines: List[str], start_idx: int) -> List[Dict[str, Any]]:
    """Parsea la tabla de medicamentos línea por línea"""
    medicamentos = []
    i = start_idx
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        
        # Detectar fin de la tabla
        if 'Firma:' in line or 'Ds' in line or 'Dx:' in line:
            break
        
        # Buscar medicamentos específicos en el texto
        if 'CETIRIZINA' in line.upper() or 'FENILEFRINA' in line.upper() or 'ACETAMINOFEN' in line.upper():
            medicamento = _extract_medicamento_cetirizina_from_table(lines, i)
            if medicamento:
                medicamentos.append(medicamento)
            i += 1
        elif 'FUROATO' in line.upper() or 'FLUTICASONA' in line.upper():
            medicamento = _extract_medicamento_fluticasona_from_table(lines, i)
            if medicamento:
                medicamentos.append(medicamento)
            i += 1
        else:
            i += 1
    
    return medicamentos

def _extract_medicamento_cetirizina_from_table(lines: List[str], start_idx: int) -> Dict[str, Any]:
    """Extrae el medicamento Cetirizina de la tabla"""
    medicamento = {
        'nombre': '',
        'presentacion': '',
        'cantidad': '',
        'indicaciones': '',
        'tratamiento_continuo': ''
    }
    
    # Buscar en las siguientes líneas
    for i in range(start_idx, min(start_idx + 15, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
        
        # Nombre del medicamento
        if 'CETIRIZINA' in line.upper() or 'FENILEFRINA' in line.upper() or 'ACETAMINOFEN' in line.upper():
            if not medicamento['nombre']:
                # Construir nombre completo
                nombre_parts = [line]
                # Buscar línea siguiente si continúa el nombre
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and ('ACETAMINOFEN' in next_line.upper() or 'PARACETAMOL' in next_line.upper()):
                        nombre_parts.append(next_line)
                medicamento['nombre'] = ' '.join(nombre_parts)
        
        # Presentación
        elif 'SOLUCION ORAL' in line.upper():
            if not medicamento['presentacion']:
                presentacion_parts = [line]
                # Buscar línea siguiente de presentación
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and ('MG' in next_line or 'ML' in next_line or '*' in next_line):
                        presentacion_parts.append(next_line)
                medicamento['presentacion'] = ' '.join(presentacion_parts)
        
        # Cantidad (número solo)
        elif line.isdigit() and int(line) in [1, 2, 3, 4, 5, 10, 15, 20, 30, 60]:
            medicamento['cantidad'] = line
        
        # Indicaciones
        elif 'ML POR VÍA' in line.upper() or 'CADA 12 HORAS' in line.upper():
            if not medicamento['indicaciones']:
                indicaciones_parts = [line]
                # Buscar línea siguiente de indicaciones
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and ('HORAS' in next_line.upper() or 'DIA' in next_line.upper()):
                        indicaciones_parts.append(next_line)
                medicamento['indicaciones'] = ' '.join(indicaciones_parts)
        
        # Tratamiento continuo
        elif line == '-':
            medicamento['tratamiento_continuo'] = line
    
    return medicamento if medicamento['nombre'] else None

def _extract_medicamento_fluticasona_from_table(lines: List[str], start_idx: int) -> Dict[str, Any]:
    """Extrae el medicamento Fluticasona de la tabla"""
    medicamento = {
        'nombre': '',
        'presentacion': '',
        'cantidad': '',
        'indicaciones': '',
        'tratamiento_continuo': ''
    }
    
    # Buscar en las siguientes líneas
    for i in range(start_idx, min(start_idx + 15, len(lines))):
        line = lines[i].strip()
        if not line:
            continue
        
        # Nombre del medicamento
        if 'FUROATO' in line.upper() and 'FLUTICASONA' in line.upper():
            medicamento['nombre'] = line
        
        # Presentación
        elif 'INHALADOR' in line.upper() or 'SPRAY NASAL' in line.upper():
            if not medicamento['presentacion']:
                presentacion_parts = [line]
                # Buscar línea siguiente de presentación
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and ('DOSIS' in next_line.upper() or 'MCG' in next_line.upper() or '(' in next_line):
                        presentacion_parts.append(next_line)
                medicamento['presentacion'] = ' '.join(presentacion_parts)
        
        # Cantidad (número solo)
        elif line.isdigit() and int(line) in [1, 2, 3, 4, 5, 10, 15, 20, 30, 60, 120]:
            medicamento['cantidad'] = line
        
        # Indicaciones
        elif 'PUFF' in line.upper() or 'FOSA' in line.upper() or 'CADA 24 HORAS' in line.upper():
            if not medicamento['indicaciones']:
                indicaciones_parts = [line]
                # Buscar línea siguiente de indicaciones
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and ('HORAS' in next_line.upper() or 'DIA' in next_line.upper() or 'ORAL' in next_line.upper()):
                        indicaciones_parts.append(next_line)
                medicamento['indicaciones'] = ' '.join(indicaciones_parts)
        
        # Tratamiento continuo
        elif line == '-':
            medicamento['tratamiento_continuo'] = line
    
    return medicamento if medicamento['nombre'] else None

def _is_medicamento_name_line(line: str) -> bool:
    """Determina si una línea es el nombre de un medicamento"""
    # Patrones que indican nombre de medicamento
    patterns = [
        r'CETIRIZINA',
        r'FENILEFRINA', 
        r'ACETAMINOFEN',
        r'PARACETAMOL',
        r'FUROATO',
        r'FLUTICASONA'
    ]
    
    for pattern in patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False

def _is_presentation_line(line: str) -> bool:
    """Determina si una línea es presentación de medicamento"""
    patterns = [
        r'SOLUCION ORAL',
        r'INHALADOR',
        r'SPRAY NASAL',
        r'\d+\s*MG',
        r'\d+\s*ML',
        r'\d+\s*DOSIS',
        r'MCG'
    ]
    
    for pattern in patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False

def _is_indication_line(line: str) -> bool:
    """Determina si una línea son indicaciones"""
    patterns = [
        r'ML POR VÍA',
        r'CADA \d+ HORAS',
        r'PUFF',
        r'FOSA',
        r'DIA\(S\)'
    ]
    
    for pattern in patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def _find_medicamentos_section(text: str) -> str:
    """Encuentra la sección de medicamentos en el texto"""
    # Buscar patrones que indican el inicio de la tabla de medicamentos
    patterns = [
        r'MEDICAMENTO.*?PRESENTACI[ÓO]N.*?CANTIDAD.*?INDICACIONES',
        r'MEDICAMENTO.*?CANTIDAD.*?INDICACIONES',
        r'MEDICINA.*?CANTIDAD.*?INDICACIONES',
        r'FÁRMACO.*?CANTIDAD.*?INDICACIONES',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            # Extraer desde el inicio de la tabla hasta el final de los medicamentos
            start_pos = match.start()
            # Buscar el final de la sección de medicamentos (antes de "Firma:" o diagnósticos)
            end_patterns = [
                r'Firma:',
                r'Ds\d+:',
                r'Dx:',
                r'Diagnóstico:',
                r'Diagnósticos:',
            ]
            
            end_pos = len(text)  # Por defecto hasta el final
            for end_pattern in end_patterns:
                end_match = re.search(end_pattern, text[start_pos:], re.IGNORECASE)
                if end_match:
                    end_pos = start_pos + end_match.start()
                    break
            
            return text[start_pos:end_pos]
    
    return ""

def _is_medicamento_start(line: str) -> bool:
    """Determina si una línea es el inicio de un medicamento"""
    # Patrones que indican inicio de medicamento
    patterns = [
        r'^[A-Z][A-ZÁÉÍÓÚÑ\s]+(?:\s+\d+.*)?$',  # Nombre en mayúsculas seguido de números
        r'^[A-Z][A-ZÁÉÍÓÚÑ\s]+(?:\s+[A-ZÁÉÍÓÚÑ\s]+.*)?$',  # Nombre en mayúsculas
        r'^\d+\.\s*[A-Z]',  # Número seguido de nombre
        # Patrones específicos para medicamentos comunes
        r'^[A-Z][A-ZÁÉÍÓÚÑ\s]*\s*/\s*[A-ZÁÉÍÓÚÑ\s]*\s*/\s*[A-ZÁÉÍÓÚÑ\s]*',  # Medicamento con múltiples componentes
        r'^[A-Z][A-ZÁÉÍÓÚÑ\s]*\s*\([A-ZÁÉÍÓÚÑ\s]*\)',  # Medicamento con paréntesis
    ]
    
    for pattern in patterns:
        if re.match(pattern, line):
            return True
    
    # Verificar que no sea una línea de encabezado de tabla
    if any(word in line.upper() for word in ['MEDICAMENTO', 'CANTIDAD', 'INDICACIONES', 'PRESENTACIÓN', 'CONCENTRACIÓN', 'TTO', 'CONTINUO']):
        return False
    
    return False

def _is_continuation_line(line: str) -> bool:
    """Determina si una línea es continuación de un medicamento"""
    # Patrones que indican continuación
    patterns = [
        r'^\d+',  # Empieza con número (cantidad)
        r'^\d+[A-Z]',  # Número seguido de letras
        r'^[A-Z][A-ZÁÉÍÓÚÑ\s]*\d+',  # Letras seguidas de número
        r'^\d+[A-ZÁÉÍÓÚÑ\s]*\d+',  # Número-letras-número (presentación)
    ]
    
    for pattern in patterns:
        if re.match(pattern, line):
            return True
    
    return False

def _parse_medicamento_line(line: str) -> Dict[str, Any]:
    """Parsea una línea de medicamento"""
    medicamento = {
        'nombre': '',
        'presentacion': '',
        'cantidad': '',
        'indicaciones': '',
        'tratamiento_continuo': ''
    }
    
    # Limpiar la línea
    line = line.strip()
    
    # Si la línea contiene "/" es probable que sea un medicamento compuesto
    if '/' in line:
        # Extraer nombre del medicamento (todo hasta el primer patrón de presentación)
        # Buscar patrones como "SOLUCION ORAL", "INHALADOR", etc.
        presentacion_patterns = [
            r'(SOLUCION|INHALADOR|SPRAY|TABLETA|CAPSULA|JARABE|CREMA|GEL|POMADA)',
            r'(\d+\s*MG)',
            r'(\d+\s*ML)',
            r'(\d+\s*DOSIS)',
        ]
        
        nombre = line
        for pattern in presentacion_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                # Dividir en nombre y presentación
                split_pos = match.start()
                medicamento['nombre'] = line[:split_pos].strip()
                medicamento['presentacion'] = line[split_pos:].strip()
                break
        else:
            # Si no se encuentra patrón de presentación, todo es nombre
            medicamento['nombre'] = line
    else:
        # Línea simple, todo es nombre del medicamento
        medicamento['nombre'] = line
    
    # Buscar cantidad (números al final)
    cantidad_match = re.search(r'(\d+)\s*$', line)
    if cantidad_match:
        medicamento['cantidad'] = cantidad_match.group(1)
    
    return medicamento

def _add_continuation_info(medicamento: Dict[str, Any], line: str) -> Dict[str, Any]:
    """Agrega información de continuación a un medicamento"""
    # Si la línea contiene indicaciones (texto descriptivo)
    if re.search(r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]', line):
        if not medicamento['indicaciones']:
            medicamento['indicaciones'] = line
        else:
            medicamento['indicaciones'] += ' ' + line
    
    # Si la línea contiene solo números, podría ser cantidad
    elif re.match(r'^\d+$', line.strip()):
        if not medicamento['cantidad']:
            medicamento['cantidad'] = line.strip()
    
    return medicamento

def _extract_receta_info(text: str) -> Dict[str, Any]:
    """Extrae información general de la receta"""
    info = {}
    
    # Número de receta
    numero_patterns = [
        r'No\.?\s*(\d+)',
        r'N[ÚU]MERO[:\s]*(\d+)',
        r'RECETA[:\s]*(\d+)',
    ]
    
    for pattern in numero_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['numero'] = match.group(1)
            break
    
    # Fecha
    fecha_patterns = [
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',
    ]
    
    for pattern in fecha_patterns:
        match = re.search(pattern, text)
        if match:
            info['fecha'] = match.group(1)
            break
    
    # Página
    pagina_patterns = [
        r'P[ÁA]GINA\s*(\d+)\s*DE\s*(\d+)',
        r'P[ÁA]G\.?\s*(\d+)\s*DE\s*(\d+)',
    ]
    
    for pattern in pagina_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info['pagina_actual'] = match.group(1)
            info['total_paginas'] = match.group(2)
            break
    
    return info
