@echo off
echo ========================================
echo   API-FORENSE - Instalacion Local
echo ========================================
echo.

REM Verificar si Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo.
    echo Por favor instala Python 3.12+ desde:
    echo https://www.python.org/downloads/
    echo.
    echo Asegurate de marcar "Add Python to PATH" durante la instalacion
    pause
    exit /b 1
)

echo Python detectado:
python --version
echo.

REM Crear entorno virtual
echo Creando entorno virtual...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: No se pudo crear el entorno virtual
    pause
    exit /b 1
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Actualizar pip
echo Actualizando pip...
python -m pip install --upgrade pip

REM Instalar dependencias
echo Instalando dependencias...
pip install -r requerimientos.txt
if %errorlevel% neq 0 (
    echo ERROR: No se pudieron instalar las dependencias
    echo.
    echo Posibles soluciones:
    echo 1. Instalar Visual Studio Build Tools
    echo 2. Verificar conexion a internet
    echo 3. Ejecutar como administrador
    pause
    exit /b 1
)

echo.
echo ========================================
echo   INSTALACION COMPLETADA
echo ========================================
echo.
echo Para iniciar el servidor ejecuta:
echo   start_server.bat
echo.
echo O manualmente:
echo   venv\Scripts\activate
echo   python main.py
echo.
echo El servidor estara disponible en:
echo   http://127.0.0.1:8005
echo.
pause
