# app-LIS — Triaje Hospitalario Inteligente

Sistema **Django** para el flujo clínico de urgencias:
**admisión → triaje → cola de atención → consulta médica**, con sugerencia
asistida de códigos **CIE-10** y portal del paciente por *magic link*.

Aplicación **hypermedia** (renderizado en servidor con HTMX + cotton), sin SPA:
cada rol entra a una vista aislada y propia, con una estética de clínica
profesional, sobria y densa.

> Documentación complementaria:
> - **[`ESTADO_ACTUAL.md`](ESTADO_ACTUAL.md)** — auditoría técnica (qué hay hoy).
> - **[`PLAN_PENDIENTES.md`](PLAN_PENDIENTES.md)** — plan de cierre por fases (backend).
> - **[`PLAN_UIUX.md`](PLAN_UIUX.md)** — plan de rediseño de interfaz por rol (Fases A–E, completas).

---

## Capturas

> _Pendiente: se agregarán capturas de cada perfil (login, dashboards, triaje,
> cola en vivo, consulta + sugerencia CIE-10, portal del paciente)._

<!--
| Login | Cola de atención (médico) | Consulta + CIE-10 |
|-------|---------------------------|-------------------|
| ![login](docs/img/login.png) | ![cola](docs/img/cola.png) | ![consulta](docs/img/consulta.png) |
-->

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Lenguaje / framework | **Python 3.12** · **Django 5.0** (patrón MVT) |
| Base de datos | **PostgreSQL 15** (Docker/prod) · **SQLite** (fallback local automático) |
| Tareas asíncronas | **Celery 5** + **RabbitMQ** (broker) |
| Presentación | **HTMX** · **Alpine.js** · **Bootstrap 5** · **django-cotton** (componentes) |
| NLP CIE-10 | **spaCy** (`es_core_news_sm/md`) como **normalizador** + catálogo JSON determinístico |
| Estáticos | **WhiteNoise** (`CompressedManifestStaticFilesStorage`) |
| Otros | **simple_history** (historización de triajes) · **WeasyPrint** (recetas PDF) |

> **Enfoque CIE-10 (híbrido, no caja negra):** spaCy lematiza y limpia el texto
> clínico; el motor determinístico cruza esos lemas contra el catálogo JSON.
> spaCy **no** se usa como clasificador de Machine Learning.

---

## Apps

| App | Responsabilidad |
|-----|-----------------|
| `core` | Usuario (UUID), modelo base abstracto, despacho por rol, dashboards, navegación, shell cotton, grupos de permisos |
| `admision` | Registro y gestión de pacientes (RF-01) |
| `triage` | Captura de biometría y cálculo inmutable de prioridad Manchester (RF-02/03) |
| `medico` | Cola de atención en tiempo real y FSM de estados (RF-04) |
| `consulta` | Nota clínica (Markdown), recetas y sugerencia CIE-10 (RF-05/06/07) |
| `portal_paciente` | Portal del paciente (consultas y recetas) |
| `autenticacion_paciente` | Acceso del paciente por *magic link* vía email |

---

## Roles y perfiles

La resolución de rol es la **única fuente de verdad** y vive en
[`src/core/roles.py`](src/core/roles.py). Los grupos se crean automáticamente
vía **migraciones de datos** (sin fixtures): `Medicos`, `Enfermeros`,
`Admision`, `Pacientes`. **Superadmin no es un grupo** — es `user.is_superuser`.

Al iniciar sesión, una vista de despacho redirige a cada usuario al *landing* de
su rol. El acceso entre roles está bloqueado (`role_required` → 403). Prioridad
de resolución: **Superadmin > Médico > Enfermero > Admisión > Paciente**.

| Rol | Cómo entra | Landing | Navegación (sidebar) | Qué hace |
|-----|-----------|---------|----------------------|----------|
| **Superadmin** | `is_superuser` | `dashboard_admin` | Dashboard · Admin Django | KPIs globales (pacientes del día, cola activa, triajes, notas) y acceso al admin |
| **Médico** | grupo `Medicos` | `dashboard_medico` | Dashboard · Cola de atención · Notas clínicas | Atiende la cola **en vivo (SSE)**, redacta notas y recetas con sugerencia CIE-10 |
| **Enfermería** | grupo `Enfermeros` | `dashboard_enfermero` | Dashboard · Triaje | Registra signos vitales, calcula prioridad Manchester, ve red flags |
| **Admisión** | grupo `Admision` | `dashboard_admision` | Dashboard · Pacientes | Alta y gestión de pacientes (búsqueda HTMX en vivo) |
| **Paciente** | **magic link** (email, sin contraseña) | `portal_paciente:dashboard` | Mis recetas | Consulta su historial y recetas; nunca ve el chrome del staff |

> **Doble sistema de auth:** el staff usa usuario/contraseña estándar de Django;
> el paciente entra solo por *magic link* (su `username` es el DNI, sin
> contraseña). Ambos comparten el modelo `core.User` (`AUTH_USER_MODEL`).

---

## Flujo clínico

```
Admisión              Enfermería            Médico                     Paciente
─────────             ──────────            ──────                     ────────
registra paciente  →  triaje (Manchester) → cola en vivo (SSE)     →   recibe magic link
                      prioridad inmutable    consulta + receta          ve recetas/historial
                                             sugerencia CIE-10 (NLP)
```

El cálculo de prioridad (RN-01) y la FSM de la cola (`EN_ESPERA →
EN_CONSULTORIO → FINALIZADO`) son determinísticos y están testeados.

---

## Ejecución local

### Con Docker (recomendado)

```bash
# Creá tu .env (ver "Variables de entorno" más abajo para el ejemplo completo)
docker compose up --build
```

Levanta cuatro servicios:

| Servicio | Imagen / build | Puerto | Rol |
|----------|----------------|--------|-----|
| `db` | `postgres:15-alpine` | — | Base de datos |
| `web` | `Dockerfile` | **8000** | Django (`migrate` + `runserver`) |
| `rabbitmq` | `rabbitmq:3-management` | 5672 · **15672** (panel) | Broker Celery |
| `worker` | `Dockerfile.worker` | — | Celery (procesamiento NLP CIE-10) |

App en **http://localhost:8000**. El `web` corre `migrate` al arrancar; las
migraciones de datos crean los grupos de permisos. Para operar necesitás al
menos un superusuario:

```bash
docker compose exec web python src/manage.py createsuperuser
```

> El email en `DEBUG` se escribe a la **consola** (backend de consola), así que
> los *magic links* del paciente aparecen en los logs sin necesidad de SMTP.

### Sin Docker

Requiere PostgreSQL o, en su defecto, el **fallback automático a SQLite** (si no
hay `DB_ENGINE` ni variables `POSTGRES_*`, usa SQLite).

```bash
python -m venv .venv && . .venv/Scripts/activate    # Windows: . .venv/Scripts/activate
pip install -r requirements.txt
python -m spacy download es_core_news_sm            # modelo NLP en español
PYTHONPATH=src python src/manage.py migrate
PYTHONPATH=src python src/manage.py createsuperuser
PYTHONPATH=src python src/manage.py runserver
```

> Sin RabbitMQ/worker, el procesamiento CIE-10 no corre asíncrono. Para tests o
> uso local podés forzar ejecución síncrona con `CELERY_TASK_ALWAYS_EAGER=1`.

---

## Variables de entorno

Definidas en `.env` (en la raíz del proyecto). Todas tienen un valor por defecto
seguro para desarrollo; en producción (`DEBUG=0`) `SECRET_KEY` es obligatorio y
las cabeceras seguras (HSTS, SSL redirect, cookies seguras) se activan solas.

| Variable | Default (dev) | Descripción |
|----------|---------------|-------------|
| `SECRET_KEY` | clave insegura de dev | **Obligatoria si `DEBUG=0`** |
| `DEBUG` | `1` | `0` activa el modo producción y el hardening |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver` | Hosts permitidos (coma-separados) |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000,...` | Orígenes CSRF de confianza |
| `DB_ENGINE` | — (vacío → SQLite) | Definir para forzar Postgres |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `app_lis` | Credenciales Postgres (usadas por `db` y `web`) |
| `POSTGRES_HOST` / `POSTGRES_PORT` | `db` / `5432` | Conexión Postgres |
| `CELERY_BROKER_URL` | `amqp://guest:guest@rabbitmq:5672//` | Broker RabbitMQ |
| `CELERY_TASK_ALWAYS_EAGER` | `0` | `1` ejecuta las tasks síncronas (tests/local) |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_USE_TLS` | — / `587` / `1` | SMTP (solo si `DEBUG=0`) |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | — | Credenciales SMTP |
| `DEFAULT_FROM_EMAIL` | `noreply@applis.com` | Remitente de los magic links |
| `LOG_LEVEL` | `INFO` | Nivel de logging estructurado |
| `SECURE_SSL_REDIRECT` / `SECURE_HSTS_*` | según `DEBUG` | Hardening TLS (auto en prod) |

<details>
<summary><strong>Ejemplo de <code>.env</code> para desarrollo</strong> (copiar y ajustar)</summary>

```dotenv
# Django core
SECRET_KEY=django-insecure-dev-key-change-me
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1,testserver
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
LOG_LEVEL=INFO

# PostgreSQL (sin estas vars ni DB_ENGINE, Django cae a SQLite)
DB_ENGINE=django.db.backends.postgresql
POSTGRES_DB=app_lis
POSTGRES_USER=app_lis
POSTGRES_PASSWORD=app_lis
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Celery / RabbitMQ
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_TASK_ALWAYS_EAGER=0

# Email (magic link). En DEBUG se imprime a consola; requerido solo si DEBUG=0.
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=noreply@applis.com
```
</details>

---

## Tests

El código vive bajo `src/`, así que las pruebas requieren `src` en el
`PYTHONPATH`:

```bash
# Suite completa con cobertura (gate en pytest.ini)
PYTHONPATH=src python -m pytest

# Rápido, sin cobertura
PYTHONPATH=src python -m pytest -q --no-cov
```

Estado actual: **133 passed, 1 skipped**.

> **Gotcha estáticos:** WhiteNoise usa `CompressedManifestStaticFilesStorage`.
> Tras agregar cualquier archivo estático nuevo, corré
> `PYTHONPATH=src python src/manage.py collectstatic --noinput` antes de los
> tests o la resolución de URLs de estáticos fallará.

---

## Estructura del proyecto

```
app-LIS/
├─ src/
│  ├─ config/            # settings, urls, celery
│  ├─ core/              # User, roles, navegación, dashboards, shell + cotton, static (css/js)
│  │  └─ templates/cotton/   # librería de componentes (c-page-header, c-card, c-stat, …)
│  ├─ admision/          # pacientes (RF-01)
│  ├─ triage/            # triaje + Manchester (RF-02/03)
│  ├─ medico/            # cola en vivo SSE (RF-04)
│  ├─ consulta/          # notas, recetas, CIE-10 (RF-05/06/07)
│  ├─ portal_paciente/   # portal del paciente
│  └─ autenticacion_paciente/  # magic link
├─ Dockerfile · Dockerfile.worker · docker-compose.yml · docker-compose.staging.yml
├─ requirements.txt · pytest.ini · .pre-commit-config.yaml
└─ ESTADO_ACTUAL.md · PLAN_PENDIENTES.md · PLAN_UIUX.md
```

---

## CI/CD

- **GitHub Actions** en `.github/workflows/`: `ci.yml`, `django.yml`,
  `deploy-staging.yml`, `deploy_main.yml`.
- **Jenkinsfile** para pipeline alternativo.
- **pre-commit** (`black`, `flake8`) en `.pre-commit-config.yaml`.
- La protección de rama se configura en la plataforma, fuera del repositorio.
