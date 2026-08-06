# 10 — Wireframes

Wireframes de baja fidelidad en ASCII, organizados por pantalla y breakpoint (Desktop ≥1280px, Tablet 768–1023px, Mobile <768px). El objetivo es fijar **estructura y jerarquía**, no estilo visual final (eso corresponde a `11-design-system.md` y a la implementación).

Convención de breakpoints: coincide con `04-requerimientos-no-funcionales.md` (RNF-RESP) y con los ya validados en el login (390 / 768 / 1024px).

---

## 1. Login (ya implementado — referencia de anclaje visual)

Ya construido y auditado en accesibilidad (`index.html` actual del repositorio). Se documenta aquí solo como referencia de que el resto de la plataforma **hereda** su lenguaje visual (split layout, panel institucional + formulario), no lo reinventa. Wireframe de detalle: ver el archivo real existente.

---

## 2. Dashboard

### Desktop (≥1280px)
```
┌─────────┬──────────────────────────────────────────────────────────┐
│ SIDEBAR │  NAVBAR: [Buscar ⌘K]           [🔔 Alertas] [Tema] [Perfil]│
│         ├──────────────────────────────────────────────────────────┤
│ Logo    │  Dashboard                                                │
│         │                                                            │
│ Dashboard│ ┌────────┬────────┬────────┬────────┬────────┬────────┐  │
│ Equipos │  │ Equipos│ Fuera  │ Calib. │ Calib. │ Doc.   │ Mant.  │  │
│ Docum.  │  │ activos│ servic.│ próxim.│ vencid.│ vencer │ pend.  │  │
│ Calibr. │  └────────┴────────┴────────┴────────┴────────┴────────┘  │
│ Manten. │                                                            │
│ Calend. │  ┌──────────────────────────┐  ┌────────────────────────┐ │
│ Alertas │  │  Cumplimiento (línea)     │  │ Equipos por estado     │ │
│ Reportes│  │                            │  │ (donut)                │ │
│ Auditor.│  └──────────────────────────┘  └────────────────────────┘ │
│ Usuarios│                                                            │
│ Config. │  ┌──────────────────────────┐  ┌────────────────────────┐ │
│         │  │ Alertas prioritarias      │  │ Actividad reciente      │ │
│         │  │ (lista, rojo primero)     │  │ (timeline)               │ │
│         │  └──────────────────────────┘  └────────────────────────┘ │
└─────────┴──────────────────────────────────────────────────────────┘
```

### Tablet (768–1023px)
```
┌──┬────────────────────────────────────────┐
│☰ │ NAVBAR: [Buscar]      [🔔] [Tema][Perfil]│
├──┴────────────────────────────────────────┤
│ Dashboard                                   │
│ ┌────────┬────────┬────────┐               │
│ │ KPI 1  │ KPI 2  │ KPI 3  │  (scroll → más)│
│ └────────┴────────┴────────┘               │
│ ┌──────────────────────────┐                │
│ │ Cumplimiento (línea)      │                │
│ └──────────────────────────┘                │
│ ┌──────────────────────────┐                │
│ │ Equipos por estado (donut)│                │
│ └──────────────────────────┘                │
│ ┌──────────────────────────┐                │
│ │ Alertas prioritarias      │                │
│ └──────────────────────────┘                │
└──────────────────────────────────────────────┘
```
Sidebar colapsa a ícono hamburguesa (☰) → drawer superpuesto, mismo patrón ya usado en el panel izquierdo del login a 768px (colapso a barra superior compacta).

### Mobile (<768px)
```
┌────────────────────────┐
│ ☰   LabSync Pro    🔔 👤 │
├────────────────────────┤
│ Dashboard                │
│ ┌──────────┐ ┌─────────┐│
│ │ Equipos  │ │ Calib.  ││
│ │ activos  │ │ vencidas││ ← KPIs en grid 2 col,
│ └──────────┘ └─────────┘│   scroll vertical
│ ┌──────────┐ ┌─────────┐│
│ │ Doc. por │ │ Mant.   ││
│ │ vencer   │ │ pend.   ││
│ └──────────┘ └─────────┘│
│ ┌────────────────────┐ │
│ │ Alertas prioritarias│ │ ← prioridad de contenido:
│ └────────────────────┘ │   alertas antes que gráficas
│ ┌────────────────────┐ │   (RNF-RESP + content-priority)
│ │ Gráfica (1 por fila)│ │
│ └────────────────────┘ │
└────────────────────────┘
```

---

## 3. Listado de Equipos

### Desktop
```
┌─────────┬──────────────────────────────────────────────────────────┐
│ SIDEBAR │ Equipos                          [+ Nuevo equipo]         │
│         ├──────────────────────────────────────────────────────────┤
│         │ [Buscar equipos...]  [Categoría ▾][Estado ▾][Área ▾][⚙]  │
│         ├──────────────────────────────────────────────────────────┤
│         │ ☐ Código │ Nombre        │ Categoría │ Estado │ Semáforo│⋮│
│         │ ☐ EQ-001 │ Microscopio A │ Micro.    │ Operat.│  🟢    │⋮│
│         │ ☐ EQ-002 │ Centrífuga B  │ Hematol.  │ Operat.│  🟡    │⋮│
│         │ ☐ EQ-003 │ Analizador C  │ Bioquím.  │ Fuera  │  🔴    │⋮│
│         │  ...                                          [Exportar]│
│         │                                    [◂ 1 2 3 ... 12 ▸]   │
└─────────┴──────────────────────────────────────────────────────────┘
```

### Tablet — misma tabla con columnas reducidas (oculta Categoría/Área tras un toggle "más filtros"); filas con más padding táctil.

### Mobile — la tabla se transforma en tarjetas (RNF-RESP-03):
```
┌────────────────────────┐
│ Equipos      [+ Nuevo]  │
│ [Buscar...]     [⚙]     │
├────────────────────────┤
│ ┌──────────────────┐   │
│ │ EQ-001  🟢         │   │
│ │ Microscopio A      │   │
│ │ Microbiología      │   │
│ │ Operativo          │   │
│ └──────────────────┘   │
│ ┌──────────────────┐   │
│ │ EQ-002  🟡         │   │
│ │ Centrífuga B       │   │
│ └──────────────────┘   │
└────────────────────────┘
```

---

## 4. Ficha de detalle de Equipo

### Desktop
```
┌─────────┬──────────────────────────────────────────────────────────┐
│ SIDEBAR │ Equipos / EQ-001 Microscopio A          [Editar][⋮][QR]  │
│         ├──────────────────────────────────────────────────────────┤
│         │ ┌─────────────┐  Nombre, categoría, estado 🟢            │
│         │ │   Foto      │  Marca / Modelo / N° serie                │
│         │ │   equipo    │  Área / Responsable / Fecha adquisición   │
│         │ └─────────────┘                                           │
│         ├──────────────────────────────────────────────────────────┤
│         │ [Resumen][Calibraciones][Mantenimientos][Documentos][Historial]│
│         ├──────────────────────────────────────────────────────────┤
│         │ (contenido de la pestaña activa)                          │
└─────────┴──────────────────────────────────────────────────────────┘
```
Tablet/Mobile: la foto pasa arriba a ancho completo, las pestañas se vuelven un select/scroll horizontal, el resto apila en una columna — mismo patrón de colapso ya validado en el login.

---

## 5. Gestor Documental

### Desktop
```
┌─────────┬──────────────────────────────────────────────────────────┐
│ SIDEBAR │ Documentos                          [Subir archivos ▾]   │
│         ├──────────────────────────────────────────────────────────┤
│ ▸ Carpetas│ [Buscar en documentos...]                                │
│  ▾ Calidad│ ┌────────────────────────────────────────────────────┐ │
│    Proced.│ │  ▤ Nombre        Estado    Vigencia   Versión  ⋮   │ │
│  ▸ Equipos│ │  📄 Manual X.pdf  Vigente   2026-05-01   v3     ⋮   │ │
│ ▸ Favoritos│ │  📄 Proc-Y.docx   Revisión  —           v2     ⋮   │ │
│ ▸ Papelera │ └────────────────────────────────────────────────────┘ │
│         │  (zona de drop activa al arrastrar archivos sobre la tabla)│
└─────────┴──────────────────────────────────────────────────────────┘
```
Mobile: árbol de carpetas colapsa a un breadcrumb + selector; tabla → tarjetas con ícono de tipo de archivo, nombre, badge de estado.

---

## 6. Calendario Operacional

### Desktop
```
┌─────────┬──────────────────────────────────────────────────────────┐
│ SIDEBAR │ Calendario         [Día][Semana][Mes][Agenda]  [+ Evento] │
│         ├──────────────────────────────────────────────────────────┤
│         │  Lun   Mar   Mié   Jue   Vie   Sáb   Dom                  │
│         │  [ ]   [🟡]  [ ]   [🔴]  [ ]   [ ]   [ ]   ← vista mes    │
└─────────┴──────────────────────────────────────────────────────────┘
```
Mobile: vista por defecto = Agenda (lista cronológica), no grid de mes — un grid mensual completo no es usable en 375px sin sacrificar legibilidad (decisión de UX, no solo técnica).

---

## 7. Reportes

Desktop/Tablet/Mobile: patrón consistente de "selector de tipo de reporte" (grid de tarjetas) → panel de filtros → botón de generación, apilando de grid 3 columnas (desktop) a 1 columna (mobile).

---

## 8. Configuración y Usuarios

Patrón de formulario por secciones con navegación lateral tipo tabs (desktop) que colapsa a acordeón (mobile) — mismo patrón de layout usado en la ficha de equipo.

---

## 9. Vista pública QR (`/qr/:token`)

### Mobile (diseño mobile-first — es el uso principal de esta vista)
```
┌────────────────────────┐
│      LabSync Pro         │  ← header minimal, sin sidebar
├────────────────────────┤
│      [Foto equipo]        │
│  Microscopio A · EQ-001   │
│  Estado: 🟢 Operativo     │
│  Última calibración:      │
│    2026-01-15              │
│  Próxima calibración:      │
│    2027-01-15               │
│  [Ver documentos]           │
│  [Reportar novedad]         │
└────────────────────────┘
```
Desktop: mismo contenido centrado en columna angosta (max-width ~480px) — no se "estira" a ancho completo, ya que es contenido de consulta rápida, no un dashboard.
