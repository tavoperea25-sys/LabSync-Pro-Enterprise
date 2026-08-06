# 02 — Objetivos del Producto

## 1. Objetivo general

Entregar una plataforma SaaS multi-tenant para la gestión integral de equipos biomédicos, documentación de calidad, calibraciones y mantenimientos en laboratorios clínicos y de metrología, con una experiencia de usuario de nivel Enterprise comparable a productos SaaS internacionales de referencia (Linear, Notion, Stripe Dashboard), que reduzca a cero los vencimientos no detectados y el tiempo de preparación de auditorías ISO 15189 / ISO 17025.

## 2. Objetivos específicos

### Producto
- OE-1: Permitir el registro y consulta de la ficha técnica completa de un equipo en menos de 2 minutos.
- OE-2: Calcular automáticamente el estado de vigencia de cada calibración y documento, sin intervención manual.
- OE-3: Generar un "paquete de auditoría" exportable de cualquier equipo en un solo clic (ver mejora propuesta en `00-analisis-critico-y-recomendaciones.md`).
- OE-4: Notificar proactivamente (in-app, con outbox preparado para email) toda calibración, mantenimiento o documento que entre en ventana de vencimiento.

### Experiencia de usuario
- OE-5: Que un usuario sin formación técnica pueda completar las tareas más frecuentes (registrar equipo, subir documento, consultar calendario) sin capacitación formal, guiado por la propia interfaz.
- OE-6: Mantener tiempos de carga percividos por debajo de 1 segundo en las vistas principales (Dashboard, listados) bajo condiciones normales de uso.
- OE-7: Cumplir WCAG 2.2 nivel AA en la totalidad de la interfaz.

### Arquitectura y calidad
- OE-8: Aislar completamente los datos entre laboratorios (tenants) mediante Row Level Security, verificado con pruebas automatizadas de aislamiento como criterio de aceptación no negociable.
- OE-9: Registrar el 100% de las acciones de creación, edición y eliminación en un log de auditoría inmutable.
- OE-10: Mantener una cobertura de pruebas automatizadas mínima del 80% en la capa de dominio/servicios del backend.

### Negocio (SaaS)
- OE-11: Soportar el alta de un nuevo laboratorio (tenant) sin cambios de código ni migración manual de esquema.
- OE-12: Diseñar el modelo de datos y la API de forma que agregar un nuevo módulo (ej. un nuevo tipo de reporte) no requiera modificar módulos existentes (Open/Closed Principle aplicado a nivel de arquitectura).

## 3. Objetivos medibles por fase

| Fase | Objetivo medible |
|---|---|
| Fase 1 (Documentación) | 100% de los 19 documentos revisados y aprobados por el Product Owner antes de iniciar código |
| Fase 2 (MVP: Auth + Equipos + Documentos) | Un usuario puede registrar un equipo, subirle un documento y ver su estado en el dashboard, de punta a punta |
| Fase 3 (Calibraciones + Mantenimientos + Alertas) | El sistema calcula y notifica automáticamente vencimientos sin intervención manual |
| Fase 4 (Reportes + Auditoría + QR) | Un laboratorio piloto puede preparar una auditoría ISO 15189 completa usando únicamente LabSync Pro |

Ver desglose completo de fases en `17-roadmap.md` y `18-sprints.md`.
