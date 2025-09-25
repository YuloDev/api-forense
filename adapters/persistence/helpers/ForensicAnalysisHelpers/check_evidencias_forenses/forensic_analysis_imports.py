"""
Imports para las funciones de análisis forense existentes.
"""

# Importar las funciones necesarias del helper existente
try:
    from helpers.analisis_forense_profesional import (
        analizar_metadatos_forenses,
        detectar_texto_sintetico_aplanado,
        detectar_texto_sobrepuesto,
        safe_serialize_dict
    )
except ImportError:
    # Fallback si no se pueden importar las funciones
    def analizar_metadatos_forenses(imagen_bytes):
        return {"error": "Función no disponible"}
    
    def detectar_texto_sintetico_aplanado(imagen_bytes, metadatos):
        return {"error": "Función no disponible"}
    
    def detectar_texto_sobrepuesto(imagen_bytes):
        return {"error": "Función no disponible"}
    
    def safe_serialize_dict(data):
        return data
