"""
Paquete de helpers para análisis forense de PDFs.

Este paquete contiene módulos especializados para diferentes aspectos
del análisis forense de documentos PDF:

- validacion_financiera: Validación completa de contenido financiero
- firma_digital: Análisis avanzado de firmas digitales
"""

from .validacion_financiera import validar_contenido_financiero
from .firma_digital import analizar_firmas_digitales, tiene_firma_digital

__version__ = "1.0.0"
__author__ = "API-Forense Team"

# Exportar funciones principales para fácil importación
__all__ = [
    "validar_contenido_financiero",
    "analizar_firmas_digitales", 
    "tiene_firma_digital"
]
