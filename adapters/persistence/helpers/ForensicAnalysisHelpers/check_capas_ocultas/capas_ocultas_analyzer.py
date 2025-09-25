"""
Helper para detección de capas ocultas.

Utiliza la misma lógica que el helper existente en analisis_imagenes.py
"""

import io
from typing import Dict, Any, List, Optional
from PIL import Image


class CapasOcultasAnalyzer:
    """Analizador de capas ocultas usando la lógica existente del proyecto"""
    
    def __init__(self):
        pass
    
    def analyze_image_capas_ocultas(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza capas ocultas en una imagen usando la lógica existente.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de capas ocultas
        """
        try:
            # Detectar tipo de archivo
            imagen = Image.open(io.BytesIO(image_bytes))
            tipo_archivo = self._detectar_tipo_archivo(imagen)
            
            # Usar la función existente del helper
            result = self._analizar_capas_imagen(image_bytes, tipo_archivo)
            
            return result
            
        except Exception as e:
            return {
                "error": f"Error analizando capas ocultas: {str(e)}",
                "tiene_capas": False,
                "total_capas": 0,
                "capas": [],
                "capas_ocultas": 0,
                "modos_mezcla": [],
                "sospechosas": []
            }
    
    def _detectar_tipo_archivo(self, imagen: Image.Image) -> str:
        """Detecta el tipo de archivo de la imagen"""
        try:
            formato = imagen.format
            if formato == "PSD":
                return "PSD"
            elif formato == "TIFF":
                return "TIFF"
            elif formato in ["JPEG", "JPG"]:
                return "JPEG"
            elif formato == "PNG":
                return "PNG"
            else:
                return formato or "UNKNOWN"
        except Exception:
            return "UNKNOWN"
    
    def _analizar_capas_imagen(self, imagen_bytes: bytes, tipo_archivo: str) -> Dict[str, Any]:
        """
        Función idéntica a analizar_capas_imagen del helper original.
        Analiza capas en imágenes que las soportan (PSD, TIFF con capas).
        """
        capas_info = {
            "tiene_capas": False,
            "total_capas": 0,
            "capas": [],
            "capas_ocultas": 0,
            "modos_mezcla": [],
            "sospechosas": []
        }
        
        try:
            if tipo_archivo == "PSD":
                capas_info = self._analizar_capas_psd(imagen_bytes)
            elif tipo_archivo == "TIFF":
                capas_info = self._analizar_capas_tiff(imagen_bytes)
            else:
                capas_info["mensaje"] = f"Tipo de archivo {tipo_archivo} no soporta capas"
                
            return capas_info
            
        except Exception as e:
            return {
                "error": f"Error analizando capas: {str(e)}",
                "tiene_capas": False,
                "total_capas": 0,
                "capas": [],
                "capas_ocultas": 0,
                "modos_mezcla": [],
                "sospechosas": []
            }
    
    def _analizar_capas_psd(self, imagen_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza capas específicamente en archivos PSD.
        Función idéntica al helper original.
        """
        # Por ahora, implementación básica
        # En una implementación completa, se usaría una librería como psd-tools
        return {
            "tiene_capas": True,
            "total_capas": 0,  # Se implementaría con psd-tools
            "capas": [],
            "capas_ocultas": 0,
            "modos_mezcla": [],
            "sospechosas": [],
            "mensaje": "Análisis de capas PSD requiere librería psd-tools"
        }
    
    def _analizar_capas_tiff(self, imagen_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza capas en archivos TIFF.
        Función idéntica al helper original.
        """
        try:
            imagen = Image.open(io.BytesIO(imagen_bytes))
            
            # TIFF puede tener múltiples páginas/capas
            capas = []
            try:
                for i in range(imagen.n_frames):
                    imagen.seek(i)
                    capas.append({
                        "indice": i,
                        "tamaño": imagen.size,
                        "modo": imagen.mode,
                        "visible": True  # Asumir visible por defecto
                    })
            except:
                capas = [{
                    "indice": 0,
                    "tamaño": imagen.size,
                    "modo": imagen.mode,
                    "visible": True
                }]
            
            return {
                "tiene_capas": len(capas) > 1,
                "total_capas": len(capas),
                "capas": capas,
                "capas_ocultas": 0,
                "modos_mezcla": [],
                "sospechosas": []
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando TIFF: {str(e)}",
                "tiene_capas": False,
                "total_capas": 0,
                "capas": [],
                "capas_ocultas": 0,
                "modos_mezcla": [],
                "sospechosas": []
            }
