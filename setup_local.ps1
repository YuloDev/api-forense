# API-Forense - Script de instalación local para PowerShell
# Ejecutar con: PowerShell -ExecutionPolicy Bypass -File setup_local.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   API-FORENSE - Instalacion Local" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Python está instalado
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Python detectado: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python no encontrado"
    }
} catch {
    Write-Host "ERROR: Python no está instalado" -ForegroundColor Red
    Write-Host ""
    Write-Host "Por favor instala Python 3.12+ desde:" -ForegroundColor Yellow
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Asegúrate de marcar 'Add Python to PATH' durante la instalación" -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Crear entorno virtual
Write-Host "Creando entorno virtual..." -ForegroundColor Yellow
try {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        throw "Error creando entorno virtual"
    }
    Write-Host "✓ Entorno virtual creado" -ForegroundColor Green
} catch {
    Write-Host "ERROR: No se pudo crear el entorno virtual" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Activar entorno virtual
Write-Host "Activando entorno virtual..." -ForegroundColor Yellow
try {
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "✓ Entorno virtual activado" -ForegroundColor Green
} catch {
    Write-Host "ERROR: No se pudo activar el entorno virtual" -ForegroundColor Red
    Write-Host "Puede que necesites cambiar la política de ejecución:" -ForegroundColor Yellow
    Write-Host "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}

# Actualizar pip
Write-Host "Actualizando pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Instalar dependencias
Write-Host "Instalando dependencias..." -ForegroundColor Yellow
try {
    pip install -r requerimientos.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Error instalando dependencias"
    }
    Write-Host "✓ Dependencias instaladas" -ForegroundColor Green
} catch {
    Write-Host "ERROR: No se pudieron instalar las dependencias" -ForegroundColor Red
    Write-Host ""
    Write-Host "Posibles soluciones:" -ForegroundColor Yellow
    Write-Host "1. Instalar Visual Studio Build Tools" -ForegroundColor Yellow
    Write-Host "2. Verificar conexión a internet" -ForegroundColor Yellow
    Write-Host "3. Ejecutar como administrador" -ForegroundColor Yellow
    Read-Host "Presiona Enter para salir"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "   INSTALACION COMPLETADA" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar el servidor:" -ForegroundColor Cyan
Write-Host "  .\start_server.bat" -ForegroundColor White
Write-Host ""
Write-Host "O manualmente:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
Write-Host "El servidor estará disponible en:" -ForegroundColor Cyan
Write-Host "  http://127.0.0.1:8005" -ForegroundColor White
Write-Host ""
Read-Host "Presiona Enter para continuar"
