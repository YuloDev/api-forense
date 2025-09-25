"""
Generador de IDs para reclamos.

Contiene las funciones necesarias para generar IDs únicos de reclamos.
"""

import re
from typing import Optional


def obtener_siguiente_id(ultimo_id: Optional[str]) -> str:
    """
    Genera el siguiente ID basado en el último ID existente.
    
    Args:
        ultimo_id: Último ID generado (formato: REC-YYYY-XXXX)
        
    Returns:
        Nuevo ID generado
    """
    if not ultimo_id:
        # Si no hay último ID, empezar con REC-2024-0001
        return "REC-2024-0001"
    
    try:
        # Extraer año y número del último ID
        match = re.match(r"REC-(\d{4})-(\d{4})", ultimo_id)
        if not match:
            # Si el formato no es válido, empezar con REC-2024-0001
            return "REC-2024-0001"
        
        año = int(match.group(1))
        numero = int(match.group(2))
        
        # Incrementar número
        numero += 1
        
        # Si llegamos a 9999, incrementar año y resetear número
        if numero > 9999:
            año += 1
            numero = 1
        
        # Formatear nuevo ID
        return f"REC-{año}-{numero:04d}"
        
    except (ValueError, AttributeError):
        # Si hay error en el parsing, empezar con REC-2024-0001
        return "REC-2024-0001"


def generar_id_reclamo() -> str:
    """
    Genera un nuevo ID de reclamo.
    
    Returns:
        Nuevo ID generado
    """
    # Por simplicidad, generar un ID basado en timestamp
    # En un sistema real, esto debería consultar la base de datos
    from datetime import datetime
    now = datetime.now()
    timestamp = int(now.timestamp())
    
    # Usar los últimos 4 dígitos del timestamp como número
    numero = timestamp % 10000
    
    return f"REC-{now.year}-{numero:04d}"


def validar_id_reclamo(id_reclamo: str) -> bool:
    """
    Valida si un ID de reclamo tiene el formato correcto.
    
    Args:
        id_reclamo: ID a validar
        
    Returns:
        True si el formato es válido, False en caso contrario
    """
    if not id_reclamo:
        return False
    
    # Patrón: REC-YYYY-XXXX
    pattern = r"^REC-\d{4}-\d{4}$"
    return bool(re.match(pattern, id_reclamo))


def extraer_año_del_id(id_reclamo: str) -> Optional[int]:
    """
    Extrae el año de un ID de reclamo.
    
    Args:
        id_reclamo: ID del reclamo
        
    Returns:
        Año extraído o None si el formato no es válido
    """
    if not validar_id_reclamo(id_reclamo):
        return None
    
    try:
        match = re.match(r"REC-(\d{4})-\d{4}", id_reclamo)
        if match:
            return int(match.group(1))
    except (ValueError, AttributeError):
        pass
    
    return None


def extraer_numero_del_id(id_reclamo: str) -> Optional[int]:
    """
    Extrae el número de un ID de reclamo.
    
    Args:
        id_reclamo: ID del reclamo
        
    Returns:
        Número extraído o None si el formato no es válido
    """
    if not validar_id_reclamo(id_reclamo):
        return None
    
    try:
        match = re.match(r"REC-\d{4}-(\d{4})", id_reclamo)
        if match:
            return int(match.group(1))
    except (ValueError, AttributeError):
        pass
    
    return None
