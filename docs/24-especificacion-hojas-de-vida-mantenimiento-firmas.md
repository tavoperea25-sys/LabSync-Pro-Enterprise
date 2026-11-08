# 24 — Especificación: Hojas de vida, reportes de mantenimiento y firma electrónica

**Proyecto:** LabSync Pro Enterprise
**Autor:** Gustavo Perea (Líder de Gestión Metrológica, LSPC)
**Estado:** Aprobado por Calidad del LSPC (aprobación verbal, registrada el 2026-11-06) para digitalizar FOR-003 y FOR-005 con firma electrónica.
**Fase 0 (seguridad):** completada — PR #60 y PR #61 fusionados en `develop`.

> **Nota de nomenclatura:** en este documento, "Fase N" se refiere a las etapas del plan (sección 5).
> "PR #N" se refiere siempre a un pull request de GitHub. No confundirlos.
**Formatos institucionales de referencia:**
- `LSPC-GMT-GPM-FOR-003` — Hoja de vida y mantenimiento de equipos (versión 6, 2024-10-01). Hojas: `H.V.` y `MTTO`.
- `LSPC-GMT-ECM-FOR-005` — Reporte de mantenimiento de equipos (versión 04, 2024-10-01).

> Guardar este archivo en `docs/24-especificacion-hojas-de-vida-mantenimiento-firmas.md` del repositorio y
> guardar copias en blanco de ambos formatos en `docs/formatos/` (sin datos reales). Claude Code los leerá desde ahí.

---

## 1. Objetivo

Pasar a digital el ciclo completo que hoy se lleva en papel:

1. **Ficha técnica** del equipo → genera su **hoja de vida digital** (FOR-003), descargable en PDF.
2. **Hojas de vida físicas existentes** → se escanean y se adjuntan al equipo como antecedente histórico.
3. **Reporte de mantenimiento** (FOR-005) preventivo, correctivo o de instalación → se **firma en tablet o celular** → se genera el PDF.
4. Todo mantenimiento firmado aparece **automáticamente** en el historial de la hoja de vida, sin transcribir nada.

## 2. Punto de partida (lo que ya existe en el repo)

No se construye desde cero. Ya existen y deben **extenderse**, no reemplazarse:

| Pieza existente | Qué tiene hoy | Qué le falta |
|---|---|---|
| `equipos.Equipo` | código, nombre, categoría, marca, modelo, serie, fabricante/proveedor (texto), fecha adquisición, estado operativo, área, foto, manual, observaciones, borrado lógico | grupo, subgrupo, capítulo, ubicación, N° inventario, condición física, riesgo, criticidad, forma de adquisición, garantía, datos técnicos y físicos, accesorios, manuales por tipo |
| `mantenimientos.Mantenimiento` | tipo, estado, fechas programada/ejecutada, técnico, descripción, repuestos (texto), costo, adjunto, frecuencia, recurrencia | falla reportada, checklist, repuestos estructurados, evidencias antes/durante/después, recibido/supervisado por, firmas, PDF, anulación |
| `calibraciones` | registro de calibraciones con semáforo | integrarse al historial y al cronograma metrológico |
| `documentos` / MinIO | gestor documental con buckets por tipo | tipo "hoja de vida física escaneada" |
| `auditoria` | registro de cambios | — (reutilizar) |
| `fpdf2` | ya se usa para reportes | plantillas FOR-003 y FOR-005 |

Convención del proyecto: **nombres en español** (`Equipo`, `Mantenimiento`), arquitectura por capas (`domain/application/infrastructure/presentation`), migraciones Alembic numeradas, RLS por laboratorio, tests por sprint. Todo lo nuevo sigue esa convención.

## 3. Decisiones de diseño (cerrar ANTES de programar)

### 3.1 Un documento firmado es inmutable

Un reporte firmado es un registro de calidad y evidencia ante auditorías. Por eso:

- Estados del reporte: `borrador → pendiente_firmas → firmado → (anulado)`.
- Mientras es `borrador` se puede editar libremente.
- Al completarse las firmas obligatorias, el reporte queda **firmado y bloqueado**. No se edita nunca más.
- Si hay un error en un reporte firmado, se **anula** (motivo + quién + cuándo, auditado) y se crea uno nuevo que referencia al anulado (`reemplaza_a_id`). El anulado sigue visible en el historial, marcado como tal.

### 3.2 Relación viva + instantánea congelada

Regla general: el reporte se relaciona con el equipo por `equipo_id`, sin duplicar datos. **Excepción deliberada:** al firmar, se guarda una instantánea (`snapshot` JSONB) con los datos del equipo tal como estaban en ese momento, y el PDF generado se guarda en MinIO con su hash SHA-256.

Motivo: si mañana el equipo cambia de ubicación, el reporte de hoy debe seguir diciendo la ubicación de hoy. Un documento firmado no puede "cambiar solo" al regenerarse.

### 3.3 El historial es una consulta, no una tabla copiada

El historial de la hoja de vida se construye como una **vista** (o consulta de servicio) que une mantenimientos, calibraciones, calificaciones y verificaciones del equipo, ordenados por fecha. No existe un proceso que "copie" registros al historial: el historial **es** la unión de esos registros. Así es imposible que se desincronice o se duplique.

Nota: la hoja `MTTO` del FOR-003 registra todas las intervenciones metrológicas (MTTO preventivo, correctivo, calibración, calificación, verificación interna), no solo mantenimientos. El historial digital debe reflejar eso.

### 3.4 Condición física ≠ estado operativo

El formato pide condición **Bueno / Regular / Malo**. El sistema ya tiene `estado_operativo` (operativo, en mantenimiento, fuera de servicio…). Son conceptos distintos: un equipo puede estar en condición "Regular" y operativo. Se agregan como dos campos separados.

### 3.5 Firma electrónica

- **Captura:** trazo en `<canvas>` con la librería `signature_pad` (con `touch-action: none` para tablet y celular). Se guarda como PNG en un bucket privado de MinIO.
- **Registro de cada firma:** rol (`realiza`, `recibe`, `supervisa`), nombre, cargo, registro INVIMA cuando aplique, `usuario_id` si el firmante tiene cuenta, fecha y hora del servidor, IP, user agent, y hash del contenido firmado.
- **Quién recibe normalmente no tiene cuenta:** firma de forma presencial en el mismo dispositivo del técnico, escribiendo nombre y cargo. La firma remota por enlace queda para una fase posterior.
- **Marco legal:** en Colombia aplican la Ley 527 de 1999 y el Decreto 2364 de 2012 (firma electrónica). **Aprobación:** Calidad del LSPC aprobó verbalmente el uso de firma electrónica capturada en tablet o celular para FOR-003 y FOR-005 (registrado el 2026-11-06). Evidencia: aprobación verbal, registrada en este documento. Si el procedimiento de los formatos debe actualizarse, lo gestiona Calidad; el sistema no depende de ello para construirse.
- **Dato sensible — cédula:** el FOR-003 tiene un campo "CC." del ingeniero. **Decisión:** el PDF muestra solo nombre, cargo y registro INVIMA; la cédula no se almacena ni se imprime.

### 3.6 Versiones de formato

Cada PDF lleva código, versión y fecha del formato. Esos valores se configuran por laboratorio, y cada documento generado guarda **qué versión usó**. Si Calidad publica la versión 7 del FOR-003, los PDF anteriores siguen mostrando la versión 6.

### 3.7 Checklist por tipo de equipo, configurable

Las actividades del FOR-005 (generales, sistema hidráulico, eléctrico, electrónico) se cargan como **plantillas** asociadas a la categoría del equipo, editables por el administrador. Nada hardcodeado en el frontend. Al crear un reporte, se copia el texto de cada ítem al reporte, para que cambiar la plantilla después no altere reportes ya firmados.

### 3.8 Campos técnicos variables

El formato antiguo (ficha técnica de dotación) tiene campos que solo aplican a ciertos equipos: CFM, refrigerante, compresor, ventiladores, potencia en frío/calor. Los campos comunes van como columnas; los específicos van en un JSONB `datos_adicionales` con un esquema por categoría. Todo campo técnico admite vacío o "N/A": no se obliga a inventar datos.

## 4. Modelo de datos propuesto (para validar en la auditoría)

- `equipos` (extender): `capitulo`, `grupo`, `subgrupo`, `ubicacion`, `numero_inventario`, `condicion_fisica`, `clasificacion_riesgo` (I, IIA, IIB, III), `criticidad` (baja, media, alta), `forma_adquisicion` (compra, donación, comodato), `garantia`, `garantia_inicio`, `garantia_fin`, `proveedor_id`, `fabricante_id`.
- `equipo_ficha_tecnica` (1:1): voltaje, corriente, frecuencia, mA, variable de medición, rango, RPM, temperatura y humedad de trabajo, peso, dimensiones, color, número de puertas, clase de sistema, alimentación, uso, uso específico, condiciones ambientales, `datos_adicionales` JSONB.
- `equipo_accesorios` (1:N): cantidad, descripción, observaciones.
- `equipo_manuales` (1:N, único por tipo): tipo, disponible, idioma, `documento_id`.
- `proveedores`, `fabricantes`: catálogos reutilizables. Migrar los textos actuales de `equipos.fabricante` y `equipos.proveedor`.
- `cronograma_metrologico`: (`equipo_id`, `tipo_actividad`) único; frecuencia, última ejecución, próxima ejecución. Reconciliar con `mantenimientos.frecuencia_meses` y con la frecuencia por defecto de calibración de la categoría.
- `mantenimientos` (extender): `falla_reportada`, `actividades_realizadas`, `comentarios`, `resultado`, `recomendaciones`, `estado_final_equipo`, `estado_documento`, `anulado_en`, `anulado_por`, `motivo_anulacion`, `reemplaza_a_id`, `consecutivo`.
- `plantillas_checklist` + `plantilla_checklist_items` (sistema, descripción, orden), asociadas a categoría.
- `mantenimiento_checklist`: texto del ítem copiado + `realizado`.
- `mantenimiento_repuestos`: pieza, referencia, cantidad, observaciones. Migrar el texto actual de `repuestos_utilizados` sin perderlo.
- `mantenimiento_evidencias`: momento (antes, durante, después, otro), reutilizando el almacenamiento de evidencias existente.
- `firmas`: polimórfica (`documento_tipo`, `documento_id`), con los campos de la sección 3.5.
- `documentos_generados`: tipo (FOR-003 / FOR-005), entidad, código y versión de formato, `object_key` del PDF, SHA-256, `snapshot` JSONB, generado por y cuándo.
- `equipo_novedades`: fallas, traslados, cambios de estado, baja; con fecha y responsable.

Todas las tablas nuevas con `laboratorio_id` y política RLS, igual que las existentes.

## 5. Plan de entrega por PR

Cada fase se entrega en uno o más PRs, cada uno en su propia rama desde `develop`, con migraciones, tests y verificación manual. **No se pasa a la siguiente fase sin aprobar el punto de control.**

**Prerrequisito para iniciar la Fase 1:** actualizaciones de dependencias del frontend fusionadas (Grupo B, zod v4 y vitest v4) y `develop` promovido a `main`. Los formularios nuevos se escriben directamente con la API de zod 4.

| Fase | Alcance | Punto de control (lo verifica Gustavo) |
|---|---|---|
| **0** | ✅ **Completada** (PR #60 y #61). Correcciones de seguridad: refresh concurrente, ventana de gracia fija, persistencia de la revocación por robo de token, "Recordarme", validación de secretos en producción, enumeración por tiempo, techo del bloqueo; imagen de MinIO fijada por digest | — |
| **1** | Auditoría y diseño **sin código**: mapa de lo existente, modelo de datos final, migraciones planeadas, wireframes de pantallas, riesgos | Documento aprobado por Gustavo |
| **2** | Ficha técnica extendida: migraciones, formulario por pestañas, foto, accesorios, manuales, proveedor y fabricante | Crear un equipo real completo desde la tablet en menos de 10 min |
| **3** | Hoja de vida digital: vista con pestañas, historial como vista unificada, cronograma, documentos, novedades, carga de hojas de vida escaneadas | El historial muestra mantenimientos y calibraciones existentes sin copiar nada |
| **4** | Reporte FOR-005 en borrador: carga automática de datos del equipo, checklist por plantilla, repuestos, evidencias | Diligenciar un preventivo real en tablet sin escribir datos del equipo |
| **5** | Firmas y PDF FOR-005: captura en canvas, bloqueo tras firmar, PDF con hash, anulación con reemplazo | Firmar en celular, descargar e imprimir; intentar editar un firmado y que el sistema lo impida |
| **6** | PDF FOR-003 + cálculo automático de próximas fechas + indicadores del panel de equipos | El PDF de hoja de vida es aceptado por Calidad comparándolo con el formato físico |

**Fases posteriores (backlog):** firma remota por enlace, modo offline (PWA) para zonas sin señal, OCR de hojas de vida escaneadas, migración masiva desde el Excel `LSPC-GMT-GPM-FOR-001`.

## 6. Criterios de aceptación globales

- Ningún dato del equipo se escribe dos veces.
- Ningún registro histórico se elimina físicamente.
- Ningún documento firmado se puede modificar.
- Todo PDF indica código y versión de formato y se puede verificar con su hash.
- Ningún dato ficticio en fichas técnicas; vacío o N/A cuando no se conoce.
- Ningún botón sin funcionalidad real en backend.
- Funciona en escritorio y tablet; la firma funciona en celular.
- Tests de aislamiento entre laboratorios para cada tabla nueva, igual que los existentes.

---

## 7. Prompt para Claude Code — Fase 1 (auditoría y diseño)

Copiar en Claude Code, dentro del repositorio, en una rama `docs/diseno-hojas-de-vida`:

```text
Trabaja desde develop actualizado (git pull), en la rama docs/diseno-hojas-de-vida.
Lee docs/24-especificacion-hojas-de-vida-mantenimiento-firmas.md y los formatos en
docs/formatos/. Esta tarea es SOLO de análisis y diseño: no modifiques código, modelos
ni migraciones.

Entrega un documento docs/25-diseno-tecnico-hojas-de-vida.md que contenga:

1. Mapa de lo existente: modelos, servicios, endpoints y componentes de frontend de
   equipos, mantenimientos, calibraciones, documentos y reportes que este desarrollo
   va a tocar o reutilizar, con rutas de archivo.
2. Modelo de datos final: valida o corrige la sección 4 de la especificación contra el
   esquema real. Para cada cambio, indica la migración Alembic que lo hará y cómo se
   migran los datos existentes (por ejemplo, equipos.fabricante en texto hacia la tabla
   fabricantes, y repuestos_utilizados en texto hacia mantenimiento_repuestos) sin
   perder información.
3. Reconciliación de estados: cómo encajan los estados actuales de mantenimiento
   (incluida la migración 0011) con borrador, pendiente_firmas, firmado y anulado, y
   cómo encaja la frecuencia actual con cronograma_metrologico.
4. Diseño de la vista de historial unificado y su consulta.
5. Diseño del flujo de firma: endpoints, validaciones, cuándo se congela el snapshot,
   cómo se calcula el hash y cómo se impide editar un reporte firmado (en el servicio
   y con una restricción en base de datos).
6. Wireframes en texto de: formulario de ficha técnica por pestañas, hoja de vida,
   formulario FOR-005 y pantalla de firma en celular.
7. Riesgos, dudas abiertas y cualquier punto donde la especificación contradiga el
   código actual.

Respeta las convenciones del proyecto: nombres en español, capas
domain/application/infrastructure/presentation, RLS por laboratorio y tests por
módulo. Los formularios del frontend usan zod 4: diseña los esquemas con su API
actual y con todos los mensajes de error en español. Si algo de la especificación te parece incorrecto, dilo y propón la
alternativa; no lo implementes en silencio.

Al terminar, abre un PR hacia develop solo con el documento y detente. No
empieces la Fase 2 hasta que yo apruebe el diseño.
```
