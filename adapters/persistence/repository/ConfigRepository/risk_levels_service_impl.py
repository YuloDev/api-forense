"""
Implementación del servicio de niveles de riesgo.

Implementa el puerto RiskLevelsServicePort usando el file handler.
"""

from typing import Dict, Any
from domain.ports.config.risk_levels_service import RiskLevelsServicePort
from adapters.persistence.helpers.ConfigHelpers.risk_levels_file_handler import RiskLevelsFileHandler
from domain.entities.config.risk_level import RiskLevel
from domain.entities.config.risk_levels_collection import RiskLevelsCollection


class RiskLevelsServiceAdapter(RiskLevelsServicePort):
    """Adaptador para el servicio de niveles de riesgo"""
    
    def __init__(self, file_path: str = "risk_levels_config.json"):
        """
        Inicializa el adaptador.
        
        Args:
            file_path: Ruta al archivo de configuración
        """
        self.file_handler = RiskLevelsFileHandler(file_path)
    
    def get_all_levels(self) -> Dict[str, Any]:
        """
        Obtiene todos los niveles de riesgo.
        
        Returns:
            Dict con resultado de la operación
        """
        try:
            levels = self.file_handler.load_levels()
            levels_dict = levels.to_detailed_dict()
            
            return {
                "success": True,
                "data": levels_dict,
                "count": len(levels_dict),
                "message": "Niveles de riesgo obtenidos correctamente"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo niveles de riesgo: {str(e)}",
                "data": {},
                "count": 0
            }
    
    def get_level_by_name(self, name: str) -> Dict[str, Any]:
        """
        Obtiene un nivel de riesgo específico por nombre.
        
        Args:
            name: Nombre del nivel de riesgo
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            levels = self.file_handler.load_levels()
            level = levels.get_level_by_name(name)
            
            if level:
                return {
                    "success": True,
                    "data": level.to_dict(),
                    "count": 1,
                    "message": f"Nivel '{name}' obtenido correctamente"
                }
            else:
                return {
                    "success": False,
                    "error": f"Nivel de riesgo '{name}' no encontrado",
                    "data": {},
                    "count": 0
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo nivel '{name}': {str(e)}",
                "data": {},
                "count": 0
            }
    
    def get_level_by_score(self, score: int) -> Dict[str, Any]:
        """
        Obtiene el nivel de riesgo para un puntaje específico.
        
        Args:
            score: Puntaje a evaluar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            result = self.file_handler.get_level_by_score(score)
            
            # Convertir el formato del file handler al formato esperado por el caso de uso
            if result["success"]:
                return {
                    "success": True,
                    "data": result["level"],
                    "count": 1 if result["level"] else 0,
                    "message": result["message"]
                }
            else:
                return {
                    "success": False,
                    "error": result["message"],
                    "data": {},
                    "count": 0
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo nivel para puntaje {score}: {str(e)}",
                "data": {},
                "count": 0
            }
    
    def update_level(self, name: str, level_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un nivel de riesgo existente.
        
        Args:
            name: Nombre del nivel de riesgo
            level_data: Datos del nivel a actualizar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Validar datos
            validation = self.file_handler.validate_level_data(level_data)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": f"Error de validación: {validation['error']}",
                    "updated": False
                }
            
            # Cargar niveles existentes
            levels = self.file_handler.load_levels()
            
            # Crear nivel actualizado
            updated_level = RiskLevel(
                name=level_data["name"],
                min_score=int(level_data["min_score"]),
                max_score=int(level_data["max_score"]),
                description=level_data.get("description", "")
            )
            
            # Actualizar nivel
            levels.update_level(name, updated_level)
            
            # Guardar cambios
            self.file_handler.save_levels(levels)
            
            return {
                "success": True,
                "message": f"Nivel '{name}' actualizado correctamente",
                "data": updated_level.to_dict(),
                "updated": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error actualizando nivel '{name}': {str(e)}",
                "updated": False
            }
    
    def add_level(self, level_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agrega un nuevo nivel de riesgo.
        
        Args:
            level_data: Datos del nuevo nivel
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Validar datos
            validation = self.file_handler.validate_level_data(level_data)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": f"Error de validación: {validation['error']}",
                    "added": False
                }
            
            # Cargar niveles existentes
            levels = self.file_handler.load_levels()
            
            # Crear nuevo nivel
            new_level = RiskLevel(
                name=level_data["name"],
                min_score=int(level_data["min_score"]),
                max_score=int(level_data["max_score"]),
                description=level_data.get("description", "")
            )
            
            # Agregar nivel
            levels.add_level(new_level)
            
            # Guardar cambios
            self.file_handler.save_levels(levels)
            
            return {
                "success": True,
                "message": f"Nivel '{level_data['name']}' agregado correctamente",
                "data": new_level.to_dict(),
                "added": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error agregando nivel: {str(e)}",
                "added": False
            }
    
    def remove_level(self, name: str) -> Dict[str, Any]:
        """
        Elimina un nivel de riesgo.
        
        Args:
            name: Nombre del nivel a eliminar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Cargar niveles existentes
            levels = self.file_handler.load_levels()
            
            # Eliminar nivel
            levels.remove_level(name)
            
            # Guardar cambios
            self.file_handler.save_levels(levels)
            
            return {
                "success": True,
                "message": f"Nivel '{name}' eliminado correctamente",
                "data": {},
                "removed": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error eliminando nivel '{name}': {str(e)}",
                "removed": False
            }
    
    def update_all_levels(self, levels_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza todos los niveles de riesgo.
        
        Args:
            levels_data: Datos de todos los niveles
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            # Crear nueva colección desde los datos
            new_levels = RiskLevelsCollection.from_dict(levels_data)
            
            # Guardar cambios
            self.file_handler.save_levels(new_levels)
            
            return {
                "success": True,
                "message": "Todos los niveles de riesgo actualizados correctamente",
                "data": new_levels.to_detailed_dict(),
                "updated": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error actualizando todos los niveles: {str(e)}",
                "updated": False
            }
