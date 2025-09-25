"""
Caso de uso para obtener niveles de riesgo.

Maneja la lógica de negocio para obtener niveles de riesgo.
"""

from typing import Dict, Any
from domain.ports.config.risk_levels_service import RiskLevelsServicePort


class GetRiskLevelsUseCase:
    """Caso de uso para obtener niveles de riesgo"""
    
    def __init__(self, risk_levels_service: RiskLevelsServicePort):
        """
        Inicializa el caso de uso.
        
        Args:
            risk_levels_service: Servicio de niveles de riesgo
        """
        self.risk_levels_service = risk_levels_service
    
    def execute_all(self) -> Dict[str, Any]:
        """
        Obtiene todos los niveles de riesgo.
        
        Returns:
            Dict con resultado de la operación
        """
        try:
            result = self.risk_levels_service.get_all_levels()
            
            if result["success"]:
                return {
                    "success": True,
                    "message": "Niveles de riesgo obtenidos correctamente",
                    "data": result["data"],
                    "count": result["count"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "data": {},
                    "count": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "data": {},
                "count": 0
            }
    
    def execute_by_name(self, name: str) -> Dict[str, Any]:
        """
        Obtiene un nivel de riesgo específico por nombre.
        
        Args:
            name: Nombre del nivel de riesgo
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "El nombre del nivel es requerido",
                    "data": {},
                    "count": 0
                }
            
            result = self.risk_levels_service.get_level_by_name(name)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Nivel de riesgo '{name}' obtenido correctamente",
                    "data": result["data"],
                    "count": result["count"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "data": {},
                    "count": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "data": {},
                "count": 0
            }
    
    def execute_by_score(self, score: int) -> Dict[str, Any]:
        """
        Obtiene el nivel de riesgo para un puntaje específico.
        
        Args:
            score: Puntaje a evaluar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            if not isinstance(score, int) or score < 0:
                return {
                    "success": False,
                    "error": "El puntaje debe ser un número entero no negativo",
                    "data": {},
                    "count": 0
                }
            
            result = self.risk_levels_service.get_level_by_score(score)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Nivel encontrado para puntaje {score}",
                    "data": result["data"],
                    "count": result["count"]
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "data": {},
                    "count": 0
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Error interno: {str(e)}",
                "data": {},
                "count": 0
            }
