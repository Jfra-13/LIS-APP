# app-LIS - MVP0 (alineacion tecnica)

Este repositorio mantiene una base Django hospitalaria orientada a crecimiento incremental por MVPs.

## Estado actual del MVP0

- Apps activas: `core`, `admision`, `triage`, `medico`, `consulta`.
- Base tecnica mantenida: Django, autenticacion, Celery + RabbitMQ, Docker y PostgreSQL.
- Enfoque MVP0: ordenar responsabilidades y dejar una base limpia, sin redisenar flujos clinicos.

## Estructura objetivo de dominio (alto nivel)

```text
src/
|- core/       # autenticacion y layout base
|- admision/   # ingreso de paciente
|- triage/     # prioridad clinica inmutable
|- consulta/   # nota medica e integracion CIE-10 (base creada en MVP0)
|- medico/     # orquestacion de cola/estado
|- config/     # settings, urls, celery
|- tests/      # pruebas de integracion/e2e
```

## Alcance de MVP0

- Se crea y registra la app `consulta`.
- Se alinea la documentacion tecnica con el estado real del codigo.
- Se preservan `admision` y `triage` sin reescritura funcional.
- No se implementa UI final en esta fase.

## Ejecucion local

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Validar configuracion y migraciones

```bash
python src/manage.py check
python src/manage.py makemigrations
python src/manage.py migrate
```

### 3. Levantar servidor

```bash
python src/manage.py runserver
```

## Contenedores

```bash
docker compose up --build
```

## Criterio de terminado MVP0

- Proyecto inicia sin errores (`manage.py check`).
- Migraciones ejecutan sin conflictos.
- `consulta` queda registrada en `INSTALLED_APPS` y con estructura base.
