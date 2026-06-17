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

## Estado de las fases (revisión 2026-06-17)

| Fase | Estado | Nota |
|------|--------|------|
| Fase 0 — Estabilización | ✅ Completa | Suite verde (141 passed, 1 skipped); sin `src/src/`; typo CELERY corregido; README reescrito |
| Fase 1 — Async IA (RF-06/07) | ✅ Completa | `consulta/tasks.py`, campo `estado_ia`, migración 0004, `test_tasks.py`; checkbox `cie_accepted` ya usa `id_cie_accepted` (sin typo) |
| Fase 2 — Captura clínica | 🟢 Mayormente | Presión arterial (sistólica/diastólica) en `Triaje`; RF-05 pendiente decisión texto plano vs editor |
| Fase 3 — Cola tiempo real (RF-04) | ✅ Completa | SSE (`medico:cola_stream`); transición de cola manual (único dueño) |
| Fase 4 — Hardening | 🟡 Parcial | WhiteNoise OK; falta split de settings (`base/dev/prod`) y validar `manage.py check --deploy` |
| **HACER ANTES DEL 5** — UX y datos | 🔲 Pendiente | P1 sidebar colapsable · P2 hover/activo · P3 área del médico · P4 403 en contexto · P5 catálogo+receta horizontal |
| Fase 5 — Calidad/CI | 🟠 En curso | `--cov` ya cubre las 7 apps (90% total) y `ci.yml` usa fuente única; falta perf RNF-02 y E2E completo |

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

# HACER ANTES DEL 5 — Correcciones de UX y datos clínicos

> Bloque de trabajo solicitado tras probar el sistema (`nuevos_detalles.txt`).
> Son ajustes de experiencia de usuario y de datos que deben cerrarse **antes**
> de blindar calidad/CI (Fase 5), porque cambian plantillas, vistas, CSS y
> seeds que la Fase 5 luego tiene que cubrir con tests. Orden recomendado:
> P1 → P2 (CSS, base visual), luego P3/P4/P5 en paralelo.
>
> Cada sub-fase indica **Problema**, **Qué hacer**, **Decisión técnica**
> (alternativa elegida y por qué), **Archivos** y **Criterio de aceptación**.

## Fase P1 — Sidebar colapsable, expandible y fijable (todos los roles)

**Problema:** la barra lateral no se puede contraer. El usuario quiere poder
contraerla, expandirla y **fijarla** (que quede en un estado y se recuerde).
En estado contraído solo deben verse los **iconos** de cada ítem (logo LIS,
icono de dashboard, icono de paciente, etc.) y, abajo, el bloque de usuario
reducido a su icono más el botón de salir.

**Qué hacer:**
1. Añadir un control en la esquina superior derecha del sidebar con icono que
   alterne **expandir / contraer** (p. ej. `bi-chevron-double-left` /
   `bi-chevron-double-right`) y un segundo control de **fijar** (p. ej.
   `bi-pin-angle` ↔ `bi-pin-fill`).
2. Estado contraído (`lis-sidebar--collapsed`): ancho reducido (~64px), se
   ocultan los textos (`span`/labels) y solo quedan los iconos centrados;
   tooltip nativo (`title=`) por ítem para conservar el significado.
3. Persistir la preferencia (colapsado y fijado) por usuario.

**Decisión técnica (elegida):**
- **Estado en el cliente con Alpine.js + `localStorage`**, no en backend.
  *Por qué:* es instantáneo (sin round-trip), no requiere migración ni columna
  nueva en `User`, y la preferencia de layout es puramente de presentación.
  Escala sin tocar la BD. El `x-data` ya existe en `cotton/layout.html`; se
  extiende con `collapsed` y `pinned` inicializados desde `localStorage`
  (`$persist` del plugin de Alpine o lectura manual en `init()`).
- **Iconos garantizados por ítem:** el `nav_items` del context processor debe
  exponer un campo `icon` por ítem (clase Bootstrap Icons). Hoy los iconos
  viven en la plantilla; se centralizan en el backend de navegación para que el
  modo contraído siempre tenga icono. *Por qué:* fuente única, evita ítems sin
  icono al contraer.
- **Diferencia con "fijar":** sin fijar, el sidebar puede colapsar/expandir al
  pasar el mouse (hover-expand) y vuelve a su estado; fijado, queda en el estado
  elegido y el contenido principal reserva ese ancho. En móvil el comportamiento
  off-canvas actual no cambia (el colapso aplica solo a `≥992px`).

**Archivos:** `src/core/templates/cotton/sidebar.html`,
`src/core/templates/cotton/layout.html`, `src/core/static/css/theme.css`
(`.lis-sidebar--collapsed`, anchos, ocultar labels), context processor de
navegación en `src/core/` (campo `icon` por ítem).

**Criterio de aceptación:**
- En cualquier rol, el sidebar contrae/expande y el estado persiste al recargar.
- Contraído muestra solo iconos + botón salir; con tooltip por ítem.
- El ancho del contenido principal se ajusta sin saltos al fijar/contraer.

## Fase P2 — Hover y estado activo uniformes en la navegación

**Problema:** el ítem activo se ve como un bloque **verde oscuro fijo** que no
gusta; el hover del resto de ítems es **gris**. El usuario quiere que el hover
sea un **verde más claro para todos los ítems** y que el activo no parezca
"pegado"/permanente con verde oscuro. Aplica a admisión, enfermería y médico.

**Qué hacer:**
1. Cambiar `.lis-sidebar__link:hover` para que use un **tinte verde claro**
   (no el gris `--lis-bg` actual).
2. Suavizar `.lis-sidebar__link--active`: mantener un indicador sutil
   (borde izquierdo + texto en color primario) pero **sin** relleno verde
   saturado; usar el mismo tinte claro o uno apenas más marcado que el hover.
3. Unificar: el mismo criterio de hover/activo en los tres roles (es un único
   componente, así que se corrige una vez).

**Decisión técnica (elegida):**
- Introducir un token CSS `--lis-nav-hover` (verde claro derivado de
  `--lis-primary`, ~8–12% de opacidad) y usarlo tanto en hover como, un poco
  más intenso, en activo. *Por qué:* tokenizar mantiene coherencia con el
  design system existente (un solo acento teal) y permite ajustar el tono en un
  solo lugar; evita colores mágicos dispersos.
- El estado activo conserva el **borde izquierdo** como señal de "dónde estoy"
  (accesible, no depende solo del color de fondo).

**Archivos:** `src/core/static/css/theme.css` (tokens + reglas
`.lis-sidebar__link:hover` y `--active`).

**Criterio de aceptación:**
- Hover verde claro idéntico en todos los ítems y roles; sin hover gris.
- El ítem activo se distingue por borde + color, sin bloque verde oscuro.

## Fase P3 — Reestructurar el área del médico (de "lista de notas" a flujo por paciente)

**Problema:** hoy "Notas clínicas" (`NotaMedicaListView` → `consulta/list.html`)
es una lista plana de todas las notas, en desorden percibido. El médico no
tiene un lugar donde ver **sus pacientes ordenados** y desde ahí entrar a las
notas de cada uno. Se piden 3 vistas.

**Qué hacer (3 vistas):**
1. **"Mis pacientes"** — pacientes que el médico atendió, ordenados por
   atención **más reciente → más antigua**, con buscador y contador de notas.
   Cada fila enlaza a la vista 2.
2. **Notas por paciente** — al entrar a un paciente, sus notas clínicas
   ordenadas de la **más reciente a la más antigua**.
3. **"Mi día" (mejora libre elegida)** — panel resumen del médico: pacientes en
   cola ahora, atendidos hoy, y accesos rápidos a la cola y a "Mis pacientes".

**Decisión técnica (elegida):**
- **Vista 2 reutiliza la `HistoriaClinicaView` existente**
  (`consulta:historia_clinica`, que ya combina notas + triajes por paciente,
  recientes primero). *Por qué:* ya está construida y testeada; evita duplicar
  lógica. Si se quiere una vista "solo notas del médico", se agrega un filtro,
  pero la historia unificada es más útil clínicamente.
- **Vista 1 ("Mis pacientes")**: nueva `ListView` que agrupa por paciente las
  `NotaMedica` del médico autenticado. Consulta eficiente:
  `Paciente.objects.filter(notamedica__medico=request.user).annotate(
  ultima=Max('notamedica__created_at'), n=Count('notamedica')).order_by(
  '-ultima')`. *Por qué:* agrupar en BD (no en Python) escala y respeta RNF-02.
- **Vista 3 ("Mi día")**: `TemplateView` que reúne KPIs ya disponibles
  (cola `ColaEstado`, notas del día). *Por qué:* da al médico contexto operativo
  sin inventar modelos nuevos; reusa datos existentes.
- **Navegación:** los 3 entran como ítems del rol médico en el context
  processor de navegación. "Notas clínicas" plano se mantiene o se reemplaza por
  "Mis pacientes" como entrada principal.

**Archivos:** `src/consulta/views.py` (nuevas vistas), `src/consulta/urls.py`,
`src/consulta/templates/consulta/` (nuevas plantillas: `mis_pacientes.html`,
`mi_dia.html`; reusar `historia_clinica.html`), context processor de navegación
en `src/core/`, tests en `src/consulta/tests/`.

**Criterio de aceptación:**
- El médico ve "Mis pacientes" ordenados por atención reciente y entra a las
  notas/historia de cada uno.
- "Mi día" muestra cola actual y atendidos de hoy con accesos rápidos.
- Las consultas usan agregación en BD (sin N+1).

## Fase P4 — Acceso denegado en contexto (no expulsar al home)

**Problema:** al no tener permiso, algunas vistas **redirigen al home (302)** con
un mensaje arriba, sacando al usuario de donde estaba. Otras devuelven 403. El
usuario quiere: ver el aviso **donde está** (sin redirección automática) y que
el botón de volver lo lleve a **la página anterior** (de donde hizo clic), no
siempre al inicio.

**Qué hacer:**
1. Unificar el comportamiento de los mixins de permiso para **renderizar una
   página 403 en contexto** en lugar de redirigir al home.
2. La página 403 muestra el mensaje y un botón **"Volver"** que usa la URL
   anterior (`HTTP_REFERER`), con fallback al home solo si no hay referer.

**Decisión técnica (elegida):**
- **Estandarizar en `403` con `raise_exception=True`** en todos los mixins
  (`MedicoPermissionMixin`, `AdmisionPermissionMixin`, `TriagePermissionMixin`,
  `ConsultaPermissionMixin`) y un `handler403` global con plantilla propia.
  *Por qué:* es el patrón correcto de Django (no inventar redirecciones), es
  consistente, ya hay tests que esperan 403 (`CrossRole403Tests`,
  `test_cola_stream`) — esto los **alinea** en vez de romperlos. Los mixins que
  hoy hacen `redirect("home")` (medico/admision/triage) se cambian a 403.
- **Botón "Volver" con `HTTP_REFERER`** saneado (validar que sea del mismo host
  con `url_has_allowed_host_and_scheme`) para no introducir open-redirect.
  *Por qué:* seguridad — un referer externo no debe usarse a ciegas.
- *Riesgo a verificar:* algún test podría esperar el `redirect("home")` actual;
  hay que actualizar esas aserciones al nuevo 403 en contexto.

**Archivos:** `src/medico/views.py`, `src/admision/views.py`,
`src/triage/views.py`, `src/consulta/views.py` (mixins), `src/config/urls.py`
(`handler403`), plantilla `403.html` (en `core/templates/` o equivalente),
tests afectados en cada app.

**Criterio de aceptación:**
- Sin permiso, la vista responde 403 y se ve el aviso **sin** redirigir al home.
- El botón "Volver" regresa a la página anterior del mismo sitio; fallback home.
- Suite verde con las aserciones de permisos actualizadas.

## Fase P5 — Catálogo de medicamentos ampliado y receta horizontal inferior

**Problema:** (a) el catálogo de medicamentos es chico — `medicamentos.json`
tiene 8 ítems; el mapa CIE→medicamentos (`cie_med_map.json`, 30 diagnósticos ×
2) resuelve 29/30 pero hay poca variedad y falta sembrar "Sales de
rehidratación oral". (b) En la consulta, el bloque de medicamentos está en la
columna derecha; el usuario lo quiere **abajo, horizontal, a todo el ancho**,
con buscador y sugerencias (como se diseñó).

> Estado parcial ya hecho: `cie10.json` reducido a 30 diagnósticos generales y
> `cie_med_map.json` con 2 medicamentos por diagnóstico (commit `d2ecf05`).
> Esta fase **amplía variedad y reorganiza el layout**, no parte de cero.

**Qué hacer:**
1. **Ampliar `medicamentos.json`** con más variedad (tabletas, jarabes,
   cremas/ungüentos, etc.), incluyendo el faltante "Sales de rehidratación
   oral", y asegurar que todo nombre referenciado por `cie_med_map.json` exista
   como `Medicamento` tras `cargar_medicamentos`.
2. **Mover el bloque de receta** a una fila inferior a todo el ancho
   (`col-12`), fuera de la columna derecha. Distribución horizontal de cada
   fila de prescripción (medicamento · dosis · frecuencia · duración ·
   instrucciones · quitar) en una sola línea responsive.
3. Mantener el **buscador** (`med_suggest`) y las **sugerencias por diagnóstico**
   (`med_suggest_by_cie`) ya implementadas; al elegir un CIE, precargar
   sugerencias en el bloque inferior.

**Decisión técnica (elegida):**
- **Seguir usando JSON seed + comando `cargar_medicamentos`** como fuente del
  catálogo (no hardcodear en migración). *Por qué:* el catálogo es dato, no
  esquema; el comando es idempotente y reejecutable, y mantiene los pks UUID
  reales que la receta necesita (`med_suggest` ya devuelve el pk de la BD, no el
  id del JSON).
- **Layout:** reestructurar `form.html` a dos zonas: arriba 2 columnas
  (nota + asistente CIE), abajo una **tarjeta full-width** para la receta con
  filas horizontales (Bootstrap grid `row`/`col`), conservando el inline
  formset (`PrescripcionFormSet`) y el JS de clonado de filas. *Por qué:* da más
  espacio horizontal a la receta (mejor lectura/edición) sin romper el formset
  ni los endpoints HTMX existentes.
- **Sugerencias por CIE:** cablear `med_suggest_by_cie` al evento de selección
  de diagnóstico para poblar `#med-results` en el bloque inferior. *Por qué:*
  cierra el flujo "diagnóstico → medicación sugerida" sin búsqueda manual.

**Archivos:** `src/consulta/data/medicamentos.json` (ampliar),
`src/consulta/data/cie_med_map.json` (ajustar variedad si hace falta),
`src/consulta/management/commands/cargar_medicamentos.py` (verificar carga),
`src/consulta/templates/consulta/form.html` (layout receta),
`src/core/static/css/theme.css` (estilos de fila horizontal), tests en
`src/consulta/tests/`.

**Criterio de aceptación:**
- Todo medicamento del mapa CIE→meds existe en la BD tras `cargar_medicamentos`
  (sin nombres sin resolver) y el catálogo tiene variedad real.
- En la consulta, la receta aparece abajo a todo el ancho, en horizontal, con
  buscador funcionando y sugerencias por diagnóstico.

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
