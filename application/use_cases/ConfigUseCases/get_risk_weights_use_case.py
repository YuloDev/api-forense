"""
Caso de uso para obtener risk weights.
"""

from typing import Dict, Any, Optional
from domain.ports.config.risk_weights_service import RiskWeightsServicePort
from domain.entities.config.risk_weights_collection import RiskWeightsCollection
from domain.entities.config.risk_weight import RiskWeight


class GetRiskWeightsUseCase:
    """Caso de uso para obtener risk weights"""
    
    def __init__(self, risk_weights_service: RiskWeightsServicePort):
        self.risk_weights_service = risk_weights_service
    
    def execute_all(self) -> Dict[str, Any]:
        """
        Obtiene todos los risk weights.
        
        Returns:
            Dict con todos los risk weights
        """
        try:
            weights_collection = self.risk_weights_service.get_all_risk_weights()
            return {
                "success": True,
                "data": weights_collection.to_json_dict(),
                "count": len(weights_collection)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo risk weights: {str(e)}",
                "data": {},
                "count": 0
            }
    
    def execute_single(self, key: str) -> Dict[str, Any]:
        """
        Obtiene un risk weight específico.
        
        Args:
            key: Clave del risk weight
            
        Returns:
            Dict con el risk weight solicitado
        """
        try:
            weight = self.risk_weights_service.get_risk_weight(key)
            if weight:
                return {
                    "success": True,
                    "data": {key: weight.to_dict()},
                    "count": 1
                }
            else:
                return {
                    "success": False,
                    "error": f"Risk weight '{key}' no encontrado",
                    "data": {},
                    "count": 0
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error obteniendo risk weight '{key}': {str(e)}",
                "data": {},
                "count": 0
            }
