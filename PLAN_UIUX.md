# Plan de rediseño UI/UX — Aislamiento por rol + sistema de diseño

> Rediseño integral de la interfaz de app-LIS para lograr **5 roles con vistas
> propias y aisladas** (Superadmin, Médicos, Enfermeros, Admisión, Pacientes) y
> una estética de **clínica profesional**, construido sobre el stack hypermedia
> que ya existe (Bootstrap 5 + HTMX + Alpine + SSE).

Este documento es el contrato del cambio: qué se hace, por qué, en qué orden y
cómo se valida. No es solo "pintar templates" — el aislamiento real exige tocar
backend.

---

## TL;DR

| Tema | Decisión |
|------|----------|
| Framework CSS | **Bootstrap 5 tematizado** (no Tailwind — sin build de Node, componentes ya hechos). |
| Componentes | **django-cotton** (atomic design, fin del copypaste de markup). |
| Assets | **Locales en `static/vendor/`**, servidos por WhiteNoise. Se elimina el CDN (offline-safe en intranet). |
| Navegación | **Sidebar lateral scopeado por rol** + topbar. Reemplaza el navbar superior genérico. |
| Aislamiento | **Resolvedor único de rol** + redirect post-login por rol + dashboard dedicado por rol. |
| Alcance backend | Sí, hay cambios de backend. El aislamiento NO se logra solo con CSS. |

---

## Por qué este cambio (estado actual)

El backend ya tiene control de permisos sólido (un `PermissionRequiredMixin` por
app), pero la **capa de presentación no aísla roles**:

- Existe **un solo `/home/`** para todos. Los módulos se muestran/ocultan con
  `{% if perms.X %}` en `core/home.html`. Es una pantalla compartida con candados
  visuales, no vistas propias por rol.
- No hay **redirect por rol** tras el login: `LOGIN_REDIRECT_URL = "home"` para
  todos (`src/config/settings.py:209`).

### Bugs de aislamiento detectados (se arreglan en este cambio)

| # | Bug | Ubicación | Impacto |
|---|-----|-----------|---------|
| 1 | Magic link manda al paciente a `home` (staff), no a su portal | `src/autenticacion_paciente/views.py:73` | Un paciente aterriza en el dashboard del personal. |
| 2 | Tile muerto: chequea `portal_paciente.view_receta`, permiso inexistente | `src/core/templates/core/home.html:130` | Nunca renderiza; código zombi. |
| 3 | Dos logins de paciente coexisten (magic link + password) | `/auth-paciente/solicitar/` y `/paciente/login/` | Flujo confuso; hay que unificar a uno. |

### Datos del modelo de roles (a respetar)

- Grupos existentes **sin tilde**: `Medicos`, `Enfermeros`, `Admision`, `Pacientes`
  (migraciones `src/core/migrations/0002_create_groups.py` y `0003_update_groups.py`).
- **Superadmin no es un grupo**: es `user.is_superuser`.
- **Identidad del paciente = `user.username == paciente.dni`**. No hay modelo ni
  sesión separada para pacientes.

---

## Arquitectura de roles (núcleo del aislamiento)

### Resolvedor único de rol

Un solo punto de verdad: `src/core/roles.py`.

```python
# Enum de roles + función resolvedora con prioridad.
class Role(models.TextChoices):
    SUPERADMIN = "SUPERADMIN"
    MEDICO     = "MEDICO"
    ENFERMERO  = "ENFERMERO"
    ADMISION   = "ADMISION"
    PACIENTE   = "PACIENTE"

# Prioridad de resolución cuando un usuario pertenece a varios grupos:
# SUPERADMIN > MEDICO > ENFERMERO > ADMISION > PACIENTE
def get_role(user) -> Role | None: ...
```

Todo lo demás (redirect, navegación, dashboards) consume `get_role()`. Una sola
fuente, cero lógica de rol duplicada en templates.

### Redirect post-login por rol

Reemplazar el `LOGIN_REDIRECT_URL` plano por una vista de despacho que use
`get_role()` y mande a cada rol a SU dashboard:

| Rol | Destino tras login |
|-----|--------------------|
| Superadmin | `core:dashboard_admin` |
| Médico | `medico:cola_atencion` (o dashboard médico) |
| Enfermero | `triage:triage_list` (o dashboard enfermería) |
| Admisión | `admision:paciente_list` (o dashboard admisión) |
| Paciente | `portal_paciente:dashboard` |

### Matriz de aislamiento por rol

| Rol | Detección | Vistas propias (rutas reales) | Ve del resto |
|-----|-----------|-------------------------------|--------------|
| **Superadmin** | `is_superuser` | Dashboard de métricas + Django admin | Todo (por diseño) |
| **Admisión** | grupo `Admision` | `admision:paciente_list` / `paciente_create` / `paciente_detail` / `paciente_update` / `paciente_delete` | Nada clínico |
| **Enfermeros** | grupo `Enfermeros` | `triage:triage_list` / `triage_create` / `paciente_triaje_history` | Nada de consulta médica |
| **Médicos** | grupo `Medicos` | `medico:cola_atencion` (SSE) / `llamar_paciente`; `consulta:nota_list` / `nota_create` / `nota_detail` + panel IA | Nada de admisión/triaje-edición |
| **Pacientes** | grupo `Pacientes` / DNI | `portal_paciente:dashboard` / `receta_detail` | Solo lo SUYO; shell separado |

> El portal del paciente usa un **layout separado y más liviano**. Un paciente
> nunca debe ver el chrome (sidebar/topbar) del personal.

---

## Sistema de diseño

### Tokens de tema (clínica profesional)

Definidos como CSS custom properties sobre Bootstrap (sobreescritura, sin SCSS
build obligatorio):

- **Paleta**: base neutra (blancos, grises suaves), acento azul/teal sobrio,
  estados claros (success/warn/danger/info).
- **Colores Manchester**: se **mantienen tal cual** (semántica médica, no
  decoración) — niveles 1–5 ya definidos en `base.html`.
- **Tipografía**: fuente legible (system stack o Inter local), jerarquía clara.
- **Densidad**: espaciado consistente, alta legibilidad (entorno clínico).

### App-shell (layout)

Nueva estructura de `base.html` como layout cotton:

```
┌─────────────────────────────────────────┐
│ Topbar: marca · usuario · rol · logout   │
├──────────┬──────────────────────────────┤
│ Sidebar  │  Page header                  │
│ (por rol)│  ──────────────────────────   │
│  · item  │  Contenido (bloque content)   │
│  · item  │                               │
│  · item  │                               │
└──────────┴──────────────────────────────┘
```

El sidebar renderiza **solo los ítems del rol activo** (vía `get_role()`).

### Librería de componentes (django-cotton)

| Componente | Uso |
|------------|-----|
| `<c-layout>` | Shell completo (topbar + sidebar + contenido). |
| `<c-sidebar>` | Navegación scopeada por rol. |
| `<c-topbar>` | Barra superior con usuario/rol/logout. |
| `<c-page-header>` | Título de página + acciones. |
| `<c-card>` | Tarjeta contenedora estándar. |
| `<c-stat>` | Métrica/KPI para dashboards. |
| `<c-badge-manchester>` | Badge de prioridad 1–5 con color correcto. |
| `<c-patient-row>` | Fila de paciente reutilizable (cola/listas). |
| `<c-empty-state>` | Estado vacío consistente. |
| `<c-form-field>` | Campo de formulario con label/error/ayuda. |
| `<c-alert>` | Mensajes/flash messages. |

---

## Auditoría visual post-Fase C (2026-06-11)

Fases A–C entregaron el shell (topbar + sidebar responsive off-canvas) y la
librería cotton, pero **las páginas internas nunca adoptaron el sistema**. De los
11 componentes, solo 4 se usan (`layout`, `sidebar`, `topbar`, `alert`). El
resultado: un shell moderno envolviendo páginas de tres "épocas" de diseño
distintas. De ahí la sensación de app poco estética, recargada y anticuada.

### Hallazgos por archivo

| Archivo | Problema |
|---------|----------|
| `admision/paciente_form.html` | No usa Bootstrap: CSS propio embebido en `<style>`, clases `.button` inexistentes (botones sin estilo), ~200 líneas de `if/else` duplicado por campo. El "formulario anticuado". |
| `portal_paciente/dashboard.html` | Todo con `style=""` inline y clases muertas (`.button`, `.muted`) de un design system anterior que ya no existe. |
| `triage/triage_form.html` | Sobrecarga visual: icono en cada label, `input-group-lg` con doble addon, tres headers de card de colores distintos (azul/amarillo/cyan), alertas que empujan el layout dentro del form, doble explicación del campo bloqueado. El "cansancio visual". |
| `admision/paciente_list.html` | Ruido: iconos en todo, sexo como badge de color (`bg-danger` para F — rojo no es "femenino"), botonera arcoíris (info/warning/danger), búsqueda que promete "tiempo real" pero el Alpine no hace nada (solo submit GET). |
| `medico/cola_list.html` | Aceptable, pero no usa cotton; `<style>` inline (`.pulsate`); clase `text-gray-800` inexistente en Bootstrap; "Rol: Médico Especialista" duplica el chip del topbar. |
| `registration/login.html` | Header `bg-primary` pesado, `alert-info` de relleno, validación cliente con `alert()` nativo del navegador. |
| `cotton/form_field.html` | No aplica `is-invalid` al widget → el estilo de error de Bootstrap nunca se activa visualmente. |
| Varios templates | **Mensajes flash duplicados**: el layout YA renderiza `messages` y 3+ templates los vuelven a renderizar (doble alerta en pantalla). |
| `theme.css` | Tokens mínimos: primario = azul Bootstrap default (`#0d6efd`), sin tipografía propia, sin `:focus-visible` ni print styles. Se ve "Bootstrap genérico". |
| Dashboards por rol | Placeholders con `list-group` y `style="max-width"` inline; `c-stat` construido y sin usar. |
| Branding | `base.html` dice "Sistema de Información de Laboratorio", el login dice "Sistema de Información Clínica"; footer fijo "© 2024". |

### Principios de diseño (reglas anti-ruido — aplican a TODA la Fase D)

1. **Un solo acento**: el color primario del tema. Headers de card neutros
   (blanco + borde), nunca `bg-primary`/`bg-warning`/`bg-info`.
2. **Iconos con propósito**: máximo un icono por concepto (nav, acción primaria,
   empty state). Nunca en labels de formulario ni en textos de ayuda.
3. **Color solo semántico**: Manchester 1–5, estados de cola y errores. El sexo,
   la edad o un dato neutro jamás llevan badge de color de estado.
4. **Un solo texto de ayuda por campo**, corto. No repetir la misma explicación
   dos veces (pasa hoy con el campo de prioridad).
5. **Cero estilos inline y cero `<style>` por página**: todo va a `theme.css` o
   al componente cotton correspondiente.
6. **Flash messages solo en el layout**: se eliminan todos los bloques
   `{% if messages %}` de las páginas.
7. **Todo formulario usa `<c-form-field>`**; todo listado usa `c-page-header` +
   `c-card` (+ `c-empty-state` cuando aplique).
8. **Densidad clínica**: tamaños default (sin `btn-lg`/`input-group-lg` salvo
   justificación táctil), espaciado consistente.

---

## Plan por fases

Orden con dependencias: A → B habilitan el resto. C da las piezas. D y E construyen
encima. **No saltear A/B**: sin ellas el aislamiento y el reuso no existen.
A–C están cerradas; **D0 es bloqueante para D1–D5** (arregla la deuda transversal
que hoy hace que cada página se vea distinta).

### Fase A — Fundaciones del front ✅
- [x] Bajar Bootstrap, Bootstrap Icons, HTMX, Alpine y la extensión SSE a `static/vendor/`.
- [x] Cambiar `base.html` para cargar assets locales (no CDN).
- [x] Verificar que WhiteNoise hashea/comprime los nuevos assets (`collectstatic`).
- [x] Instalar y configurar `django-cotton` en `INSTALLED_APPS` + settings de templates.
- [x] Definir tokens de tema (CSS variables) en un `static/css/theme.css`.

**Aceptación**: la app levanta sin internet externo; estilos y JS cargan desde
`/static/`; `collectstatic` no rompe.

### Fase B — Identidad de rol y ruteo (backend) ✅
- [x] Crear `src/core/roles.py` con `Role` + `get_role(user)` (con prioridad).
- [x] Vista de despacho post-login que redirige por rol.
- [x] Crear dashboards por rol (vista + ruta + template mínimo).
- [x] **Arreglar bug #1**: magic link redirige a `portal_paciente:dashboard`.
- [x] **Arreglar bug #2**: eliminar tile muerto en `home.html` (archivo borrado).
- [x] **Arreglar bug #3**: unificar login de paciente a magic link (password eliminado, `portal_paciente:login` → RedirectView).
- [x] Bloquear a pacientes del `home`/vistas de staff (y viceversa) de forma explícita.

**Aceptación**: cada rol, al loguear, cae en su dashboard; ningún rol puede abrir
una ruta de otro rol (403/redirect); tests de acceso por rol en verde.

### Fase C — Componentización (cotton) ✅
- [x] Construir la librería de componentes de la tabla anterior.
- [x] Migrar `base.html` al `<c-layout>` + `<c-sidebar>` + `<c-topbar>`.

**Aceptación**: los componentes renderizan aislados; `base.html` ya no tiene
markup duplicado de navegación.

### Fase D0 — Deuda transversal (bloqueante; habilita D1–D5) ✅
- [x] `c-form-field` v2: aplicar `is-invalid` al widget cuando hay errores
      (template filter `add_class` en `core/templatetags/form_extras.py`).
- [x] Eliminar TODOS los bloques `{% if messages %}` de templates de página
      (el layout ya los renderiza) — fix del doble flash. Quitados de
      `paciente_form`, `paciente_list` y `triage_form`.
- [x] Paleta clínica real en `theme.css`: teal sobrio (`#0f766e`) propagado vía
      puente a CSS vars de Bootstrap 5.3 (`--bs-primary*`, `--bs-link-*`,
      `.btn-primary`, `.btn-outline-primary`, focus de form, pagination).
- [x] Tipografía: system stack explícito + escala de headings compacta
      (h1 1.5rem — densidad de app clínica, no marketing). Inter local quedó
      descartada: el system stack era la primera opción del plan y evita
      ~300 KB de fonts vendor.
- [x] Mover `.pulsate` (cola médica) y la timeline del paciente a `theme.css`
      como utilidades reutilizables (`lis-timeline`, se aplica en D4).
- [x] Purgar clases muertas en templates: `.button`, `.muted`, `.text-gray-800`
      reemplazadas por clases Bootstrap reales en 9 templates. El `.form-group`
      custom de `paciente_form` muere con la reescritura completa en D1.
      `magic_link_email.html` se deja intacto (template de email, CSS inline
      propio por diseño).
- [x] Branding unificado: "LIS — Sistema de Información Clínica" en `base.html`
      y login; footer con año dinámico (`{% now "Y" %}`).

**Aceptación**: un solo flash por mensaje; un error de campo pinta el input en
rojo (`is-invalid`); no quedan clases muertas ni `<style>` nuevos en los
templates tocados.

### Fase D1 — Admisión
- [x] `paciente_form.html`: reescritura completa → `c-page-header` + `c-card` +
      `<c-form-field>` por campo (los 3 fieldsets se conservan como secciones).
      Quitar el `<style>` embebido y el `if/else` duplicado (~250 líneas → ~60).
      Conservar la UX de JS (placeholder por tipo de documento, prefijo +51,
      bloqueo de dígitos en nombres, Ctrl+S/ESC) extraída a
      `static/js/admision-form.js` o Alpine.
- [x] `paciente_list.html`: `c-page-header` (título + botón "Nuevo Paciente"
      tamaño normal); búsqueda como toolbar simple sobre la tabla (sin card
      aparte); convertirla en búsqueda HTMX real (`hx-get` +
      `hx-trigger="keyup changed delay:400ms"` → parcial de tabla) o quitar el
      Alpine muerto y la promesa de "tiempo real". Sexo como texto plano.
      Acciones ver/editar discretas (`btn-outline-secondary`), eliminar separado
      en rojo.
- [x] `paciente_detail.html` + `paciente_confirm_delete.html`: alinear a
      `c-card`/`c-page-header`; confirm_delete con resumen del paciente y un
      único botón rojo.

**Aceptación**: CRUD completo navegable y visualmente consistente; el formulario
sigue siendo operable por teclado; cero CSS embebido.

### Fase D2 — Enfermería (triaje)
- [x] `triage_form.html`: bajar el ruido — sin iconos en labels; inputs tamaño
      default con UNA unidad como addon (%, lpm, °C); headers de card neutros;
      hints de rango en una sola línea `form-text`; las alertas Alpine
      (SpO2 bajo / fiebre / red flag) como texto compacto `small text-danger`
      que no empuja el layout; la sección "Prioridad" como banda Manchester
      readonly (`c-badge-manchester` grande) con UNA línea explicando RN-01.
      Quitar el hack muerto de `alpine:init`/`__x` (API de Alpine 2, no existe
      en v3).
- [x] `triage_list.html` + `paciente_triaje_history.html`: `c-page-header`,
      `c-card`, `c-badge-manchester`, `c-empty-state`.

**Aceptación**: el form de triaje entra en una pantalla 1366×768 sin scroll
excesivo; el feedback de valores anormales es visible pero sin saltos de layout.

### Fase D3 — Médico
- [x] `cola_list.html`: migrar a `c-page-header` + `c-card` +
      `c-badge-manchester` + `c-empty-state`. **Intocable**: `hx-ext="sse"`,
      `sse-connect`, `hx-get`/`hx-trigger`/`hx-select`/`hx-target` y el id
      `cola-table-body`. Quitar "Rol: Médico Especialista" (el topbar ya muestra
      el rol). `.pulsate` pasa a theme.css (D0).
- [x] `consulta/form.html`: campos vía `<c-form-field>`; panel IA re-encuadrado
      en `c-card` con header neutro — **sin tocar** los endpoints/atributos HTMX
      (`cie_suggest`, `med_suggest`) ni los ids (`id_contenido`, `id_motivo_consulta`,
      `ai-results`, `manual-cie-results`, `med-results`, `cie-selection-display`).
- [x] `consulta/list.html` + `detail.html`: componentes + tipografía legible
      para la nota clínica (el Markdown ya renderizado).

**Aceptación**: la cola actualiza en vivo vía SSE contra Docker (verificación
manual con dos sesiones); typeahead CIE-10 y medicamentos intactos.

### Fase D4 — Paciente (portal)
- [x] `portal_paciente/dashboard.html`: reescritura sin estilos inline; timeline
      con clases `lis-timeline` de theme.css; header con nombre + DNI; CTA
      "Ver Receta" como botón outline tamaño normal.
- [x] `receta_detail.html`: card limpia + botón de imprimir.
- [x] `autenticacion_paciente/*` (request_link, link_sent, invalid_link):
      pantalla de auth centrada, consistente con el login de staff, un solo
      mensaje claro por pantalla.

**Aceptación**: portal usable en mobile (360 px); el paciente nunca ve el chrome
del staff.

### Fase D5 — Superadmin + autenticación staff
- [ ] `registration/login.html`: card neutra (sin header `bg-primary`), sin
      `alert-info` de relleno, sin validación con `alert()` (la validación real
      es del server). Mantener el toggle de visibilidad de contraseña.
- [ ] `dashboard/admin.html`: métricas reales con `c-stat` (pacientes del día,
      cola activa, triajes, notas) consumiendo `consulta:reportes` o queries
      simples en la vista.
- [ ] Dashboards médico/enfermero/admisión: 2–3 `c-stat` con datos reales +
      accesos rápidos como cards (reemplaza el `list-group` con `max-width`
      inline).

**Aceptación**: cada dashboard muestra al menos un dato real del sistema; login
sobrio y profesional.

### Fase E — Pulido
- [ ] Responsive por página (el shell ya es responsive; las páginas no): tablas
      con columnas priorizadas en mobile (`d-none d-md-table-cell` en columnas
      secundarias) o patrón stacked; formularios a una columna en `< md`;
      botones de acción full-width en mobile.
- [ ] Accesibilidad: `:focus-visible` con ring del tema; `aria-current="page"`
      en el item de nav activo; contraste AA (verificar manchester-3 y 5 con
      texto negro); `aria-label` en botones de solo icono.
- [ ] Estados: `hx-indicator` (spinner) en búsquedas y typeahead;
      `c-empty-state` en todos los listados; páginas 403/404/500 con el shell.
- [ ] Print styles (`@media print`): nota clínica y receta — ocultar
      sidebar/topbar/botones, tipografía de documento.
- [ ] `collectstatic` con manifest + smoke test sin red externa.

**Aceptación**: contraste AA en textos clave; navegable por teclado; impresión de
receta legible; vistas principales usables a 360 px.

---

## Riesgos y dependencias

| Riesgo | Mitigación |
|--------|------------|
| Romper el SSE de la cola al reescribir `cola_list.html` | Mantener atributos `hx-ext="sse"` / `sse-connect` intactos; verificar en vivo contra Docker. |
| Romper el panel IA de la nota (`get_ai_suggestions` polling) | No tocar los endpoints HTMX; solo re-encuadrar el markup. |
| `collectstatic` con `CompressedManifestStaticFilesStorage` falla si falta un asset referenciado | Verificar todas las refs a `static` tras bajar vendor. |
| Usuario en múltiples grupos resuelve a rol ambiguo | Prioridad explícita en `get_role()` (Superadmin > Médico > Enfermero > Admisión > Paciente). |
| Grupos sin tilde (`Medicos`, `Admision`) | Usar nombres exactos en `get_role()` y fixtures. |
| Reescribir `paciente_form.html` pierde la UX de JS (placeholder por tipo de doc, prefijo +51, Ctrl+S/ESC) | Extraer el JS a archivo estático ANTES de reescribir el markup; verificar manualmente cada comportamiento. |
| Quitar los `{% if messages %}` de página rompe feedback en alguna vista | El layout cotton ya renderiza `messages` globalmente; verificar un create/update/delete por rol tras el cambio. |

---

## Fuera de alcance

- Migración a SPA (React/Vue/DRF): explícitamente descartada — la app es
  hypermedia y eso es correcto para este caso.
- Permisos a nivel objeto (`django-guardian`): no necesario hoy; los mixins por
  modelo alcanzan.
- Cambios en la lógica de triaje/Manchester, NLP CIE-10 o FSM de la cola: este
  cambio es solo presentación + ruteo por rol.

---

## Verificación end-to-end (manual, por rol)

1. Loguear como cada rol → confirmar dashboard propio y sidebar scopeado.
2. Intentar abrir una ruta de otro rol → confirmar bloqueo.
3. Paciente vía magic link → confirmar que cae en su portal, no en `home`.
4. Cola médica → confirmar actualización en vivo (SSE) sin recargar.
5. Nota clínica → confirmar panel IA y typeahead CIE-10/medicamentos.
6. `collectstatic` + correr sin CDN → confirmar estilos/JS desde `/static/`.
