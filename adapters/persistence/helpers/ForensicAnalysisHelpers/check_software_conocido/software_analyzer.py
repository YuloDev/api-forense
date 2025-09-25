"""
Helper para análisis de software conocido.

Analiza el software usado para crear PDFs y determina si es confiable o sospechoso.
"""

import fitz
import pikepdf
from typing import Dict, Any, Optional, List
import re


class SoftwareAnalyzer:
    """Analizador de software conocido"""
    
    def __init__(self):
        # Lista de software conocido y confiable
        self.trusted_software = [
            "Adobe Acrobat",
            "Adobe Acrobat Pro",
            "Adobe Acrobat Standard",
            "Adobe Acrobat Reader",
            "Adobe PDF Library",
            "Adobe InDesign",
            "Adobe Illustrator",
            "Adobe Photoshop",
            "Microsoft Word",
            "Microsoft Excel",
            "Microsoft PowerPoint",
            "Microsoft Office",
            "LibreOffice",
            "OpenOffice",
            "Google Docs",
            "Google Sheets",
            "Google Slides",
            "iText",
            "iTextSharp",
            "PDFtk",
            "Ghostscript",
            "wkhtmltopdf",
            "Chrome",
            "Firefox",
            "Safari",
            "Edge"
        ]
        
        # Lista de software sospechoso o desconocido
        self.suspicious_software = [
            "Unknown",
            "Custom",
            "Internal",
            "Proprietary",
            "Modified",
            "Cracked",
            "Pirated",
            "Hacked",
            "Tool",
            "Generator",
            "Creator",
            "Maker",
            "Builder",
            "Editor",
            "Modifier"
        ]
        
        # Patrones sospechosos en nombres de software
        self.suspicious_patterns = [
            r"crack",
            r"hack",
            r"pirate",
            r"illegal",
            r"stolen",
            r"fake",
            r"clone",
            r"copy",
            r"mod",
            r"cracked",
            r"hacked",
            r"pirated",
            r"illegal",
            r"stolen",
            r"fake",
            r"clone",
            r"copy",
            r"modified",
            r"custom",
            r"internal",
            r"proprietary"
        ]
    
    def analyze_pdf_software(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza el software usado para crear un PDF.
        
        Args:
            pdf_bytes: Bytes del archivo PDF
            
        Returns:
            Dict con información de software y análisis
        """
        try:
            # Análisis con PyMuPDF
            pymupdf_result = self._analyze_pdf_pymupdf(pdf_bytes)
            
            # Análisis con pikepdf
            pikepdf_result = self._analyze_pdf_pikepdf(pdf_bytes)
            
            # Combinar resultados
            combined_result = self._combine_pdf_results(pymupdf_result, pikepdf_result)
            
            return combined_result
            
        except Exception as e:
            return {
                "error": f"Error analizando software PDF: {str(e)}",
                "creator": None,
                "producer": None,
                "has_creator": False,
                "has_producer": False
            }
    
    def _analyze_pdf_pymupdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Análisis de software usando PyMuPDF"""
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            metadata = doc.metadata
            
            creator = metadata.get('creator')
            producer = metadata.get('producer')
            
            doc.close()
            
            return {
                "creator": creator,
                "producer": producer,
                "has_creator": creator is not None and creator.strip() != "",
                "has_producer": producer is not None and producer.strip() != "",
                "metadata_source": "pymupdf",
                "raw_metadata": metadata
            }
            
        except Exception as e:
            return {
                "error": f"Error en análisis PyMuPDF: {str(e)}",
                "creator": None,
                "producer": None,
                "has_creator": False,
                "has_producer": False
            }
    
    def _analyze_pdf_pikepdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Análisis de software usando pikepdf"""
        try:
            with pikepdf.open(pdf_bytes) as pdf:
                metadata = pdf.docinfo
                
                creator = None
                producer = None
                
                # Extraer Creator
                if hasattr(metadata, 'Creator') and metadata.Creator:
                    creator = str(metadata.Creator)
                
                # Extraer Producer
                if hasattr(metadata, 'Producer') and metadata.Producer:
                    producer = str(metadata.Producer)
                
                return {
                    "creator": creator,
                    "producer": producer,
                    "has_creator": creator is not None and creator.strip() != "",
                    "has_producer": producer is not None and producer.strip() != "",
                    "metadata_source": "pikepdf",
                    "raw_metadata": {
                        "Creator": str(metadata.Creator) if hasattr(metadata, 'Creator') else None,
                        "Producer": str(metadata.Producer) if hasattr(metadata, 'Producer') else None,
                        "Title": str(metadata.Title) if hasattr(metadata, 'Title') else None,
                        "Author": str(metadata.Author) if hasattr(metadata, 'Author') else None,
                        "Subject": str(metadata.Subject) if hasattr(metadata, 'Subject') else None,
                        "Keywords": str(metadata.Keywords) if hasattr(metadata, 'Keywords') else None
                    }
                }
                
        except Exception as e:
            return {
                "error": f"Error en análisis pikepdf: {str(e)}",
                "creator": None,
                "producer": None,
                "has_creator": False,
                "has_producer": False
            }
    
    def _combine_pdf_results(self, pymupdf_result: Dict, pikepdf_result: Dict) -> Dict[str, Any]:
        """Combina resultados de PyMuPDF y pikepdf"""
        # Priorizar pikepdf para metadatos más precisos
        creator = pikepdf_result.get("creator") or pymupdf_result.get("creator")
        producer = pikepdf_result.get("producer") or pymupdf_result.get("producer")
        
        # Detectar inconsistencias
        inconsistencies = []
        if (pymupdf_result.get("creator") and pikepdf_result.get("creator") and 
            pymupdf_result["creator"] != pikepdf_result["creator"]):
            inconsistencies.append("Inconsistencia en Creator entre PyMuPDF y pikepdf")
        
        if (pymupdf_result.get("producer") and pikepdf_result.get("producer") and 
            pymupdf_result["producer"] != pikepdf_result["producer"]):
            inconsistencies.append("Inconsistencia en Producer entre PyMuPDF y pikepdf")
        
        return {
            "creator": creator,
            "producer": producer,
            "has_creator": creator is not None and creator.strip() != "",
            "has_producer": producer is not None and producer.strip() != "",
            "inconsistencies": inconsistencies,
            "pymupdf_result": pymupdf_result,
            "pikepdf_result": pikepdf_result
        }
    
    def classify_software(self, software_name: Optional[str]) -> Dict[str, Any]:
        """
        Clasifica el software según su confiabilidad.
        
        Args:
            software_name: Nombre del software a clasificar
            
        Returns:
            Dict con clasificación del software
        """
        if not software_name or software_name.strip() == "":
            return {
                "category": "missing",
                "is_known": False,
                "is_trusted": False,
                "confidence": 0.0,
                "suspicious_indicators": ["Software no especificado"]
            }
        
        software_lower = software_name.lower()
        
        # Verificar si es software confiable
        is_trusted = any(trusted.lower() in software_lower for trusted in self.trusted_software)
        
        # Verificar si es software sospechoso
        is_suspicious = any(suspicious.lower() in software_lower for suspicious in self.suspicious_software)
        
        # Verificar patrones sospechosos
        suspicious_patterns_found = []
        for pattern in self.suspicious_patterns:
            if re.search(pattern, software_lower):
                suspicious_patterns_found.append(f"Patrón sospechoso detectado: '{pattern}'")
        
        # Determinar categoría
        if is_trusted and not is_suspicious and not suspicious_patterns_found:
            category = "known_trusted"
            confidence = 0.9
        elif is_suspicious or suspicious_patterns_found:
            category = "known_suspicious"
            confidence = 0.8
        elif any(trusted.lower() in software_lower for trusted in self.trusted_software):
            category = "known_trusted"
            confidence = 0.7
        else:
            category = "unknown"
            confidence = 0.5
        
        # Combinar indicadores sospechosos
        all_suspicious_indicators = []
        if is_suspicious:
            all_suspicious_indicators.append("Software marcado como sospechoso")
        all_suspicious_indicators.extend(suspicious_patterns_found)
        
        return {
            "category": category,
            "is_known": is_trusted or is_suspicious,
            "is_trusted": is_trusted and not is_suspicious and not suspicious_patterns_found,
            "confidence": confidence,
            "suspicious_indicators": all_suspicious_indicators
        }
    
    def analyze_software_combination(self, creator: Optional[str], producer: Optional[str]) -> Dict[str, Any]:
        """
        Analiza la combinación de Creator y Producer.
        
        Args:
            creator: Software Creator
            producer: Software Producer
            
        Returns:
            Dict con análisis de la combinación
        """
        creator_analysis = self.classify_software(creator)
        producer_analysis = self.classify_software(producer)
        
        # Análisis de consistencia
        inconsistencies = []
        if creator and producer and creator != producer:
            inconsistencies.append("Creator y Producer diferentes")
        
        if creator_analysis["category"] != producer_analysis["category"]:
            inconsistencies.append("Categorías de software diferentes entre Creator y Producer")
        
        # Determinar categoría general
        if creator_analysis["is_trusted"] and producer_analysis["is_trusted"]:
            general_category = "known_trusted"
            general_confidence = 0.9
        elif creator_analysis["is_trusted"] or producer_analysis["is_trusted"]:
            general_category = "known_trusted"
            general_confidence = 0.7
        elif creator_analysis["category"] == "known_suspicious" or producer_analysis["category"] == "known_suspicious":
            general_category = "known_suspicious"
            general_confidence = 0.8
        elif creator_analysis["category"] == "unknown" or producer_analysis["category"] == "unknown":
            general_category = "unknown"
            general_confidence = 0.5
        else:
            general_category = "missing"
            general_confidence = 0.0
        
        # Combinar indicadores sospechosos
        all_suspicious_indicators = []
        all_suspicious_indicators.extend(creator_analysis["suspicious_indicators"])
        all_suspicious_indicators.extend(producer_analysis["suspicious_indicators"])
        all_suspicious_indicators.extend(inconsistencies)
        
        return {
            "general_category": general_category,
            "general_confidence": general_confidence,
            "creator_analysis": creator_analysis,
            "producer_analysis": producer_analysis,
            "inconsistencies": inconsistencies,
            "all_suspicious_indicators": all_suspicious_indicators
        }
    
    def analyze_image_software(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Analiza el software usado para crear una imagen.
        
        Args:
            image_bytes: Bytes del archivo de imagen
            
        Returns:
            Dict con información de software y análisis
        """
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            import io
            
            # Abrir imagen
            image = Image.open(io.BytesIO(image_bytes))
            
            # Extraer metadatos EXIF
            exif_data = {}
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif is not None:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif_data[tag] = value
            
            # Extraer información de software
            software = exif_data.get('Software', '')
            make = exif_data.get('Make', '')
            model = exif_data.get('Model', '')
            
            # Combinar información de software
            combined_software = []
            if software:
                combined_software.append(software)
            if make:
                combined_software.append(make)
            if model:
                combined_software.append(model)
            
            creator = ' '.join(combined_software) if combined_software else None
            producer = exif_data.get('Software', None)
            
            return {
                "creator": creator,
                "producer": producer,
                "has_creator": creator is not None and creator.strip() != "",
                "has_producer": producer is not None and producer.strip() != "",
                "exif_data": exif_data,
                "software": software,
                "make": make,
                "model": model,
                "metadata_source": "exif"
            }
            
        except Exception as e:
            return {
                "error": f"Error analizando software de imagen: {str(e)}",
                "creator": None,
                "producer": None,
                "has_creator": False,
                "has_producer": False
            }
