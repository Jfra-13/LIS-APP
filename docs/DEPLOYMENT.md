# Despliegue y endurecimiento — app-LIS

Guía operativa para correr app-LIS en un entorno tipo producción (Fase 4 del
`PLAN_PENDIENTES.md`). El objetivo de aceptación es:

```bash
python src/manage.py check --deploy   # 0 warnings con el entorno de producción
```

## 1. Variables de entorno requeridas en producción

Los settings son únicos y *env-driven* (`src/config/settings.py`). En producción
hay que definir, como mínimo:

| Variable | Valor en prod | Notas |
|----------|---------------|-------|
| `DEBUG` | `0` | Con `DEBUG=0` los flags de seguridad pasan a *secure-by-default*. |
| `SECRET_KEY` | clave fuerte y única | La app **se niega a arrancar** (`ImproperlyConfigured`) si `DEBUG=0` y la clave sigue siendo la de desarrollo. Generar: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. |
| `ALLOWED_HOSTS` | dominios reales | Coma-separado. |
| `CSRF_TRUSTED_ORIGINS` | `https://tu-dominio` | Coma-separado. |
| `DB_ENGINE` | `django.db.backends.postgresql` | + `POSTGRES_*` (o alias `DB_*`). |
| `CELERY_BROKER_URL` | URL del broker | RabbitMQ. |
| `LOG_LEVEL` | `INFO` (o `WARNING`) | Controla el `LOGGING` de la app y del worker. |

### Flags de seguridad (TLS)

Con `DEBUG=0` quedan activados por defecto y se pueden sobreescribir por entorno:

`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
`SECURE_HSTS_SECONDS` (1 año), `SECURE_HSTS_INCLUDE_SUBDOMAINS`,
`SECURE_HSTS_PRELOAD`, `SECURE_CONTENT_TYPE_NOSNIFF`, y
`SECURE_PROXY_SSL_HEADER` (confía en `X-Forwarded-Proto`).

> Si el staging se sirve por **HTTP plano** (sin proxy TLS), poné
> `SECURE_SSL_REDIRECT=0` para evitar el bucle de redirección.

## 2. Archivos estáticos

Se sirven con **WhiteNoise** (sin servidor de estáticos aparte). El `Dockerfile`
corre `collectstatic` en el build y `STORAGES.staticfiles` usa
`CompressedManifestStaticFilesStorage` (compresión + *hashing* para cache larga).

## 3. Servidor de aplicación (SSE en producción)

`docker-compose.staging.yml` corre `web` con **gunicorn `--worker-class gthread`**
(no `runserver`). Los workers *gthread* dan un thread por conexión, así el stream
SSE de la cola (`medico:cola_stream`) funciona en producción **sin necesitar un
servidor ASGI**. Cada conexión SSE mantiene un thread ocupado mientras dura: si se
esperan muchas conexiones simultáneas, escalar `--threads`/`--workers` o migrar a
ASGI (uvicorn/daphne).

## 4. Celery / resultados de tareas

`CELERY_RESULT_BACKEND` es opcional (vacío por defecto). Las tareas actuales
(`send_triaje_to_queue`, `process_clinical_note`) no devuelven resultado que haya
que consultar, así que no se requiere backend de resultados. Si en el futuro se
necesita, definir la variable (p. ej. Redis o RPC).

## 5. Política de retención y borrado clínico (`on_delete`)

El borrado está diseñado para **preservar el registro clínico**. Resumen de las
claves foráneas:

| Modelo · campo | Política | Razón |
|----------------|----------|-------|
| `triage.Triaje.paciente` | `PROTECT` | No se borra un paciente con triaje. |
| `triage.Triaje.usuario_enfermeria` | `SET_NULL` | El triaje sobrevive si se baja al usuario. |
| `medico.ColaEstado.triaje` | `PROTECT` | Protege la inmutabilidad del triaje. |
| `consulta.NotaMedica.paciente` | `PROTECT` | La historia clínica retiene al paciente. |
| `consulta.NotaMedica.triaje` | `PROTECT` | Ata la nota a su triaje de origen. |
| `consulta.NotaMedica.medico` | `SET_NULL` | La nota sobrevive si se baja al médico. |
| `consulta.Prescripcion.nota_medica` | `CASCADE` | La prescripción es hija de la nota. |
| `consulta.Prescripcion.medicamento` | `PROTECT` | No se borra un medicamento prescrito. |
| `admision.Paciente.usuario_creador` | `SET_NULL` | El paciente sobrevive al alta del usuario. |

`admision.Paciente` además usa *soft delete* (no se elimina físicamente). Las
entidades clínicas críticas (`Triaje`, `NotaMedica`) son inmutables/historizadas
(`simple_history`), por lo que el borrado real debe ser excepcional y auditado.
