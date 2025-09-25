"""
Helper para manejo de archivos de configuración de niveles de riesgo.

Maneja la lectura y escritura del archivo risk_levels_config.json.
"""

import json
import os
from typing import Dict, Any, List
from domain.entities.config.risk_level import RiskLevel
from domain.entities.config.risk_levels_collection import RiskLevelsCollection


class RiskLevelsFileHandler:
    """Helper para manejo de archivos de niveles de riesgo"""
    
    def __init__(self, file_path: str = "risk_levels_config.json"):
        """
        Inicializa el handler con la ruta del archivo.
        
        Args:
            file_path: Ruta al archivo de configuración
        """
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Asegura que el archivo de configuración existe"""
        if not os.path.exists(self.file_path):
            # Crear archivo con configuración por defecto
            default_config = {
                "bajo": [0, 25],
                "medio": [26, 42],
                "alto": [43, 100]
            }
            self._write_to_file(default_config)
    
    def _read_from_file(self) -> Dict[str, List[int]]:
        """
        Lee la configuración desde el archivo JSON.
        
        Returns:
            Dict con la configuración de niveles de riesgo
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                return data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise Exception(f"Error leyendo archivo de configuración: {str(e)}")
    
    def _write_to_file(self, data: Dict[str, List[int]]) -> None:
        """
        Escribe la configuración al archivo JSON.
        
        Args:
            data: Datos a escribir
        """
        try:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
        except Exception as e:
            raise Exception(f"Error escribiendo archivo de configuración: {str(e)}")
    
    def load_levels(self) -> RiskLevelsCollection:
        """
        Carga los niveles de riesgo desde el archivo.
        
        Returns:
            RiskLevelsCollection con los niveles cargados
        """
        try:
            data = self._read_from_file()
            return RiskLevelsCollection.from_dict(data)
        except Exception as e:
            raise Exception(f"Error cargando niveles de riesgo: {str(e)}")
    
    def save_levels(self, levels: RiskLevelsCollection) -> None:
        """
        Guarda los niveles de riesgo al archivo.
        
        Args:
            levels: Colección de niveles a guardar
        """
        try:
            data = levels.to_dict()
            self._write_to_file(data)
        except Exception as e:
            raise Exception(f"Error guardando niveles de riesgo: {str(e)}")
    
    def get_level_by_score(self, score: int) -> Dict[str, Any]:
        """
        Obtiene el nivel de riesgo para un puntaje específico.
        
        Args:
            score: Puntaje a evaluar
            
        Returns:
            Dict con el nivel encontrado o None
        """
        try:
            levels = self.load_levels()
            level = levels.get_level_by_score(score)
            
            if level:
                return {
                    "success": True,
                    "level": level.to_dict(),
                    "message": f"Nivel encontrado para puntaje {score}"
                }
            else:
                return {
                    "success": False,
                    "level": None,
                    "message": f"No se encontró nivel para puntaje {score}"
                }
        except Exception as e:
            return {
                "success": False,
                "level": None,
                "message": f"Error obteniendo nivel: {str(e)}"
            }
    
    def validate_level_data(self, level_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida los datos de un nivel de riesgo.
        
        Args:
            level_data: Datos del nivel a validar
            
        Returns:
            Dict con resultado de la validación
        """
        try:
            # Validar campos requeridos
            if "name" not in level_data:
                return {"valid": False, "error": "El campo 'name' es requerido"}
            
            if "min_score" not in level_data or "max_score" not in level_data:
                return {"valid": False, "error": "Los campos 'min_score' y 'max_score' son requeridos"}
            
            # Validar tipos
            try:
                min_score = int(level_data["min_score"])
                max_score = int(level_data["max_score"])
            except (ValueError, TypeError):
                return {"valid": False, "error": "Los puntajes deben ser números enteros"}
            
            # Validar rangos
            if min_score < 0:
                return {"valid": False, "error": "El puntaje mínimo no puede ser negativo"}
            
            if max_score < min_score:
                return {"valid": False, "error": "El puntaje máximo no puede ser menor al mínimo"}
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": f"Error en validación: {str(e)}"}
