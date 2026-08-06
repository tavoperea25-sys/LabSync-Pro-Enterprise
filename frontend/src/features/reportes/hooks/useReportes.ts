import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useConectadoWebSocket } from "@/features/alertas/hooks/NotificacionesProvider";

import * as api from "../api/reportesApi";
import type { FiltrosReporte, FormatoReporte, TipoReporte } from "../types";

const CLAVE = "reportes";
const INTERVALO_POLLING_MS = 15_000;

export function useTiposReporte() {
  return useQuery({ queryKey: [CLAVE, "tipos"], queryFn: api.listarTiposReporte });
}

/** Con el WebSocket conectado, el historial se invalida por el evento
 * `reporte.listo` (ver NotificacionesProvider) — el polling es solo el
 * fallback cuando el socket no está disponible, mismo criterio que
 * `useAlertas` (RF-ALT-06). */
export function useHistorialReportes() {
  const conectado = useConectadoWebSocket();
  return useQuery({
    queryKey: [CLAVE, "historial"],
    queryFn: api.listarHistorialReportes,
    refetchInterval: conectado ? false : INTERVALO_POLLING_MS,
  });
}

export function useGenerarReporte() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tipo, formato, filtros }: { tipo: TipoReporte; formato: FormatoReporte; filtros: FiltrosReporte }) =>
      api.generarReporte(tipo, formato, filtros),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useDescargarReporte() {
  return useMutation({
    mutationFn: async ({ id, nombreArchivo }: { id: string; nombreArchivo: string }) => {
      const { url } = await api.obtenerUrlDescarga(id);
      const enlace = document.createElement("a");
      enlace.href = url;
      enlace.download = nombreArchivo;
      document.body.appendChild(enlace);
      enlace.click();
      enlace.remove();
    },
  });
}
