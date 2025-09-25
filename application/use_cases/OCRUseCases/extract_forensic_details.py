from typing import Dict, Any
from domain.entities.forensic_ocr_details import ForensicOCRDetails
from domain.ports.forensic_ocr_service import ForensicOCRServicePort


class ExtractForensicDetailsUseCase:
    """Caso de uso para extraer detalles forenses del OCR"""
    
    def __init__(self, forensic_ocr_service: ForensicOCRServicePort):
        self.forensic_ocr_service = forensic_ocr_service
    
    def execute_image(self, image_base64: str, tipo: str) -> Dict[str, Any]:
        """Ejecuta la extracción de detalles forenses para una imagen"""
        try:
            # Extraer detalles forenses de la imagen
            forensic_details = self.forensic_ocr_service.extract_forensic_details_from_image(image_base64, tipo)
            
            return forensic_details.to_dict()  # Convertir dataclass a dict usando método personalizado
        except Exception as e:
            from domain.entities.forensic_ocr_details import (
                SourceInfo, OCRInfo, MetricasOCR, Normalizaciones, 
                ForenseInfo, ResumenForense, TiemposMS
            )
            return ForensicOCRDetails(
                source=SourceInfo("", "", 0, 0, 0.0, 0.0),
                ocr=OCRInfo("", [], 0.0, 0.0, "", [], MetricasOCR(0.0, 0.0, 0.0, [])),
                normalizaciones=Normalizaciones([], [], [], [], []),
                forense=ForenseInfo([], ResumenForense(0.0, 0.0, False, False)),
                version="ocr-forense-1.0.0",
                tiempos_ms=TiemposMS(0, 0, 0),
                success=False,
                error=str(e)
            ).__dict__
    
    def execute_pdf(self, pdf_base64: str, tipo: str) -> Dict[str, Any]:
        """Ejecuta la extracción de detalles forenses para un PDF"""
        try:
            # Extraer detalles forenses del PDF
            forensic_details = self.forensic_ocr_service.extract_forensic_details_from_pdf(pdf_base64, tipo)
            
            return forensic_details.to_dict()  # Convertir dataclass a dict usando método personalizado
        except Exception as e:
            from domain.entities.forensic_ocr_details import (
                SourceInfo, OCRInfo, MetricasOCR, Normalizaciones, 
                ForenseInfo, ResumenForense, TiemposMS
            )
            return ForensicOCRDetails(
                source=SourceInfo("", "", 0, 0, 0.0, 0.0),
                ocr=OCRInfo("", [], 0.0, 0.0, "", [], MetricasOCR(0.0, 0.0, 0.0, [])),
                normalizaciones=Normalizaciones([], [], [], [], []),
                forense=ForenseInfo([], ResumenForense(0.0, 0.0, False, False)),
                version="ocr-forense-1.0.0",
                tiempos_ms=TiemposMS(0, 0, 0),
                success=False,
                error=str(e)
            ).__dict__
