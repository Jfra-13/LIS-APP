# Plan de Cierre por Fases — app-LIS

> Hoja de ruta para llevar el proyecto desde su estado actual (ver
> `ESTADO_ACTUAL.md`) hasta cumplir los requerimientos de
> `ContextClaude/contexto.txt`. Las fases están ordenadas por dependencia:
> primero se estabiliza, luego se cierra la arquitectura asíncrona, después
> compliance de spec, tiempo real y hardening.

## Cómo leer este plan

Cada fase tiene **Objetivo**, **Tareas**, **Archivos afectados** y **Criterio de
aceptación** (cómo sabés que terminó). El esfuerzo es una estimación relativa,
no un compromiso.

---

## Fase 0 — Estabilización y limpieza (bloqueante)

**Objetivo:** repo verde y sin ruido antes de construir encima. Sin esto, todo
lo demás se construye sobre arena.

**Tareas:**
1. Unificar nombres de grupos de permisos en una sola fuente de verdad
   (`Enfermeros` vs `Enfermeria`, `Medicos`, `Admision`, `Pacientes`). Alinear
   migraciones, `admision/fixtures/initial_groups.json` y los `setUp` de los
   tests. Recomendado: constantes compartidas en `core` y un helper de test que
   asigne permisos reales.
2. Reparar aserciones obsoletas (`core/tests.py::test_login_flow_works` busca
   "MVP0 base" inexistente).
3. Corregir el typo `CELCELERY_ACCEPT_CONTENT` → `CELERY_ACCEPT_CONTENT`
   (`settings.py`).
4. Eliminar el directorio basura `src/src/portal_paciente/`.
5. Corregir el icono `bi bi- megaphone` → `bi bi-megaphone` (`cola_list.html`).
6. Reescribir `README.md` (está describiendo un MVP0 con apps archivadas que ya
   no existen). Puede apuntar a `ESTADO_ACTUAL.md` y a este plan.
7. Agregar `EMAIL_BACKEND` de consola cuando `DEBUG` esté activo (o variable de
   entorno) para no romper *magic links* en local.

**Archivos:** `core/migrations/*`, `admision/fixtures/initial_groups.json`,
`triage/tests.py`, `consulta/tests*`, `core/tests.py`, `config/settings.py`,
`src/src/` (borrar), `medico/templates/medico/cola_list.html`, `README.md`.

**Criterio de aceptación:**
- `pytest` con la suite completa: **0 fallos** (o fallos documentados y
  justificados).
- `flake8`/`black`/`pre-commit` pasan.
- `git status` sin directorios espurios.

---

## Fase 1 — Cerrar la arquitectura asíncrona de IA (RF-06 + RF-07 + RNF-01)

**Objetivo:** que guardar una nota médica dispare un procesamiento en segundo
plano que termine sugiriendo (y persistiendo) un código CIE-10, sin bloquear la
pantalla del médico. Este es el corazón de la propuesta de valor del sistema.

**Tareas:**
1. **Crear `consulta/tasks.py`** con `process_clinical_note(nota_id)` (task
   Celery, idempotente, con reintentos, igual que `medico.tasks`):
   - Lee `NotaMedica`, extrae texto (`motivo_consulta` + `contenido`).
   - Llama al motor de sugerencia (ver tarea 3) y persiste el resultado.
2. **Agregar campo de estado de procesamiento** a `NotaMedica` (p. ej.
   `estado_ia` con `PENDIENTE / PROCESANDO / LISTO / ERROR`) para soportar el
   estado visual "Procesando IA" (RF-06) + migración.
3. **Decidir el motor** y dejarlo explícito:
   - **Opción A (recomendada, coherente con "Resultados Esperados"):** motor
     determinístico. Reusar `cie_lookup.search()` sobre el texto normalizado.
     Rápido, auditable, sin caja negra. Marcar spaCy como opcional.
     `nlp_service.py` puede usarse solo para lematizar/limpiar la query.
   - **Opción B:** activar spaCy de verdad (descargar `es_core_news_sm` en el
     `Dockerfile.worker`, NER de síntomas) y alimentar con eso a `cie_lookup`.
   > Decisión de producto pendiente — A y B no son excluyentes; A primero.
4. **Resolver el handoff de resultados.** Hoy `get_ai_suggestions` lee de cache
   pero el cache es local por proceso. Dos caminos:
   - Persistir la sugerencia en la BD (`NotaMedica.cie_*` + `estado_ia`) y que
     el polling lea de la BD (simple, sin Redis). **Recomendado.**
   - O agregar Redis (servicio en Compose + bloque `CACHES`) si se quiere usar
     cache real compartido.
5. **Cablear el polling de la UI** en `consulta/form.html`/`detail.html` para
   leer el estado/sugerencia (HTMX `hx-trigger="every 2s"` hasta `LISTO`).
6. **Reparar el bug del checkbox** `cie_accepted` (typo `id_id_` y manejo de
   `.checked`).

**Archivos:** `consulta/tasks.py` (nuevo), `consulta/models.py` (+ migración),
`consulta/views.py`, `consulta/services/*`, `consulta/templates/consulta/*`,
`Dockerfile.worker` (si Opción B), `docker-compose.yml` + `settings.py` (si Redis).

**Criterio de aceptación:**
- Al guardar una nota, el estado pasa a `PROCESANDO` y, tras el worker, a `LISTO`
  con `cie_code`/`cie_short_description` poblados.
- Test de integración del flujo con `CELERY_TASK_ALWAYS_EAGER=1`.
- La pantalla del médico nunca se bloquea esperando la IA.

---

## Fase 2 — Compliance de captura clínica (RF-02, RF-05)

**Objetivo:** cerrar las brechas de datos que pide la spec.

**Tareas:**
1. **Agregar Presión Arterial** a `Triaje` (sistólica/diastólica), con
   validadores de rango, e incorporarla como regla en `BasicVitalSignsRule` (o
   una `BloodPressureRule` nueva — el diseño OCP lo permite sin tocar las demás).
   Actualizar formulario y plantilla de triaje + tests de límites.
2. **Historia clínica enriquecida (RF-05):** evaluar editor de texto enriquecido
   ligero (p. ej. un editor WYSIWYG mínimo o Markdown) para `contenido`, o
   documentar formalmente que se acepta texto plano. Decisión de producto.

**Archivos:** `triage/models.py` (+ migración), `triage/services.py`,
`triage/forms.py`, `triage/templates/triage/triage_form.html`, `triage/tests.py`,
`consulta/forms.py` / plantilla (RF-05).

**Criterio de aceptación:**
- El triaje captura presión arterial y la regla afecta el `nivel_prioridad`
  con tests de borde.
- RF-05 resuelto o explícitamente acotado.

---

## Fase 3 — Cola en tiempo real (RF-04)

**Objetivo:** acercar la cola al "tiempo real / milisegundos" que promete el
contexto, hoy resuelto con polling cada 15s.

**Tareas (incremental, elegir según ambición):**
1. **Mínimo:** bajar el intervalo de polling y/o usar `hx-trigger` por eventos.
2. **Recomendado:** Server-Sent Events (SSE) o WebSockets (Django Channels) para
   empujar cambios de la cola cuando entra un triaje o cambia un estado.
3. **Resolver la contradicción de diseño** del §5.9 de `ESTADO_ACTUAL.md`:
   definir si el worker debe auto-mover a `EN_CONSULTORIO` o si eso es decisión
   manual del médico ("Llamar"). Hoy ambos coexisten y se pisan.

**Archivos:** `medico/views.py`, `medico/templates/medico/cola_list.html`,
`medico/tasks.py`, posible `config/asgi.py` + Channels.

**Criterio de aceptación:**
- La cola se actualiza ante un nuevo triaje sin recargar y sin esperar 15s.
- El flujo de transición de estado tiene un único dueño (manual **o**
  automático), documentado.

---

## Fase 4 — Hardening de producción y seguridad

**Objetivo:** que sea desplegable en un entorno hospitalario real.

**Tareas:**
1. Separar settings por entorno (`base`/`dev`/`prod`) o endurecer por variables:
   `DEBUG=0`, `SECRET_KEY` obligatoria, `ALLOWED_HOSTS`, cookies seguras,
   `SECURE_*`, HSTS.
2. Servir estáticos en producción (WhiteNoise o servidor) — hoy todo viene por
   CDN, evaluar dependencia de red externa en un hospital.
3. Configurar `CELERY_RESULT_BACKEND` si se requieren resultados de tareas.
4. Logging estructurado y observabilidad del worker.
5. Revisar `on_delete=PROTECT` y políticas de retención clínica.

**Archivos:** `config/settings.py` (split), `requirements.txt`,
`docker-compose.staging.yml`, infraestructura.

**Criterio de aceptación:**
- `python manage.py check --deploy` sin warnings críticos.
- Despliegue a staging reproducible.

---

## Fase 5 — Calidad, cobertura y CI verde end-to-end

**Objetivo:** garantizar las reglas de negocio médicas (cero regresiones) que
exige la sección QA/DevOps del contexto.

**Tareas:**
1. Llevar cobertura ≥ 80% (gate ya configurado en `pytest.ini`,
   `--cov-fail-under=80`) incluyendo `medico`, `portal_paciente`,
   `autenticacion_paciente` (hoy fuera del `--cov`).
2. Test de performance que valide RNF-02 (< 1.5s) en CRUD de admisión/triaje.
3. Verificar que los 4 workflows de GitHub Actions + Jenkinsfile corren la suite
   real (broker/db efímeros) y bloquean merge ante fallos.
4. Pruebas E2E del flujo completo: admisión → triaje → cola → consulta →
   sugerencia CIE-10 asíncrona.

**Archivos:** `pytest.ini` (ampliar `--cov`), `.github/workflows/*`,
`Jenkinsfile`, `src/tests/e2e/*`.

**Criterio de aceptación:**
- CI verde en cada PR con cobertura ≥ 80%.
- E2E del flujo clínico completo pasa en CI.

---

## Orden recomendado y dependencias

```
Fase 0 (estabilizar)
   └─> Fase 1 (async IA) ──┐
   └─> Fase 2 (captura)    ├─> Fase 4 (hardening) ─> Fase 5 (CI/QA)
   └─> Fase 3 (tiempo real)┘
```

Fase 0 es prerrequisito de todo. Fases 1, 2 y 3 son independientes entre sí y
pueden paralelizarse. Fase 4 y 5 cierran cuando lo funcional está listo.

## Decisiones de producto pendientes (requieren tu input)

1. **Motor de diagnóstico:** determinístico (Opción A) vs spaCy real (Opción B).
2. **Transición de cola:** ✅ RESUELTO (Fase 3) — **manual por el médico**. El
   worker (`send_triaje_to_queue`) ya no auto-mueve a `EN_CONSULTORIO`; solo
   asegura el `ColaEstado` en `EN_ESPERA`. La transición la dispara el botón
   "Llamar paciente" (`LlamarPacienteView`). Único dueño, sin colisión.
3. **Historia clínica:** texto plano vs editor enriquecido.
4. **Tiempo real:** ✅ RESUELTO (Fase 3) — **SSE**. La cola usa Server-Sent
   Events (`medico:cola_stream`, vista síncrona sobre WSGI) con un tick de
   detección de cambios en BD; el front (htmx SSE ext) re-pide la tabla solo
   cuando algo cambia, reemplazando el polling de 15s. Deuda Fase 4: cada
   conexión SSE ocupa un thread/worker — para escalar, servir bajo ASGI o con
   workers async (gevent/uvicorn).
