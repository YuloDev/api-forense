from typing import Dict, Any, List, Tuple, Optional

from domain.entities.aws_textract_forms import KeyValuePair


class KeyValueProcessor:
    """Procesador especializado para pares clave-valor de Textract"""

    def __init__(self, blocks_map: Dict[str, Dict[str, Any]]):
        self.blocks_map = blocks_map

    def extract_pairs(self, blocks: List[Dict[str, Any]]) -> List[KeyValuePair]:
        """Extrae todos los pares clave-valor"""
        key_value_pairs = []
        
        for block in blocks:
            if self._is_key_block(block):
                pair = self._create_key_value_pair(block)
                if pair:
                    key_value_pairs.append(pair)
        
        return key_value_pairs

    def _is_key_block(self, block: Dict[str, Any]) -> bool:
        """Verifica si el bloque es un KEY"""
        return (block.get('BlockType') == 'KEY_VALUE_SET' and 
                block.get('EntityTypes') and 
                'KEY' in block.get('EntityTypes'))

    def _create_key_value_pair(self, key_block: Dict[str, Any]) -> KeyValuePair:
        """Crea un par clave-valor desde un bloque KEY"""
        key_id = key_block.get('Id')
        key_text = self._get_complete_text(key_id)
        key_confidence = key_block.get('Confidence', 0.0)
        
        value_info = self._extract_value_info(key_block)
        
        return KeyValuePair(
            page=key_block.get('Page', 1),
            key=key_text,
            value=value_info["text"],
            key_confidence=round(key_confidence, 8),
            value_confidence=round(value_info["confidence"], 8),
            key_id=key_id,
            value_id=value_info["value_id"],
            selection_status=value_info["selection_status"]
        )

    def _extract_value_info(self, key_block: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae información del valor asociado a una clave"""
        relationships = key_block.get('Relationships', [])
        
        for rel in relationships:
            if rel.get('Type') == 'VALUE':
                value_ids = rel.get('Ids', [])
                if value_ids:
                    value_id = value_ids[0]
                    text, confidence, selection_status = self._get_real_value(value_id)
                    return {
                        "text": text,
                        "confidence": confidence,
                        "value_id": value_id,
                        "selection_status": selection_status
                    }
        
        # No se encontró VALUE
        return {
            "text": "",
            "confidence": key_block.get('Confidence', 0.0),
            "value_id": None,
            "selection_status": None
        }

    def _get_complete_text(self, block_id: str) -> str:
        """Obtiene texto completo de un bloque"""
        block = self.blocks_map.get(block_id)
        if not block:
            return ""
        
        if block.get('Text'):
            return block.get('Text', '').strip()
        
        return self._extract_child_texts(block)

    def _extract_child_texts(self, block: Dict[str, Any]) -> str:
        """Extrae textos de los bloques hijo"""
        texts = []
        relationships = block.get('Relationships', [])
        
        for rel in relationships:
            if rel.get('Type') == 'CHILD':
                for child_id in rel.get('Ids', []):
                    child_block = self.blocks_map.get(child_id)
                    if child_block:
                        child_text = child_block.get('Text', '').strip()
                        if child_text:
                            texts.append(child_text)
        
        return ' '.join(texts)

    def _get_real_value(self, value_block_id: str) -> Tuple[str, float, str]:
        """Obtiene el valor real de un VALUE block"""
        value_block = self.blocks_map.get(value_block_id)
        if not value_block:
            return "", 0.0, None
        
        confidence = value_block.get('Confidence', 0.0)
        
        # Verificar si es un SELECTION_ELEMENT directo
        selection_status = value_block.get('SelectionStatus')
        if selection_status:
            return selection_status, confidence, selection_status
        
        # Obtener texto del value
        text = self._get_complete_text(value_block_id)
        
        # Buscar SELECTION_ELEMENT en children si no hay texto
        if not text:
            selection_info = self._find_selection_element(value_block)
            if selection_info:
                return selection_info
        
        return text, confidence, None

    def _find_selection_element(self, value_block: Dict[str, Any]) -> Optional[Tuple[str, float, str]]:
        """Busca elementos de selección en los hijos"""
        relationships = value_block.get('Relationships', [])
        
        for rel in relationships:
            if rel.get('Type') == 'CHILD':
                result = self._check_child_selection_elements(rel.get('Ids', []))
                if result:
                    return result
        
        return None

    def _check_child_selection_elements(self, child_ids: List[str]) -> Optional[Tuple[str, float, str]]:
        """Verifica elementos de selección en una lista de IDs hijo"""
        for child_id in child_ids:
            child_block = self.blocks_map.get(child_id)
            if child_block and child_block.get('BlockType') == 'SELECTION_ELEMENT':
                selection_status = child_block.get('SelectionStatus')
                if selection_status:
                    return (selection_status, 
                           child_block.get('Confidence', 0.0), 
                           selection_status)
        return None
