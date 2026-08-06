# 12 — Component Library

Catálogo de componentes reutilizables. Cada uno se implementa sobre primitivas de `shadcn/ui` (Radix UI + Tailwind) para heredar accesibilidad de base (foco, ARIA, teclado), y se personaliza con los tokens de `11-design-system.md`.

Formato por componente: Nombre · Uso · Propiedades · Estados · Variantes · Accesibilidad.

---

### Button
- **Uso:** acción primaria/secundaria en formularios, toolbars, cards.
- **Propiedades:** `variant` (primary/secondary/destructive/ghost), `size` (sm/md/lg), `loading`, `disabled`, `icon`.
- **Estados:** default, hover, focus-visible, active/pressed, disabled, loading.
- **Variantes:** con ícono izquierdo, solo ícono (requiere `aria-label`), ancho completo.
- **Accesibilidad:** `<button>` nativo, `aria-busy="true"` durante loading, foco visible con anillo de 2px, área táctil mínima 44×44px.

### Input / TextField
- **Uso:** captura de texto, email, contraseña, número.
- **Propiedades:** `label`, `icon`, `error`, `helperText`, `type`, `autoComplete`.
- **Estados:** default, hover, focus, error, disabled, read-only.
- **Variantes:** con toggle de contraseña, con ícono de validación.
- **Accesibilidad:** `<label for>` obligatorio, `aria-invalid` + `aria-describedby` en error, nunca placeholder como único label (patrón ya implementado y auditado en el login).

### Select / Combobox
- **Uso:** selección de una opción de una lista (categoría, área, rol).
- **Propiedades:** `options`, `searchable`, `multiple`, `error`.
- **Estados:** cerrado, abierto, con búsqueda activa, sin resultados, error.
- **Accesibilidad:** patrón ARIA APG combobox/listbox, navegación completa por teclado, anuncio de resultados vía live region cuando `searchable`.

### Checkbox / Switch
- **Uso:** valores booleanos (Recordarme, activar notificaciones).
- **Propiedades:** `checked`, `indeterminate` (checkbox), `disabled`.
- **Estados:** unchecked, checked, indeterminate, disabled, focus-visible.
- **Accesibilidad:** `<input>` real detrás del control visual (patrón ya implementado en el checkbox "Recordarme" del login), label clicable con hit-area compartida.

### Card
- **Uso:** contenedor de contenido agrupado (KPI, resumen de equipo, item de listado en mobile).
- **Propiedades:** `variant` (default/kpi/interactive), `padding`.
- **Estados:** default, hover (solo si `interactive`), focus-visible (si es clicable).
- **Accesibilidad:** si es clicable en su totalidad, usar `<button>`/`<a>` como wrapper semántico, no `onClick` sobre un `<div>`.

### DataTable
- **Uso:** listados de equipos, documentos, calibraciones, auditoría.
- **Propiedades:** `columns`, `data`, `sortable`, `pagination`, `rowActions`, `emptyState`.
- **Estados:** cargando (skeleton rows), con datos, vacío, error de carga.
- **Variantes:** modo tarjeta automático en mobile (ver `10-wireframes.md`).
- **Accesibilidad:** `<table>` semántico con `scope` en encabezados, `aria-sort` en columnas ordenables, foco gestionado en paginación.

### Modal / Dialog
- **Uso:** confirmaciones, formularios cortos, previsualización de documentos.
- **Propiedades:** `title`, `size`, `dismissible`, `onConfirm`.
- **Estados:** abierto/cerrado, con cambios sin guardar (confirma antes de cerrar).
- **Accesibilidad:** `role="dialog"`, `aria-modal="true"`, foco atrapado (`inert` en el fondo), retorno de foco al disparador.

### Toast
- **Uso:** confirmaciones puntuales de acciones (guardado, error de red).
- **Propiedades:** `variant` (success/warning/error/info), `duration`, `action`.
- **Estados:** entrando, visible, saliendo, con acción pendiente (no auto-dismiss).
- **Accesibilidad:** `aria-live="polite"` (o `assertive` solo para errores críticos), no roba el foco.

### Badge (estado semafórico)
- **Uso:** estado de calibración/documento/equipo.
- **Propiedades:** `status` (vigente/proximo/vencido/sin-info).
- **Accesibilidad:** siempre incluye texto además del color (ver `11-design-system.md`).

### Tabs
- **Uso:** navegación entre secciones de un mismo detalle (ficha de equipo).
- **Accesibilidad:** patrón ARIA APG tabs, `roving tabindex`, flechas para navegar entre tabs con foco.

### Breadcrumb
- **Uso:** orientación en vistas profundas.
- **Accesibilidad:** `<nav aria-label="Breadcrumb">`, último ítem sin enlace (`aria-current="page"`).

### Sidebar
- **Uso:** navegación primaria de la aplicación.
- **Propiedades:** `collapsed`, `items` (filtrados por rol).
- **Accesibilidad:** `<nav aria-label="Principal">`, ítem activo indicado con `aria-current="page"` además de estilo visual.

### Navbar
- **Uso:** barra superior con búsqueda, notificaciones, tema, perfil.
- **Accesibilidad:** cada ícono-botón con `aria-label` descriptivo (búsqueda, notificaciones, cambiar tema).

### CommandPalette (omnibox)
- **Uso:** búsqueda global (`Cmd/Ctrl+K`).
- **Propiedades:** `groups`, `onSelect`, `recentItems`.
- **Accesibilidad:** patrón ARIA APG listbox dentro de dialog, anuncio de número de resultados vía live region.

### Calendar
- **Uso:** calendario operacional.
- **Propiedades:** `view` (día/semana/mes/agenda), `events`, `onEventClick`.
- **Accesibilidad:** grid navegable por teclado, cada celda de día con `aria-label` de fecha completa y conteo de eventos.

### Chart (wrapper sobre librería de gráficas)
- **Uso:** KPIs visuales del Dashboard y Reportes.
- **Propiedades:** `type` (line/donut/bar), `data`, `accessibleTable` (siempre `true` por defecto).
- **Accesibilidad:** tabla de datos alternativa colapsable junto a cada gráfico (regla `data-table`).

### FileUpload / Dropzone
- **Uso:** subida de documentos y evidencias.
- **Propiedades:** `multiple`, `accept`, `maxSize`, `onProgress`.
- **Estados:** idle, arrastrando sobre la zona, subiendo (progreso), error, completado.
- **Accesibilidad:** alternativa de botón "Seleccionar archivo" siempre visible (el drag & drop nunca es el único método — regla `gesture-alternative`).

### EmptyState
- **Uso:** listados sin datos (ilustrado, con acción sugerida).
- **Propiedades:** `title`, `description`, `action`, `illustration`.

### Skeleton Loader
- **Uso:** estado de carga >300ms en tablas, cards y detalle.
- **Accesibilidad:** `aria-busy="true"` en el contenedor mientras se muestra.

---

## Gobernanza de componentes

- Todo componente nuevo debe pasar el checklist de accesibilidad de `19-checklist.md` antes de integrarse a la librería compartida.
- Los componentes viven en `frontend/src/shared/components/` (ver `13-arquitectura.md`) y se documentan con Storybook — cada historia cubre variante, estado y ambos modos de tema.
