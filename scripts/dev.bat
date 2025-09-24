@echo off
echo ==========================================
echo   API Forense - Modo Desarrollo
echo ==========================================
echo.

if "%1"=="up" (
    echo Iniciando contenedor en modo desarrollo...
    docker-compose -f docker-compose.dev.yml up --build
    goto end
)

if "%1"=="down" (
    echo Deteniendo contenedor de desarrollo...
    docker-compose -f docker-compose.dev.yml down
    goto end
)

if "%1"=="logs" (
    echo Mostrando logs del contenedor...
    docker-compose -f docker-compose.dev.yml logs -f api-forense
    goto end
)

if "%1"=="restart" (
    echo Reiniciando contenedor...
    docker-compose -f docker-compose.dev.yml restart
    goto end
)

if "%1"=="shell" (
    echo Accediendo al shell del contenedor...
    docker-compose -f docker-compose.dev.yml exec api-forense /bin/bash
    goto end
)

echo.
echo Uso: dev.bat [comando]
echo.
echo Comandos disponibles:
echo   up       - Iniciar en modo desarrollo (con hot reload)
echo   down     - Detener contenedor
echo   logs     - Ver logs en tiempo real
echo   restart  - Reiniciar contenedor
echo   shell    - Acceder al shell del contenedor
echo.
echo Ejemplo: dev.bat up
echo.

:end
