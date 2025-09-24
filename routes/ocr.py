#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Endpoint de OCR para extracción de texto de imágenes y PDFs
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from core.ocrLogic.servicios.ocr_service import ForensicOCRService


# Modelos de datos
class ImageOCRRequest(BaseModel):
    """Modelo para peticiones de OCR de imágenes"""
    image_base64: str


class PDFOCRRequest(BaseModel):
    """Modelo para peticiones de OCR de PDFs"""
    pdf_base64: str


# Inicializar router y servicio
router = APIRouter(prefix="/ocr", tags=["OCR"])
ocr_service = ForensicOCRService()


@router.post("/extract-image")
async def extract_text_from_image(request: ImageOCRRequest):
    """
    Extraer texto de una imagen usando OCR
    
    Args:
        request: Datos de la imagen (solo base64)
        
    Returns:
        Respuesta con texto extraído y metadatos
    """
    try:
        result = ocr_service.extract_from_image(request.image_base64)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content=result
            )
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "text": "",
                "language": "spa+eng",
                "confidence": 0.0,
                "word_count": 0,
                "processing_time": 0.0,
                "error": str(e)
            }
        )


@router.post("/extract-pdf")
async def extract_text_from_pdf(request: PDFOCRRequest):
    """
    Extraer texto de un PDF usando OCR
    
    Args:
        request: Datos del PDF (solo base64)
        
    Returns:
        Respuesta con texto extraído de todas las páginas
    """
    try:
        result = ocr_service.extract_from_pdf(request.pdf_base64)
        
        if result["success"]:
            return JSONResponse(
                status_code=200,
                content=result
            )
        else:
            return JSONResponse(
                status_code=400,
                content=result
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "pages": [],
                "total_pages": 0,
                "total_text": "",
                "language": "spa+eng",
                "average_confidence": 0.0,
                "total_word_count": 0,
                "processing_time": 0.0,
                "error": str(e)
            }
        )
