"""
Helper para análisis de JavaScript embebido.

Analiza la presencia de código JavaScript embebido en documentos PDF.
"""

import re
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF
import pikepdf


class JavascriptAnalyzer:
    """Analizador de JavaScript embebido"""
    
    def __init__(self):
        # Patrones de JavaScript sospechosos
        self.suspicious_patterns = [
            r'eval\s*\(',
            r'Function\s*\(',
            r'setTimeout\s*\(',
            r'setInterval\s*\(',
            r'document\.write',
            r'innerHTML\s*=',
            r'outerHTML\s*=',
            r'window\.open',
            r'location\.href',
            r'document\.cookie',
            r'localStorage',
            r'sessionStorage',
            r'XMLHttpRequest',
            r'fetch\s*\(',
            r'atob\s*\(',
            r'btoa\s*\(',
            r'unescape\s*\(',
            r'escape\s*\(',
            r'decodeURIComponent',
            r'encodeURIComponent'
        ]
        
        # Patrones de eventos JavaScript
        self.event_patterns = [
            r'onclick\s*=',
            r'onload\s*=',
            r'onmouseover\s*=',
            r'onmouseout\s*=',
            r'onkeypress\s*=',
            r'onkeydown\s*=',
            r'onkeyup\s*=',
            r'onchange\s*=',
            r'onsubmit\s*=',
            r'onfocus\s*=',
            r'onblur\s*=',
            r'onresize\s*=',
            r'onscroll\s*='
        ]
        
        # Patrones de funciones JavaScript
        self.function_patterns = [
            r'function\s+\w+\s*\(',
            r'var\s+\w+\s*=\s*function',
            r'let\s+\w+\s*=\s*function',
            r'const\s+\w+\s*=\s*function',
            r'\(\s*\)\s*=>\s*{',
            r'function\s*\([^)]*\)\s*{'
        ]
    
    def analyze_pdf_javascript(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza JavaScript embebido en un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con información de JavaScript y análisis
        """
        try:
            # Abrir PDF con PyMuPDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            scripts_encontrados = []
            funciones_detectadas = []
            eventos_detectados = []
            indicadores_sospechosos = []
            
            # Buscar JavaScript en cada página
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Buscar en el contenido de la página
                page_scripts = self._find_javascript_in_page(page, page_num)
                scripts_encontrados.extend(page_scripts)
                
                # Extraer funciones y eventos de los scripts encontrados
                for script in page_scripts:
                    funciones_detectadas.extend(self._extract_functions(script.get("code", "")))
                    eventos_detectados.extend(self._extract_events(script.get("code", "")))
            
            # Buscar JavaScript en metadatos y objetos del PDF
            metadata_scripts = self._find_javascript_in_metadata(pdf_document)
            scripts_encontrados.extend(metadata_scripts)
            
            # Buscar JavaScript en formularios y anotaciones
            form_scripts = self._find_javascript_in_forms(pdf_document)
            scripts_encontrados.extend(form_scripts)
            
            pdf_document.close()
            
            # Analizar scripts encontrados
            cantidad_scripts = len(scripts_encontrados)
            scripts_sospechosos = self._analyze_suspicious_scripts(scripts_encontrados)
            
            # Generar indicadores sospechosos
            indicadores_sospechosos = self._generate_suspicious_indicators(
                cantidad_scripts, scripts_sospechosos, funciones_detectadas, eventos_detectados
            )
            
            return {
                "javascript_detectado": cantidad_scripts > 0,
                "cantidad_scripts": cantidad_scripts,
                "scripts_sospechosos": scripts_sospechosos,
                "scripts_encontrados": scripts_encontrados,
                "funciones_detectadas": list(set(funciones_detectadas)),
                "eventos_detectados": list(set(eventos_detectados)),
                "indicadores_sospechosos": indicadores_sospechosos
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando JavaScript del PDF: {str(e)}",
                "javascript_detectado": False,
                "cantidad_scripts": 0,
                "scripts_sospechosos": 0
            }
    
    def analyze_image_javascript(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza JavaScript embebido en una imagen (siempre retorna sin JavaScript).
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de JavaScript y análisis
        """
        # Las imágenes no pueden contener JavaScript embebido
        return {
            "javascript_detectado": False,
            "cantidad_scripts": 0,
            "scripts_sospechosos": 0,
            "scripts_encontrados": [],
            "funciones_detectadas": [],
            "eventos_detectados": [],
            "indicadores_sospechosos": []
        }
    
    def _find_javascript_in_page(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Busca JavaScript en el contenido de una página"""
        scripts = []
        
        try:
            # Obtener el texto de la página
            page_text = page.get_text()
            
            # Buscar patrones de JavaScript
            js_patterns = [
                r'<script[^>]*>(.*?)</script>',
                r'javascript:',
                r'on\w+\s*=\s*["\'][^"\']*["\']',
                r'<[^>]*\s+on\w+\s*=[^>]*>'
            ]
            
            for pattern in js_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    script_code = match.group(1) if match.groups() else match.group(0)
                    scripts.append({
                        "page": page_num + 1,
                        "type": "page_content",
                        "code": script_code,
                        "position": match.start(),
                        "suspicious": self._is_suspicious_code(script_code)
                    })
            
        except Exception:
            pass
        
        return scripts
    
    def _find_javascript_in_metadata(self, pdf_document) -> List[Dict[str, Any]]:
        """Busca JavaScript en metadatos del PDF"""
        scripts = []
        
        try:
            # Obtener metadatos
            metadata = pdf_document.metadata
            
            for key, value in metadata.items():
                if value and isinstance(value, str):
                    if self._contains_javascript(value):
                        scripts.append({
                            "page": 0,
                            "type": "metadata",
                            "code": value,
                            "position": 0,
                            "suspicious": self._is_suspicious_code(value),
                            "metadata_key": key
                        })
            
        except Exception:
            pass
        
        return scripts
    
    def _find_javascript_in_forms(self, pdf_document) -> List[Dict[str, Any]]:
        """Busca JavaScript en formularios y anotaciones"""
        scripts = []
        
        try:
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                # Buscar en anotaciones
                annotations = page.annots()
                for annot in annotations:
                    if hasattr(annot, 'content') and annot.content:
                        if self._contains_javascript(annot.content):
                            scripts.append({
                                "page": page_num + 1,
                                "type": "annotation",
                                "code": annot.content,
                                "position": 0,
                                "suspicious": self._is_suspicious_code(annot.content)
                            })
                
                # Buscar en widgets (formularios)
                widgets = page.widgets()
                for widget in widgets:
                    if hasattr(widget, 'field_value') and widget.field_value:
                        if self._contains_javascript(widget.field_value):
                            scripts.append({
                                "page": page_num + 1,
                                "type": "form_widget",
                                "code": widget.field_value,
                                "position": 0,
                                "suspicious": self._is_suspicious_code(widget.field_value)
                            })
            
        except Exception:
            pass
        
        return scripts
    
    def _contains_javascript(self, text: str) -> bool:
        """Verifica si un texto contiene JavaScript"""
        if not text:
            return False
        
        # Buscar patrones básicos de JavaScript
        js_indicators = [
            'javascript:', 'function', 'var ', 'let ', 'const ',
            'eval(', 'setTimeout', 'setInterval', 'onclick',
            'onload', 'onmouseover', 'document.', 'window.'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in js_indicators)
    
    def _is_suspicious_code(self, code: str) -> bool:
        """Determina si el código JavaScript es sospechoso"""
        if not code:
            return False
        
        code_lower = code.lower()
        
        # Verificar patrones sospechosos
        for pattern in self.suspicious_patterns:
            if re.search(pattern, code_lower):
                return True
        
        return False
    
    def _extract_functions(self, code: str) -> List[str]:
        """Extrae funciones JavaScript del código"""
        functions = []
        
        if not code:
            return functions
        
        for pattern in self.function_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                function_name = match.group(0).strip()
                functions.append(function_name)
        
        return functions
    
    def _extract_events(self, code: str) -> List[str]:
        """Extrae eventos JavaScript del código"""
        events = []
        
        if not code:
            return events
        
        for pattern in self.event_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                event_name = match.group(0).strip()
                events.append(event_name)
        
        return events
    
    def _analyze_suspicious_scripts(self, scripts: List[Dict[str, Any]]) -> int:
        """Analiza y cuenta scripts sospechosos"""
        suspicious_count = 0
        
        for script in scripts:
            if script.get("suspicious", False):
                suspicious_count += 1
        
        return suspicious_count
    
    def _generate_suspicious_indicators(self, cantidad_scripts: int, scripts_sospechosos: int, 
                                      funciones_detectadas: List[str], eventos_detectados: List[str]) -> List[str]:
        """Genera indicadores sospechosos basados en el análisis"""
        indicators = []
        
        if cantidad_scripts > 0:
            indicators.append(f"JavaScript detectado en documento PDF ({cantidad_scripts} scripts)")
        
        if scripts_sospechosos > 0:
            indicators.append(f"{scripts_sospechosos} scripts con patrones sospechosos")
        
        if len(funciones_detectadas) > 0:
            indicators.append(f"Funciones JavaScript detectadas: {len(funciones_detectadas)}")
        
        if len(eventos_detectados) > 0:
            indicators.append(f"Eventos JavaScript detectados: {len(eventos_detectados)}")
        
        if cantidad_scripts > 5:
            indicators.append("Múltiples scripts JavaScript - posible manipulación avanzada")
        
        if scripts_sospechosos > 2:
            indicators.append("Alto número de scripts sospechosos - posible código malicioso")
        
        return indicators
