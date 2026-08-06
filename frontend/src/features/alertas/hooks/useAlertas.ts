import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "../api/alertasApi";
import type { EstadoAlerta } from "../types";
import { useConectadoWebSocket } from "./NotificacionesProvider";

const CLAVE = "alertas";
const INTERVALO_POLLING_MS = 30_000;

/** Con el WebSocket conectado, las queries se invalidan por evento (ver
 * `NotificacionesProvider`) — el polling solo es el fallback RF-ALT-06
 * cuando el socket no está disponible. RNF-PERF-03: pagina de verdad;
 * `tamanoPagina` permite pedir una página chica (ver `NotificacionesBell`). */
export function useAlertas(estado?: EstadoAlerta, pagina?: number, tamanoPagina?: number) {
  const conectado = useConectadoWebSocket();
  return useQuery({
    queryKey: [CLAVE, "lista", estado ?? "todas", pagina ?? 1, tamanoPagina ?? 20],
    queryFn: () => api.listarAlertas(estado, pagina, tamanoPagina),
    placeholderData: (anterior) => anterior,
    refetchInterval: conectado ? false : INTERVALO_POLLING_MS,
  });
}

export function useContarActivas() {
  const conectado = useConectadoWebSocket();
  return useQuery({
    queryKey: [CLAVE, "contar-activas"],
    queryFn: api.contarActivas,
    refetchInterval: conectado ? false : INTERVALO_POLLING_MS,
  });
}

export function useMarcarLeida() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.marcarLeida(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useResolverManual() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.resolverManual(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}
