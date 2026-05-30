# Proyecto LIS (Sistema de Información Clínica y Laboratorio)

Este proyecto es un sistema de gestión clínica desarrollado en **Python con Django**, diseñado para manejar la admisión de pacientes, triaje, consultas médicas, notas narrativas y prescripción de medicamentos. Todo el entorno está contenedorizado utilizando **Docker** para facilitar su despliegue y desarrollo.

---

## 🛠️ Tecnologías Utilizadas

- **Backend Framework:** Django (Python)
- **Base de Datos:** SQLite / PostgreSQL (según entorno)
- **Contenedores:** Docker & Docker Compose
- **Arquitectura:** Monolito modular basado en aplicaciones de Django (Apps).

---

## 🚀 Comandos de Docker (Gestión del Servidor)

El proyecto utiliza Docker Compose para orquestar los servicios. Ejecuta estos comandos desde la raíz del proyecto (donde se encuentra el archivo `docker-compose.yml`).

| Acción | Comando | Descripción |
|---|---|---|
| **Levantar Servidor** | `docker compose up -d` | Inicia los contenedores en segundo plano (modo detached). |
| **Forzar Reconstrucción** | `docker compose up --build` | Útil si agregaste nuevas dependencias (`requirements.txt`) o cambiaste el `Dockerfile`. |
| **Ver Logs en vivo** | `docker compose logs -f` | Muestra la consola del servidor en tiempo real. Usa `Ctrl + C` para salir de los logs. |
| **Detener Servidor** | `docker compose stop` | Detiene los contenedores sin eliminarlos. |
| **Apagar y Limpiar** | `docker compose down` | Detiene y elimina los contenedores de la sesión actual (recomendado para reiniciar limpio). |

---

## 🔐 Gestión de Usuarios y Administrador (Modo Interactivo)

Para ejecutar comandos administrativos dentro de Django (como crear usuarios o resetear bases de datos), la mejor forma es ingresar directamente a la terminal del contenedor de Docker.

### 1. Entrar al contenedor web
Asegúrate de que el contenedor esté corriendo (`docker compose up -d`), luego ejecuta:
```bash
docker compose exec web bash
```
*Una vez dentro, navega a la carpeta principal del código fuente:*
```bash
cd src
```

### 2. Crear un nuevo Superadministrador
Dentro de la carpeta `src` en el contenedor, ejecuta:
```bash
python manage.py createsuperuser
```
*(Te pedirá ingresar el Username, Email y el Password dos veces).*

### 3. Cambiar / Recuperar Contraseña de un usuario
Si el usuario ya existe pero olvidaste la contraseña, no es necesario borrar la base de datos, simplemente ejecuta:
```bash
python manage.py changepassword nombre_del_usuario
```
*(Ejemplo: `python manage.py changepassword admin`)*.

### 4. Salir del contenedor
Cuando termines, simplemente escribe:
```bash
exit
```

---

## 📦 Carga de Datos Iniciales (Seeders)

El proyecto cuenta con comandos personalizados para poblar la base de datos con información base (catálogos).

Para cargar el catálogo de **Medicamentos** desde el archivo JSON (`medicamentos.json`), entra al contenedor (ver paso 1 de Gestión de Usuarios) y ejecuta:

```bash
python manage.py cargar_medicamentos
```
*Nota: Este comando limpia la tabla actual y vuelve a insertar los medicamentos para evitar duplicados.*

---

## 📂 Estructura del Proyecto y Rutas (Paths)

El proyecto está dividido en aplicaciones modulares para separar la lógica de negocio.

| Path / Directorio | Uso / Propósito |
|---|---|
| `/docker-compose.yml` | Archivo principal de orquestación de Docker. Define los servicios (web, db, etc.). |
| `/src/` | Carpeta raíz del backend de Django. Aquí reside `manage.py`. |
| `/src/core/` | Configuraciones globales de Django, utilidades compartidas y el modelo base (`AbstractBaseModel`). |
| `/src/admision/` | App responsable del registro y gestión de la información demográfica de los `Pacientes`. |
| `/src/triage/` | App para la toma de signos vitales, evaluación inicial y clasificación del paciente (`Triaje`). |
| `/src/consulta/` | App para la atención médica. Incluye `NotaMedica`, Catálogo de `Medicamento` y `Prescripcion`. |
| `/src/consulta/data/` | Directorio que almacena los archivos estáticos de datos semilla (ej. `medicamentos.json`). |
| `/src/consulta/management/`| Comandos de consola personalizados (`cargar_medicamentos.py`). |

---

## 🌐 URLs y Endpoints Principales

Una vez levantado el servidor (`http://localhost:8000`), puedes acceder a las siguientes rutas:

| URL | Descripción |
|---|---|
| `/admin/` | Panel de superadministrador de Django. Permite crear y gestionar todos los registros de la DB. |
| `/login/` | Pantalla de inicio de sesión para el personal médico/administrativo. |
| `/home/` | Dashboard principal con acceso rápido según rol de usuario. |
| `/admision/pacientes/` | Listado de pacientes para técnicos administrativos. |
| `/triage/` | Registro de triaje para enfermería. |
| `/consulta/` | Gestión de notas médicas y recetas. |
| `/medico/cola/` | Cola de atención para médicos. |
| `/paciente/dashboard/` | Portal del paciente para ver sus recetas. |

*(Agrega aquí más rutas conforme el frontend o la API vaya creciendo)*.

---

## 🎨 Mejoras de Frontend (v1.0)

### Stack de Tecnologías Frontend Implementado

✅ **Bootstrap 5.3.3** - Framework CSS moderno  
✅ **Bootstrap Icons 1.11.3** - Librería de iconos  
✅ **HTMX 1.9.11** - Interactividad sin JavaScript vanilla  
✅ **Alpine.js 3.x** - Reactividad ligera en el navegador  

### Cambios Implementados

1. **Login Mejorado** - Validación en vivo, mostrar/ocultar contraseña
2. **Dashboard Home** - Tarjetas interactivas por rol, diseño moderno
3. **Lista de Pacientes** - Búsqueda en tiempo real, tablas responsivas
4. **Formulario de Triaje** - Validación visual de signos vitales, alertas automáticas
5. **Diseño Responsivo** - Funciona perfecto en móvil, tablet y desktop

### Características Principales

- 🎯 **Validación Reactiva**: Feedback visual mientras escribes
- 🎨 **Diseño Bootstrap**: Moderno y profesional
- ⚡ **Performance**: Debounce en búsquedas, lazy loading
- 🔔 **Alertas Inteligentes**: Mostradas según valores críticos
- 📱 **Mobile First**: Totalmente responsivo

### Documentación

Para detalles completos sobre las mejoras implementadas, ver:
- 📖 [`FRONTEND_IMPROVEMENTS.md`](./FRONTEND_IMPROVEMENTS.md) - Documentación técnica
- 📚 [`FRONTEND_TUTORIALS.md`](./FRONTEND_TUTORIALS.md) - Tutoriales con ejemplos

### Cómo Extender

Consulta [`FRONTEND_TUTORIALS.md`](./FRONTEND_TUTORIALS.md) para:
- Crear modales con Alpine.js
- Implementar búsquedas en tiempo real con HTMX
- Hacer tabs/acordeones interactivos
- Validar formularios progresivamente
- Cargar contenido dinámico sin recargar

---
