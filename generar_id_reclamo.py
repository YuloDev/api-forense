#!/usr/bin/env python3
"""
Script para generar IDs de reclamo con el formato CLM-000-001
"""

def generar_id_reclamo(secuencial: int) -> str:
    """
    Genera un ID de reclamo con el formato CLM-000-001
    
    Args:
        secuencial: Número secuencial del reclamo
        
    Returns:
        ID formateado como CLM-000-001
    """
    # Formatear con 6 dígitos, separados por guiones cada 3
    secuencial_str = f"{secuencial:06d}"
    parte1 = secuencial_str[:3]
    parte2 = secuencial_str[3:]
    
    return f"CLM-{parte1}-{parte2}"

def obtener_siguiente_id(ultimo_id: str = None) -> str:
    """
    Obtiene el siguiente ID basado en el último ID usado
    
    Args:
        ultimo_id: Último ID usado (ej: "CLM-000-005")
        
    Returns:
        Siguiente ID (ej: "CLM-000-006")
    """
    if ultimo_id is None:
        return generar_id_reclamo(1)
    
    # Extraer el número del último ID
    try:
        # Quitar "CLM-" y los guiones para obtener el número
        numero_str = ultimo_id.replace("CLM-", "").replace("-", "")
        numero_actual = int(numero_str)
        siguiente_numero = numero_actual + 1
        return generar_id_reclamo(siguiente_numero)
    except (ValueError, AttributeError):
        # Si hay error, empezar desde 1
        return generar_id_reclamo(1)

# Ejemplos de uso
if __name__ == "__main__":
    print("=== GENERADOR DE IDs DE RECLAMO ===")
    
    # Generar algunos IDs secuenciales
    for i in range(1, 11):
        id_reclamo = generar_id_reclamo(i)
        print(f"Reclamo {i:2d}: {id_reclamo}")
    
    print("\n=== OBTENER SIGUIENTE ID ===")
    
    # Ejemplos de obtener siguiente ID
    ultimo_usado = "CLM-000-005"
    siguiente = obtener_siguiente_id(ultimo_usado)
    print(f"Último usado: {ultimo_usado}")
    print(f"Siguiente:    {siguiente}")
    
    # Ejemplo con ID más alto
    ultimo_usado = "CLM-001-234"
    siguiente = obtener_siguiente_id(ultimo_usado)
    print(f"Último usado: {ultimo_usado}")
    print(f"Siguiente:    {siguiente}")
    
    # Empezar desde cero
    primero = obtener_siguiente_id()
    print(f"Primer ID:    {primero}")
