"""
Caso de uso para actualizar niveles de riesgo.

Maneja la lógica de negocio para actualizar niveles de riesgo.
"""

from typing import Dict, Any
from domain.ports.config.risk_levels_service import RiskLevelsServicePort


class UpdateRiskLevelsUseCase:
    """Caso de uso para actualizar niveles de riesgo"""
    
    def __init__(self, risk_levels_service: RiskLevelsServicePort):
        """
        Inicializa el caso de uso.
        
        Args:
            risk_levels_service: Servicio de niveles de riesgo
        """
        self.risk_levels_service = risk_levels_service
    
    def execute_single(self, name: str, level_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza un nivel de riesgo específico.
        
        Args:
            name: Nombre del nivel de riesgo
            level_data: Datos del nivel a actualizar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "El nombre del nivel es requerido",
                    "updated": False
                }
            
            result = self.risk_levels_service.update_level(name, level_data)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "updated": result["updated"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "updated": result["updated"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "updated": False
            }
    
    def execute_add(self, level_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Agrega un nuevo nivel de riesgo.
        
        Args:
            level_data: Datos del nuevo nivel
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            result = self.risk_levels_service.add_level(level_data)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "added": result["added"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "added": result["added"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "added": False
            }
    
    def execute_remove(self, name: str) -> Dict[str, Any]:
        """
        Elimina un nivel de riesgo.
        
        Args:
            name: Nombre del nivel a eliminar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "El nombre del nivel es requerido",
                    "removed": False
                }
            
            result = self.risk_levels_service.remove_level(name)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "removed": result["removed"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "removed": result["removed"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "removed": False
            }
    
    def execute_all(self, levels_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualiza todos los niveles de riesgo.
        
        Args:
            levels_data: Datos de todos los niveles
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            result = self.risk_levels_service.update_all_levels(levels_data)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": result["message"],
                    "data": result["data"],
                    "updated": result["updated"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "updated": result["updated"]
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "updated": False
            }
