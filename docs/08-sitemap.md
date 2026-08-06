# 08 — Sitemap

## 1. Mapa de navegación completo

```
LabSync Pro
│
├── /login                          (público)
├── /recuperar-contraseña           (público)
├── /activar-cuenta/:token          (público)
├── /qr/:token                      (público — vista de equipo por QR)
│
└── (autenticado — dentro del shell de la aplicación)
    │
    ├── /dashboard                              [A, DT, C, M, T*, CO]
    │
    ├── /equipos                                [A, DT, C, M, T, CO]
    │   ├── /equipos/nuevo                      [A, DT, M]
    │   ├── /equipos/:id                        [todos — lectura]
    │   ├── /equipos/:id/editar                 [A, DT, M]
    │   └── /equipos/:id/historial              [todos — lectura]
    │
    ├── /documentos                             [A, DT, C, M, T*, CO]
    │   ├── /documentos/carpeta/:id
    │   ├── /documentos/:id                     (detalle + versiones)
    │   ├── /documentos/favoritos
    │   ├── /documentos/recientes
    │   └── /documentos/papelera                [A, C]
    │
    ├── /calibraciones                          [A, DT, C, M, T*, CO]
    │   ├── /calibraciones/nueva                [A, M]
    │   ├── /calibraciones/:id
    │   └── /calibraciones/criticos             (equipos próximos a vencer)
    │
    ├── /mantenimientos                         [A, DT, C, M, T, CO]
    │   ├── /mantenimientos/nuevo                [A, M, T]
    │   ├── /mantenimientos/:id
    │   └── /mantenimientos/programados
    │
    ├── /calendario                             [todos]
    │
    ├── /alertas                                [todos — ámbito según rol]
    │
    ├── /reportes                               [A, DT, C, M*, T*, CO*]
    │   ├── /reportes/inventario
    │   ├── /reportes/calibraciones
    │   ├── /reportes/cumplimiento
    │   ├── /reportes/mantenimiento
    │   ├── /reportes/trazabilidad-documental
    │   └── /reportes/paquete-auditoria/:equipoId
    │
    ├── /auditoria                              [A, C]
    │
    ├── /usuarios                               [A]
    │   ├── /usuarios/nuevo                     [A]
    │   └── /usuarios/:id                       [A]
    │
    └── /configuracion                          [todos — sección "Mi perfil"; el resto de secciones ["Laboratorio",
        "Alertas", "Categorías y áreas"] solo visibles para A dentro de la misma página]

* Ajuste de Sprint 12 sobre el diseño original: una sola ruta con secciones
  (pestañas) en vez de `/configuracion/*` + `/perfil` como rutas separadas
  — un único punto de entrada de "Configuración" es el patrón más común en
  SaaS comparables y evita duplicar el shell de página para cada sección.

* = vista con alcance reducido a su ámbito/rol, no la vista completa
```

## 2. Notas de navegación

- El **shell autenticado** incluye: sidebar colapsable (navegación primaria), navbar superior (búsqueda global, notificaciones, selector de tema, menú de perfil), y breadcrumb en vistas de 3+ niveles de profundidad.
- La navegación primaria (sidebar) es idéntica en estructura para todos los roles; los ítems a los que un rol no tiene acceso simplemente no se renderizan (no se muestran deshabilitados, para no generar ruido visual — ver `RN-USR` y principio de "menos es más" del Design System).
- Las rutas de detalle (`/equipos/:id`, `/documentos/:id`, etc.) son deep-linkeables y compartibles — requisito no funcional RNF-ESC / buena práctica de navegación (`09-user-flows.md` detalla el comportamiento de retroceso).
- La vista `/qr/:token` vive **fuera** del shell autenticado — es una página pública standalone, ligera, sin sidebar ni navegación de la app (ver `03-requerimientos-funcionales.md`, Módulo 13).

## 3. Landmarks y estructura semántica (ligado a `10-jakubkrehel/better-accessibility` ya aplicado en el login)

- Un único `<main>` por vista.
- `<nav>` para sidebar y breadcrumb, cada uno con `aria-label` distintivo.
- Encabezados jerárquicos: `<h1>` = título de la vista actual, nunca el nombre del producto.
