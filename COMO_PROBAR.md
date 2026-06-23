# Cómo probar los cambios (P1–P5)

> Checklist de comandos para levantar el sistema y ver las correcciones de UX y
> datos del bloque **HACER ANTES DEL 5**. Hacelo en este orden.

## 1. Levantar los servicios (Docker)

```bash
# Compose v2 (Docker Desktop actual)
docker compose up -d

# …o Compose v1
docker-compose up -d
```

El código está montado como volumen (`.:/code`), así que los cambios de
plantillas, CSS, vistas y JS se toman sin reconstruir la imagen. Solo reconstruí
si cambiaste dependencias:

```bash
docker compose up -d --build
```

Servicios: `db` (Postgres), `web` (Django :8000), `rabbitmq` (broker) y `worker`
(Celery).

## 2. Migraciones

P1–P5 **no agregan modelos nuevos** (son UI, permisos y datos semilla). El
contenedor `web` ya corre `migrate` al arrancar, pero si querés forzarlo:

```bash
docker compose exec web python src/manage.py migrate --noinput
```

Los grupos de permisos (`Medicos`, `Enfermeros`, `Admision`, etc.) se siembran
por migración, no hace falta nada extra.

## 3. Recargar el catálogo de medicamentos (OBLIGATORIO para P5)

Ampliamos `medicamentos.json` (de 8 a 29 ítems, con variedad: jarabes, cremas,
gotas, sprays, sobres) y el mapa CIE→medicamentos. El comando **borra y vuelve a
cargar** la tabla `Medicamento`, así que corrélo para que aparezcan los nuevos
(incluida "Sales de Rehidratación Oral") y las sugerencias por diagnóstico:

```bash
docker compose exec web python src/manage.py cargar_medicamentos
```

> Si no lo corrés, la receta seguirá mostrando solo los 8 medicamentos viejos.

## 4. Refrescar el navegador (P1 y P2)

El sidebar colapsable y los colores de hover viven en `theme.css` y en JS de
Alpine. Hacé **hard refresh** para evitar caché: `Ctrl + Shift + R` (o
`Ctrl + F5`).

---

## Qué deberías ver

- **P1 — Sidebar:** arriba a la derecha del panel lateral hay dos botones:
  📌 *fijar/desfijar* y ⏴⏵ *contraer/expandir*. Contraído queda solo con iconos
  (~64px) y tooltips; el estado **persiste al recargar** (se guarda en
  `localStorage`). Sin fijar, al contraer se expande al pasar el mouse.
- **P2 — Hover/activo:** el hover de todos los ítems es un **verde claro**
  (no gris); el ítem activo se marca con un borde lateral + tinte suave, sin el
  bloque verde oscuro fijo. Igual en admisión, enfermería y médico.
- **P3 — Médico:** en el menú del médico hay **Mi día** (resumen: en espera,
  en consultorio, atendidos hoy, últimas notas) y **Mis pacientes** (ordenados
  por atención más reciente, con buscador y contador de notas). Al entrar a un
  paciente se ve su historia clínica (notas + triajes), recientes primero.
- **P4 — Acceso denegado:** si entrás a una sección sin permiso, ves el aviso
  **403 en el lugar** (ya no te expulsa al inicio) con un botón **Volver** que te
  lleva a la página anterior. Probalo, por ejemplo, logueado como enfermero
  intentando abrir una URL de admisión.
- **P5 — Receta:** en la consulta médica, el bloque de receta está **abajo, a
  todo el ancho, en horizontal** (medicamento · dosis · frecuencia · duración ·
  instrucciones · quitar). El buscador funciona y, al elegir un diagnóstico
  CIE-10, se precargan los medicamentos sugeridos.

---

## Correr los tests (opcional)

La suite corre con Postgres en CI, pero localmente usa SQLite si no hay variables
`POSTGRES_*` en el entorno:

```bash
PYTHONPATH=src .venv/Scripts/python.exe -m pytest
```

Estado actual: **150 passed**, cobertura **≈90%** (gate de 80% en `pytest.ini`).

> Nota: al crear un triaje en local sin broker, Celery loguea un error de
> conexión a RabbitMQ que **se captura** y no rompe el flujo. En Docker el broker
> está disponible y el procesamiento asíncrono corre normal.
