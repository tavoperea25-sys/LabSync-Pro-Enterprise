import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "../api/qrApi";
import type { EstadoIncidencia } from "../types";

const CLAVE = "incidencias-qr";

/** RF-QR-03 "Salidas" — se muestra en Mantenimientos (`MantenimientosListPage`)
 * como solicitudes pendientes de triage, no en el propio módulo QR. */
export function useIncidenciasQr() {
  return useQuery({ queryKey: [CLAVE], queryFn: api.listarIncidencias });
}

export function useActualizarEstadoIncidencia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, estado }: { id: string; estado: EstadoIncidencia }) =>
      api.actualizarEstadoIncidencia(id, estado),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}
