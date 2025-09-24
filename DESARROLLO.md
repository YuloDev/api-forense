# Desarrollo con Hot Reload

## 🔥 Configuración para desarrollo con recarga automática

### Opción 1: Usar docker-compose.dev.yml (Recomendado)

```bash
# Iniciar en modo desarrollo
dev.bat up

# Ver logs en tiempo real
dev.bat logs

# Detener
dev.bat down

# Reiniciar
dev.bat restart

# Acceder al shell del contenedor
dev.bat shell
```

### Opción 2: Usar docker-compose.yml modificado

```bash
# El archivo docker-compose.yml ya está configurado con hot reload
docker-compose up --build
```

## ✨ Características del modo desarrollo

- **Hot Reload**: Los cambios se reflejan automáticamente sin reiniciar el contenedor
- **Código montado**: Tu código local se monta en el contenedor
- **Logs detallados**: Configurado con `--log-level debug`
- **Puerto expuesto**: Disponible en `http://localhost:9000`

## 📁 Archivos creados para desarrollo

- `docker-compose.dev.yml`: Configuración específica para desarrollo
- `.dockerignore`: Optimiza la construcción y hot reload
- `dev.bat`: Script de comandos para desarrollo
- `config.env.dev`: Variables de entorno para desarrollo

## 🛠️ Funcionamiento del Hot Reload

1. **Volumen montado**: Tu código se monta como volumen (`-v .:/app`)
2. **Uvicorn --reload**: El servidor detecta cambios automáticamente
3. **Exclusiones**: Los archivos `__pycache__` y `.git` se excluyen

## 📝 Notas importantes

- Los cambios en archivos `.py` se recargan automáticamente
- Los cambios en `requirements.txt` requieren reconstruir (`docker-compose up --build`)
- Los archivos en `.dockerignore` no se sincronizan
