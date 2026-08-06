import { useQuery } from "@tanstack/react-query";

import * as api from "../api/dashboardApi";

export function useKpis() {
  return useQuery({ queryKey: ["dashboard", "kpis"], queryFn: api.obtenerKpis });
}

export function useEquiposCriticos(limite = 10) {
  return useQuery({
    queryKey: ["dashboard", "equipos-criticos", limite],
    queryFn: () => api.obtenerEquiposCriticos(limite),
  });
}

/** `enabled` es obligatorio a propósito: `/dashboard/actividad-reciente`
 * exige el permiso `auditoria.ver` (no todos los roles lo tienen) — el
 * llamador decide si el usuario actual puede verlo antes de disparar la
 * petición, en vez de dejar que un 403 esperado ensucie la consola. */
export function useActividadReciente(enabled: boolean, limite = 8) {
  return useQuery({
    queryKey: ["dashboard", "actividad-reciente", limite],
    queryFn: () => api.obtenerActividadReciente(limite),
    enabled,
  });
}
