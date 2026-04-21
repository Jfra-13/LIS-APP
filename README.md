# MicroLIS: Laboratory Information System especializado en Microbiología

## Descripcion del Proyecto
MicroLIS es una plataforma de gestion hospitalaria diseñada para automatizar el flujo de trabajo de un laboratorio de microbiologia. El sistema gestiona procesos criticos de incubacion, identificacion de microorganismos y pruebas de susceptibilidad (antibiogramas), asegurando la trazabilidad desde la recepcion de la muestra hasta la emision del informe final bajo estandares de privacidad medica.

## Arquitectura de Software
El sistema emplea un Patron de Capas (Layered Architecture) bajo un modelo Cliente-Servidor. Esta estructura separa la logica de negocio, el acceso a datos y la interfaz de usuario, facilitando el mantenimiento y la escalabilidad del sistema.

## Stack Tecnologico
- Lenguaje: Python 3.10+
- Backend Framework: FastAPI (Asincrono)
- Base de Datos: PostgreSQL (Soporte para JSONB en resultados dinamicos)
- Validacion de Datos: Pydantic
- Autenticacion: OAuth2 + JWT (JSON Web Tokens)
- Gestion de Entorno: Virtualenv / Pip

## Areas y Modulos del Sistema
1. Recepcion y Pre-analitica: Registro de pacientes, ordenes medicas y etiquetado de muestras.
2. Gestion de Incubacion: Seguimiento de tiempos de cultivo y alertas de revision.
3. Identificacion Microbiologica: Registro de hallazgos y clasificacion de microorganismos.
4. Modulo de Antibiograma: Matriz dinamica de sensibilidad antibiotica (Sensible, Intermedio, Resistente).
5. Post-analitica y Reportes: Validacion clinica y generacion de informes PDF.

## Seguridad y Cumplimiento
El diseño contempla controles de acceso basados en roles (RBAC) y protocolos de cifrado para cumplir con normativas de proteccion de datos de salud como HIPAA.
