import { History } from "lucide-react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/shared/components/ui/empty-state";
import { Skeleton } from "@/shared/components/ui/skeleton";

import { useActividadReciente } from "../hooks/useDashboard";

// Espejo de los literales `accion=` usados en cada `*_service.py` a través
// de todos los módulos — ver docs/07-reglas-de-negocio.md RN-AUD-02. Un
// valor sin traducir cae al texto crudo (snake_case) en vez de romper, pero
// se mantiene esta lista al día para que eso sea la excepción, no la regla.
//
// `generica: true` -> se compone como "{accion} {entidad}" (ej. "creó" +
// "un equipo"). Las demás ya son una frase completa por sí solas — muchas
// de estas acciones solo existen para UN `entidad_tipo` específico en el
// backend, así que anteponer la etiqueta genérica de esa entidad sería
// redundante ("eliminó un área en una categoría/área") o gramaticalmente
// incorrecto ("actualizó los datos de el laboratorio").
const ETIQUETAS_ACCION: Record<string, { texto: string; generica?: boolean }> = {
  crear: { texto: "creó", generica: true },
  actualizar: { texto: "actualizó", generica: true },
  eliminar: { texto: "eliminó", generica: true },
  crear_categoria: { texto: "creó una categoría de equipo" },
  actualizar_categoria: { texto: "actualizó una categoría de equipo" },
  eliminar_categoria: { texto: "eliminó una categoría de equipo" },
  crear_area: { texto: "creó un área" },
  actualizar_area: { texto: "actualizó un área" },
  eliminar_area: { texto: "eliminó un área" },
  actualizar_metadatos: { texto: "actualizó los metadatos de un documento" },
  actualizar_institucion: { texto: "actualizó los datos del laboratorio" },
  actualizar_umbrales: { texto: "actualizó los umbrales de alerta" },
  actualizar_politica_password: { texto: "actualizó la política de contraseña" },
  actualizar_mapeo_estados_mantenimiento: { texto: "actualizó la configuración de mantenimientos" },
  actualizar_perfil_propio: { texto: "actualizó su perfil" },
  restaurar: { texto: "restauró", generica: true },
  purgar: { texto: "purgó", generica: true },
  aprobar: { texto: "aprobó", generica: true },
  rechazar: { texto: "rechazó", generica: true },
  corregir: { texto: "corrigió", generica: true },
  renombrar: { texto: "renombró", generica: true },
  mover: { texto: "movió", generica: true },
  copiar: { texto: "copió", generica: true },
  nueva_version: { texto: "subió una nueva versión de un documento" },
  iniciar: { texto: "inició", generica: true },
  cerrar: { texto: "cerró", generica: true },
  cancelar: { texto: "canceló", generica: true },
  generar: { texto: "generó un reporte" },
  generar_recurrente: { texto: "generó automáticamente el siguiente mantenimiento" },
  solicitar_async: { texto: "solicitó la generación de un reporte" },
  descargar: { texto: "descargó", generica: true },
  exportar_datos_tenant: { texto: "exportó los datos del laboratorio" },
  desactivar: { texto: "desactivó un usuario" },
  activar: { texto: "activó un usuario" },
  cambiar_password_propio: { texto: "cambió su contraseña" },
  asignar_roles: { texto: "cambió los roles de un usuario" },
  cerrar_sesion: { texto: "cerró una sesión" },
};

const ETIQUETAS_ENTIDAD: Record<string, string> = {
  equipo: "un equipo",
  documento: "un documento",
  calibracion: "una calibración",
  mantenimiento: "un mantenimiento",
  usuario: "un usuario",
  laboratorio: "el laboratorio",
  configuracion_laboratorio: "la configuración",
  referencia_equipo: "una categoría/área",
  reporte: "un reporte",
  evento_calendario: "un evento del calendario",
};

function describirActividad(accion: string, entidadTipo: string): string {
  const info = ETIQUETAS_ACCION[accion];
  if (!info) return `${accion} ${entidadTipo}`;
  if (!info.generica) return info.texto;
  return `${info.texto} ${ETIQUETAS_ENTIDAD[entidadTipo] ?? entidadTipo}`;
}

function iniciales(nombre: string): string {
  const partes = nombre.trim().split(/\s+/);
  return ((partes[0]?.[0] ?? "") + (partes[1]?.[0] ?? "")).toUpperCase();
}

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

export function ActivityTimeline({ puedeVer }: { puedeVer: boolean }) {
  const { data: actividad, isLoading } = useActividadReciente(puedeVer);

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-ink-soft" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-ink">Historial de actividad</h2>
        </div>
        {puedeVer && (
          <Link to="/auditoria" className="text-xs font-semibold text-primary-600 hover:text-primary-900">
            Ver auditoría →
          </Link>
        )}
      </div>

      {!puedeVer && (
        <p className="px-2 py-6 text-center text-sm text-ink-soft">
          Tu rol no tiene acceso a la bitácora de auditoría del laboratorio.
        </p>
      )}

      {puedeVer && isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      )}

      {puedeVer && !isLoading && (!actividad || actividad.length === 0) && (
        <EmptyState icon={History} title="Sin actividad reciente" description="Todavía no hay nada que mostrar." />
      )}

      {puedeVer && !isLoading && actividad && actividad.length > 0 && (
        <ul>
          {actividad.map((item, i) => (
            <li
              key={i}
              className="flex gap-3 border-b border-border py-2.5 last:border-0 last:pb-0 first:pt-0"
            >
              <div
                className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full font-display text-[11px] font-bold ${
                  item.usuario_nombre ? "bg-primary-tint text-primary-900" : "bg-surface-alt text-ink-soft"
                }`}
              >
                {item.usuario_nombre ? iniciales(item.usuario_nombre) : "SYS"}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-ink">
                  <strong className="font-semibold">{item.usuario_nombre ?? "Sistema"}</strong>{" "}
                  {describirActividad(item.accion, item.entidad_tipo)}
                </p>
                <p className="text-xs text-ink-soft">{formatearFecha(item.creado_en)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
