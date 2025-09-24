@echo off
echo ========================================
echo   API-FORENSE - Iniciando Servidor
echo ========================================
echo.

REM Verificar si existe el entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Entorno virtual no encontrado
    echo.
    echo Ejecuta primero: setup_local.bat
    pause
    exit /b 1
)

REM Activar entorno virtual
echo Activando entorno virtual...
call venv\Scripts\activate.bat

REM Verificar que las dependencias esten instaladas
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Dependencias no instaladas
    echo.
    echo Ejecuta: setup_local.bat
    pause
    exit /b 1
)

echo.
echo Iniciando servidor API-Forense...
echo.
echo Servidor disponible en:
echo   - Health: http://127.0.0.1:8005/health
echo   - Docs:   http://127.0.0.1:8005/docs
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

REM Iniciar servidor
python main.py
