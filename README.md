# app-LIS — Triaje Hospitalario Inteligente

Sistema Django para el flujo clínico de urgencias: **admisión → triaje →
cola de atención → consulta médica** con sugerencia de códigos **CIE-10**.

> Para el detalle del estado del proyecto y el plan de trabajo:
> - **[`ESTADO_ACTUAL.md`](ESTADO_ACTUAL.md)** — auditoría técnica (qué hay hoy).
> - **[`PLAN_PENDIENTES.md`](PLAN_PENDIENTES.md)** — plan de cierre por fases.

## Stack

- **Python 3.12 + Django 5.0** (patrón MVT).
- **PostgreSQL 15** (producción/Docker) · **SQLite** (fallback local).
- **RabbitMQ + Celery** para procesamiento asíncrono.
- **HTMX + Bootstrap 5 + Alpine.js** en la capa de presentación (SSR).
- **spaCy** (normalización lingüística) + **catálogo JSON determinístico**
  para la sugerencia CIE-10 — enfoque **híbrido**: spaCy lematiza y limpia el
  texto, el motor determinístico cruza esos lemas contra el catálogo. spaCy
  **no** se usa como clasificador de Machine Learning.
- **simple_history** (historización de triajes) · **WeasyPrint** (recetas PDF).

## Apps

| App | Responsabilidad |
|-----|-----------------|
| `core` | Usuario (UUID), base abstracta, landing/home, grupos de permisos |
| `admision` | Registro y gestión de pacientes (RF-01) |
| `triage` | Captura de biometría y cálculo inmutable de prioridad (RF-02/03) |
| `medico` | Cola de atención y transiciones de estado (RF-04) |
| `consulta` | Nota médica, recetas y sugerencia CIE-10 (RF-05/06/07) |
| `portal_paciente` | Portal del paciente (consultas y recetas) |
| `autenticacion_paciente` | Acceso del paciente por *magic link* vía email |

## Roles y grupos de permisos

Los grupos se crean automáticamente vía **migraciones de datos** (no requieren
fixtures): `Admision`, `Enfermeros`, `Medicos`, `Pacientes`. Son la única fuente
de verdad para los permisos.

## Ejecución local

### Con Docker (recomendado)

```bash
cp .env.example .env   # ajustar variables
docker compose up --build
```

Levanta `db` (PostgreSQL), `web` (Django), `rabbitmq` y `worker` (Celery).

### Sin Docker

```bash
pip install -r requirements.txt
python -m spacy download es_core_news_sm   # modelo NLP en español
python src/manage.py migrate
python src/manage.py createsuperuser
python src/manage.py runserver
```

## Tests

El proyecto vive bajo `src/`, así que las pruebas necesitan `src` en el
`PYTHONPATH`:

```bash
# Suite completa con cobertura (gate configurado en pytest.ini)
PYTHONPATH=src python -m pytest

# Rápido, sin cobertura
PYTHONPATH=src python -m pytest -q --no-cov
```

## CI/CD

`.github/workflows/` (CI, despliegue a staging y main) + `Jenkinsfile` +
`.pre-commit-config.yaml` (black, flake8). La protección de rama se configura en
la plataforma, fuera del repositorio.
