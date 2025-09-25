import base64
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import HTTPException

from config import MAX_PDF_BYTES, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION


class TextractClientHelper:
    """Helper para operaciones básicas de AWS Textract"""

    @staticmethod
    def create_textract_client():
        """Crea y configura el cliente de AWS Textract"""
        try:
            kwargs = {'region_name': AWS_DEFAULT_REGION}
            
            if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
                kwargs.update({
                    'aws_access_key_id': AWS_ACCESS_KEY_ID,
                    'aws_secret_access_key': AWS_SECRET_ACCESS_KEY
                })
                print(f"🔑 Usando credenciales AWS configuradas explícitamente para región: {AWS_DEFAULT_REGION}")
            else:
                print("⚠️  Usando credenciales AWS del ambiente (variables de entorno, IAM roles, etc.)")
            
            return boto3.client('textract', **kwargs)
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al configurar cliente AWS Textract: {str(e)}"
            )

    @staticmethod
    def validate_base64_document(document_b64: str) -> bytes:
        """Valida y decodifica el documento base64"""
        try:
            document_bytes = base64.b64decode(document_b64, validate=True)
        except Exception:
            raise HTTPException(
                status_code=400, 
                detail="El campo 'documentobase64' no es base64 válido."
            )
        
        if len(document_bytes) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=413, 
                detail=f"El documento excede el tamaño máximo permitido ({MAX_PDF_BYTES} bytes)."
            )
        
        return document_bytes

    @staticmethod
    def detect_document_type(document_bytes: bytes) -> str:
        """Detecta el tipo de documento basado en su contenido"""
        type_signatures = [
            (b'%PDF-', "PDF"),
            (b'\xFF\xD8\xFF', "JPEG"),
            (b'\x89PNG\r\n\x1a\n', "PNG"),
            (b'GIF87a', "GIF"),
            (b'GIF89a', "GIF"),
            (b'\x42\x4D', "BMP")
        ]
        
        for signature, doc_type in type_signatures:
            if document_bytes.startswith(signature):
                return doc_type
        
        if document_bytes.startswith(b'RIFF') and b'WEBP' in document_bytes[:12]:
            return "WEBP"
        
        return "UNKNOWN"

    @staticmethod
    def handle_textract_errors(func):
        """Decorador para manejar errores de AWS Textract"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                raise HTTPException(
                    status_code=400,
                    detail=f"Error de AWS Textract ({error_code}): {error_message}"
                )
            except BotoCoreError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error de configuración AWS: {str(e)}"
                )
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error inesperado con AWS Textract: {str(e)}"
                )
        return wrapper
