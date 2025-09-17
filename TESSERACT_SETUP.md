# Instalación de Tesseract OCR para Windows

Para que funcione la API de OCR, necesitas instalar **Tesseract OCR** en tu sistema.

## 🔧 Instalación en Windows

### Opción 1: Instalador Directo (Recomendado)

1. **Descarga Tesseract para Windows:**
   - Ve a: https://github.com/UB-Mannheim/tesseract/wiki
   - Descarga la versión más reciente (64-bit)
   - Ejemplo: `tesseract-ocr-w64-setup-5.3.3.20231005.exe`

2. **Ejecuta el instalador:**
   - Ejecuta como administrador
   - Acepta la ruta por defecto: `C:\Program Files\Tesseract-OCR`
   - **IMPORTANTE**: Marca la opción "Add to PATH" durante la instalación

3. **Instalar paquetes de idiomas (Opcional):**
   - Durante la instalación, asegúrate de incluir:
     - ✅ **Spanish** (spa)
     - ✅ **English** (eng) - ya incluido por defecto
     - ✅ **Script and orientation detection** (osd)

### Opción 2: Usando Chocolatey

```powershell
# Instalar Chocolatey si no lo tienes
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Instalar Tesseract
choco install tesseract

# Instalar idiomas adicionales
choco install tesseract-languages
```

### Opción 3: Usando Scoop

```powershell
# Instalar Scoop si no lo tienes
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex

# Instalar Tesseract
scoop install tesseract

# Agregar bucket para idiomas
scoop bucket add extras
scoop install tesseract-languages
```

## ✅ Verificar Instalación

### 1. Verificar en Terminal/PowerShell:
```bash
tesseract --version
```

**Resultado esperado:**
```
tesseract 5.3.3
 leptonica-1.83.1
  libgif 5.2.1 : libjpeg 8d (libjpeg-turbo 3.0.1) : libpng 1.6.40 : libtiff 4.6.0 : zlib 1.3 : libwebp 1.3.2 : libopenjp2 2.5.0
 Found AVX2
 Found AVX
 Found FMA
 Found SSE4.1
 Found libarchive 3.7.2 zlib/1.3.0 liblzma/5.4.4 bz2/1.0.8 liblz4/1.9.4 libzstd/1.5.5
```

### 2. Verificar idiomas disponibles:
```bash
tesseract --list-langs
```

**Resultado esperado:**
```
List of available languages (3):
eng
osd
spa
```

### 3. Probar en Python:
```python
import pytesseract
print("Versión:", pytesseract.get_tesseract_version())
print("Idiomas:", pytesseract.get_languages())
```

## 🔧 Configuración Adicional (Si es necesario)

### Si Tesseract no se encuentra en PATH:

1. **Agregar manualmente al PATH:**
   - Ve a "Variables de entorno del sistema"
   - Edita la variable `PATH`
   - Agrega: `C:\Program Files\Tesseract-OCR`

2. **O configurar en Python:**
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Ubicaciones típicas de instalación:
- `C:\Program Files\Tesseract-OCR\tesseract.exe`
- `C:\Users\{username}\scoop\apps\tesseract\current\tesseract.exe`
- `C:\tools\tesseract\tesseract.exe` (Chocolatey)

## 🌍 Paquetes de Idiomas Adicionales

Si necesitas más idiomas después de la instalación:

### Descarga manual:
1. Ve a: https://github.com/tesseract-ocr/tessdata/
2. Descarga archivos `.traineddata` para idiomas específicos
3. Cópialos a: `C:\Program Files\Tesseract-OCR\tessdata\`

### Idiomas disponibles:
- `spa.traineddata` - Español
- `eng.traineddata` - Inglés
- `fra.traineddata` - Francés
- `deu.traineddata` - Alemán
- `por.traineddata` - Portugués
- Y muchos más...

## 🧪 Probar la API OCR

Una vez instalado Tesseract, puedes probar la API:

### 1. Verificar disponibilidad:
```bash
curl http://localhost:8000/ocr-info
```

### 2. Probar OCR básico:
```bash
curl -X POST "http://localhost:8000/ocr-pdf-upload" \
  -F "file=@documento.pdf" \
  -F "lang=spa"
```

## ❌ Solución de Problemas

### Error: "tesseract is not recognized"
- ✅ Verifica que Tesseract esté en el PATH
- ✅ Reinicia PowerShell/Terminal después de la instalación
- ✅ Reinstala Tesseract marcando "Add to PATH"

### Error: "Failed loading language 'spa'"
- ✅ Instala paquetes de idiomas adicionales
- ✅ Verifica que `spa.traineddata` esté en `tessdata/`

### Error: "Permission denied"
- ✅ Ejecuta como administrador
- ✅ Verifica permisos de la carpeta de instalación

### Rendimiento lento:
- ✅ Usa PSM mode apropiado (6 para bloques de texto)
- ✅ Optimiza DPI (300 es bueno para la mayoría de casos)
- ✅ Considera usar `force_ocr: false` para usar texto embebido cuando sea posible

¡Una vez instalado Tesseract, tu API OCR estará completamente funcional! 🎉
