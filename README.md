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

## Siguiente paso ...

#### MVP 1: Módulo de Admisión Transaccional

**Objetivo:** Digitalizar el primer paso del flujo hospitalario asegurando tiempos de respuesta óptimos.

- **Requerimientos Cubiertos:** RF-01, RNF-02.
    
- **Backend:**
    
    - Crear la app `admision` y el modelo `Paciente`.
        
    - Implementar Class-Based Views (CBV) para el CRUD del paciente.
        
    - _Clean Code:_ Optimizar las consultas usando `select_related` o `prefetch_related` desde el principio para garantizar que las operaciones se rendericen en menos de 1.5 segundos.
        
- **Frontend:**
    
    - Construir un formulario ágil para el Técnico Administrativo, optimizado para navegación por teclado.
        
- **QA:**
    
    - Pruebas de integración para la creación de pacientes y validación de DNI.
        
    - _Performance testing_ inicial en QA local para validar el RNF-02 (< 1.5s).
        
- **DevOps (CI/CD):**
    
    - **Jenkins:** Se añaden reportes de cobertura de código (ej. `pytest-cov`). Jenkins falla el _build_ si la cobertura baja del 80%.

#### MVP 2: Motor Logico de Triaje (Sincrono)

**Objetivo:** Captura de biometria y calculo algoritmico inmutable de la prioridad clinica.

- **Requerimientos cubiertos:** RF-02, RF-03, RN-01, RN-03.
- **Backend:**
    - App `triage` con modelo `Triaje` relacionado a `Paciente`.
    - `TriageCalculatorService` con arquitectura OCP (`RuleEngine`, `BasicVitalSignsRule`, `RedFlagRule`).
    - `red_flag` definido con `TextChoices` (`DOLOR_TORACICO`, `DIFICULTAD_RESPIRATORIA`, `HEMORRAGIA_ACTIVA`).
    - Persistencia solo de `nivel_prioridad` (1..5); el color Manchester se deriva por `@property`.
    - Inmutabilidad estricta: cualquier update de `Triaje` lanza `RN01ImmutableTriageError`.
- **Frontend:**
    - Formulario de enfermeria con validaciones visuales y campo `nivel_prioridad` bloqueado (`readonly`).
- **QA:**
    - Pruebas unitarias de limites para SpO2, frecuencia cardiaca y temperatura.
    - Validacion RN-03 con excepcion de dominio por falta de datos criticos.
- **DevOps (CI/CD):**
    - Jenkins valida lint/formato/tests/cobertura incluyendo `triage`.
    - GitHub Actions despliega a `staging` via SSH en servidor Docker/Compose, usando secretos:
      `SERVER_IP`, `SSH_USER`, `SSH_PRIVATE_KEY`, `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`.
        

