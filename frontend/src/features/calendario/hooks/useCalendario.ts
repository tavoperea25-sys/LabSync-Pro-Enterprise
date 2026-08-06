import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as api from "../api/calendarioApi";
import type { FiltrosCalendario } from "../api/calendarioApi";
import type { DatosEventoCalendario } from "../types";

const CLAVE = "calendario";

export function useEventos(filtros: FiltrosCalendario) {
  return useQuery({
    queryKey: [CLAVE, filtros],
    queryFn: () => api.listarEventos(filtros),
  });
}

export function useCrearEvento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (datos: DatosEventoCalendario) => api.crearEvento(datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useActualizarEvento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, datos }: { id: string; datos: DatosEventoCalendario }) =>
      api.actualizarEvento(id, datos),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}

export function useEliminarEvento() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.eliminarEvento(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [CLAVE] }),
  });
}
