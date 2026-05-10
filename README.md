# app-LIS MVP0 base técnica

Este repositorio quedó reducido a una base Django mínima para el MVP0:

- `core` como app activa principal.
- `triage` y `nlp_engine` archivadas en `_archived_apps/`.
- usuario personalizado con PK UUID.
- login, home protegida y landing pública.
- Docker con Django + PostgreSQL 15.

## Estructura actual

- `src/config/settings.py`: configuración del proyecto.
- `src/config/urls.py`: ruteo principal.
- `src/core/`: app activa del MVP0.
- `_archived_apps/triage/`: flujo clínico anterior archivado.
- `_archived_apps/nlp_engine/`: procesamiento NLP anterior archivado.

## Ejecución local

### 1. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 2. Ejecutar migraciones
```bash
python src/manage.py makemigrations
python src/manage.py migrate
```

### 3. Levantar el servidor
```bash
python src/manage.py runserver
```

## Contenedores

```bash
docker compose up --build
```

## Nota sobre CI/CD

La configuración de Jenkins, protección de rama en GitHub y el flujo final de GitHub Actions deben hacerse fuera del código del proyecto, en la plataforma correspondiente.
