# 11 — Design System

## 0. Nota de continuidad con el login existente

El login ya construido (`index.html`/`styles.css`) ancla la identidad de marca en verde `#0F5132`. Este documento **extiende** esa base para toda la plataforma, con dos ajustes deliberados que se documentan explícitamente en lugar de dejarlos como inconsistencia silenciosa:

1. **Paleta**: se adopta la paleta ampliada especificada para LabSync Pro (con verde clínico `#198754` como color medio y una escala completa de estados), reemplazando el verde medio provisional `#1B7A4A` usado en el login. El verde oscuro ancla `#0F5132` se mantiene idéntico — es la raíz de marca y no cambia.
2. **Tipografía**: el login usa Fraunces (serif editorial) + Inter, apropiado para una pantalla de marca de baja frecuencia de uso. El resto de la plataforma es un dashboard denso de alta frecuencia de uso, donde una serif editorial perjudica la legibilidad en tablas y KPIs. Se adopta **Inter (interfaz) + Plus Jakarta Sans (títulos)** — ambas sans-serif geométricas modernas, coherentes con el registro visual de Linear/Vercel — como tipografía del producto. Fraunces se conserva **únicamente** en el panel institucional del login como acento de marca, no se propaga al resto de la UI.

---

## 1. Paleta de colores

### Primarios (marca)
| Token | Valor | Uso |
|---|---|---|
| `--color-primary-900` | `#0F5132` | Verde profundo — texto de marca, botones primarios, sidebar activo |
| `--color-primary-600` | `#198754` | Verde clínico — hover, acentos, gráficas, elementos interactivos |
| `--color-primary-100` | `#D1E7DD` | Verde suave — fondos de badges, hover sutil, superficies de apoyo |

### Neutros
| Token | Valor | Uso |
|---|---|---|
| `--color-white` | `#FFFFFF` | Superficie base (light mode) |
| `--color-bg` | `#F8FAFC` | Fondo de aplicación (light mode) |
| `--color-border` | `#E5E7EB` | Bordes, divisores |
| `--color-ink` | `#111827` | Texto principal |

### Estados (semánticos — nunca color solo, siempre + ícono/texto, ver `16-jakubkrehel/better-accessibility` ya aplicado)
| Token | Valor | Uso |
|---|---|---|
| `--color-success` | `#16A34A` | Confirmaciones, estado "Vigente" |
| `--color-warning` | `#F59E0B` | Estado "Próximo a vencer" |
| `--color-danger` | `#DC2626` | Estado "Vencido", errores |
| `--color-info` | `#2563EB` | Información neutra, enlaces informativos |
| `--color-neutral-status` | `#94A3B8` | Estado "Sin información" (gris del semáforo) |

### Dark mode (paridad de contraste, no inversión simple — ver `16-seguridad.md`/checklist de accesibilidad)
| Token | Light | Dark |
|---|---|---|
| `--surface` | `#FFFFFF` | `#0F1720` |
| `--surface-alt` | `#F8FAFC` | `#161F2B` |
| `--text-primary` | `#111827` | `#F1F5F9` |
| `--text-secondary` | `#5C6862` | `#94A3B8` |
| `--border` | `#E5E7EB` | `#263042` |
| `--primary-900` (marca) | `#0F5132` | `#3FAE73` (aclarado para mantener 4.5:1 sobre superficie oscura) |

Todas las combinaciones texto/fondo de esta tabla están verificadas ≥4.5:1 (texto normal) / ≥3:1 (texto grande e íconos), por rol, en ambos modos — criterio de aceptación obligatorio antes de aprobar cualquier componente nuevo (RNF-ACC-02).

---

## 2. Tipografía

| Token | Fuente | Uso |
|---|---|---|
| `--font-display` | Plus Jakarta Sans (600/700) | Títulos de página, encabezados de sección, KPIs numéricos |
| `--font-body` | Inter (400/500/600) | Cuerpo de texto, tablas, formularios, navegación |

**Escala tipográfica:**
```
--text-xs:   12px / 1.5   (metadatos, etiquetas)
--text-sm:   13px / 1.5   (texto secundario, tablas)
--text-base: 16px / 1.6   (cuerpo de texto — nunca menor en contenido de lectura)
--text-lg:   18px / 1.5   (subtítulos)
--text-xl:   22px / 1.3   (títulos de sección)
--text-2xl:  28px / 1.2   (títulos de página)
--text-3xl:  36px / 1.15  (KPIs destacados, valores numéricos grandes)
```

---

## 3. Espaciados (escala 8pt, heredada del login)

```
--space-1: 4px   --space-4: 24px   --space-7: 56px
--space-2: 8px   --space-5: 32px   --space-8: 64px
--space-3: 16px  --space-6: 40px
```

---

## 4. Iconografía

- Set único: **Lucide** (consistente con lo ya usado como SVG lineales en el login — mismo grosor de trazo 2px).
- Tamaños tokenizados: `--icon-sm: 16px`, `--icon-md: 20px`, `--icon-lg: 24px`.
- Nunca emojis como íconos funcionales (regla ya aplicada en el login, se mantiene como estándar del producto).

---

## 5. Componentes base

### Botones
- **Primario**: fondo `--color-primary-900`, hover `--color-primary-600`, texto blanco, radio `10px`, altura `40px` (desktop) / `44px` (táctil).
- **Secundario**: borde `--color-border`, fondo transparente, texto `--text-primary`.
- **Destructivo**: fondo `--color-danger`, reservado para acciones irreversibles, siempre con confirmación previa.
- **Estados**: hover (150–250ms), focus-visible con anillo `--color-primary-600` 2px offset 2px, disabled (opacidad 0.5 + cursor not-allowed), loading (spinner + texto de estado, patrón ya implementado en el botón del login).

### Inputs
- Altura `44px`, borde `1.5px solid --color-border`, radio `10px`, ícono contextual a la izquierda, focus con anillo de color de marca — mismo patrón ya construido y auditado en el login (reutilizar el componente, no reinventarlo).
- Error: borde `--color-danger` + ícono + texto de error asociado vía `aria-describedby` (patrón ya implementado y corregido en la auditoría de accesibilidad del login).

### Cards
- Fondo `--surface`, borde `1px solid --border`, radio `14px`, sombra suave de un solo nivel (`0 1px 3px rgba(0,0,0,.06)`), padding `--space-4`.
- Variante "KPI card": número grande (`--text-3xl`, `--font-display`), etiqueta (`--text-sm`, `--text-secondary`), ícono de estado opcional.

### Tablas
- Encabezado sticky en scroll vertical, filas con hover sutil, densidad configurable (cómoda/compacta), nunca menos de 40px de alto de fila en modo cómodo (RNF-ACC touch targets).
- En mobile: transformación a tarjetas (ver `10-wireframes.md`), nunca scroll horizontal forzado sin indicación visual.

### Modales
- Overlay `rgba(0,0,0,.5)` mínimo (regla de "scrim" de `better-accessibility`), foco atrapado dentro del modal, `Esc` cierra, foco retorna al disparador al cerrar.
- Confirmación de cierre si hay cambios sin guardar (regla `sheet-dismiss-confirm`).

### Dropdowns / Selects
- Nativo cuando es posible (mejor soporte de accesibilidad); custom solo cuando se requiere búsqueda o multi-selección, siempre con patrón ARIA APG (combobox) completo.

### Alertas y Toasts
- Alertas persistentes (banner) para estados de página; toasts para confirmaciones puntuales, auto-dismiss 4–5s **excepto** toasts de error o con acción, que permanecen hasta interacción explícita (regla `toast-dismiss` ya aplicada como criterio).
- Siempre ícono + color + texto — nunca color como único indicador (RN transversal de accesibilidad).

### Badges (estado semafórico — reutilizado en Equipos, Calibraciones, Documentos)
```
🟢 Vigente     → fondo --color-primary-100, texto --color-primary-900
🟡 Por vencer  → fondo #FEF3C7, texto #92400E
🔴 Vencido     → fondo #FEE2E2, texto #991B1B
⚪ Sin info    → fondo #F1F5F9, texto #475569
```
(íconos de color acompañados siempre de texto de estado, no solo el punto de color — ver `RN` de accesibilidad)

### Tabs / Breadcrumb / Sidebar / Navbar
- Tabs: subrayado animado (200ms) bajo el tab activo, navegación con flechas ← → cuando tienen foco (patrón ARIA APG tabs).
- Breadcrumb: presente en vistas de 3+ niveles, cada nivel navegable.
- Sidebar: colapsable, ítem activo con fondo `--color-primary-100` + borde izquierdo `--color-primary-900`, íconos + etiqueta siempre visibles (nunca solo ícono, salvo modo colapsado explícito con tooltip).
- Navbar: búsqueda global, centro de notificaciones (badge de conteo), selector de tema, menú de perfil — igual en todas las vistas autenticadas.

### Calendario
- Grid mensual (desktop/tablet), lista de agenda (mobile por defecto — ver `10-wireframes.md`), eventos codificados por color según tipo + ícono distintivo (nunca solo color).

### Gráficas
- Paleta de datos accesible (no depender solo de rojo/verde para series comparables — se usa la escala de estados + azul info para series neutras).
- Todo gráfico tiene tabla de datos alternativa accesible (RNF-ACC / regla `data-table` de UI/UX Pro Max).

---

## 6. Modo claro / oscuro

- Variables CSS centralizadas (ver tabla de la sección 1), sin colores embebidos en componentes.
- Cambio instantáneo sin recarga, persistido en `localStorage`, respetando `prefers-color-scheme` como valor inicial si el usuario no ha elegido explícitamente.
- Cada componente nuevo se diseña y verifica en **ambos** modos antes de aprobarse (checklist en `19-checklist.md`).

---

## 7. Design Tokens (resumen técnico)

```css
:root {
  --color-primary-900: #0F5132;
  --color-primary-600: #198754;
  --color-primary-100: #D1E7DD;
  --color-white: #FFFFFF;
  --color-bg: #F8FAFC;
  --color-border: #E5E7EB;
  --color-ink: #111827;
  --color-success: #16A34A;
  --color-warning: #F59E0B;
  --color-danger: #DC2626;
  --color-info: #2563EB;
  --font-display: 'Plus Jakarta Sans', sans-serif;
  --font-body: 'Inter', sans-serif;
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --ease-out: cubic-bezier(.16,1,.3,1);
  --dur-fast: 150ms;
  --dur-base: 220ms;
}
```

Estos tokens son la fuente única de verdad; se implementan como CSS variables (frontend) y se documentan en Storybook/Component Library (`12-component-library.md`) para que ningún componente use un valor hardcodeado fuera de este set.
