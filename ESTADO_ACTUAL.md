# Estado Actual — app-LIS (Triaje Hospitalario Inteligente)

> Auditoría técnica del proyecto contrastada contra los requerimientos de
> `ContextClaude/contexto.txt`. Fecha de revisión: 2026-06-17.
> Rama: `master`.
>
> **Nota de revisión (2026-06-17):** este documento se actualizó tras cerrar las
> Fases 0–3 y la mayor parte de la 5. El detalle histórico de §5 (bugs) refleja
> el estado del 2026-06-05 y se conserva como registro; ver el estado vigente en
> §1 y en `PLAN_PENDIENTES.md` (tabla "Estado de las fases").

## 1. Resumen ejecutivo

El proyecto es un sistema Django (MVT) para admisión, triaje, cola de atención y
consulta médica con sugerencia de códigos CIE-10. La **base de dominio está bien
construida** (modelos, reglas de negocio, arquitectura SOLID en el cálculo de
triaje, inmutabilidad clínica, UUIDs, historización). La **UI es de buena
calidad** (Bootstrap 5 + HTMX + Alpine.js, colores Manchester, formularios
reactivos).

La **arquitectura asíncrona de IA (RF-06 / RF-07)** ya está cerrada (Fase 1):
existe `consulta/tasks.py` (`process_clinical_note`, idempotente con reintentos),
`NotaMedica` tiene campo `estado_ia` (PENDIENTE/PROCESANDO/LISTO/ERROR) +
migración 0004, la nota dispara el procesamiento al guardarse y la UI lee el
estado por polling. El motor de diagnóstico sigue siendo el catálogo
determinístico CIE-10 (coherente con "Resultados Esperados"); spaCy queda como
opcional.

Estado de pruebas: **suite verde** (última corrida: 141 passed, 1 skipped). La
regresión de grupos de permisos y aserciones obsoletas (Fase 0) está resuelta.

| Capa | Estado | Nota |
|------|--------|------|
| Modelado de datos / dominio | 🟢 Sólido | UUIDs, SOLID, inmutabilidad, historial |
| UI / UX (código) | 🟢 Buena | Cotton design system; rediseño D0–E completo |
| Backend transaccional | 🟢 Funcional | Admisión, triaje, cola, consulta operan |
| Arquitectura asíncrona NLP | 🟢 Cerrada | `consulta/tasks.py` + `estado_ia`; RF-06/07 cableados (Fase 1) |
| Cola en tiempo real | 🟢 SSE | `medico:cola_stream`; transición manual (único dueño) |
| Contenerización / DevOps | 🟢 Presente | Docker, Compose, CI workflows, Jenkinsfile |
| Calidad / Tests | 🟢 Verde | 141 passed, 1 skipped; cobertura en cierre (Fase 5) |

Leyenda: 🟢 cumple · 🟡 parcial · 🔴 falta / roto.

## 2. Stack real verificado

- **Python 3.12 + Django 5.0.14** (MVT). ✔️
- **PostgreSQL 15** en `docker-compose.yml`; por defecto local usa **SQLite**
  (selección automática por variables de entorno en `settings.py`). ✔️ / ⚠️
- **RabbitMQ 3 + Celery 5.6** declarados (broker `amqp://...`, `worker` con
  `Dockerfile.worker`). ✔️
- **spaCy 3.8** instalado (`requirements.txt`) y `nlp_service.py` presente, pero
  **no se invoca desde ningún flujo** (código muerto). ⚠️
- **HTMX (django-htmx) + Bootstrap 5 + Alpine.js + Bootstrap Icons** vía CDN. ✔️
- **simple_history** (historización de `Triaje`). ✔️
- **WeasyPrint** para PDFs de recetas (portal del paciente). ✔️ (extra a la spec)
- **pytest / pytest-django / coverage / flake8 / black / pre-commit**. ✔️

## 3. Mapa de requerimientos vs. implementación

### Requerimientos Funcionales

| ID | Requerimiento | Estado | Evidencia / Brecha |
|----|---------------|--------|--------------------|
| RF-01 | Registro de pacientes (DNI + UUID) | 🟢 | `admision.Paciente`, CRUD CBV, validación DNI/PAS/CE, soft delete, UUID PK |
| RF-02 | Captura de biometría | 🟢 | `triage.Triaje` captura SpO2, FC, Temperatura, bandera roja **y presión arterial** (sistólica/diastólica, Fase 2) |
| RF-03 | Cálculo algorítmico + bloqueo del nivel | 🟢 | `TriageCalculatorService` (OCP: `RuleEngine`, `BasicVitalSignsRule`, `RedFlagRule`); `nivel_prioridad` con `editable=False` |
| RF-04 | Cola dinámica en tiempo real | 🟢 | `medico.ColaEstado` ordenado por prioridad; frontend con **SSE** (`medico:cola_stream`) que re-pide la tabla solo ante cambios (Fase 3) |
| RF-05 | Historia clínica narrativa | 🟡 | `consulta.NotaMedica.contenido` (TextField) + `motivo_consulta`; textarea plano. Decisión pendiente: texto plano vs editor enriquecido. Existe vista de **historia clínica unificada** (`consulta:historia_clinica`) |
| RF-06 | Disparador NLP por Signal + estado "Procesando IA" | 🟢 | `consulta/tasks.py::process_clinical_note` + campo `NotaMedica.estado_ia` (migración 0004); la UI refleja el estado por polling (Fase 1) |
| RF-07 | Sugerencia CIE-10 por agente autónomo | 🟢 | Flujo asíncrono cableado: el task procesa la nota y persiste la sugerencia; el motor es el catálogo determinístico `cie_lookup.py` (spaCy opcional) |

### Requerimientos No Funcionales

| ID | Requerimiento | Estado | Evidencia / Brecha |
|----|---------------|--------|--------------------|
| RNF-01 | Arquitectura asíncrona (RabbitMQ + Celery) | 🟢 | Infra completa + dos tasks reales: `medico.tasks.send_triaje_to_queue` y `consulta.tasks.process_clinical_note` (NLP), ambos idempotentes con reintentos |
| RNF-02 | CRUD < 1.5s | 🟢 (no medido) | `select_related`/managers optimizados, índices en modelos. Falta prueba de performance que lo verifique |
| RNF-03 | Contenerización | 🟢 | `Dockerfile`, `Dockerfile.worker`, `docker-compose.yml` (db, web, rabbitmq, worker) |
| RNF-04 | PKs UUIDv4 en tablas críticas | 🟢 | `core.AbstractBaseModel` (UUID) en Paciente, Triaje, NotaMedica, User. `ColaEstado` usa PK entera (estado operativo, no transaccional crítico) |
| RNF-05 | Python/Django + PostgreSQL + spaCy | 🟡 | Django y Postgres ✔️. spaCy instalado pero **inactivo**; el diagnóstico real lo hace el catálogo JSON determinístico (coherente con "Resultados Esperados", contradictorio con RNF-05) |

## 4. Inventario por app

- **`core`** — `User` (UUID) + `AbstractBaseModel`, vistas `landing`/`home`,
  `base.html`, migraciones de grupos de permisos. 🟢
- **`admision`** — `Paciente` con manager (búsqueda, validación DNI), CRUD,
  plantillas, signals. 🟢
- **`triage`** — `Triaje` inmutable + historización, `services.py` (cálculo
  SOLID), `signals.py` (crea `ColaEstado` y encola task), formulario reactivo
  Alpine. 🟢
- **`medico`** — `ColaEstado` (FSM manual con `can_transition`/`set_estado`),
  vista de cola con polling, `tasks.send_triaje_to_queue` (Celery, idempotente,
  reintentos). 🟢 backend / 🟡 lógica (ver §5.9)
- **`consulta`** — `NotaMedica`, `Prescripcion`, `Medicamento`; servicios
  `cie_lookup` (determinístico) y `med_lookup`; endpoints HTMX de sugerencia;
  reportes/KPIs. 🟡 (falta `tasks.py`, cache compartido)
- **`portal_paciente`** — dashboard del paciente + receta PDF. 🟢 (extra a la spec)
- **`autenticacion_paciente`** — login del paciente por *magic link* por email
  (`services.py`, `tokens.py`). 🟢 (extra a la spec)

## 5. Hallazgos y bugs (priorizados)

1. **🔴 ALTA — `consulta/tasks.py` no existe.** `consulta/views.py:88` hace
   `from .tasks import process_clinical_note` dentro de un `try/except
   ImportError` que oculta el fallo. Rompe RF-06 y RF-07 end-to-end.
2. **🔴 ALTA — Sin `CACHES`/Redis para el handoff de IA.** `get_ai_suggestions`
   lee `cache.get("suggestions_nota_{pk}")`, pero (a) nadie lo escribe y (b) el
   cache por defecto es local en memoria por proceso → no se comparte entre
   `web` y `worker`. `redis` está en `requirements.txt` pero **no hay servicio
   redis en `docker-compose.yml` ni bloque `CACHES` en settings**.
3. **🔴 ALTA — Inconsistencia de nombres de grupos rompe 17 tests.** La
   migración `core/0002_create_groups.py` crea el grupo **"Enfermeros"**, pero
   `triage/tests.py` usa **"Enfermeria"** → grupo vacío sin
   `triage.add_triaje` → la vista redirige 302. Patrón similar en pruebas de
   `consulta`. Hay que unificar nombres entre migraciones, fixtures y tests.
4. **🟡 MEDIA — `EMAIL_BACKEND` forzado a SMTP incluso en DEBUG.** En
   `settings.py` el backend de consola quedó comentado; sin credenciales SMTP el
   *magic link* del paciente falla en local.
5. **🟡 MEDIA — Bug de checkbox CIE-10 en `consulta/form.html`.** Línea 152:
   `getElementById('id_id_cie_accepted')` (typo `id_id_`). Además se asigna
   `.value='true'` a un campo BooleanField (checkbox), que no marca `.checked` →
   `cie_accepted` puede no persistir correctamente.
6. **🟡 MEDIA — Captura de Presión Arterial ausente (RF-02).** El modelo `Triaje`
   no tiene campos de presión arterial pese a estar en la spec.
7. **🟡 MEDIA — Aserciones de test obsoletas.** `core/tests.py::test_login_flow_works`
   exige el texto "MVP0 base" que ya no está en `home.html`.
8. **🟢 BAJA — `CELCELERY_ACCEPT_CONTENT` (typo).** `settings.py:179` define una
   variable mal escrita; `accept_content` cae al default `["json"]` (sin efecto
   real, pero es deuda).
9. **🟢 BAJA — Contradicción de diseño en el task de Celery.** `send_triaje_to_queue`
   mueve **automáticamente** la cola a `EN_CONSULTORIO` al crear el triaje, lo
   que choca con el botón manual "Llamar paciente" del médico y con el concepto
   de "cola de espera". El contexto lo menciona, pero el comportamiento es
   contradictorio con la UX. Requiere decisión de producto.
10. **🟢 BAJA — Directorio basura `src/src/portal_paciente/forms.py`.** Duplicado
    fuera de lugar; eliminar.
11. **🟢 BAJA — Icono roto** en `medico/cola_list.html:59`: `bi bi- megaphone`
    (espacio dentro del nombre de clase).
12. **🟢 BAJA — `README.md` obsoleto.** Describe un "MVP0" con apps archivadas
    (`_archived_apps/triage`, `nlp_engine`) que ya no existen.

## 6. Conexiones e infraestructura

- **DB:** PostgreSQL 15 en Compose con healthcheck; local cae a SQLite. ✔️/⚠️
- **Broker:** RabbitMQ 3-management con healthcheck; `web` y `worker` dependen
  de él. ✔️
- **Worker:** servicio dedicado con `Dockerfile.worker` y `PYTHONPATH=src`. ✔️
- **Cache:** ❌ no configurado (bloqueante para el handoff de sugerencias IA).
- **Email:** SMTP por variables de entorno (sin fallback de consola en dev). ⚠️
- **CI/CD:** `.github/workflows/` (`ci.yml`, `django.yml`, `deploy-staging.yml`,
  `deploy_main.yml`) + `Jenkinsfile` + `.pre-commit-config.yaml`. ✔️

## 7. Cómo ejecutar / verificar (estado real)

```bash
# Tests (requiere el venv del proyecto y PYTHONPATH=src)
PYTHONPATH=src .venv/Scripts/python.exe -m pytest -q --no-cov

# Stack completo
docker compose up --build
```

Resultado actual de la suite: **17 failed, 59 passed, 1 skipped**
(ver §5 para causa raíz).

---

Para el plan de cierre por fases, ver **`PLAN_PENDIENTES.md`**.
