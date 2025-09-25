# 🐳 Configuración Docker con AWS

Esta guía explica cómo ejecutar la API usando Docker con soporte completo para AWS Textract.

## 📋 Archivos Docker del Proyecto

| Archivo | Uso | Descripción |
|---------|-----|-------------|
| `build/Dockerfile` | Producción | Imagen optimizada para despliegue |
| `docker-compose.yml` | Producción | Orquestación para producción |
| `docker-compose.dev.yml` | Desarrollo | Con hot-reload y debugging |
| `.env.example.docker` | Configuración | Template para variables de entorno |

## 🚀 **Inicio Rápido**

### 1. **Configurar Variables AWS**
```bash
# Copiar template de configuración
cp .env.example.docker .env

# Editar archivo .env con tus credenciales reales
notepad .env  # Windows
nano .env     # Linux/Mac
```

### 2. **Agregar Credenciales AWS en .env**
```env
# En archivo .env
AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
```

### 3. **Ejecutar en Modo Desarrollo**
```bash
# Con hot-reload para desarrollo
docker-compose -f docker-compose.dev.yml up --build

# En background
docker-compose -f docker-compose.dev.yml up -d --build
```

### 4. **Ejecutar en Modo Producción**
```bash
# Para producción
docker-compose up --build

# En background
docker-compose up -d --build
```

---

## 🔧 **Configuración Detallada**

### **Opción 1: Archivo .env (Recomendado)**
```bash
# Crear archivo .env en la raíz del proyecto
cp .env.example.docker .env

# Editar con credenciales reales
```

**Contenido de .env:**
```env
AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
```

### **Opción 2: Variables de Sistema (CI/CD)**
```bash
# Definir en el sistema antes de ejecutar docker-compose
export AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
export AWS_DEFAULT_REGION=us-east-1

# Ejecutar docker-compose
docker-compose up
```

### **Opción 3: Inline en docker-compose**
```yaml
# Directamente en docker-compose.yml (NO recomendado para producción)
environment:
  - AWS_ACCESS_KEY_ID=AKIA1234567890EXAMPLE
  - AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY
  - AWS_DEFAULT_REGION=us-east-1
```

---

## 🏗️ **Estructura de Archivos Docker**

### **build/Dockerfile**
```dockerfile
# Variables AWS por defecto (región)
ENV AWS_DEFAULT_REGION=us-east-1

# Las credenciales se pasan via docker-compose
```

### **docker-compose.yml** (Producción)
```yaml
environment:
  # AWS desde archivo .env o variables del sistema
  - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
  - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
  - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
```

### **docker-compose.dev.yml** (Desarrollo)
```yaml
environment:
  # Misma configuración + variables de desarrollo
  - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
  - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
  - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
  - PYTHONUNBUFFERED=1
  - DEVELOPMENT=true
```

---

## 🎯 **Comandos Útiles**

### **Desarrollo**
```bash
# Iniciar con logs visibles
docker-compose -f docker-compose.dev.yml up

# Reconstruir imagen completa
docker-compose -f docker-compose.dev.yml up --build --force-recreate

# Ver logs en tiempo real
docker-compose -f docker-compose.dev.yml logs -f

# Entrar al contenedor
docker-compose -f docker-compose.dev.yml exec api-forense bash
```

### **Producción**
```bash
# Iniciar servicio
docker-compose up -d

# Ver estado de servicios
docker-compose ps

# Ver logs
docker-compose logs api-forense

# Parar servicios
docker-compose down
```

### **Debugging**
```bash
# Verificar variables de entorno en el contenedor
docker-compose exec api-forense env | grep AWS

# Probar conectividad AWS desde el contenedor
docker-compose exec api-forense curl http://localhost:8000/aws-textract-ocr/health

# Ver logs de la aplicación
docker-compose logs -f api-forense
```

---

## 🔍 **Verificar Configuración**

### **1. Health Check General**
```bash
curl http://localhost:9000/health
```

### **2. Health Check AWS Textract**
```bash
curl http://localhost:9000/aws-textract-ocr/health
```

### **3. Respuesta Exitosa**
```json
{
    "status": "ok",
    "servicio": "AWS Textract",
    "region": "us-east-1",
    "mensaje": "Conexión AWS Textract funcionando correctamente"
}
```

---

## 🚨 **Solución de Problemas**

### ❌ **"Unable to locate credentials"**
```bash
# Verificar que el archivo .env existe
ls -la .env

# Verificar contenido del archivo .env
cat .env | grep AWS

# Verificar variables en el contenedor
docker-compose exec api-forense env | grep AWS
```

### ❌ **"Connection refused"**
```bash
# Verificar que el contenedor está corriendo
docker-compose ps

# Verificar logs del contenedor
docker-compose logs api-forense

# Verificar puertos
netstat -tulpn | grep 9000
```

### ❌ **"No such file or directory" (.env)**
```bash
# Crear archivo .env desde template
cp .env.example.docker .env

# Editar con credenciales reales
nano .env
```

---

## 🏢 **Despliegue en Producción**

### **1. Con Docker Swarm**
```bash
# Convertir docker-compose para swarm
docker stack deploy -c docker-compose.yml api-forense-stack
```

### **2. Con Kubernetes**
```bash
# Convertir a manifiestos k8s (requiere kompose)
kompose convert -f docker-compose.yml
```

### **3. Variables de Entorno Seguras**
```bash
# Usar secretos de Docker
echo "AKIA1234567890EXAMPLE" | docker secret create aws_access_key_id -
echo "wJalrXUt..." | docker secret create aws_secret_access_key -
```

---

## ⚙️ **Personalización Avanzada**

### **Múltiples Regiones AWS**
```yaml
# docker-compose.yml
environment:
  - AWS_DEFAULT_REGION=${AWS_REGION:-us-east-1}
  - AWS_REGION_BACKUP=eu-west-1
```

### **Perfils AWS**
```yaml
# Para usar perfiles específicos
environment:
  - AWS_PROFILE=textract-profile
volumes:
  - ~/.aws:/home/appuser/.aws:ro
```

### **IAM Roles (ECS/EKS)**
```yaml
# No se necesitan credenciales, usar task role
environment:
  - AWS_DEFAULT_REGION=us-east-1
  # AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY no necesarios
```

---

## 📊 **Monitoreo**

### **Health Checks**
```yaml
# Ya incluido en docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### **Logs Centralizados**
```bash
# Enviar logs a archivo
docker-compose logs api-forense > api-forense.log

# Usar driver de logs específico
docker-compose up --log-driver=syslog
```

---

## 🔄 **Actualización de la Aplicación**

```bash
# 1. Parar servicios actuales
docker-compose down

# 2. Actualizar código (git pull, etc.)
git pull origin main

# 3. Reconstruir y reiniciar
docker-compose up --build -d

# 4. Verificar que funciona
curl http://localhost:9000/health
```

---

## 📚 **Recursos Adicionales**

- **Variables disponibles**: Ver `config.py` para todas las opciones
- **AWS Setup**: Ver `docs/AWS_SETUP.md` para obtener credenciales
- **API Documentation**: Ver `docs/AWS_TEXTRACT_OCR_API.md` para usar el endpoint
- **Instalación local**: Ver `docs/INSTALACION_LOCAL.md` para desarrollo sin Docker
