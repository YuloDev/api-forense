# 📋 API de Reclamos - Documentación

## 🚀 Endpoints Disponibles

### **Base URL**: `http://127.0.0.1:8005`

---

## 📊 **GET /reclamos** - Listar Reclamos
Obtiene una lista de reclamos con filtros opcionales.

**Query Parameters:**
- `estado` (opcional): Filtrar por estado
- `proveedor` (opcional): Buscar por nombre de proveedor  
- `limit` (opcional): Límite de resultados (sin límite por defecto)
- `offset` (opcional, default=0): Desplazamiento para paginación

**Ejemplo:**
```bash
GET /reclamos?estado=En%20Revisión&limit=5
```

**Respuesta:**
```json
{
  "reclamos": [
    {
      "id_reclamo": "CLM-000-001",
      "fecha_envio": "19/08/2024",
      "proveedor": {
        "nombre": "Hospital San Juan",
        "tipo_servicio": "Consulta Especializada"
      },
      "estado": "Aprobado",
      "monto_solicitado": 450.00,
      "monto_aprobado": 405.00,
      "moneda": "$",
      "acciones": {
        "ver": true,
        "subir": false
      }
    }
  ],
  "total": 5,
  "limit": null,
  "offset": 0,
  "metadatos": {
    "total_reclamos": 5,
    "estados_disponibles": ["En Revisión", "Aprobado", "Rechazado"]
  }
}
```

---

## 🔍 **GET /reclamos/{id_reclamo}** - Obtener Reclamo Específico

**Ejemplo:**
```bash
GET /reclamos/CLM-000-001
```

**Respuesta:**
```json
{
  "id_reclamo": "CLM-000-001",
  "fecha_envio": "19/08/2024",
  "proveedor": {
    "nombre": "Hospital San Juan",
    "tipo_servicio": "Consulta Especializada"
  },
  "estado": "Aprobado",
  "monto_solicitado": 450.00,
  "monto_aprobado": 405.00,
  "moneda": "$",
  "acciones": {
    "ver": true,
    "subir": false
  }
}
```

---

## ➕ **POST /reclamos** - Crear Nuevo Reclamo

**Body (JSON):**
```json
{
  "proveedor": {
    "nombre": "Nuevo Proveedor",
    "tipo_servicio": "Consulta Médica"
  },
  "estado": "En Revisión",
  "monto_solicitado": 250.00,
  "moneda": "$",
  "observaciones": "Consulta de urgencia"
}
```

**Respuesta:**
```json
{
  "mensaje": "Reclamo creado exitosamente",
  "reclamo": {
    "id_reclamo": "CLM-000-006",
    "fecha_envio": "15/09/2024",
    "proveedor": {
      "nombre": "Nuevo Proveedor",
      "tipo_servicio": "Consulta Médica"
    },
    "estado": "En Revisión",
    "monto_solicitado": 250.00,
    "monto_aprobado": null,
    "moneda": "$",
    "acciones": {
      "ver": true,
      "subir": true
    }
  }
}
```

---

## ✏️ **PUT /reclamos/{id_reclamo}** - Actualizar Reclamo

**Body (JSON) - Campos opcionales:**
```json
{
  "estado": "Aprobado",
  "monto_aprobado": 200.00,
  "observaciones": "Aprobado con descuento"
}
```

**Respuesta:**
```json
{
  "mensaje": "Reclamo actualizado exitosamente",
  "reclamo": {
    "id_reclamo": "CLM-000-006",
    "estado": "Aprobado",
    "monto_aprobado": 200.00,
    // ... resto de campos
  }
}
```

---

## ❌ **DELETE /reclamos/{id_reclamo}** - Eliminar Reclamo

**Ejemplo:**
```bash
DELETE /reclamos/CLM-000-006
```

**Respuesta:**
```json
{
  "mensaje": "Reclamo CLM-000-006 eliminado exitosamente"
}
```

---

## 📈 **GET /reclamos/estadisticas/resumen** - Estadísticas

**Respuesta:**
```json
{
  "total_reclamos": 5,
  "por_estado": {
    "En Revisión": 4,
    "Aprobado": 1
  },
  "montos": {
    "total_solicitado": 1264.50,
    "total_aprobado": 405.00,
    "moneda": "$"
  },
  "estados_disponibles": ["En Revisión", "Aprobado", "Rechazado"]
}
```

---

## ⚙️ **GET /reclamos/config/estados** - Estados Disponibles

**Respuesta:**
```json
{
  "estados": ["En Revisión", "Aprobado", "Rechazado"],
  "descripcion": "Estados disponibles para los reclamos"
}
```

---

## 🎯 **Ejemplos de Uso con JavaScript/Fetch**

### Obtener todos los reclamos:
```javascript
const response = await fetch('http://127.0.0.1:8005/reclamos');
const data = await response.json();
console.log(data.reclamos);
```

### Crear un nuevo reclamo:
```javascript
const nuevoReclamo = {
  proveedor: {
    nombre: "Clínica ABC",
    tipo_servicio: "Examen Médico"
  },
  monto_solicitado: 150.00,
  moneda: "€"
};

const response = await fetch('http://127.0.0.1:8005/reclamos', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(nuevoReclamo)
});

const resultado = await response.json();
console.log(resultado.mensaje);
```

### Actualizar estado de un reclamo:
```javascript
const actualizacion = {
  estado: "Aprobado",
  monto_aprobado: 140.00
};

const response = await fetch('http://127.0.0.1:8005/reclamos/CLM-000-001', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(actualizacion)
});

const resultado = await response.json();
console.log(resultado.reclamo);
```

---

## 🔧 **Estados y Transiciones**

### Estados Disponibles:
- **"En Revisión"**: Estado inicial de todos los reclamos nuevos
- **"Aprobado"**: Reclamo aprobado (con o sin ajuste de monto)
- **"Rechazado"**: Reclamo rechazado

### Comportamiento de Acciones:
- **Estado "En Revisión"**: `ver: true, subir: true`
- **Estado "Aprobado"**: `ver: true, subir: false` 
- **Estado "Rechazado"**: `ver: true, subir: true` (para resubir documentos)

---

## 🚨 **Códigos de Error**

- **404**: Reclamo no encontrado
- **500**: Error interno del servidor
- **422**: Error de validación en los datos enviados

---

## 📝 **Notas**

- Los IDs se generan automáticamente con formato `CLM-000-001`
- Las fechas están en formato `DD/MM/YYYY`
- Los montos son números decimales
- La moneda por defecto es `$`
- Los datos se persisten en `reclamos_data.json`
