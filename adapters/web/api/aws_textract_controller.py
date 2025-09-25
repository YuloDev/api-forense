from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from application.use_cases.AWSTextractUseCases.analyze_document_use_case import AnalyzeDocumentUseCase
from application.use_cases.AWSTextractUseCases.extract_forms_use_case import ExtractFormsUseCase
from application.use_cases.AWSTextractUseCases.extract_tables_use_case import ExtractTablesUseCase
from adapters.persistence.repository.AWSTextractRepository.aws_textract_service_impl import AWSTextractServiceAdapter


# Modelos de datos para la API
class PeticionTextract(BaseModel):
    """Modelo de petición para AWS Textract OCR"""
    documentobase64: str
    tipo_analisis: str = "DETECT_DOCUMENT_TEXT"
    features: Optional[List[str]] = None


class RespuestaTextract(BaseModel):
    """Modelo de respuesta del OCR con AWS Textract"""
    texto_extraido: str
    confianza_promedio: float
    total_bloques: int
    metadata: Dict[str, Any]
    mensaje: str


class ParClaveValor(BaseModel):
    """Modelo para un par clave-valor extraído de formularios"""
    pagina: int
    clave: str
    valor: str
    confianza_clave: float
    confianza_valor: float
    key_id: str
    value_id: Optional[str]
    selection_status: Optional[str]


class RespuestaFormularios(BaseModel):
    """Modelo de respuesta específico para formularios con pares clave-valor"""
    total_pares: int
    pares_clave_valor: List[ParClaveValor]
    confianza_promedio_claves: float
    confianza_promedio_valores: float
    tipo_documento: str
    mensaje: str


class CeldaTabla(BaseModel):
    """Modelo para una celda individual de tabla"""
    fila: int
    columna: int
    texto: str
    confianza: float
    cell_id: str
    es_header: bool = False
    es_merged: bool = False
    rowspan: int = 1
    colspan: int = 1


class TablaDetectada(BaseModel):
    """Modelo para una tabla completa detectada"""
    table_id: str
    numero_tabla: int
    total_filas: int
    total_columnas: int
    confianza: float
    celdas: List[CeldaTabla]
    titulo: Optional[str] = None
    pie_tabla: Optional[str] = None
    tipo_tabla: str = "STRUCTURED"


class ValidacionTabla(BaseModel):
    """Modelo para validación específica de una tabla"""
    tabla_id: str
    es_valida: bool
    problemas_detectados: List[str]
    celdas_vacias: int
    celdas_con_texto: int
    filas_completas: int
    columnas_completas: int
    score_integridad: float


class RespuestaTablas(BaseModel):
    """Modelo de respuesta específico para análisis de tablas"""
    total_tablas: int
    tablas_detectadas: List[TablaDetectada]
    validaciones: List[ValidacionTabla]
    confianza_promedio: float
    tipo_documento: str
    estadisticas: Dict[str, Any]
    mensaje: str


# Inicializar router y dependencias
router = APIRouter(tags=["AWS Textract"])

# Inyección de dependencias
textract_service = AWSTextractServiceAdapter()
analyze_document_use_case = AnalyzeDocumentUseCase(textract_service)
extract_forms_use_case = ExtractFormsUseCase(textract_service)
extract_tables_use_case = ExtractTablesUseCase(textract_service)


@router.post("/aws-textract-ocr", response_model=RespuestaTextract)
async def aws_textract_ocr(req: PeticionTextract):
    """
    Endpoint que recibe un documento en base64 y usa AWS Textract para OCR.
    """
    result = analyze_document_use_case.execute(
        document_base64=req.documentobase64,
        analysis_type=req.tipo_analisis,
        features=req.features
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return RespuestaTextract(
        texto_extraido=result["extracted_text"],
        confianza_promedio=result["average_confidence"],
        total_bloques=result["total_blocks"],
        metadata=result["metadata"],
        mensaje=result["message"]
    )


@router.post("/aws-textract-forms", response_model=RespuestaFormularios)
async def aws_textract_forms(req: PeticionTextract):
    """
    Endpoint específico para extraer pares clave-valor de formularios.
    """
    result = extract_forms_use_case.execute(req.documentobase64)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Convertir a modelos Pydantic
    pares_pydantic = [
        ParClaveValor(
            pagina=pair["page"],
            clave=pair["key"],
            valor=pair["value"],
            confianza_clave=pair["key_confidence"],
            confianza_valor=pair["value_confidence"],
            key_id=pair["key_id"],
            value_id=pair["value_id"],
            selection_status=pair["selection_status"]
        )
        for pair in result["key_value_pairs"]
    ]
    
    return RespuestaFormularios(
        total_pares=result["total_pairs"],
        pares_clave_valor=pares_pydantic,
        confianza_promedio_claves=result["average_key_confidence"],
        confianza_promedio_valores=result["average_value_confidence"],
        tipo_documento=result["document_type"],
        mensaje=result["message"]
    )


@router.post("/aws-textract-tables", response_model=RespuestaTablas)
async def aws_textract_tables(req: PeticionTextract):
    """
    Endpoint específico para extraer y validar tablas de documentos.
    """
    result = extract_tables_use_case.execute(req.documentobase64)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Convertir tablas a modelos Pydantic
    tablas_pydantic = [
        TablaDetectada(
            table_id=table["table_id"],
            numero_tabla=table["table_number"],
            total_filas=table["total_rows"],
            total_columnas=table["total_columns"],
            confianza=table["confidence"],
            celdas=[
                CeldaTabla(
                    fila=cell["row"],
                    columna=cell["column"],
                    texto=cell["text"],
                    confianza=cell["confidence"],
                    cell_id=cell["cell_id"],
                    es_header=cell["is_header"],
                    es_merged=cell["is_merged"],
                    rowspan=cell["rowspan"],
                    colspan=cell["colspan"]
                )
                for cell in table["cells"]
            ],
            titulo=table["title"],
            pie_tabla=table["footer"],
            tipo_tabla=table["table_type"]
        )
        for table in result["detected_tables"]
    ]
    
    # Convertir validaciones a modelos Pydantic
    validaciones_pydantic = [
        ValidacionTabla(
            tabla_id=validation["table_id"],
            es_valida=validation["is_valid"],
            problemas_detectados=validation["detected_problems"],
            celdas_vacias=validation["empty_cells"],
            celdas_con_texto=validation["cells_with_text"],
            filas_completas=validation["complete_rows"],
            columnas_completas=validation["complete_columns"],
            score_integridad=validation["integrity_score"]
        )
        for validation in result["validations"]
    ]
    
    return RespuestaTablas(
        total_tablas=result["total_tables"],
        tablas_detectadas=tablas_pydantic,
        validaciones=validaciones_pydantic,
        confianza_promedio=result["average_confidence"],
        tipo_documento=result["document_type"],
        estadisticas=result["statistics"],
        mensaje=result["message"]
    )
