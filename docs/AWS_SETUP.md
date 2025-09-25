# 🔐 Configuración AWS para Textract OCR

## 📋 Resumen de Opciones

El proyecto soporta **múltiples formas** de configurar las credenciales AWS:

| Método | Prioridad | Uso Recomendado | Seguridad |
|--------|-----------|-----------------|-----------|
| Archivo `.env` | 🥇 Alta | Desarrollo local | ⭐⭐⭐⭐ |
| Variables entorno | 🥈 Media | Servidores/Docker | ⭐⭐⭐ |
| Archivo credenciales | 🥉 Baja | Desarrollo | ⭐⭐ |
| IAM Roles | 🏆 Máxima | Producción AWS | ⭐⭐⭐⭐⭐ |

---

## 🚀 **Opción 1: Archivo .env (Recomendado para desarrollo)**

### 1. Crear archivo `.env`
```bash
# En la raíz del proyecto
touch .env  # Linux/Mac
# o crear archivo .env con notepad en Windows
```

### 2. Agregar credenciales
```env
# AWS Configuration
AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
```

### 3. Verificar que funciona
```bash
python -c "from config import AWS_ACCESS_KEY_ID; print('✅ AWS configurado' if AWS_ACCESS_KEY_ID else '❌ No configurado')"
```

---

## 🌍 **Opción 2: Variables de Entorno**

### Windows PowerShell:
```powershell
$env:AWS_ACCESS_KEY_ID="AKIA1234567890EXAMPLE"
$env:AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY"
$env:AWS_DEFAULT_REGION="us-east-1"

# Verificar
echo $env:AWS_ACCESS_KEY_ID
```

### Windows CMD:
```cmd
set AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
set AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
set AWS_DEFAULT_REGION=us-east-1

# Verificar
echo %AWS_ACCESS_KEY_ID%
```

### Linux/Mac:
```bash
export AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
export AWS_DEFAULT_REGION=us-east-1

# Verificar
echo $AWS_ACCESS_KEY_ID
```

---

## 📁 **Opción 3: Archivo de Credenciales AWS**

### 1. Ubicación del archivo:
```
Windows: C:\Users\{username}\.aws\credentials
Linux/Mac: ~/.aws/credentials
```

### 2. Contenido del archivo:
```ini
[default]
aws_access_key_id = AKIA1234567890EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
region = us-east-1
```

### 3. Configurar con AWS CLI:
```bash
# Instalar AWS CLI
pip install awscli

# Configurar
aws configure
```

---

## 🏢 **Opción 4: IAM Roles (Recomendado para producción)**

### En EC2/ECS/Lambda:
- ✅ No requiere credenciales en código
- ✅ Rotación automática de credenciales
- ✅ Máxima seguridad

### Configuración:
1. Crear IAM Role con política de Textract
2. Asignar role a la instancia EC2/contenedor
3. El código detectará automáticamente el role

---

## 🔑 **Obtener Credenciales AWS**

### 1. Crear Usuario IAM:
1. Ve a AWS Console → IAM → Users
2. Click "Add users"
3. Nombre: `textract-api-user`
4. Access type: ✅ Programmatic access
5. Attach policies: `AmazonTextractFullAccess` o crear custom

### 2. Política Mínima Personalizada:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "textract:DetectDocumentText",
                "textract:AnalyzeDocument"
            ],
            "Resource": "*"
        }
    ]
}
```

### 3. Guardar Credenciales:
- ⚠️ **Access Key ID**: Ej. `AKIA1234567890EXAMPLE`
- ⚠️ **Secret Access Key**: Solo se muestra **una vez**

---

## 🌎 **Regiones AWS Disponibles**

| Región | Código | Textract |
|--------|--------|----------|
| Virginia del Norte | `us-east-1` | ✅ |
| Ohio | `us-east-2` | ✅ |
| Oregon | `us-west-2` | ✅ |
| Irlanda | `eu-west-1` | ✅ |
| Londres | `eu-west-2` | ✅ |
| Sydney | `ap-southeast-2` | ✅ |

**Recomendación**: Usar `us-east-1` para mejores precios y disponibilidad.

---

## 🔍 **Verificar Configuración**

### 1. Health Check del API:
```bash
curl -X GET "http://localhost:8000/aws-textract-ocr/health"
```

### 2. Respuesta Exitosa:
```json
{
    "status": "ok",
    "servicio": "AWS Textract",
    "region": "us-east-1",
    "mensaje": "Conexión AWS Textract funcionando correctamente"
}
```

### 3. Respuesta de Error:
```json
{
    "detail": "AWS Textract no disponible: Unable to locate credentials"
}
```

---

## 🐳 **Configuración en Docker**

### docker-compose.yml:
```yaml
version: '3.8'
services:
  api-forense:
    build: .
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_DEFAULT_REGION=us-east-1
    ports:
      - "8000:8000"
```

### Archivo .env para Docker:
```env
AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
```

---

## 🚨 **Problemas Comunes**

### ❌ "Unable to locate credentials"
**Solución**: Configurar credenciales con cualquiera de los métodos arriba.

### ❌ "An error occurred (UnauthorizedOperation)"
**Solución**: Verificar permisos IAM del usuario.

### ❌ "An error occurred (InvalidParameterException)"
**Solución**: Verificar que la región soporte Textract.

### ❌ "An error occurred (ThrottlingException)"
**Solución**: Demasiadas peticiones, implementar retry logic.

---

## 💰 **Costos AWS Textract**

| Operación | Costo por página | Uso recomendado |
|-----------|------------------|-----------------|
| `DetectDocumentText` | ~$0.0015 | Extracción básica de texto |
| `AnalyzeDocument` | ~$0.05 | Análisis de tablas/formularios |

**Tip**: Para desarrollo, usa `DetectDocumentText` que es 33x más barato.

---

## 🔧 **Configuración Actual del Proyecto**

El proyecto está configurado para usar **automáticamente**:

1. **Primero**: Variables de `config.py` (desde .env o entorno)
2. **Segundo**: Credenciales del ambiente AWS
3. **Tercero**: IAM roles (si está en AWS)

### Verificar configuración actual:
```python
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION

print(f"Access Key: {'✅ Configurado' if AWS_ACCESS_KEY_ID else '❌ No configurado'}")
print(f"Secret Key: {'✅ Configurado' if AWS_SECRET_ACCESS_KEY else '❌ No configurado'}")
print(f"Región: {AWS_DEFAULT_REGION}")
```

---

## 📞 **Soporte**

Si tienes problemas:

1. ✅ Verifica que las credenciales sean válidas
2. ✅ Confirma permisos IAM
3. ✅ Prueba el health check endpoint
4. ✅ Revisa logs del servidor para errores específicos
